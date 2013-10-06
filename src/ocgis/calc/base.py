import numpy as np
import abc
import itertools
from ocgis.interface.base.variable import DerivedVariable, VariableCollection
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
    
    def __init__(self,alias=None,dtype=None,field=None,file_only=False,vc=None,
                 parms=None,tgd=None,use_raw_values=False):
        self.alias = alias or self.key
        self.dtype = dtype or self.dtype
        self.vc = vc or VariableCollection()
        self.field = field
        self.file_only = file_only
        self.parms = get_default_or_apply(parms,self._format_parms_,default={})
        self.tgd = tgd
        self.use_raw_values = use_raw_values
        
    def aggregate_spatial(self,**kwds):
        raise(NotImplementedError)
    
    def aggregate_temporal(self,values,**kwds):
        return(np.ma.mean(values,axis=0))
        
    @abc.abstractmethod
    def calculate(self,**kwds): pass
    
    @abc.abstractmethod
    def execute(self): pass
    
    def get_function_definition(self):
        ret = {'key':self.key,'alias':self.alias,'parms':self.parms}
        return(ret)
    
    def get_output_units(self,variable):
        return(None)
    
    def get_variable_value(self,variable):
        ## raw values are to be used by the calculation. if this is True, and
        ## no raw field is associated with the input field, then use the standard
        ## value.
        if self.use_raw_values:
            if self.field._raw is None:
                ret = variable.value
            else:
                ret = self.field._raw.variables[variable.alias].value
        else:
            ret = variable.value
        return(ret)
    
    @classmethod
    def validate(self,ops):
        pass
    
    def _add_to_collection_(self,units=None,value=None,parent_variables=None,alias=None):
        units = units or self.get_output_units(parent_variables[0])
        alias = alias or '{0}_{1}'.format(self.alias,parent_variables[0].alias)
        fdef = self.get_function_definition()
        dv = DerivedVariable(name=self.key,alias=alias,units=units,value=value,
                             fdef=fdef,parents=VariableCollection(variables=parent_variables))
        self.vc.add_variable(dv)
    
    def _format_parms_(self,values):
        return(values)
    
    def _get_temporal_agg_fill_(self,dtype,shp_fill=None):
        if shp_fill is None:
            shp_fill = list(self.field.shape)
            shp_fill[1] = len(self.tgd.dgroups)
        return(np.ma.array(np.zeros(shp_fill,dtype=dtype)))
    
    def _set_fill_temporal_(self,fill,value,f=None,parms=None):
        f = f or self.calculate
        parms = parms or self.parms
        for ir,it,il in itertools.product(*(range(s) for s in fill.shape[0:3])):
            values = value[ir,self.tgd.dgroups[it],il,:,:]
            assert(len(values.shape) == 3)
            cc = f(values,**parms)
            assert(len(cc.shape) == 2)
            cc = cc.reshape(1,1,1,cc.shape[0],cc.shape[1])
            fill[ir,it,il,:,:] = cc
        
        
class AbstractUnivariateFunction(AbstractFunction):
    '''
    field=<required>,alias=None,dtype=None,file_only=False,groups=None,spatial_weights=None,
     use_aggregated_values=False
    '''
    __metaclass__ = abc.ABCMeta
        
    def execute(self):
        for variable in self.field.variables.itervalues():
            cc = self.calculate(variable.value,**self.parms)
            dtype = self.dtype or variable.value.dtype
            if dtype != cc.dtype:
                cc = cc.astype(dtype)
            assert(cc.shape == self.field.shape)
            if self.tgd is not None:
                fill = self._get_temporal_agg_fill_(dtype)
                self._set_fill_temporal_(fill,cc,f=self.aggregate_temporal,parms={})
                cc = fill
            self._add_to_collection_(value=cc,parent_variables=[variable])
        return(self.vc)
        
    def aggregate_spatial(self,**kwds):
        raise(NotImplementedError)


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
        for variable in self.field.variables.itervalues():
            value = self.get_variable_value(variable)
            dtype = self.dtype or value.dtype
            fill = self._get_temporal_agg_fill_(dtype,shp_fill=shp_fill)
            self._set_fill_temporal_(fill,value)
            self._add_to_collection_(value=fill,parent_variables=[variable])
        return(self.vc)
    

class AbstractMultivariateFunction(AbstractFunction):
    __metaclass__ = abc.ABCMeta
    
    @abc.abstractproperty
    def required_variables(self): [str]
    
    def execute(self):
        parms = {k:self.field.variables[self.parms[k]].value for k in self.required_variables}
        for k,v in self.parms.iteritems():
            if k not in self.required_variables:
                parms.update({k:v})
        cc = self.calculate(**parms)
        if self.dtype is not None:
            cc = cc.astype(self.dtype)
        assert(cc.shape == self.field.shape)
        if self.tgd is not None:
            fill = self._get_temporal_agg_fill_(cc.dtype)
            self._set_fill_temporal_(fill,cc,f=self.aggregate_temporal,parms={})
            cc = fill
        units = self.get_output_units()
        self._add_to_collection_(units=units,value=cc,parent_variables=self.field.variables.values(),
                                 alias=self.alias)
        return(self.vc)
    
    def get_output_units(self):
        return('undefined')
    
    
class AbstractKeyedOutputFunction(object):
    __metaclass__ = abc.ABCMeta
    
    @abc.abstractproperty
    def dtype(self): dict
