import numpy as np
import abc


class OcgFunction(object):
    __metaclass__ = abc.ABCMeta
    
    @abc.abstractproperty
    def description(self): str
    @abc.abstractproperty
    def dtype(self): type
    Group = None
    @abc.abstractproperty
    def key(self): str
    long_name = ''
    standard_name = ''
    
    def __init__(self,alias=None,file_only=False,spatial_weights=None,
                 use_aggregated_values=False):
        self.alias = alias or self.key
        self.file_only = file_only
        self.spatial_weights = spatial_weights
        self.use_aggregated_values = use_aggregated_values
        
    @abc.abstractmethod
    def aggregate_spatial(self,**kwds): pass
    
    @abc.abstractmethod
    def aggregate_temporal(self,**kwds): pass
        
    @abc.abstractmethod
    def calculate(self,**kwds): pass
    
    @abc.abstractmethod
    def _aggregate_spatial_(self,**kwds): pass
    
    @abc.abstractmethod
    def _aggregate_temporal_(self,**kwds): pass
        
    @abc.abstractmethod
    def _calculate_(self,**kwds): pass
        
        
class OcgUnivariateFunction(OcgFunction):
    '''
    field=<required>,alias=None,file_only=False,spatial_weights=None,
     use_aggregated_values=False
    '''
    __metaclass__ = abc.ABCMeta
    
    def __init__(self,**kwds):
        self.field = kwds.pop('field')
        
        super(OcgUnivariateFunction,self).__init__(**kwds)


class OcgParameterizedFunction(OcgFunction):
    __metaclass__ = abc.ABCMeta
    
    @abc.abstractproperty
    def parms(self): dict

        
class OcgUnivariateSetFunction(OcgUnivariateFunction):
    __metaclass__ = abc.ABCMeta
    
    def aggregate_temporal(self):
        raise(NotImplementedError('aggregation implicit to calculate method'))
    
    def _aggregate_temporal_(self):
        raise(NotImplementedError('aggregation implicit to calculate method'))
    

class OcgUnivariateScalarFunction(OcgUnivariateFunction):
    __metaclass__ = abc.ABCMeta
    

class OcgMultivariateFunction(OcgFunction):
    __metaclass__ = abc.ABCMeta
    
    @abc.abstractproperty
    def variables(self): [str]
    
    
class OcgKeyedOutputFunction(object):
    __metaclass__ = abc.ABCMeta
    
    @abc.abstractproperty
    def dtype(self): dict
 