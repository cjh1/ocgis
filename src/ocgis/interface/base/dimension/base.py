import abc
import numpy as np
from ocgis.interface.base.field import AbstractSourcedVariable,\
    AbstractValueVariable
from ocgis import constants
from ocgis.util.logging_ocgis import ocgis_lh
from ocgis.util.helpers import get_none_or_1d, get_none_or_2d, get_none_or_slice,\
    get_formatted_slice
from copy import copy
from ocgis.exc import EmptySubsetError
from operator import mul


class AbstractDimension(object):
    __metaclass__ = abc.ABCMeta
    
    @abc.abstractproperty
    def _axis(self): ['R','T','Z','X','Y','GEOM','GRID','POINT','POLYGON',None]
    @abc.abstractproperty
    def _ndims(self): int
    @abc.abstractproperty
    def _attrs_slice(self): 'sequence of strings'
    
    def __init__(self,meta=None,name=None):
        self.meta = meta or {}
        self.name = name or self._axis
        self._field = None
    
    def __getitem__(self,slc):
        slc = get_formatted_slice(slc,self._ndims)
        ret = copy(self)
        for attr in self._attrs_slice:
            ref_set = get_none_or_slice(getattr(ret,attr),slc)
            setattr(ret,attr,ref_set)
        ret = self._format_slice_state_(ret,slc)
        return(ret)
    
    @abc.abstractmethod
    def get_iter(self): pass
        
    def _format_slice_state_(self,state,slc):
        return(state)
    
    def _get_none_or_array_(self,arr,masked=False):
        if self._ndims == 1:
            ret = get_none_or_1d(arr)
        elif self._ndims == 2:
            ret = get_none_or_2d(arr)
        else:
            raise(NotImplementedError)
        if ret is not None and masked and not isinstance(ret,np.ma.MaskedArray):
            ret = np.ma.array(ret,mask=False)
        return(ret)
    
    
class AbstractValueDimension(AbstractValueVariable,AbstractDimension):
    __metaclass__ = abc.ABCMeta
    
    def __init__(self,*args,**kwds):
        self.name_value = kwds.pop('name_value',None)
        self.units = kwds.pop('units',None)
        
        AbstractValueVariable.__init__(self,value=kwds.pop('value',None))
        AbstractDimension.__init__(self,*args,**kwds)
        
        if self.name_value is None:
            self.name_value = self.name
    
    @property
    def shape(self):
        return(self.value.shape)
    
#    @property
#    def value(self):
#        if self._value is None:
#            self._value = self._get_value_()
#        return(self._value)
#    @abc.abstractmethod
#    def _get_value_(self): pass
    
    def get_iter(self):
        raise(NotImplementedError)
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
            
#    @abc.abstractmethod
#    def _format_value_(self,value): pass
    
    
class AbstractUidDimension(AbstractDimension):
    
    def __init__(self,*args,**kwds):
        self.uid = kwds.pop('uid',None)
        self.name_uid = kwds.pop('name_uid',None)
        
        super(AbstractUidDimension,self).__init__(*args,**kwds)
        
        if self.name_uid is None:
            self.name_uid = '{0}_uid'.format(self.name)
            
    @property
    def uid(self):
        if self._uid is None:
            self._uid = self._get_uid_()
        return(self._uid)
    @uid.setter
    def uid(self,value):
        self._uid = self._get_none_or_array_(value)
    def _get_uid_(self):
        if self.value is None:
            ret = None
        else:
            n = reduce(mul,self.value.shape)
            ret = np.arange(1,n+1).reshape(self.value.shape)
        return(ret)


class AbstractUidValueDimension(AbstractValueDimension,AbstractUidDimension):
    
    def __init__(self,*args,**kwds):
        self.properties = kwds.pop('properties',None)
        
        kwds_value = {key:kwds.get(key,None) for key in ('value','name_value','units','meta','name')}
        kwds_uid = {key:kwds.get(key,None) for key in ('uid','name_uid','meta','name')}
        AbstractValueDimension.__init__(self,*args,**kwds_value)
        AbstractUidDimension.__init__(self,*args,**kwds_uid)
        
        if self.properties is not None:
            assert(isinstance(self.properties,np.ndarray))
            assert(self.properties.shape[0] == self.shape[0])

class VectorDimension(AbstractSourcedVariable,AbstractUidValueDimension):
    _axis = None
    _attrs_slice = ('uid','_value','_src_idx')
    _ndims = 1
    
    def __init__(self,*args,**kwds):
        self.bounds = kwds.pop('bounds',None)
        self.name_bounds = kwds.pop('name_bounds',None)
        self._axis = kwds.pop('axis',None)
        
        AbstractSourcedVariable.__init__(self,kwds.pop('data',None),src_idx=kwds.pop('src_idx',None),value=kwds.get('value'))
        AbstractUidValueDimension.__init__(self,*args,**kwds)
        
        if self.name_bounds is None:
            self.name_bounds = '{0}_bnds'.format(self.name)
        if self._axis is None:
            self._axis = 'undefined'
            
    def __len__(self):
        return(self.shape[0])
    
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
            ret = np.abs(res_array).mean()
        return(ret)
    
    @property
    def shape(self):
        return(self.uid.shape)
    
    def get_between(self,lower,upper,return_indices=False):
        assert(lower <= upper)
        
        bounds_min = np.min(self.bounds,axis=1)
        bounds_max = np.max(self.bounds,axis=1)
        select_lower = np.logical_or(bounds_min >= lower,bounds_max >= lower)
        select_upper = np.logical_or(bounds_min <= upper,bounds_max <= upper)
        select = np.logical_and(select_lower,select_upper)
        
        if select.any() == False:
            ocgis_lh(exc=EmptySubsetError(origin=self.name))
            
        ret = self[select]
        
        if return_indices:
            indices = np.arange(self.bounds.shape[0])
            ret = (ret,indices[select])
        
        return(ret)
    
    def _format_private_value_(self,value):
        return(self._get_none_or_array_(value,masked=True))
    
    def _format_slice_state_(self,state,slc):
        state.bounds = get_none_or_slice(state._bounds,(slc,slice(None)))
        return(state)
    
    def _format_src_idx_(self,value):
        return(self._get_none_or_array_(value))
    
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
