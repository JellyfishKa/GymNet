_GROUPS: dict[str, list[str]] = {
    "PushUps": ["chest", "triceps", "shoulders"],
    "Squats": ["quadriceps", "glutes", "hamstrings"],
    "RunInPlace": ["cardio", "calves", "core"],
}


def get_muscle_groups(exercise: str | None) -> list[str] | None:
    if not exercise:
        return None
    return _GROUPS.get(exercise)
