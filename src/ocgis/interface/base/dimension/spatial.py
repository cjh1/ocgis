from base import AbstractDimension
import numpy as np
from copy import copy
from ocgis.util.logging_ocgis import ocgis_lh
from ocgis.util.helpers import iter_array, get_isempty
from shapely.geometry.point import Point
from ocgis import constants
import itertools
from shapely.geometry.polygon import Polygon


class SpatialDimension(AbstractDimension):
    
    def __init__(self,*args,**kwds):
        self.grid = kwds.pop('grid',None)
        self.crs = kwds.pop('crs',None)
        self._geom = kwds.pop('geom',None)
        
        if self.grid is None and self._geom is None:
            self.grid = SpatialGridDimension(row=kwds.pop('row',None),
                                             col=kwds.pop('col',None))
        
        super(SpatialDimension,self).__init__(*args,**kwds)
            
    def __getitem__(self,slc):
        raise(NotImplementedError)
    
    def __iter__(self):
        raise(NotImplementedError)
    
    @property
    def geom(self):
        if self._geom is None:
            self._geom = SpatialGeometryDimension(grid=self.grid)
        return(self._geom)
    
    @property
    def uid(self):
        raise(NotImplementedError)
    @uid.setter
    def uid(self,value):
        self._uid = value
    
    @property
    def value(self):
        raise(NotImplementedError)
    @value.setter
    def value(self,value):
        self._value = value
    
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
    def uid(self):
        if self._uid is None:
            self._uid = np.arange(1,self.value.shape[1]*self.value.shape[2]+1,dtype=constants.np_int).\
                        reshape(self.value.shape[1],self.value.shape[2])
        return(self._uid)
    @uid.setter
    def uid(self,value):
        self._uid = value
    
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
    @value.setter
    def value(self,value):
        self._value = value
    
    
class SpatialGeometryDimension(AbstractDimension):
    
    def __init__(self,*args,**kwds):
        self.grid = kwds.pop('grid',None)
        
        super(SpatialGeometryDimension,self).__init__(*args,**kwds)
        
        self._point = None
        self._polygon = None
        
    def __getitem__(self,slc):
        raise(NotImplementedError)
    
    def __iter__(self):
        raise(NotImplementedError)
    
    @property
    def point(self):
        if self._point == None:
            self._point = SpatialGeometryPointDimension(grid=self.grid)
        return(self._point)
    
    @property
    def polygon(self):
        if self._polygon == None:
            self._polygon = SpatialGeometryPolygonDimension(grid=self.grid)
        return(self._polygon)
    
    @property
    def value(self):
        ocgis_lh(exc=NotImplementedError('Geometry dimensions do not have a direct value. Chose "...geom.point.value" or "...geom.polygon.value" instead.'))
    @value.setter
    def value(self,value):
        self._value = value
    
class SpatialGeometryPointDimension(AbstractDimension):
    
    def __init__(self,*args,**kwds):
        self.grid = kwds.pop('grid',None)
        
        super(SpatialGeometryPointDimension,self).__init__(*args,**kwds)
    
    def __getitem__(self,slc):
        raise(NotImplementedError)
    
    def __iter__(self):
        raise(NotImplementedError)
    
    @property
    def value(self):
        if self._value is None:
            ref_grid = self.grid.value
            fill = self._get_geometry_fill_()
            for idx_row,idx_col in iter_array(ref_grid[0]):
                y = ref_grid[0,idx_row,idx_col]
                x = ref_grid[1,idx_row,idx_col]
                fill[idx_row,idx_col] = Point(x,y)
            self._value = fill
        return(self._value)
    @value.setter
    def value(self,value):
        self._value = value
    
    def _get_geometry_fill_(self):
        fill = np.ma.array(np.zeros(self.grid.shape),
                           mask=self.grid.value[0].mask,dtype=object)
        return(fill)
    
    
class SpatialGeometryPolygonDimension(SpatialGeometryPointDimension):
    
    def __init__(self,*args,**kwds):
        super(SpatialGeometryPolygonDimension,self).__init__(*args,**kwds)
        
        if self.grid.row is None:
            ocgis_lh(exc=ValueError('Polygon dimensions require a row and column dimension with bounds.'))
        else:
            if self.grid.row.bounds[0,0] == self.grid.row.bounds[0,1]:
                ocgis_lh(exc=ValueError('Polygon dimensions require row and column dimension bounds to have delta > 0.'))
    
    @property
    def value(self):
        if self._value is None:
            ref_row_bounds = self.grid.row.bounds
            ref_col_bounds = self.grid.col.bounds
            fill = self._get_geometry_fill_()
            for idx_row,idx_col in itertools.product(range(ref_row_bounds.shape[0]),range(ref_col_bounds.shape[0])):
                row_min,row_max = ref_row_bounds[idx_row,:]
                col_min,col_max = ref_col_bounds[idx_col,:]
                fill[idx_row,idx_col] = Polygon([(col_min,row_min),(col_min,row_max),(col_max,row_max),(col_max,row_min)])
            self._value = fill
        return(self._value)
    @value.setter
    def value(self,value):
        self._value = value
