from app.services.sadla import SadlaState

def test_sadla_sequence_reps() -> None:
    state = SadlaState()
    assert state.current_phase == "Standing"
    assert state.reps == 0

    # First repetition cycle
    state.apply_phase("TransitionDown")
    assert state.current_phase == "TransitionDown"
    
    state.apply_phase("Bottom")
    assert state.current_phase == "Bottom"
    
    state.apply_phase("TransitionUp")
    assert state.current_phase == "TransitionUp"
    
    state.apply_phase("Standing")
    assert state.current_phase == "Standing"
    assert state.reps == 1

    # Second repetition cycle (starts directly with TransitionDown)
    state.apply_phase("TransitionDown")
    assert state.current_phase == "TransitionDown"
    
    state.apply_phase("Bottom")
    assert state.current_phase == "Bottom"
    
    state.apply_phase("TransitionUp")
    assert state.current_phase == "TransitionUp"
    
    state.apply_phase("Standing")
    assert state.current_phase == "Standing"
    assert state.reps == 2

def test_sadla_neutral_reset() -> None:
    state = SadlaState()
    state.apply_phase("TransitionDown")
    assert state.current_phase == "TransitionDown"
    
    # Receive Neutral out-of-band phase
    state.apply_phase("Neutral")
    assert state.current_phase == "Standing"
    assert state.reps == 0
