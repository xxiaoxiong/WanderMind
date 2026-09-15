from __future__ import annotations

from wandermind.models import CognitiveState


class InvalidStateTransition(ValueError):
    pass


LEGAL_TRANSITIONS: dict[CognitiveState, set[CognitiveState]] = {
    CognitiveState.IDLE: {CognitiveState.SEEDING, CognitiveState.STOPPED, CognitiveState.FAILED},
    CognitiveState.SEEDING: {CognitiveState.WANDER, CognitiveState.STOPPED, CognitiveState.FAILED},
    CognitiveState.WANDER: {
        CognitiveState.COLLISION,
        CognitiveState.STOPPED,
        CognitiveState.FAILED,
    },
    CognitiveState.COLLISION: {
        CognitiveState.GENERATE,
        CognitiveState.WANDER,
        CognitiveState.STOPPED,
        CognitiveState.FAILED,
    },
    CognitiveState.GENERATE: {CognitiveState.SCORE, CognitiveState.WANDER, CognitiveState.FAILED},
    CognitiveState.SCORE: {
        CognitiveState.EXPLORE,
        CognitiveState.WANDER,
        CognitiveState.PERSIST,
        CognitiveState.STOPPED,
        CognitiveState.FAILED,
    },
    CognitiveState.EXPLORE: {
        CognitiveState.CRITIQUE,
        CognitiveState.PERSIST,
        CognitiveState.WANDER,
        CognitiveState.FAILED,
    },
    CognitiveState.CRITIQUE: {
        CognitiveState.PERSIST,
        CognitiveState.WANDER,
        CognitiveState.STOPPED,
        CognitiveState.FAILED,
    },
    CognitiveState.PERSIST: {CognitiveState.SURFACE, CognitiveState.WANDER, CognitiveState.FAILED},
    CognitiveState.SURFACE: {CognitiveState.STOPPED},
    CognitiveState.STOPPED: set(),
    CognitiveState.FAILED: set(),
}


class CognitiveStateMachine:
    def __init__(self, initial: CognitiveState = CognitiveState.IDLE) -> None:
        self.state = initial

    def transition(self, target: CognitiveState) -> CognitiveState:
        if target not in LEGAL_TRANSITIONS[self.state]:
            raise InvalidStateTransition(
                f"cannot transition from {self.state.value} to {target.value}"
            )
        self.state = target
        return self.state
