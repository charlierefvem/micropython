# Finite-state-machine support for cooperative MicroPython tasks.
#
# This module provides a lightweight base class for state-machine tasks. It
# tracks the current and previously run states and provides a transition helper
# for use by subclasses.
#
# Original work:
#     Copyright (c) 2026 Charlie Refvem
#     Released under the GNU General Public License, version 3.0.
#
# This software is intended for educational use, but its use is not limited
# thereto.
#
# This program is free software: you can redistribute it and/or modify it under
# the terms of the GNU General Public License as published by the Free Software
# Foundation, version 3.0.
#
# This program is distributed in the hope that it will be useful, but WITHOUT
# ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS
# FOR A PARTICULAR PURPOSE. See the GNU General Public License for more
# details.

import micropython


# Base class for finite-state-machine cooperative tasks.
class FSM:

    # Store the initial and previously-run state for subclasses.
    def __init__(self, initial_state=0):
        # The next state to run
        self._state: int = initial_state

        # The last state ran
        self._last_state: int = 0

    # Placeholder run method for subclasses to override.
    def run(self):
        pass

    # Move to a new state and return the state that just finished.
    @micropython.native
    def transition_to(self, new_state) -> int:
        if new_state is not None:
            self._state, self._last_state = new_state, self._state
        return self._last_state
