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
