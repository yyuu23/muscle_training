"""
Agent orchestrator (plan §7.1 / §7.2)

Fixed task flows — no free-form multi-agent loops:
- explicit entry points (generate plan / weekly review / record form)
  skip intent classification and go straight to their flow;
- only free chat classifies intent;
- every model call counts against the budget and is recorded in
  model_runs with the prompt version;
- at most one repair attempt per output.

Model outputs are validated (structure + citations + domain) before
they are ever shown or saved; plans are never auto-activated.
"""

import hashlib
import logging
from pathlib import Path
from uuid import UUID, uuid4

from sqlalchemy.ext.asyncio import AsyncSession

from app.agent.context_builder import KnowledgeEvidence, build_context
from app.agent.limits import BudgetTracker, record_model_run, reserve_budget
from app.agent.output_validation import (
    build_repair_prompt,
    check_citations,
    parse_structured,
)
from app.agent.schemas import (
    CoachAnswer,
    CoachResponse,
    IntentClassification,
    MemoryCandidateExtraction,
    PlanCandidate,
    WorkoutDraft,
)
from app.agent.tools import AgentTools
from app.api.errors import ApiError, ErrorCode
from app.config import get_settings
from app.providers import get_chat_provider
from app.providers.interfaces import ChatMessage, ChatRequest

logger = logging.getLogger(__name__)

PROMPTS_DIR = Path(__file__).parent / "prompts"

SYSTEM_PROMPT_VERSION = "system-v1"


def load_prompt(name: str) -> str:
    """Load a prompt file; version = content hash prefix."""
    path = PROMPTS_DIR / f"{name}.md"
    return path.read_text(encoding="utf-8")


def prompt_version(name: str) -> str:
    content = load_prompt(name)
    return f"{name}-v1:{hashlib.sha256(content.encode()).hexdigest()[:8]}"


class Orchestrator:
    """Controlled workflow executor."""

    def __init__(self, db: AsyncSession, user_id: UUID, *, request_id: str | None = None):
        self.db = db
        self.user_id = user_id
        self.request_id = request_id or str(uuid4())
        self.settings = get_settings()
        self.chat = get_chat_provider()
        self.budget = BudgetTracker()

    # ------------------------------------------------------------------
    # Model call plumbing
    # ------------------------------------------------------------------

    async def _call_model(self, operation: str, prompt_name: str, user_payload: str, *, json_output: bool = True) -> str:
        """One budgeted model call, recorded in model_runs."""
        self.budget.check_timeout()
        self.budget.check_model_call()
        await reserve_budget(self.db, 10)  # reserve an estimate; settle below

        version = prompt_version(prompt_name)
        messages = [
            ChatMessage(role="system", content=load_prompt("system")),
            ChatMessage(role="system", content=load_prompt(prompt_name)),
            ChatMessage(role="user", content=user_payload),
        ]
        request = ChatRequest(messages=messages, operation=operation, response_format_json=json_output)
        result = await self.chat.generate(request)

        self.budget.record_model_call(
            input_tokens=result.usage.input_tokens,
            output_tokens=result.usage.output_tokens,
            cost_fen=result.usage.estimated_cost_fen,
        )
        record_model_run(
            self.db,
            user_id=self.user_id,
            operation=operation,
            provider=self.settings.model_provider,
            model=getattr(self.chat, "model", self.settings.default_chat_model),
            prompt_version=version,
            input_tokens=result.usage.input_tokens,
            output_tokens=result.usage.output_tokens,
            estimated_cost_fen=result.usage.estimated_cost_fen,
            latency_ms=(result.raw or {}).get("latency_ms", 0),
        )
        await self.db.commit()
        return result.content

    async def _validated_call(
        self,
        operation: str,
        prompt_name: str,
        user_payload: str,
        model_cls,
        *,
        citation_check=None,
    ):
        """Model call + structure validation + one repair."""
        raw = await self._call_model(operation, prompt_name, user_payload)
        parsed, error = parse_structured(raw, model_cls)

        if error is None and citation_check is not None:
            error = await citation_check(parsed)

        if error is not None:
            # Single repair attempt (plan §4.4 repair_output)
            if self.budget.model_calls < self.budget.max_model_calls:
                repair_payload = build_repair_prompt(load_prompt(prompt_name), raw, error)
                raw = await self._call_model(operation, "repair_output", repair_payload)
                parsed, error = parse_structured(raw, model_cls)
                if error is None and citation_check is not None:
                    error = await citation_check(parsed)

        if error is not None:
            raise ApiError(
                ErrorCode.MODEL_OUTPUT_INVALID,
                f"模型输出未通过校验: {error}",
                {"operation": operation},
            )
        return parsed

    # ------------------------------------------------------------------
    # Free chat (plan §7.2)
    # ------------------------------------------------------------------

    async def handle_chat(self, message: str, conversation_id: UUID | None = None) -> CoachResponse:
        """Free chat: classify once, then run the matched flow."""
        # Persist the user message
        conversation_id = await self._ensure_conversation(conversation_id)
        await self._append_message(conversation_id, "user", message)

        classification = await self._validated_call(
            "classify_intent",
            "classify_intent",
            message,
            IntentClassification,
        )

        if classification.intent == "needs_clarification":
            return CoachResponse(
                status="needs_input",
                answer_markdown=classification.clarification_question or "请补充更多信息。",
                missing_fields=classification.missing_fields,
                request_id=self.request_id,
            )

        if classification.intent == "parse_workout":
            return await self._flow_parse_workout(conversation_id, message)

        if classification.intent in ("generate_plan", "adjust_plan"):
            return CoachResponse(
                status="needs_input",
                answer_markdown="计划生成请使用计划页面的「生成计划」入口，那里会使用已审核模板和你的最新档案。",
                request_id=self.request_id,
            )

        if classification.intent == "discuss_nutrition":
            answer = await self._flow_answer(conversation_id, message, knowledge_query=message)
            return answer

        # explain_exercise / ask_knowledge / general_chat
        return await self._flow_answer(conversation_id, message, knowledge_query=message)

    async def _flow_answer(self, conversation_id: UUID, message: str, *, knowledge_query: str | None) -> CoachResponse:
        """Answer flow with knowledge retrieval and citation validation."""
        evidence: list[KnowledgeEvidence] = []
        retrieved_ids: list[UUID] = []

        if knowledge_query:
            tools = AgentTools(self.db, self.user_id, self.budget)
            try:
                chunks = await tools.search_knowledge(knowledge_query)
            except ApiError:
                chunks = []
            for c in chunks:
                evidence.append(
                    KnowledgeEvidence(
                        chunk_id=c["chunk_id"],
                        title=c["title"],
                        start_ms=c.get("start_ms"),
                        end_ms=c.get("end_ms"),
                        text=c["text"],
                    )
                )
                retrieved_ids.append(UUID(c["chunk_id"]))

        context = await build_context(
            self.db,
            self.user_id,
            task_type="answer_question",
            request_id=self.request_id,
            knowledge=evidence,
            max_context_tokens=self.settings.max_context_tokens,
        )

        payload = {
            "question": message,
            "context": {
                "profile": context.confirmed_profile,
                "constraints": context.confirmed_constraints,
                "active_plan": context.active_plan_summary,
                "recent_training": context.recent_training_summary,
            },
            "evidence": [
                {
                    "chunk_id": e.chunk_id,
                    "title": e.title,
                    "start_ms": e.start_ms,
                    "end_ms": e.end_ms,
                    "text": e.text,
                }
                for e in evidence
            ],
        }
        import json as _json

        async def citation_check(answer: CoachAnswer) -> str | None:
            if not answer.citations:
                return None
            return await check_citations(
                self.db, self.user_id, retrieved_ids,
                [c.model_dump() for c in answer.citations],
            )

        answer = await self._validated_call(
            "answer_question",
            "answer_question",
            _json.dumps(payload, ensure_ascii=False),
            CoachAnswer,
            citation_check=citation_check,
        )

        await self._append_message(conversation_id, "assistant", answer.answer_markdown, evidence_refs=[c.chunk_id for c in answer.citations])

        return CoachResponse(
            status=answer.status,
            answer_markdown=answer.answer_markdown,
            citations=answer.citations,
            missing_fields=answer.missing_fields,
            proposed_actions=[],
            data_cutoff_at=context.data_cutoff_at.isoformat(),
            request_id=self.request_id,
        )

    async def _flow_parse_workout(self, conversation_id: UUID, message: str) -> CoachResponse:
        """Natural-language workout logging: preview draft, never direct save."""
        from sqlalchemy import select

        from app.db.models.catalog import Exercise

        exercises = (
            await self.db.execute(
                select(Exercise).where(Exercise.review_status == "approved").limit(100)
            )
        ).scalars().all()
        names = sorted({e.name for e in exercises} | {a for e in exercises for a in (e.aliases or [])})

        import json as _json

        draft = await self._validated_call(
            "parse_workout",
            "parse_workout",
            _json.dumps({"message": message, "catalog_names": names[:200]}, ensure_ascii=False),
            WorkoutDraft,
        )

        unresolved = list(draft.unresolved_questions)
        for s in draft.sets:
            if s.ambiguous and s.ambiguity_note:
                unresolved.append(f"{s.exercise_name}: {s.ambiguity_note}")

        markdown = "已从描述中提取以下记录草稿（未保存，请确认）：\n\n"
        for s in draft.sets:
            markdown += f"- {s.exercise_name} 第{s.set_index}组：{s.load_kg or '?'}kg × {s.reps if s.reps is not None else '?'}次"
            if s.rir is not None:
                markdown += f"（RIR {s.rir}）"
            markdown += "\n"
        if unresolved:
            markdown += "\n待确认问题：\n" + "\n".join(f"- {q}" for q in unresolved)

        await self._append_message(conversation_id, "assistant", markdown)

        return CoachResponse(
            status="draft_ready" if draft.sets else "needs_input",
            answer_markdown=markdown,
            missing_fields=unresolved,
            request_id=self.request_id,
        )

    async def _flow_extract_memory(self, message: str) -> list:
        """Extract memory candidates from a user statement (plan §7.11)."""
        import json as _json

        extraction = await self._validated_call(
            "extract_memory",
            "extract_memory",
            _json.dumps({"message": message}, ensure_ascii=False),
            MemoryCandidateExtraction,
        )

        from app.modules.profiles.service import ProfileService

        service = ProfileService(self.db)
        created = []
        for candidate in extraction.candidates:
            row = await service.create_candidate(
                self.user_id,
                proposed_fact=candidate.proposed_fact,
                source_kind=candidate.source_kind,
                source_ref=None,
                metadata={"kind": candidate.kind, "fact_key": candidate.fact_key},
            )
            created.append(str(row.id))
        return created

    # ------------------------------------------------------------------
    # Background plan generation (plan §7.4, used by the job handler)
    # ------------------------------------------------------------------

    async def generate_plan_candidate(self) -> dict:
        """Short-tx read basis → release tx → model → validated candidate."""
        from sqlalchemy import select

        from app.db.models.catalog import Exercise, TrainingTemplate
        from app.db.models.profile import Profile

        profile = (
            await self.db.execute(select(Profile).where(Profile.user_id == self.user_id))
        ).scalar_one_or_none()
        if profile is None:
            raise ApiError(ErrorCode.INSUFFICIENT_PROFILE, "档案不存在，无法生成计划")

        missing = [f for f in ("goal", "sessions_per_week", "minutes_per_session", "equipment") if getattr(profile, f) in (None, [], "")]
        if missing:
            raise ApiError(
                ErrorCode.INSUFFICIENT_PROFILE,
                "档案缺少必要字段，无法生成计划",
                {"missing_fields": missing},
            )

        templates = (
            await self.db.execute(
                select(TrainingTemplate)
                .where(TrainingTemplate.review_status == "approved")
                .where(TrainingTemplate.sessions_per_week == profile.sessions_per_week)
            )
        ).scalars().all()

        settings = self.settings
        if settings.python_env == "production":
            templates = [t for t in templates if not t.fixture]
        if not templates:
            raise ApiError(ErrorCode.CONTENT_NOT_READY, "没有适用的已审核模板，内容未就绪")

        template = templates[0]

        allowed = (
            await self.db.execute(
                select(Exercise).where(Exercise.review_status == "approved").limit(100)
            )
        ).scalars().all()
        if settings.python_env == "production":
            allowed = [e for e in allowed if not e.fixture]
        allowed_ids = set(template.allowed_exercise_ids or [])
        if allowed_ids:
            allowed = [e for e in allowed if e.id in allowed_ids]

        context = await build_context(
            self.db,
            self.user_id,
            task_type="generate_plan",
            request_id=self.request_id,
            max_context_tokens=self.settings.max_context_tokens,
        )

        import json as _json

        payload = {
            "profile": {
                "goal": profile.goal,
                "training_experience_months": profile.training_experience_months,
                "sessions_per_week": profile.sessions_per_week,
                "minutes_per_session": profile.minutes_per_session,
                "available_weekdays": profile.available_weekdays,
                "equipment": profile.equipment,
                "available_load_increments": profile.available_load_increments,
            },
            "constraints": context.confirmed_constraints,
            "unresolved_reports": context.unresolved_recent_reports,
            "template": {
                "slug": template.slug,
                "sessions_per_week": template.sessions_per_week,
                "allowed_set_ranges": template.allowed_set_ranges,
                "allowed_rep_ranges": template.allowed_rep_ranges,
                "allowed_rest_ranges": template.allowed_rest_ranges,
                "target_rir_ranges": template.target_rir_ranges,
            },
            "allowed_exercises": [
                {
                    "slug": e.slug,
                    "name": e.name,
                    "metric_type": e.metric_type,
                    "load_mode": e.load_mode,
                    "equipment_tags": e.equipment_tags,
                    "approved_alternatives": e.approved_alternatives,
                }
                for e in allowed
            ],
            "recent_training": context.recent_training_summary,
        }

        # Background generation: 1 generate + ≤1 repair, 180s budget
        self.budget = BudgetTracker(
            max_model_calls=2, max_tool_calls=0, timeout_seconds=self.settings.plan_job_timeout_seconds
        )

        candidate = await self._validated_call(
            "generate_plan",
            "generate_plan",
            _json.dumps(payload, ensure_ascii=False),
            PlanCandidate,
        )

        return {
            "candidate": candidate.model_dump(),
            "template_id": str(template.id),
            "template_version": template.content_version,
            "basis_profile_version": profile.version,
            "basis_planning_revision": context.planning_revision,
            "basis_active_plan_id": context.active_plan_id,
        }

    # ------------------------------------------------------------------
    # Conversation persistence
    # ------------------------------------------------------------------

    async def _ensure_conversation(self, conversation_id: UUID | None) -> UUID:
        from app.db.models.operations import Conversation

        if conversation_id is not None:
            return conversation_id
        conversation = Conversation(user_id=self.user_id, title=None)
        self.db.add(conversation)
        await self.db.commit()
        await self.db.refresh(conversation)
        return conversation.id

    async def _append_message(
        self, conversation_id: UUID, role: str, content: str, *, evidence_refs: list[str] | None = None
    ) -> None:
        from app.db.models.operations import Message

        self.db.add(
            Message(
                user_id=self.user_id,
                conversation_id=conversation_id,
                role=role,
                content=content,
                evidence_refs=evidence_refs or [],
            )
        )
        await self.db.commit()
