from math import sqrt

# Online statistics accumulator using Welford's algorithm.
class Running_Stats:
    # Initialize empty statistics.
    def __init__(self):
        # Sample count
        self._n = 0
        # Running mean
        self._mean = 0.0
        # Running sum of squared deviation from mean
        self._M2 = 0.0
        # Maximum value of parameter
        self._max = 0.0
        # Intermediate values for Welford's algorithm (preallocated)
        self._delta = 0.0
        self._delta2 = 0.0

    # Add a new sample to the running statistics.
    def update(self, x):
        # Check for max values
        if x > self._max:
            self._max = x
        
        # Apply Welford's online algorithm for updating mean and variance
        self._n += 1
        self._delta = x - self._mean
        self._mean += self._delta / self._n
        self._delta2 = x - self._mean
        self._M2 += self._delta * self._delta2

    # Sample variance of the values seen so far.
    @property
    def variance(self):
        if self._n < 2:
            return 0.0
        return self._M2 / (self._n - 1)

    # Sample standard deviation of the values seen so far.
    @property
    def std(self):
        return sqrt(self.variance)
    
    # Running mean of the values seen so far.
    @property
    def mean(self):
        return self._mean
        
    # Maximum observed value.
    @property
    def max(self):
        return self._max
        
    # Clear all accumulated statistics.
    def reset(self):
        self._n = 0
        self._mean = 0.0
        self._M2 = 0.0
        self._max = 0.0
