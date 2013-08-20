import abc
import numpy as np
from ocgis.interface.base.variable import AbstractSourcedVariable
from ocgis import constants
from ocgis.util.logging_ocgis import ocgis_lh
from ocgis.util.helpers import get_none_or_1d, get_none_or_2d, get_none_or_slice
from copy import copy
from ocgis.exc import EmptySubsetError


class AbstractDimension(object):
    __metaclass__ = abc.ABCMeta
    
    def __init__(self,value=None,attrs=None,uid=None,name=None,name_uid=None,units=None):
        self.attrs = attrs or {}
        self.name = name or self.__class__.__name__
        self.name_uid = name_uid or '{0}_uid'.format(self.name)
        self.units = units
        self.value = value
        self.uid = uid
        
    @abc.abstractmethod
    def __getitem__(self,slc): pass
    
    def __iter__(self):
            
        ref_value = self.value
        ref_bounds = self.bounds
        ref_uid = self.uid
        ref_name = self.name
        ref_name_uid = self.name_uid
        ref_name_bounds_lower = '{0}_lower'.format(self.name_bounds)
        ref_name_bounds_upper = '{0}_upper'.format(self.name_bounds)
        
        for ii in range(self.value.shape[0]):
            yld = {ref_name:ref_value[ii],ref_name_uid:ref_uid[ii],
                   ref_name_bounds_lower:ref_bounds[ii,0],
                   ref_name_bounds_upper:ref_bounds[ii,1]}
            yield(ii,yld)
        
    def __len__(self):
        return(self.uid.flatten().shape[0])
    
    def resolution(self):
        raise(NotImplementedError)
    
    @property
    def shape(self):
        return(self.uid.shape)
    
    @property
    def uid(self):
        return(self._uid)
    @uid.setter
    def uid(self,value):
        if value is None:
            value = self._get_uid_()
        self._uid = self._format_uid_(value)
    
    @property
    def value(self):
        if self._value is None:
            self._value = self._get_value_()
        return(self._value)
    @value.setter
    def value(self,value):
        self._value = self._format_value_(value)
    
    def _format_uid_(self,value):
        assert(value is not None)
        return(value)
    
    def _format_value_(self,value):
        return(value)
    
    @abc.abstractmethod
    def _get_uid_(self): pass
    
    def _get_value_(self):
        return(self._value)
    
    
class Abstract1d(object):
    __metaclass__ = abc.ABCMeta
    
    def _format_uid_(self,value):
        return(np.atleast_1d(value))
    
    def _format_value_(self,value):
        return(get_none_or_1d(value))
    
    def _get_uid_(self):
        ret = np.arange(1,self.value.shape[0]+1,dtype=constants.np_int)
        ret = np.atleast_1d(ret)
        return(ret)
    

class Abstract2d(object):
    __metaclass__ = abc.ABCMeta
    
    def __getitem__(self,slc):
        try:
            assert(len(slc) == 2)
        except (AssertionError,TypeError):
            ocgis_lh(exc=IndexError('Abstract2d dimensions only support two-dimensional slicing.'))
            
        def _get_as_slice_(target):
            if type(target) == int:
                ret = slice(target,target+1)
            elif type(target) == slice:
                ret = target
            else:
                raise(NotImplementedError)
            return(ret)
        
        slc = map(_get_as_slice_,slc)
        state = copy(self)
        state.uid = state.uid[slc[0],slc[1]]
        
        return(self._get_slice_(state,slc))
    
    def _format_uid_(self,value):
        return(np.atleast_2d(value))
    
    def _format_value_(self,value):
        return(get_none_or_2d(value))
    
    @abc.abstractmethod
    def _get_slice_(self,state,slc): pass
    
    def _get_uid_(self):
        ret = np.arange(1,(self.value.shape[0]*self.value.shape[1])+1,dtype=constants.np_int)
        ret = ret.reshape(self.value.shape)
        return(ret)


class VectorDimension(AbstractSourcedVariable,Abstract1d,AbstractDimension):
    
    def __init__(self,*args,**kwds):
        self._src_idx = kwds.pop('src_idx',None)
        self.bounds = kwds.pop('bounds',None)
        self.name_bounds = kwds.pop('name_bounds',None)
        
        AbstractSourcedVariable.__init__(self,kwds.pop('data',None))
        AbstractDimension.__init__(self,*args,**kwds)
        
        if self.name_bounds is None:
            self.name_bounds = '{0}_bnds'.format(self.name)
                        
    def __getitem__(self,slc):        
        ret = copy(self)
        ret.uid = self.uid[slc]
        ret.value = get_none_or_slice(ret._value,slc)
        ret.bounds = get_none_or_slice(ret._bounds,slc)
        ret._src_idx = get_none_or_slice(ret._src_idx,slc)
        
        return(ret)
    
    @property
    def bounds(self):
        if self._bounds is None:
            ret = np.zeros((self.value.shape[0],2),dtype=self.value.dtype)
            ret[:,0] = self.value
            ret[:,1] = self.value
        else:
            ret = self._bounds
        return(ret)
    @bounds.setter
    def bounds(self,value):
        self._bounds = get_none_or_2d(value)
    
    @property
    def resolution(self):
        if self.value.shape[0] < 2:
            ret = None
        else:
            if self.bounds[0,0] == self.bounds[0,1]:
                res_array = np.diff(self.value[0:constants.resolution_limit])
            else:
                res_bounds = self.bounds[0:constants.resolution_limit]
                res_array = res_bounds[:,1] - res_bounds[:,0]
            ret = (res_array.mean(),self.units)
        return(ret)
    
    @property
    def _src_idx(self):
        return(self.__src_idx)
    @_src_idx.setter
    def _src_idx(self,value):
        self.__src_idx = get_none_or_1d(value)
    
    def get_between(self,lower,upper,return_indices=False):
        assert(lower <= upper)
        ref_bounds = self.bounds
        ref_logical_or = np.logical_or
        ref_logical_and = np.logical_and
        
        select = np.zeros(ref_bounds.shape[0],dtype=bool)
        indices = np.arange(0,select.shape[0])
        for idx in range(ref_bounds.shape[0]):
            select_lower = ref_logical_and(lower >= ref_bounds[idx,0],lower <= ref_bounds[idx,1])
            select_upper = ref_logical_and(upper >= ref_bounds[idx,0],upper <= ref_bounds[idx,1])
            select[idx] = ref_logical_or(select_lower,select_upper)
        
        if select.any() == False:
            ocgis_lh(exc=EmptySubsetError(origin=self.name))
            
        ret = self[select]
        
        if return_indices:
            ret = (ret,indices[select])
        
        return(ret)
    
    def _get_uid_(self):
        if self._value is not None:
            shp = self._value.shape[0]
        else:
            shp = self._src_idx.shape[0]
        ret = np.arange(1,shp+1,dtype=constants.np_int)
        ret = np.atleast_1d(ret)
        return(ret)
    
    def _get_value_from_source_(self):
        if self._value is None:
            raise(NotImplementedError)
        else:
            ret = self._value
        return(ret)
    