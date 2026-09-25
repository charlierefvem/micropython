# Compact task and state event tracing for MicroPython.
#
# This module implements a fixed-size buffer which stores task identifiers,
# state identifiers, and 16-bit event data in a compact byte-packed format. It
# supports optional overwrite behavior and formatted trace output.
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

from struct import pack_into, unpack_from

from micropython import const

EVENT_STATE_CHANGE = const(1)
EVENT_MODE_CHANGE = const(2)
EVENT_FAULT = const(3)
_ITEM_SIZE = const(4)
_ITEM_CODE = "<BBH"


# Fixed-size trace buffer for compact task/state event logging.
class TraceBuffer:
    # Allocates storage for trace items packed as task, state, and halfword.
    #
    # Each item is stored as raw bytes organized as:
    #   b0    : Task ID
    #   b1    : State ID for the task
    #   b2:b3 : Logged halfword of data representing one of the following:
    #            - A timestamp
    #            - An encoded event ID
    #            - Any 16-bit value useful for logging
    def __init__(self, length):
        if length <= 0:
            raise ValueError("TraceBuffer length must be greater than zero")

        # The length (max number of items) for the buffer
        self._length = length
        # The capacity (total number of bytes) for the buffer
        self._capacity = _ITEM_SIZE*self._length
        # The buffer itself
        self._buffer = bytearray(self._capacity)
        # The offset from the start of the buffer for the next item to be
        # placed
        self._offset = 0
        # The present number of items in the buffer
        self._num_in = 0

    # Store an item if there is space, optionally overwriting the oldest item.
    def log(self, task_id, state_id, halfword, overwrite=True):
        if (self._num_in >= self._length) and not overwrite:
            return False
        pack_into(_ITEM_CODE, self._buffer, self._offset,
                  task_id, state_id, halfword)
        self._num_in = min(self._num_in + 1, self._length)
        self._offset = (self._offset + _ITEM_SIZE) % self._capacity
        return True

    # Pop and return the most recently logged item, if one exists.
    def get(self):
        if self._num_in > 0:
            self._offset = (self._offset - _ITEM_SIZE) % self._capacity
            self._num_in -= 1
            return unpack_from(_ITEM_CODE, self._buffer, self._offset)

    # Print the buffered trace items as task, state, and value hex columns.
    def dump(self):
        print("Trace:")
        for _ in range(self._num_in):
            print("{:#04x} {:#04x} {:#06x}".format(*self.get()))
