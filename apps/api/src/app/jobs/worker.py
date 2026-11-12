"""
Job worker (plan §9.1 / §2.3)

Standalone process: python -m app.jobs.worker

- Claims jobs with FOR UPDATE SKIP LOCKED; lease committed at once.
- Renews leases every 20s while running.
- Media concurrency 1; generation concurrency 2.
- Restarts resume known external tasks via external_task_id.
"""

import asyncio
import contextlib
import logging
import signal

from app.config import get_settings
from app.db.session import async_session_maker
from app.jobs.handlers import GENERATION_JOBS, HANDLERS
from app.jobs.queue import claim_jobs, reclaim_expired_jobs, renew_lease, resume_waiting_jobs

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(name)s %(levelname)s %(message)s")
logger = logging.getLogger("worker")

shutdown = asyncio.Event()


def _request_shutdown(signum, frame) -> None:
    logger.info("signal %s received, shutting down", signum)
    shutdown.set()


class Worker:
    """Polls the job queue and executes handlers."""

    def __init__(self):
        self.settings = get_settings()
        self._active_tasks: set[asyncio.Task] = set()

    async def run(self) -> None:
        logger.info(
            "worker started (media=1, generation=%d, poll=%ds)",
            self.settings.worker_generation_concurrency,
            self.settings.worker_poll_interval_seconds,
        )
        while not shutdown.is_set():
            try:
                await self._tick()
            except Exception:  # noqa: BLE001
                logger.exception("worker tick failed")
            try:
                await asyncio.wait_for(shutdown.wait(), timeout=self.settings.worker_poll_interval_seconds)
            except TimeoutError:
                pass

        logger.info("waiting for %d in-flight jobs", len(self._active_tasks))
        if self._active_tasks:
            await asyncio.wait(self._active_tasks, timeout=60)

    async def _tick(self) -> None:
        from sqlalchemy import select as _select  # noqa: F401

        async with async_session_maker() as db:
            # Recover crashed workers' leases and resume external waits
            await reclaim_expired_jobs(db)
            await resume_waiting_jobs(db)

        # One media job slot
        if self._media_slots_free():
            await self._claim_and_run(list(HANDLERS))

        # Generation job slots
        for _ in range(self._generation_slots_free()):
            await self._claim_and_run(list(GENERATION_JOBS))

    def _media_slots_free(self) -> bool:
        media_active = sum(1 for t in self._active_tasks if getattr(t, "job_group", None) == "media")
        return media_active < self.settings.worker_media_concurrency

    def _generation_slots_free(self) -> int:
        generation_active = sum(1 for t in self._active_tasks if getattr(t, "job_group", None) == "generation")
        free = self.settings.worker_generation_concurrency - generation_active
        return max(0, free)

    async def _claim_and_run(self, job_types: list[str]) -> None:
        from app.jobs.handlers import MEDIA_JOBS

        async with async_session_maker() as db:
            jobs = await claim_jobs(db, limit=1, types=job_types)
        for job in jobs:
            group = "media" if job.type in MEDIA_JOBS else "generation"
            task = asyncio.create_task(self._execute(job.id, job.type, group))
            task.job_group = group  # type: ignore[attr-defined]
            self._active_tasks.add(task)
            task.add_done_callback(self._active_tasks.discard)

    async def _execute(self, job_id, job_type: str, group: str) -> None:
        handler = HANDLERS.get(job_type)
        if handler is None:
            logger.error("no handler for job type %s", job_type)
            return

        from sqlalchemy import select

        from app.db.models.operations import Job

        renewal_stop = asyncio.Event()
        renewal_task = asyncio.create_task(self._renew_loop(job_id, renewal_stop))
        try:
            async with async_session_maker() as db:
                job = (await db.execute(select(Job).where(Job.id == job_id))).scalar_one_or_none()
                if job is None:
                    return
                logger.info("running job %s type=%s attempt=%d", job_id, job_type, job.attempts)
                await handler(db, job)
                logger.info("job %s finished", job_id)
        except Exception:  # noqa: BLE001
            logger.exception("job %s crashed", job_id)
            async with async_session_maker() as db:
                from app.jobs.queue import fail_job

                await fail_job(db, job_id, error_code="HANDLER_CRASH")
        finally:
            renewal_stop.set()
            with contextlib.suppress(asyncio.CancelledError):
                await renewal_task

    async def _renew_loop(self, job_id, stop: asyncio.Event) -> None:
        settings = get_settings()
        while not stop.is_set():
            try:
                await asyncio.wait_for(stop.wait(), timeout=settings.worker_lease_renew_seconds)
            except TimeoutError:
                pass
            else:
                return
            try:
                async with async_session_maker() as db:
                    await renew_lease(db, job_id)
            except Exception:  # noqa: BLE001
                logger.warning("lease renewal failed for %s", job_id)
                return


def main() -> None:
    signal.signal(signal.SIGINT, _request_shutdown)
    signal.signal(signal.SIGTERM, _request_shutdown)
    worker = Worker()
    asyncio.run(worker.run())


if __name__ == "__main__":
    main()
