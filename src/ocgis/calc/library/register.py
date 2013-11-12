import math
import statistics
import thresholds


class FunctionRegistry(dict):
    
    def __init__(self):
        super(FunctionRegistry,self).__init__()
        
        self.reg = [math.Divide,math.NaturalLogarithm,math.Threshold]
        self.reg += [statistics.FrequencyPercentile,statistics.Mean,statistics.StandardDeviation,
                     statistics.Max]
        self.reg += [thresholds.Between]
        
        for cc in self.reg:
            self.update({cc.key:cc})
