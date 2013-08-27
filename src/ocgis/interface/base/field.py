import abc
from ocgis.util.logging_ocgis import ocgis_lh
from ocgis.util.helpers import get_default_or_apply, get_none_or_slice,\
    get_none_or_1d, get_formatted_slice, get_slice
import numpy as np
from copy import copy
from collections import OrderedDict
import itertools


class AbstractValueVariable(object):
    __metaclass__ = abc.ABCMeta
    
    def __init__(self,value=None):
        self._value = value
    
    @property
    def value(self):
        if self._value is None:
            self._value = self._get_value_()
        return(self._value)
    def _get_value_(self):
        return(self._value)
    
    @property
    def _value(self):
        return(self.__value)
    @_value.setter
    def _value(self,value):
        self.__value = self._format_private_value_(value)
    @abc.abstractmethod
    def _format_private_value_(self,value):
        return(value)


class AbstractSourcedVariable(AbstractValueVariable):
    __metaclass__ = abc.ABCMeta
    
    def __init__(self,data,src_idx=None,value=None,debug=False):
        if not debug and value is None and data is None:
            ocgis_lh(exc=ValueError('Sourced variables require a data source if no value is passed.'))
        self._data = data
        self._src_idx = src_idx
        
        super(AbstractSourcedVariable,self).__init__(value=value)
        
    @property
    def _src_idx(self):
        return(self.__src_idx)
    @_src_idx.setter
    def _src_idx(self,value):
        self.__src_idx = self._format_src_idx_(value)
    
    def _format_src_idx_(self,value):
        if value is None:
            ret = value
        else:
            ret = value
        return(ret)
    
    def _get_value_(self):
        if self._data is None and self._value is None:
            ocgis_lh(exc=ValueError('Values were requested from data source, but no data source is available.'))
        elif self._src_idx is None and self._value is None:
            ocgis_lh(exc=ValueError('Values were requested from data source, but no source index source is available.'))
        else:
            ret = self._get_value_from_source_()
        return(ret)
            
    @abc.abstractmethod
    def _get_value_from_source_(self): pass


class Variable(object):
    
    def __init__(self,name,alias=None,units=None,meta=None):
        self.name = name
        self.alias = alias or name
        self.units = units
        self.meta = meta or {}
        self._field = None
    
    @property
    def field(self):
        return(self._field)
    
    @property
    def value(self):
        return(self.field.value[self.alias])
        
        
class VariableCollection(OrderedDict):
    
    def __init__(self,variables=None):
        super(VariableCollection,self).__init__()
        
        if variables is not None:
            for variable in variables:
                assert(variable.alias not in self)
                self.update(variable.alias,variable)
                
    def update(self,alias,variable):
        assert(alias not in self)
        super(VariableCollection,self).update({alias:variable})


class Field(AbstractSourcedVariable):
    _axis_map = {'realization':0,'temporal':1,'level':2}
    
    def __init__(self,variables=None,value=None,realization=None,temporal=None,
                 level=None,spatial=None,units=None,data=None,debug=False,meta=None):
        try:
            assert(isinstance(variables,VariableCollection))
        except AssertionError:
            ocgis_lh(exc=ValueError('The "variables" keyword must be a VariableCollection.'))
        
        self.variables = variables
        self.realization = self._format_dimension_(realization)
        self.temporal = self._format_dimension_(temporal)
        self.level = self._format_dimension_(level)
        self.spatial = self._format_dimension_(spatial)
        self.units = units
        self.value_dimension_names = ('realization','temporal','level','row','column')
        self.meta = meta or {}
        
        super(Field,self).__init__(data,src_idx=None,value=value,debug=debug)
        
        for v in self.variables.itervalues(): v._field = self
        
    def __getitem__(self,slc):
        slc = get_formatted_slice(slc,5)        
        ret = copy(self)
        ret.realization = get_none_or_1d(get_none_or_slice(ret.realization,slc[0]))
        ret.temporal = get_none_or_slice(ret.temporal,slc[1])
        ret.level = get_none_or_slice(ret.level,slc[2])
        ret.spatial = get_none_or_slice(ret.spatial,(slc[3],slc[4]))
        
        ret._value = self._get_value_slice_or_none_(self._value,slc)

        return(ret)
    
    @property
    def shape(self):
        shape_realization = get_default_or_apply(self.realization,len,1)
        shape_temporal = get_default_or_apply(self.temporal,len,1)
        shape_level = get_default_or_apply(self.level,len,1)
        shape_spatial = get_default_or_apply(self.spatial,lambda x: x.shape,(1,1))
        ret = (shape_realization,shape_temporal,shape_level,shape_spatial[0],shape_spatial[1])
        return(ret)
    
    def get_between(self,dim,lower,upper):
        pos = self._axis_map[dim]
        ref = getattr(self,dim)
        new_dim,indices = ref.get_between(lower,upper,return_indices=True)
        ret = copy(self)
        setattr(ret,dim,new_dim)
        slc = get_slice(indices)
        slc_field = [slice(None)]*5
        slc_field[pos] = slc
        ret._value = self._get_value_slice_or_none_(ret._value,slc_field)
        return(ret)
    
    def get_intersects(self,point_or_polygon):
        ret = copy(self)
        ret.spatial,slc = self.spatial.get_intersects(point_or_polygon,return_indices=True)
        slc = [slice(None),slice(None),slice(None)] + list(slc)
        ret._value = self._get_value_slice_or_none_(ret._value,slc)

        ## we need to update the value mask with the geometry mask
        if ret._value is not None:
            ret_shp = ret.shape
            rng_realization = range(ret_shp[0])
            rng_temporal = range(ret_shp[1])
            rng_level = range(ret_shp[2])
            new_mask = ret.spatial.get_mask()
            for v in ret._value.itervalues():
                for idx_r,idx_t,idx_l in itertools.product(rng_realization,rng_temporal,rng_level):
                    ref = v[idx_r,idx_t,idx_l]
                    ref.mask = np.logical_or(ref.mask,new_mask)
        
        return(ret)
            
    def _format_dimension_(self,dim):
        if dim is not None:
            dim._field = self
        return(dim)
        
    def _format_private_value_(self,value):
        if value is None:
            ret = value
        else:
            assert(isinstance(value,dict))
            ret = value
            for k,v in ret.iteritems():
                assert(k in self.variables)
                assert(v.shape == self.shape)
                if not isinstance(v,np.ma.MaskedArray):
                    ret[k] = np.ma.array(v,mask=False)
        return(ret)
    
    def _get_value_from_source_(self):
        raise(NotImplementedError)
        ## TODO: remember to apply the geometry mask to fresh values!!
    
    def _get_value_slice_or_none_(self,value,slc):
        if value is None:
            ret = value
        else:
            ret = {k:v[slc] for k,v in value.iteritems()}
        return(ret)