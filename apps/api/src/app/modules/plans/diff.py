"""
Plan diff (plan §5.4 / §8.1)

Structural diff between two plan contents for the PlanDiff component:
added/removed exercises, set/rep/load changes, with reasons when the
candidate carries them.
"""

from app.modules.plans.schemas import PlanContent


def diff_plans(old: PlanContent | None, new: PlanContent) -> dict:
    """Compute a display-ready diff between the active plan and a candidate."""
    result: dict = {
        "title_changed": old is None or old.title != new.title,
        "goal_changed": old is None or old.goal != new.goal,
        "day_changes": [],
    }

    new_by_key = {d.day_key: d for d in new.days}
    old_by_key = {d.day_key: d for d in old.days} if old else {}

    for day_key in sorted(set(old_by_key) | set(new_by_key)):
        old_day = old_by_key.get(day_key)
        new_day = new_by_key.get(day_key)

        change: dict = {"day_key": day_key, "items": []}

        if old_day is None:
            change["kind"] = "day_added"
            change["items"] = [
                {"kind": "exercise_added", "exercise_id": str(i.exercise_id)}
                for i in new_day.exercises
            ]
        elif new_day is None:
            change["kind"] = "day_removed"
        else:
            change["kind"] = "day_modified"
            old_items = {i.item_id: i for i in old_day.exercises}
            new_items = {i.item_id: i for i in new_day.exercises}

            for item_id in sorted(set(old_items) | set(new_items)):
                oi = old_items.get(item_id)
                ni = new_items.get(item_id)

                if oi is None and ni is not None:
                    change["items"].append(
                        {"kind": "exercise_added", "item_id": item_id, "exercise_id": str(ni.exercise_id)}
                    )
                elif ni is None and oi is not None:
                    change["items"].append(
                        {"kind": "exercise_removed", "item_id": item_id, "exercise_id": str(oi.exercise_id)}
                    )
                else:
                    field_changes = {}
                    for field in ("working_sets", "reps_min", "reps_max", "duration_seconds", "rest_seconds", "initial_load_kg"):
                        ov = getattr(oi, field)
                        nv = getattr(ni, field)
                        if ov != nv:
                            field_changes[field] = {"old": ov, "new": nv}
                    if field_changes:
                        change["items"].append(
                            {"kind": "exercise_modified", "item_id": item_id, "changes": field_changes}
                        )

            if new_day.estimated_minutes != (old_day.estimated_minutes if old_day else None):
                change["estimated_minutes"] = {
                    "old": old_day.estimated_minutes if old_day else None,
                    "new": new_day.estimated_minutes,
                }

        result["day_changes"].append(change)

    return result
