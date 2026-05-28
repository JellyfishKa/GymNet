from dataclasses import dataclass


SADLA_SEQUENCE = ["Standing", "TransitionDown", "Bottom", "TransitionUp"]


@dataclass(slots=True)
class SadlaState:
    phase_idx: int = 0
    reps: int = 0

    @property
    def current_phase(self) -> str:
        return SADLA_SEQUENCE[self.phase_idx]

    def apply_phase(self, new_phase: str) -> None:
        expected_idx = (self.phase_idx + 1) % len(SADLA_SEQUENCE)
        expected_phase = SADLA_SEQUENCE[expected_idx]

        if new_phase == expected_phase:
            self.phase_idx = expected_idx
            if new_phase == "Standing":
                self.reps += 1
        elif new_phase == "Neutral":
            self.phase_idx = 0
