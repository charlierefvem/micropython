# Base class for finite-state-machine cooperative tasks.
class Task_Base:
    
    # Store the initial and previously-run state for subclasses.
    def __init__(self, initial_state = 0):
        # The next state to run
        self._state: int   = initial_state
        
        # The last state ran
        self._last_state: int = 0

    # Placeholder run method for subclasses to override.
    def run(self):
        pass
    
    # Move to a new state and return the state that just finished.
    @micropython.native
    def transitionTo(self, new_state) -> int:
        if new_state is not None:
            self._state, self._last_state = new_state, self._state
        return self._last_state
