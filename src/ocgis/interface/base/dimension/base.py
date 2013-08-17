import abc
import numpy as np
from ocgis.interface.base.variable import AbstractSourcedVariable
from ocgis.util.helpers import get_empty_or_pass_1d, get_isempty, get_none_or_2d
from ocgis import constants


class AbstractDimension(AbstractSourcedVariable):
    __metaclass__ = abc.ABCMeta
    
    def __init__(self,value=None,attrs=None,uid=None,data=None,name=None,
                 name_uid=None,units=None):
        self.attrs = attrs or {}
        self.name = name or self.__class__.__name__
        self.name_uid = name_uid or '{0}_uid'.format(self.name)
        self.units = units
        
        self._value = get_empty_or_pass_1d(value,dtype=constants.np_float)
        self._uid = get_empty_or_pass_1d(uid,dtype=constants.np_int)
        self._data = data
    
    @abc.abstractproperty
    def resolution(self): 'number'
    
    @abc.abstractproperty
    def shape(self): tuple
    
    @property
    def uid(self):
        if get_isempty(self._uid):
            self._uid = np.arange(1,self._value.shape[0]+1,dtype=constants.np_int)
        return(self._uid)


class VectorDimension(AbstractDimension):
    
    def __init__(self,*args,**kwds):
        self._src_idx = get_empty_or_pass_1d(kwds.pop('src_idx',None),dtype=constants.np_int)
        self._bounds = get_none_or_2d(kwds.pop('bounds',None))
        self.name_bounds = kwds.pop('name_bounds',None)
        
        super(VectorDimension,self).__init__(*args,**kwds)
        
        if self.name_bounds is None:
            self.name_bounds = '{0}_bnds'.format(self.name)
                        
    def __getitem__(self,slc):
        ret_value = self._value[slc]
        ret_uid = self.uid[slc]
        ret_src_idx = self._src_idx[slc]
        ret_bounds = self._bounds[slc]
        ret_attrs = self.attrs.copy()
        
        return(self.__class__(value=ret_value,attrs=ret_attrs,uid=ret_uid,
         data=self._data,src_idx=ret_src_idx,bounds=ret_bounds,
         name=self.name,name_uid=self.name_uid,name_bounds=self.name_bounds,
         units=self.units))

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
            yield(yld)
    
    @property
    def bounds(self):
        if self._bounds is None:
            self._bounds = np.zeros((self.value.shape[0],2),dtype=self.value.dtype)
            self._bounds[:,0] = self.value
            self._bounds[:,1] = self.value
        return(self._bounds)
    
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
    def shape(self):
        return(self.uid.shape)
    
    @property
    def uid(self):
        if get_isempty(super(VectorDimension,self).uid):
            self._uid = np.atleast_1d(np.arange(1,self._src_idx.shape[0]+1,dtype=constants.np_int))
        return(self._uid)
    
    def __get_value__(self):
        if not get_isempty(self._src_idx):
            ret = self._get_from_source_()
        else:
            ret = self._value
        return(ret)
    
    def _get_from_source_(self):
        raise(NotImplementedError)