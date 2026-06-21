import cotask
import utime
import micropython
from math import sqrt

class Triggered_Task(cotask.Task):
    # This class inherits from the standard cooperative task used by the
    # scheduler and modifies it to act as a triggered task instead of a periodic
    # one. That is, instead of automatically setting it's own go flag when ready
    # to run, the go flag needs to be set externally in other tasks, or in the
    # generator implementing the run function for tasks using this class.
    
    def __init__(self, *args, **kwargs):
        # Initialize the parent class
        super().__init__(*args, **kwargs)

    def schedule(self) -> bool:
        # If the go flag has been set externally and the scheduler tries to run
        # the task, it does so immediately. That is, there is no task period or
        # latency to consider.
        if self.go_flag:
            self.go_flag = False
            
            # The profiler should still work properly to measure task duration.
            # Record the start time for this task iteration.
            if self._prof:
                stime = utime.ticks_us()
                late = utime.ticks_diff(stime, self._next_run)
                self._latency_stats.update(late)
            
            # The run function implementing this task needs to be iterated upon.
            # In future revisions this may use send() instead of next() so that
            # data can be sent into this task from other tasks.
            curr_state = next(self._run_gen)
            
            # Finish computing profile specs
            if self._prof:
                
                # Compute the end time for this task iteration and accumulate
                # the number of iterations.
                etime = utime.ticks_us()
                self._runs += 1
                
                # The run time is the difference between start and end times
                runt = utime.ticks_diff(etime, stime)
                
                # If more than one run has occurred, add the run time to the
                # tracked statistics for run time
                self._runtime_stats.update(runt)
            
            return True
            
        else:
            return False
            
    def go(self):
        if self._prof and not self.go_flag:
            self._next_run = utime.ticks_us()
        self.go_flag = True
            
    def profile(self):
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
        rst = "Triggered_Task("
        rst += f"name={self.name!r}, "
        rst += f"priority={self.priority!r}, "
        if self.period is not None:
            rst += f"period={self.period/1000.0:.1f}, "
        else:
            rst += "period=None, "
        rst += f"profile={self._prof!r}, "
        rst += f"trace={self._trace!r}"
        rst += ")"
        return rst