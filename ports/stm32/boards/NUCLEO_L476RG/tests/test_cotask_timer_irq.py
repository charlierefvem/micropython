"""Run the priority scheduler with triggers from a real hardware timer ISR.

Copy this file to the board, then run:
    import test_cotask_timer_irq
    test_cotask_timer_irq.main()

Uses Timer 4 by default. Run with the application stopped and that timer free,
or pass main(timer_id=...) to select another unused timer. Each pass takes
about two seconds. Both profiled and unprofiled triggered tasks are exercised.

The light-load pass checks ordinary operation; the busy pass also checks
coalescing. Executions must match newly queued requests, rather than every
timer interrupt. This integration test complements the deterministic race
tests in test_cotask_irq.py; it cannot prove every possible IRQ interleaving.
"""

from array import array

import cotask
import micropython
import pyb
import utime


def _work(runs, index, work_us):
    while True:
        utime.sleep_us(work_us + (runs[index] % 5) * 25)
        runs[index] += 1
        yield


class _TimerTriggers:
    # A closure capturing five variables plus the timer argument needs a heap
    # allocation in MicroPython's call machinery, before its body even starts.
    # Keep callback state on an instance and bind its method before the IRQ.
    def __init__(self, profiled, unprofiled, counts):
        self.profiled = profiled
        self.unprofiled = unprofiled
        self.counts = counts
        self.go_profiled = profiled.go
        self.go_unprofiled = unprofiled.go

    def tick(self, timer):
        # Foreground scheduling cannot preempt this ISR. A false flag means
        # this call queues a new run; a true flag means it coalesces.
        if self.profiled.go_flag:
            self.counts[2] += 1
        else:
            self.counts[1] += 1
        self.go_profiled()
        if self.unprofiled.go_flag:
            self.counts[4] += 1
        else:
            self.counts[3] += 1
        self.go_unprofiled()
        self.counts[0] += 1
        self.counts[5] = utime.ticks_ms()


def _run_pass(timer_id, frequency, work_us, duration_ms, expect_coalescing):
    print("\nTimer ISR: {} Hz, {} us/task, {} ms".format(
        frequency, work_us, duration_ms))

    task_list = cotask.TaskList()
    runs = array("I", [0, 0, 0, 0])
    profiled = cotask.Task(_work(runs, 0, work_us), name="IRQ P",
                           priority=3, period=None, profile=True)
    unprofiled = cotask.Task(_work(runs, 1, work_us), name="IRQ U",
                             priority=3, period=None, profile=False)
    periodic = cotask.Task(_work(runs, 2, 100), name="Periodic",
                           priority=2, period=10, profile=True)
    idle = cotask.Task(_work(runs, 3, 50), name="Idle",
                       priority=0, period=0, profile=False)
    for task in (profiled, unprofiled, periodic, idle):
        task_list.append(task)

    # IRQs, P queued, P coalesced, U queued, U coalesced, last IRQ time (ms).
    counts = array("I", [0, 0, 0, 0, 0, 0])
    source = _TimerTriggers(profiled, unprofiled, counts)
    tick = source.tick

    # Check the exact callback, including its call machinery, before starting
    # hard IRQs. Failures here have a normal foreground traceback.
    micropython.heap_lock()
    try:
        tick(None)
    finally:
        micropython.heap_unlock()
    assert counts[0] == counts[1] == counts[3] == 1
    # Discard the dry-run requests and counts; all actual runs come from IRQs.
    profiled.go_flag = unprofiled.go_flag = False
    profiled._trigger_time = unprofiled._trigger_time = None
    for index in range(len(counts)):
        counts[index] = 0
    print("PASS: complete timer callback with heap locked.")

    timer = pyb.Timer(timer_id)
    try:
        start = utime.ticks_ms()
        timer.init(freq=frequency, callback=tick, hard=True)
        while utime.ticks_diff(utime.ticks_ms(), start) < duration_ms:
            task_list.pri_sched()
    finally:
        # Includes exceptions and Ctrl-C. Stop IRQs before reading results.
        timer.deinit()
    stopped = utime.ticks_ms()

    # Finish requests queued near the end of the timed interval.
    while profiled.go_flag or unprofiled.go_flag:
        task_list.pri_sched()

    assert counts[0] >= frequency * duration_ms // 2000, "Too few timer IRQs"
    assert utime.ticks_diff(stopped, counts[5]) < 100, "Timer callback stopped"
    assert counts[1] + counts[2] == counts[0]
    assert counts[3] + counts[4] == counts[0]
    assert runs[0] == counts[1], "Profiled task lost a queued request"
    assert runs[1] == counts[3], "Unprofiled task lost a queued request"
    assert profiled.profile()[3] == runs[0]
    assert profiled._latency_stats._n == runs[0]
    assert unprofiled.profile()[3:] == (None,) * 7
    if expect_coalescing:
        assert counts[2] + counts[4] > 0, "Busy pass did not cause coalescing"
    else:
        assert runs[2] > 2 and runs[3] > 2, "Background tasks did not run"

    print("IRQs: {}; queued/executed P: {}/{}; U: {}/{}".format(
        counts[0], counts[1], runs[0], counts[3], runs[1]))
    print("Coalesced triggers: P = {}; U = {}".format(counts[2], counts[4]))
    print(task_list.profile(), end="")
    print("PASS: hardware timer triggers and queued task executions agree.")


def main(timer_id=4, duration_ms=2000):
    if duration_ms < 500 or duration_ms > 10000:
        raise ValueError("duration_ms must be between 500 and 10000")
    micropython.alloc_emergency_exception_buf(100)
    print("P = profiled; U = unprofiled; timer callback uses hard IRQs.")
    _run_pass(timer_id, 100, 100, duration_ms, False)
    _run_pass(timer_id, 500, 2000, duration_ms, True)


if __name__ == "__main__":
    main()
