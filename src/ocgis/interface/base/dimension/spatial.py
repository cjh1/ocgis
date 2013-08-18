from base import AbstractDimension
import numpy as np
from copy import copy
from ocgis.util.helpers import iter_array
from ocgis.util.logging_ocgis import ocgis_lh


class SpatialDimension(AbstractDimension):
    
    def __init__(self,*args,**kwds):
        self.row = kwds.pop('row',None)
        self.col = kwds.pop('col',None)
        self.grid = kwds.pop('grid',None)
        self.crs = kwds.pop('crs',None)
        self.geom = kwds.pop('geom',None)
        
        super(SpatialDimension,self).__init__(*args,**kwds)
        
        if self.grid is None and self.geom is None:
            self.grid = SpatialGridDimension(row=self.row,col=self.col)
        else:
            assert(all([d is not None for d in [self.row,self.col]]))
            
    def __getitem__(self,slc):
        raise(NotImplementedError)
    
    def __iter__(self):
        raise(NotImplementedError)
            
    @property
    def resolution(self):
        raise(NotImplementedError)
    
    @property
    def value(self):
        raise(NotImplementedError)
    
    def __get_value__(self):
        raise(NotImplementedError)
    
    
class SpatialGridDimension(AbstractDimension):
    
    def __init__(self,*args,**kwds):
        for key in ['value','bounds']:
            if kwds.get(key) is not None:
                assert(all([isinstance(v,np.ma.MaskedArray) for v in kwds[key]]))
        
        self.row = kwds.pop('row',None)
        self.col = kwds.pop('col',None)
        
        super(SpatialGridDimension,self).__init__(*args,**kwds)
        
    def __getitem__(self,slc):
        try:
            assert(len(slc) == 2)
        except (AssertionError,TypeError):
            ocgis_lh(exc=IndexError('Grid dimensions only support two-dimensional slicing.'))
            
        def _get_as_slice_(target):
            if type(target) == int:
                ret = slice(target,target+1)
            elif type(target) == slice:
                ret = target
            else:
                raise(NotImplementedError)
            return(ret)
        
        slc = map(_get_as_slice_,slc)
        ret = copy(self)
        
        ret._value = ret.value[:,slc[0],slc[1]]
        if ret.row is not None:
            ret.row = ret.row[slc[0]]
            ret.col = ret.col[slc[1]]
        
        return(ret)
        
    def __iter__(self):
        raise(NotImplementedError)
        
    @property
    def resolution(self):
        raise(NotImplementedError)
    
    @property
    def value(self):
        if self._value is None:
            ## fill the value
            fill = np.empty((2,self.row.shape[0],self.col.shape[0]),dtype=self.row.value.dtype)
            fill = np.ma.array(fill,mask=False)
            col_coords,row_coords = np.meshgrid(self.col.value,self.row.value)
            fill[0,:,:] = row_coords
            fill[1,:,:] = col_coords
            self._value = fill
        return(self._value)