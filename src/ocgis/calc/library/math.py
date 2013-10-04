from ocgis.calc import base
import numpy as np
from ocgis import constants


class Divide(base.AbstractMultivariateFunction):
    key = 'divide'
    description = 'Divide arr1 by arr2.'
    required_variables = ['arr1','arr2']
    
    def calculate(self,arr1=None,arr2=None):
        return(arr1/arr2)
    
    
class NaturalLogarithm(base.AbstractUnivariateFunction):
    key = 'ln'
    description = 'Compute the natural logarithm.'
    
    def calculate(self,values):
        return(np.ma.log(values))
    
    
class Threshold(base.AbstractUnivariateSetFunction,base.AbstractParameterizedFunction):
    description = 'Count of values where the logical operation returns TRUE.'
    dtype = constants.np_int
    parms_definition = {'threshold':float,'operation':str}
    key = 'threshold'
    
    def calculate(self,values,threshold=None,operation=None):
        '''
        :param threshold: The threshold value to use for the logical operation.
        :type threshold: float
        :param operation: The logical operation. One of 'gt','gte','lt', or 'lte'.
        :type operation: str
        '''        
        ## perform requested logical operation
        if operation == 'gt':
            idx = values > threshold
        elif operation == 'lt':
            idx = values < threshold
        elif operation == 'gte':
            idx = values >= threshold
        elif operation == 'lte':
            idx = values <= threshold
        else:
            raise(NotImplementedError('The operation "{0}" was not recognized.'.format(operation)))
        
        ret = np.ma.sum(idx,axis=0)
        return(ret)
        
    def aggregate_spatial(self,values):
        return(np.ma.sum(values))
