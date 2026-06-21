from math import sqrt

class Running_Stats:
    def __init__(self):
        # Sample count
        self._n = 0
        # Running mean
        self._mean = 0.0
        # Running sum of squared deviation from mean
        self._M2 = 0.0
        # Maximum value of parameter
        self._max = 0.0
        self._delta = 0.0
        self._delta2 = 0.0

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

    @property
    def variance(self):
        if self._n < 2:
            return 0.0
        return self._M2 / (self._n - 1)

    @property
    def std(self):
        return sqrt(self.variance)
    
    @property
    def mean(self):
        return self._mean
        
    @property
    def max(self):
        return self._max
        
    def reset(self):
        self._n = 0
        self._mean = 0.0
        self._M2 = 0.0
        self._max = 0.0