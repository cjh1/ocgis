import abc
from ocgis.util.logging_ocgis import ocgis_lh
from ocgis.util.helpers import get_default_or_apply, get_none_or_slice,\
    get_none_or_1d, get_formatted_slice
import numpy as np
from copy import copy


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


class Field(AbstractSourcedVariable):
    
    def __init__(self,name=None,value=None,alias=None,realization=None,temporal=None,
                 level=None,spatial=None,units=None,attrs=None,data=None,debug=False):
        if spatial is None or name is None:
            ocgis_lh(exc=ValueError('Variables require a name and spatial dimension.'))
        
        self.name = name
        self.alias = alias or name
        self.realization = get_none_or_1d(realization)
        self.temporal = self._format_dimension_(temporal)
        self.level = self._format_dimension_(level)
        self.spatial = self._format_dimension_(spatial)
        self.units = units
        self.attrs = attrs or {}
        self.value_dimension_names = ('realization','temporal','level','row','column')
        
        super(Field,self).__init__(data,src_idx=None,value=value,debug=debug)
        
    def __getitem__(self,slc):
        slc = get_formatted_slice(slc,5)        
        ret = copy(self)
        ret.realization = get_none_or_1d(get_none_or_slice(ret.realization,slc[0]))
        ret.temporal = get_none_or_slice(ret.temporal,slc[1])
        ret.level = get_none_or_slice(ret.level,slc[2])
        ret.spatial = get_none_or_slice(ret.spatial,(slc[3],slc[4]))
        
        if self._value is not None:
            ret._value = np.atleast_1d(self._value[slc]).reshape(*ret.shape)

        return(ret)
    
    @property
    def shape(self):
        shape_realization = get_default_or_apply(self.realization,len,1)
        shape_temporal = get_default_or_apply(self.temporal,len,1)
        shape_level = get_default_or_apply(self.level,len,1)
        shape_spatial = get_default_or_apply(self.spatial,lambda x: x.shape,(1,1))
        ret = (shape_realization,shape_temporal,shape_level,shape_spatial[0],shape_spatial[1])
        return(ret)
            
    def _format_dimension_(self,dim):
        if dim is not None:
            dim._field = self
        return(dim)
        
    def _format_private_value_(self,value):
        if value is None:
            ret = value
        else:
            assert(value.shape == self.shape)
            if not isinstance(value,np.ma.MaskedArray):
                ret = np.ma.array(value,mask=False)
            else:
                ret = value
        return(ret)
    
    def _get_value_from_source_(self):
        raise(NotImplementedError)