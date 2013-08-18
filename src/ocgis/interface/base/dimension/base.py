import abc
import numpy as np
from ocgis.interface.base.variable import AbstractSourcedVariable
from ocgis import constants
from ocgis.exc import EmptyIterationError
from ocgis.util.logging_ocgis import ocgis_lh
from ocgis.util.helpers import get_none_or_1d, get_none_or_2d


class AbstractDimension(object):
    __metaclass__ = abc.ABCMeta
    
    def __init__(self,value=None,attrs=None,uid=None,name=None,name_uid=None,units=None):
        self.attrs = attrs or {}
        self.name = name or self.__class__.__name__
        self.name_uid = name_uid or '{0}_uid'.format(self.name)
        self.units = units
        
        self.value = self._format_value_(value)
        if uid is None:
            self.uid = self._get_uid_()
        else:
            self.uid = uid
        self.uid = self._format_uid_(self.uid)
        
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
    def value(self):
        return(self._value)
    @value.setter
    def value(self,value):
        self._value = value
        
    def _format_uid_(self,value):
        assert(value is not None)
        return(value)
    
    def _format_value_(self,value):
        return(value)
    
    @abc.abstractmethod
    def _get_uid_(self): pass


class VectorDimension(AbstractSourcedVariable,AbstractDimension):
    
    def __init__(self,*args,**kwds):
        self._src_idx = get_none_or_1d(kwds.pop('src_idx',None))
        self._bounds = get_none_or_2d(kwds.pop('bounds',None))
        self.name_bounds = kwds.pop('name_bounds',None)
        
        AbstractSourcedVariable.__init__(self,kwds.pop('data',None))
        AbstractDimension.__init__(self,*args,**kwds)
        
        if self.name_bounds is None:
            self.name_bounds = '{0}_bnds'.format(self.name)
                        
    def __getitem__(self,slc):
        ret_uid = self.uid[slc]
        
        if self._value is None:
            ret_value = self._value
        else:
            ret_value = self._value[slc]
            
        if self._bounds is None:
            ret_bounds = self._bounds
        else:
            ret_bounds = self._bounds[slc]
        
        if self._src_idx is None:
            ret_src_idx = self._src_idx
        else:
            ret_src_idx = self._src_idx[slc]
            
        ret_attrs = self.attrs.copy()
        
        return(self.__class__(value=ret_value,attrs=ret_attrs,uid=ret_uid,
         data=self._data,src_idx=ret_src_idx,bounds=ret_bounds,
         name=self.name,name_uid=self.name_uid,name_bounds=self.name_bounds,
         units=self.units))
    
    @property
    def bounds(self):
        if self._bounds is None:
            ret = np.zeros((self.value.shape[0],2),dtype=self.value.dtype)
            ret[:,0] = self.value
            ret[:,1] = self.value
        else:
            ret = self._bounds
        return(ret)
    
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
    
    def get_between(self,lower,upper):
        ref_bounds = self.bounds
        ref_logical_or = np.logical_or
        ref_logical_and = np.logical_and
        
        select = np.zeros(ref_bounds.shape[0],dtype=bool)
        for idx in range(ref_bounds.shape[0]):
            select_lower = ref_logical_and(lower >= ref_bounds[idx,0],lower <= ref_bounds[idx,1])
            select_upper = ref_logical_and(upper >= ref_bounds[idx,0],upper <= ref_bounds[idx,1])
            select[idx] = ref_logical_or(select_lower,select_upper)
        ret = self[select]
        
        return(ret)
    
    def _format_uid_(self,value):
        return(np.atleast_1d(value))
    
    def _format_value_(self,value):
        return(get_none_or_1d(value))
    
    def _get_from_source_(self):
        raise(NotImplementedError)
    
    def _get_uid_(self):
        if self._value is not None:
            shp = self._value.shape[0]
        else:
            shp = self._src_idx.shape[0]
        ret = np.arange(1,shp+1,dtype=constants.np_int)
        ret = np.atleast_1d(ret)
        return(ret)
    
    def __get_value__(self):
        if self._src_idx is not None:
            ret = self._get_from_source_()
        else:
            ret = self._value
        return(ret)
    