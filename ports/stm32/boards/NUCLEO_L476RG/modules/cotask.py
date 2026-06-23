# Cooperatively scheduled task support for MicroPython.
#
# This module contains classes for running tasks in a cooperative multitasking
# system. Tasks are implemented as generators: functions or methods containing
# loops which yield control back to the scheduler. References to the tasks are
# kept in a task list, and the scheduler runs them according to the selected
# scheduling policy.
#
# Original work:
#     Copyright (c) 2017-2023 JR Ridgely
#     Released under the GNU General Public License, version 3.0.
#
# Modifications:
#     Copyright (c) 2026 Charlie Refvem
#     Modified for Cal Poly Mechatronics coursework.
#     Major changes include scheduler profiling, trigger-based tasks, revised
#     task ownership conventions, and MicroPython-focused memory optimizations.
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

import micropython                     # This shuts up incorrect warnings

from runningstats import RunningStats

import utime                           # Micropython version of time library

_PROF_HEADER = ('┌───────────┬───┬───────┬──────┬───────────────────────┬───────────────────────┐\n'
                '│           │   │       │      │     DURATION (ms)     │     LATENCY (ms)      │\n'
                '│ TASK NAME │PRI│PERIOD │ RUNS ├───────┬───────┬───────┼───────┬───────┬───────┤\n'
                '│           │   │ (ms)  │      │  AVG  │  MAX  │ STDEV │  AVG  │  MAX  │ STDEV │\n'
                '├───────────┼───┼───────┼──────┼───────┼───────┼───────┼───────┼───────┼───────┤\n')
_PROF_FOOTER = ('└───────────┴───┴───────┴──────┴───────┴───────┴───────┴───────┴───────┴───────┘\n')
_PROF_ROW_PERIODIC = ('│{:<11.11s}'    # Name
                      '│{:3d}'         # Priority
                      '│{:7.1f}'       # Period
                      '│{:6d}'         # Runs
                      '│{:7.3f}'       # Avg Duration
                      '│{:7.3f}'       # Max Latency
                      '│{:7.3f}'       # St.Dev Duration
                      '│{:7.3f}'       # Avg Latency
                      '│{:7.3f}'       # Max Latency
                      '│{:7.3f}│\n')   # St.Dev Latency
_PROF_ROW_APERIODIC = ('│{:<11.11s}'   # Name
                       '│{:3d}'        # Priority
                       '│   -   '      # (No period)
                       '│{:6d}'        # Runs
                       '│{:7.3f}'      # Avg Duration
                       '│{:7.3f}'      # Max Latency
                       '│{:7.3f}'      # St.Dev Duration
                       '│{:7.3f}'      # Avg Latency
                       '│{:7.3f}'      # Max Latency
                       '│{:7.3f}│\n')  # St.Dev Latency


# Cooperative task with scheduling and performance logging support.
#
# This class implements behavior common to tasks in a cooperative multitasking
# system running in MicroPython. Tasks can be scheduled by time or by an
# external software trigger or interrupt, and run times can be profiled. The
# user's task code must be implemented in a generator which yields control
# after each short bounded run.
#
# Example:
# def task1_fun():
#     # This function switches states repeatedly for no reason.
#     state = 0
#     while True:
#         if state == 0:
#             state = 1
#         elif state == 1:
#             state = 0
#         yield state
#
# # In main, create this task and set it to run twice per second.
# task1 = cotask.Task(task1_fun, name='Task 1', priority=1,
#                     period=500, profile=True)
# cotask.task_list.append(task1)
# while True:
#     cotask.task_list.pri_sched()
class Task:

    # Initialize a task object so it may be run by the scheduler.
    #
    # Arguments:
    #   run_fun  - Function which implements the task's code. It must return a
    #              generator which yields control back to the scheduler.
    #   name     - Task name, by default "NoName".
    #   priority - Positive integer priority. Higher numbers run first.
    #   period   - Time in milliseconds between task runs, or None for a task
    #              triggered through go(). The scheduler stores this internally
    #              in microseconds.
    #   profile  - True enables run-time profiling.
    #   shares   - Optional list or tuple of shares and queues used by the
    #              task.
    def __init__(self, run_fun, name="NoName", priority=0, period=None,
                 profile=False, shares=()):
        # The function which is run to implement this task's code. Since it
        # is a generator, we "run" it here, which doesn't actually run it but
        # gets it going as a generator which is ready to yield values
        if shares:
            self._run_gen = run_fun(shares)
        else:
            self._run_gen = run_fun()

        # The name of the task, hopefully a short and descriptive string.
        self.name = name

        # The task's priority, an integer with higher numbers meaning higher
        # priority.
        self.priority = int(priority)

        # The period, in microseconds, between runs of the task's generator. If
        # the period is None, the task is triggered through go() instead of a
        # time base.
        if period is not None:
            self.period = int(period * 1000)
            self._next_run = utime.ticks_us() + self.period
        else:
            self.period = period
            self._next_run = None

        # Parameters used by the profiler to track task performance
        self._runtime_stats = RunningStats()
        self._latency_stats = RunningStats()

        # Flag which enables profiling of execution time and basic statistics.
        self._prof = profile
        self.reset_profile()

        # Flag which is set true when the task is ready to run.
        self.go_flag = False

        # Timestamp recorded when a triggered task is marked ready.
        self._trigger_time = None

    # Run this task if it is ready.
    #
    # Returns True if the task ran, or False if it was not ready.
    def schedule(self) -> bool:
        if self.ready():

            # Reset the go flag for the next run
            self.go_flag = False

            # If profiling, save the start time
            if self._prof:
                stime = utime.ticks_us()

                if self.period is None and self._trigger_time is not None:
                    late = utime.ticks_diff(stime, self._trigger_time)
                    self._latency_stats.update(late)

            # Advance the generator implementing this task.
            next(self._run_gen)

            # If profiling, save timing data.
            if self._prof:
                etime = utime.ticks_us()
                self._runs += 1
                runt = utime.ticks_diff(etime, stime)
                if self.period is None or self._runs > 2:
                    self._runtime_stats.update(runt)

            return True

        else:
            return False

    # Check whether the task is ready to run.
    #
    # Timer-based tasks update their go flag when the period has elapsed.
    # Triggered tasks rely on go_flag being set externally.
    @micropython.native
    def ready(self) -> bool:
        # If this task uses a timer, check if it's time to run run() again. If
        # so, set go flag and set the timer to go off at the next run time
        if self.period is not None:
            late = utime.ticks_diff(utime.ticks_us(), self._next_run)
            if late > 0:
                self.go_flag = True
                self._next_run = utime.ticks_add(self._next_run, self.period)

                # If keeping a latency profile, record the data
                if self._prof:
                    self._latency_stats.update(late)

        # If the task doesn't use a timer, we rely on go_flag to signal ready
        return self.go_flag

    # Set the period between task runs in milliseconds.
    #
    # Use None for a task triggered by calls to go() rather than by time.
    def set_period(self, new_period):
        if new_period is None:
            self.period = None
            self._next_run = None
        else:
            self.period = int(new_period) * 1000
            self._next_run = utime.ticks_add(utime.ticks_us(), self.period)

    # Reset the variables used for execution time profiling.
    #
    # This method is also used by __init__() to create the variables.
    def reset_profile(self):
        self._runs = 0
        self._runtime_stats.reset()
        self._latency_stats.reset()

    # Set the flag indicating that this task is ready to run.
    #
    # This may be called from an interrupt service routine or another task.
    def go(self):
        if self._prof and self.period is None and not self.go_flag:
            self._trigger_time = utime.ticks_us()
        self.go_flag = True

    # Return profiling values used by the task-list report.
    def profile(self):
        if self.period:
            return (self.name,
                    self.priority,
                    self.period/1000,
                    self._runs,
                    self._runtime_stats.mean/1000,
                    self._runtime_stats.max/1000,
                    self._runtime_stats.std/1000,
                    self._latency_stats.mean/1000,
                    self._latency_stats.max/1000,
                    self._latency_stats.std/1000)
        else:
            return (self.name,
                    self.priority,
                    self._runs,
                    self._runtime_stats.mean/1000,
                    self._runtime_stats.max/1000,
                    self._runtime_stats.std/1000,
                    self._latency_stats.mean/1000,
                    self._latency_stats.max/1000,
                    self._latency_stats.std/1000)

    # This method converts the task to a string for diagnostic use.
    # It shows information about the task.
    def __repr__(self):
        rst = "Task("
        rst += f"name={self.name!r}, "
        rst += f"priority={self.priority!r}, "
        if self.period is not None:
            rst += f"period={self.period/1000.0:.1f}, "
        else:
            rst += "period=None, "
        rst += f"profile={self._prof!r}"
        rst += ")"
        return rst


# =============================================================================

# Scheduler-owned list of cooperative tasks.
#
# The task list is usually touched directly only when tasks are added and when
# the scheduler is called. The list is sorted by priority so the scheduler can
# efficiently find the highest-priority task which is ready to run. Tasks can
# also be scheduled in round-robin fashion.
class TaskList:

    # Initialize the priority buckets used to organize tasks.
    def __init__(self):

        # The list of priority lists. Each priority with at least one task has
        # a list whose first element is the priority and whose remaining
        # elements are references to task objects at that priority.
        self.pri_list = []

    # Append a task and keep the list sorted by priority.
    def append(self, task):
        # See if there's a tasklist with the given priority in the main list
        new_pri = task.priority
        for pri in self.pri_list:
            # If a tasklist with this priority exists, add this task to it.
            if pri[0] == new_pri:
                pri.append(task)
                break

        # If the priority isn't in the list, this else clause starts a new
        # priority list with this task as first one. A priority list has the
        # priority as element 0, an index into the list of tasks (used for
        # round-robin scheduling those tasks) as the second item, and tasks
        # after those
        else:
            self.pri_list.append([new_pri, 2, task])

        # Make sure the main list (of lists at each priority) is sorted
        self.pri_list.sort(key=lambda pri: pri[0], reverse=True)

    # Run tasks in round-robin order, ignoring priority.
    #
    # Each call gives every task a chance to run. Although higher priority
    # buckets are visited first, every task gets a chance during each pass.
    @micropython.native
    def rr_sched(self):
        # For each priority level, run all tasks at that level
        for pri in self.pri_list:
            for task in pri[2:]:
                task.schedule()

    # Run tasks according to priority.
    #
    # Each call finds the highest-priority task that is ready and advances its
    # generator once.
    @micropython.native
    def pri_sched(self):
        # Go down the list of priorities, beginning with the highest
        for pri in self.pri_list:
            # Within each priority list, run tasks in round-robin order
            # Each priority list is [priority, index, task, task, ...] where
            # index is the index of the next task in the list to be run
            tries = 2
            length = len(pri)
            while tries < length:
                ran = pri[pri[1]].schedule()
                tries += 1
                pri[1] += 1
                if pri[1] >= length:
                    pri[1] = 2
                if ran:
                    return

    # Create diagnostic text showing task profiler data.
    def profile(self):
        ret_str = _PROF_HEADER
        for pri in self.pri_list:
            for task in pri[2:]:
                if task.period is not None:
                    ret_str += _PROF_ROW_PERIODIC.format(*task.profile())
                else:
                    ret_str += _PROF_ROW_APERIODIC.format(*task.profile())
        ret_str += _PROF_FOOTER

        return ret_str


# Main task list created when cotask.py is imported.
task_list = TaskList()
