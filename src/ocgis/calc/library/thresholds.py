from ocgis.calc import base
import numpy as np


class Between(base.AbstractUnivariateSetFunction,base.AbstractParameterizedFunction):
    description = 'Count of values falling within the limits lower and upper (inclusive).'
    parms_definition = {'lower':float,'upper':float}
    dtype = np.int32
    key = 'between'
    
    def _calculate_(self,values,lower=None,upper=None):
        '''
        :param lower: The lower value of the range.
        :type lower: float
        :param upper: The upper value of the range.
        :type upper: float
        '''
        assert(lower <= upper)
        idx = (values >= float(lower))*(values <= float(upper))
        return(np.ma.sum(idx,axis=0))