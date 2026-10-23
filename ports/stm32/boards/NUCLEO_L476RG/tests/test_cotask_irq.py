"""Check ISR trigger handoff and allocation-free go() on the board.

Copy this file to the board, then run:
    import test_cotask_irq
    test_cotask_irq.main()

Interrupt races use simulated IRQs for repeatable timing. The final check
calls the real go() with MicroPython's heap locked, for both profiling modes.
"""

import cotask
import micropython


class _IRQs:
    def __init__(self):
        self.enabled = True
        self.pending = None
        self.calls = 0

    def disable_irq(self):
        previous = self.enabled
        self.enabled = False
        self.calls += 1
        return previous

    def enable_irq(self, previous):
        self.enabled = previous
        if self.enabled and self.pending is not None:
            callback = self.pending
            self.pending = None
            callback()


class _Clock:
    def __init__(self):
        self.now = 100
        self.fail = False

    def ticks_us(self):
        if self.fail:
            raise RuntimeError("Simulated clock failure")
        return self.now & ((1 << 30) - 1)

    def ticks_add(self, value, delta):
        return (value + delta) & ((1 << 30) - 1)

    def ticks_diff(self, end, start):
        return ((end - start + (1 << 29)) & ((1 << 30) - 1)) - (1 << 29)


class _RaceTask(cotask.Task):
    # Request an IRQ immediately after reading the flag, before the caller
    # can clear it or update the timestamp. Disabled IRQs defer the callback.
    @property
    def go_flag(self):
        value = self._flag
        if self.interrupt is not None:
            callback = self.interrupt
            self.interrupt = None
            if self.irq.enabled:
                callback()
            else:
                self.irq.pending = callback
        return value

    @go_flag.setter
    def go_flag(self, value):
        self._flag = value


def _race_task(irq, clock, runs, profiled):
    task = _RaceTask(_work(irq, clock, runs), period=None, profile=profiled)
    task.irq = irq
    task.interrupt = None
    return task


def _work(irq, clock, runs):
    while True:
        assert irq.enabled
        runs.append(clock.now)
        clock.now += 10
        yield


def _check_handoff(irq, clock, profiled):
    runs = []
    task = _race_task(irq, clock, runs, profiled)
    assert not task.schedule()
    clock.now = 100
    task.go()
    clock.now = 150
    task.go()  # Coalesces with the first trigger and preserves its timestamp.
    assert task._trigger_time == (100 if profiled else None)

    # Request an IRQ between the flag read and clear. It must be deferred
    # until interrupts are restored and then queue a second run.
    def interrupt():
        clock.now = 220
        task.go()

    task.interrupt = interrupt
    clock.now = 200
    assert task.schedule()
    assert len(runs) == 1 and task.go_flag
    assert task._trigger_time == (220 if profiled else None)
    if profiled:
        assert task._latency_stats.mean == 120

    clock.now = 250
    assert task.schedule()
    assert len(runs) == 2 and not task.go_flag
    assert not task.schedule()
    if profiled:
        assert task._latency_stats._n == 2
        assert task._latency_stats.mean == 75
        assert task._latency_stats.max == 120

    # Preserve the caller's disabled IRQ state, including nested go() calls.
    irq.enabled = False
    assert not task.schedule()
    task.go()
    assert not irq.enabled and task.go_flag
    irq.enabled = True


def _check_go_update(irq, clock):
    task = _race_task(irq, clock, [], True)
    clock.now = 100

    def interrupt():
        clock.now = 200
        task.go()

    task.interrupt = interrupt
    task.go()
    assert task.go_flag and irq.enabled
    assert task._trigger_time == 100


def _check_wrap_and_exception(irq, clock):
    task = cotask.Task(_work(irq, clock, []), period=None, profile=True)
    clock.now = (1 << 30) - 5
    task.go()
    clock.now += 20
    assert task.schedule()
    assert task._latency_stats.mean == 20

    clock.fail = True
    try:
        task.go()
    except RuntimeError:
        pass
    else:
        raise AssertionError("Expected simulated clock failure")
    finally:
        clock.fail = False
    assert irq.enabled and not task.go_flag


def _check_timer_tasks(irq, clock):
    for period in (0, 5):
        runs = []
        task = cotask.Task(_work(irq, clock, runs), period=period, profile=True)
        calls = irq.calls
        for _ in range(4):
            clock.now = task._next_run + 100
            assert task.schedule()
        assert irq.calls == calls  # No periodic/idle processing under IRQ lock.
        assert len(runs) == task._runs == 4
        assert task._runtime_stats._n == 2
        assert task._runtime_stats.mean == 10
        if period == 0:
            assert task._latency_stats is None
        else:
            assert task._latency_stats.mean == 100


def _check_heap_locked_go():
    for profiled in (False, True):
        task = cotask.Task(iter(()), period=None, profile=profiled)
        go = task.go  # Bind the method before locking the heap.
        micropython.heap_lock()
        try:
            go()  # First trigger, including its timestamp when profiling.
            go()  # Already pending: preserve the first trigger.
        finally:
            micropython.heap_unlock()
        assert task.go_flag
        assert (task._trigger_time is not None) == profiled


def main():
    real_pyb = cotask.pyb
    real_utime = cotask.utime
    irq = _IRQs()
    clock = _Clock()
    cotask.pyb = irq
    cotask.utime = clock
    try:
        for profiled in (False, True):
            _check_handoff(irq, clock, profiled)
        _check_go_update(irq, clock)
        _check_wrap_and_exception(irq, clock)
        _check_timer_tasks(irq, clock)
    finally:
        cotask.pyb = real_pyb
        cotask.utime = real_utime
    print("PASS: trigger handoff, timestamps, coalescing, IRQ restoration, and wrap.")
    _check_heap_locked_go()
    print("PASS: go() with heap locked, profiling enabled and disabled.")


if __name__ == "__main__":
    main()
