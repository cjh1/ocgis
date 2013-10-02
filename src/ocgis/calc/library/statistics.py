from ocgis.calc.base import AbstractUnivariateSetFunction
import numpy as np


class Mean(AbstractUnivariateSetFunction):
    description = 'Compute mean value of the set.'
    key = 'mean'
    
    def calculate(self,values):
        return(np.ma.mean(values,axis=0))