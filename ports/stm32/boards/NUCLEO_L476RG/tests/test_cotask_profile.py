"""Exercise cotask profiling on the board and print both profile tables.

Copy this file to the board, then run at the REPL:
    import test_cotask_profile
    test_cotask_profile.main()

P means profiling enabled; U means profiling disabled. Each pass includes
both periodic and triggered variants, but only one idle task. The second
pass changes the idle task from profiled to unprofiled.

Unprofiled statistics, triggered periods, and idle latencies should appear
as blanks. All other statistics should contain measured values. A short guide
to interpreting the columns is printed immediately below each table.
"""

import cotask
import utime


_MIN_RUNS = 50
_TRIGGER_PERIOD_MS = 20
_TIMEOUT_MS = 5000


def _work(run_counts, index, base_us):
    while True:
        # Vary the workload so duration statistics have a visible spread.
        utime.sleep_us(base_us + (run_counts[index] % 5) * 50)
        run_counts[index] += 1
        yield


def _run_pass(profile_idle):
    print("\nIdle task profiling: " + ("enabled" if profile_idle else "disabled"))

    # Name, priority, period (ms), profiling enabled, and base workload (us).
    # Idle has the lowest priority and is the only continuously ready task.
    specs = (
        ("Periodic P", 2, 10, True, 200),
        ("Periodic U", 2, 10, False, 200),
        ("Triggered P", 1, None, True, 300),
        ("Triggered U", 1, None, False, 300),
        ("Idle P" if profile_idle else "Idle U", 0, 0, profile_idle, 100),
    )
    task_list = cotask.TaskList()
    tasks = []
    triggered = []
    run_counts = [0] * len(specs)

    for index, (name, priority, period, profile, base_us) in enumerate(specs):
        task = cotask.Task(_work(run_counts, index, base_us), name=name,
                           priority=priority, period=period, profile=profile)
        task_list.append(task)
        tasks.append(task)
        if period is None:
            triggered.append(task)

    start = utime.ticks_ms()
    next_trigger = start
    while min(run_counts) < _MIN_RUNS:
        now = utime.ticks_ms()
        if utime.ticks_diff(now, start) >= _TIMEOUT_MS:
            raise RuntimeError("Not all tasks reached the minimum run count: "
                               + str(run_counts))

        # Queue both triggered tasks; the scheduler determines when they run.
        if utime.ticks_diff(now, next_trigger) >= 0:
            for task in triggered:
                task.go()
            next_trigger = utime.ticks_add(now, _TRIGGER_PERIOD_MS)

        task_list.pri_sched()

    # Check missing values and independently confirm unprofiled tasks ran.
    for task, spec, count in zip(tasks, specs, run_counts):
        values = task.profile()
        assert len(values) == 10
        assert count >= _MIN_RUNS
        assert values[2] == spec[2]
        if spec[3]:
            assert values[3] == count
            assert values[4] > 0 and values[5] >= values[4]
            if spec[2] == 0:
                assert values[7:] == (None,) * 3
            else:
                assert all(value is not None for value in values[7:])
        else:
            assert values[3:] == (None,) * 7

    print(task_list.profile(), end="")
    print("All five tasks ran at least {} times.".format(_MIN_RUNS))


def main():
    print("P = profiled; U = unprofiled")
    _run_pass(True)
    _run_pass(False)


if __name__ == "__main__":
    main()
