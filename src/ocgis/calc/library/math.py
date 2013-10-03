from ocgis.calc import base
import numpy as np


class NaturalLogarithm(base.AbstractUnivariateFunction):
    key = 'ln'
    description = 'Compute the natural logarithm.'
    
    def calculate(self,values):
        return(np.ma.log(values))
