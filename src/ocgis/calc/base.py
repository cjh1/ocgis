import numpy as np
import abc
import itertools
from ocgis.interface.base.variable import DerivedVariable, VariableCollection
from copy import copy


class AbstractFunction(object):
    __metaclass__ = abc.ABCMeta
    
    @abc.abstractproperty
    def description(self): str
    dtype = None
    Group = None
    @abc.abstractproperty
    def key(self): str
    long_name = ''
    standard_name = ''
    
    def __init__(self,alias=None,dtype=None,file_only=False,parms=None,spatial_weights=None,tgd=None,use_aggregated_values=False):
        self.alias = alias or self.key
        self.dtype = dtype or self.dtype
        self.file_only = file_only
        self.parms = parms
        self.spatial_weights = spatial_weights
        self.tgd = tgd
        self.use_aggregated_values = use_aggregated_values
        
    @abc.abstractmethod
    def aggregate_spatial(self,**kwds): pass
    
    @abc.abstractmethod
    def aggregate_temporal(self,**kwds): pass
        
    @abc.abstractmethod
    def calculate(self,**kwds): pass
    
    @abc.abstractmethod
    def execute(self): pass
    
    def get_function_definition(self):
        ret = {'key':self.key,'alias':self.alias,'parms':self.parms}
        return(ret)
    
    def get_output_units(self,variable):
        return(None)
    
    @abc.abstractmethod
    def _aggregate_spatial_(self,**kwds): pass
    
    @abc.abstractmethod
    def _aggregate_temporal_(self,**kwds): pass
        
        
class AbstractUnivariateFunction(AbstractFunction):
    '''
    field=<required>,alias=None,dtype=None,file_only=False,groups=None,spatial_weights=None,
     use_aggregated_values=False
    '''
    __metaclass__ = abc.ABCMeta
    
    def __init__(self,**kwds):
        self.field = kwds.pop('field')
        
        super(AbstractUnivariateFunction,self).__init__(**kwds)
        
    def aggregate_spatial(self,**kwds):
        raise(NotImplementedError)
    
    def _aggregate_spatial_(self,**kwds):
        raise(NotImplementedError)


class AbstractParameterizedFunction(AbstractFunction):
    __metaclass__ = abc.ABCMeta
    
    @abc.abstractproperty
    def parms(self): dict

        
class AbstractUnivariateSetFunction(AbstractUnivariateFunction):
    '''
    field=<required>,alias=None,dtype=None,file_only=False,groups=<required>,spatial_weights=None,
     use_aggregated_values=False
    '''
    __metaclass__ = abc.ABCMeta
    
    def __init__(self,**kwds):
        assert(kwds['tgd'] is not None)
        super(AbstractUnivariateSetFunction,self).__init__(**kwds)
    
    def aggregate_temporal(self):
        raise(NotImplementedError('aggregation implicit to calculate method'))
    
    def execute(self):
        shp_fill = list(self.field.shape)
        shp_fill[1] = len(self.tgd.dgroups)
        fdef = self.get_function_definition()
        dvc = VariableCollection()
        for variable in self.field.variables.itervalues():
            dtype = self.dtype or variable.value.dtype
            fill = np.ma.array(np.zeros(shp_fill,dtype=dtype))
            for ir,it,il in itertools.product(*[range(s) for s in shp_fill[0:3]]):
                values = variable.value[ir,self.tgd.dgroups[it],il,:,:]
                assert(len(values.shape) == 3)
                cc = self.calculate(values)
                assert(len(cc.shape) == 2)
                cc = cc.reshape(1,1,1,cc.shape[0],cc.shape[1])
                fill[ir,it,il,:,:] = cc
            dv = DerivedVariable(name=self.key,alias=self.alias,
                                 units=self.get_output_units(variable),value=fill,
                                 fdef=fdef,parents=VariableCollection(variables=[variable]),
                                 collection_key='{0}_{1}'.format(self.alias,variable.alias))
            dvc.add_variable(dv)
        return(dvc)
    
    def _aggregate_temporal_(self):
        raise(NotImplementedError('aggregation implicit to calculate method'))
    

class AbstractUnivariateScalarFunction(AbstractUnivariateFunction):
    __metaclass__ = abc.ABCMeta
    

class AbstractMultivariateFunction(AbstractFunction):
    __metaclass__ = abc.ABCMeta
    
    @abc.abstractproperty
    def variables(self): [str]
    
    
class AbstractKeyedOutputFunction(object):
    __metaclass__ = abc.ABCMeta
    
    @abc.abstractproperty
    def dtype(self): dict
 