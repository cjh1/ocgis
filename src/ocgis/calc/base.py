import numpy as np
import abc
import itertools
from ocgis.interface.base.variable import DerivedVariable, VariableCollection
from copy import copy
from ocgis.util.helpers import get_default_or_apply


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
    
    def __init__(self,alias=None,dtype=None,file_only=False,parms=None,
                 spatial_weights=None,tgd=None,use_aggregated_values=False):
        self.alias = alias or self.key
        self.dtype = dtype or self.dtype
        self.file_only = file_only
        self.parms = get_default_or_apply(parms,self._format_parms_,default={})
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
        ret = {'key':self.key,'alias':self.alias,'parms':{}}
        return(ret)
    
    def get_output_units(self,variable):
        return(None)
    
    @abc.abstractmethod
    def _aggregate_spatial_(self,**kwds): pass
    
    @abc.abstractmethod
    def _aggregate_temporal_(self,**kwds): pass
    
    def _format_parms_(self,values):
        return(values)
    
    def _get_temporal_agg_fill_(self,dtype,shp_fill=None):
        if shp_fill is None:
            shp_fill = list(self.field.shape)
            shp_fill[1] = len(self.tgd.dgroups)
        return(np.ma.array(np.zeros(shp_fill,dtype=dtype)))
    
    def _set_fill_temporal_(self,fill,value,f=None):
        if f is None:
            f = self.calculate
        for ir,it,il in itertools.product(*(range(s) for s in fill.shape[0:3])):
            values = value[ir,self.tgd.dgroups[it],il,:,:]
            assert(len(values.shape) == 3)
            cc = f(values,**self.parms)
            assert(len(cc.shape) == 2)
            cc = cc.reshape(1,1,1,cc.shape[0],cc.shape[1])
            fill[ir,it,il,:,:] = cc
        
        
class AbstractUnivariateFunction(AbstractFunction):
    '''
    field=<required>,alias=None,dtype=None,file_only=False,groups=None,spatial_weights=None,
     use_aggregated_values=False
    '''
    __metaclass__ = abc.ABCMeta
    
    def __init__(self,**kwds):
        self.field = kwds.pop('field',None)
        
        super(AbstractUnivariateFunction,self).__init__(**kwds)
        
    def execute(self):
        dvc = VariableCollection()
        fdef = self.get_function_definition()
        for variable in self.field.variables.itervalues():
            cc = self.calculate(variable.value,**self.parms)
            dtype = self.dtype or variable.value.dtype
            if dtype != cc.dtype:
                cc = cc.astype(dtype)
            assert(cc.shape == self.field.shape)
            if self.tgd is not None:
                cc = self._get_temporal_agg_fill_(dtype)
                import ipdb;ipdb.set_trace()
            dv = DerivedVariable(name=self.key,alias=self.alias,
                                 units=self.get_output_units(variable),value=cc,
                                 fdef=fdef,parents=VariableCollection(variables=[variable]),
                                 collection_key='{0}_{1}'.format(self.alias,variable.alias))
            dvc.add_variable(dv)
        return(dvc)
        
    def aggregate_spatial(self,**kwds):
        raise(NotImplementedError)
    
    def _aggregate_spatial_(self,**kwds):
        raise(NotImplementedError)
    
    def aggregate_temporal(self,**kwds):
        raise(NotImplementedError)
    
    def _aggregate_temporal_(self,values):
        return(np.ma.mean(values,axis=0))


class AbstractParameterizedFunction(AbstractFunction):
    __metaclass__ = abc.ABCMeta
    
    @abc.abstractproperty
    def parms_definition(self): dict
    
    def _format_parms_(self,values):
        ret = {k:self.parms_definition[k](v) for k,v in values.iteritems()}
        return(ret)

        
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
            fill = self._get_temporal_agg_fill_(dtype,shp_fill=shp_fill)
            self._set_fill_temporal_(fill,variable.value)
#            for ir,it,il in itertools.product(*(range(s) for s in shp_fill[0:3])):
#                values = variable.value[ir,self.tgd.dgroups[it],il,:,:]
#                assert(len(values.shape) == 3)
#                cc = self.calculate(values,**self.parms)
#                assert(len(cc.shape) == 2)
#                cc = cc.reshape(1,1,1,cc.shape[0],cc.shape[1])
#                fill[ir,it,il,:,:] = cc
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
 