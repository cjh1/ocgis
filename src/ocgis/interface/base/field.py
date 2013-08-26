import abc
from ocgis.util.logging_ocgis import ocgis_lh
from ocgis.util.helpers import get_default_or_apply, get_none_or_slice,\
    get_none_or_1d
import numpy as np
from copy import copy


class AbstractSourcedVariable(object):
    __metaclass__ = abc.ABCMeta
    
    def __init__(self,data,src_idx,value):
        if value is None and src_idx is None:
            ocgis_lh(exc=ValueError('Either values or a source index are required for sourced variables.'))
        
        self._value = value
        self._data = data
        self._src_idx = src_idx
        
    @property
    def _src_idx(self):
        return(self.__src_idx)
    @_src_idx.setter
    def _src_idx(self,value):
        self.__src_idx = self._format_src_idx_(value)
        
    @property
    def _value(self):
        return(self.__value)
    @_value.setter
    def _value(self,value):
        self.__value = self._format_private_value_(value)
    
    def _get_value_(self):
        if self._data is None and self._value is None:
            ocgis_lh(exc=ValueError('Values were requested from data source, but no data source is available.'))
        elif self._src_idx is None and self._value is None:
            ocgis_lh(exc=ValueError('Values were requested from data source, but no source index source is available.'))
        else:
            ret = self._get_value_from_source_()
        return(ret)
    
    @abc.abstractmethod
    def _format_private_value_(self,value): pass
    
    @abc.abstractmethod
    def _format_src_idx_(self,value): pass
            
    @abc.abstractmethod
    def _get_value_from_source_(self): pass


class Field(AbstractSourcedVariable):
    
    def __init__(self,name=None,value=None,alias=None,realization=None,temporal=None,
                 level=None,spatial=None,units=None,attrs=None,data=None):
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
        self.value = value
        
        super(Field,self).__init__(data)
        
    def __getitem__(self,slc):
        try:
            assert(len(slc) == 5)
        except (AssertionError,TypeError):
            ocgis_lh(exc=IndexError('Variables only support 5-d slicing: {0}'.format(self.value_dimension_names)))
        
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
        
    @property
    def value(self):
        if self._value is None:
            self._value = self._get_value_()
        return(self._value)
    @value.setter
    def value(self,value):
        if value is None:
            self._value = None
        else:
            self._value = self._format_value_(value)
            
    def _format_dimension_(self,dim):
        if dim is not None:
            dim._field = self
        return(dim)
        
    def _format_value_(self,value):
        assert(value.shape == self.shape)
        if not isinstance(value,np.ma.MaskedArray):
            value = np.ma.array(value,mask=False)
        return(value)
    
    def _get_value_from_source_(self):
        raise(NotImplementedError)