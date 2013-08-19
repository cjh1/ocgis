from base import AbstractDimension
import numpy as np
from ocgis.util.logging_ocgis import ocgis_lh
from ocgis.util.helpers import iter_array, get_none_or_slice, get_slice
from shapely.geometry.point import Point
from ocgis import constants
import itertools
from shapely.geometry.polygon import Polygon
from ocgis.interface.base.dimension.base import Abstract2d
from copy import copy
from shapely.geometry.base import BaseGeometry


class SpatialDimension(AbstractDimension):
    
    def __init__(self,*args,**kwds):
        self.grid = kwds.pop('grid',None)
        self.crs = kwds.pop('crs',None)
        self._geom = kwds.pop('geom',None)
        
        if self.grid is None and self._geom is None:
            try:
                self.grid = SpatialGridDimension(row=kwds.pop('row'),
                                                 col=kwds.pop('col'))
            except KeyError:
                ocgis_lh(exc=ValueError('A SpatialDimension without "grid" or "geom" arguments requires a "row" and "column".'))
        
        super(SpatialDimension,self).__init__(*args,**kwds)
            
    def __getitem__(self,slc):
        try:
            assert(len(slc) == 2)
        except (AssertionError,TypeError):
            ocgis_lh(exc=IndexError('SpatialDimensions only support two-dimensional slicing.'))
        
        ret = copy(self)
        ret.uid = ret.uid[slc[0],slc[1]]
        ret.grid = get_none_or_slice(ret.grid,slc)
        ret._geom = get_none_or_slice(ret._geom,slc)
        
        return(ret)
    
    def __iter__(self):
        ocgis_lh(exc=NotImplementedError('Spatial dimensions do not have a direct iterator.'))
    
    @property
    def geom(self):
        if self._geom is None:
            self._geom = SpatialGeometryDimension(grid=self.grid,uid=self.grid.uid)
        return(self._geom)
    
    @property
    def value(self):
        ocgis_lh(exc=NotImplementedError('Spatial dimension values should be accessed through "grid" and/or "geom".'))
    @value.setter
    def value(self,value):
        self._value = value
        
    def _format_uid_(self,value):
        return(np.atleast_2d(value))
        
    def _get_uid_(self):
        if self._geom is not None:
            ret = self._geom.uid
        else:
            ret = self.grid.uid
        return(ret)

    
class SpatialGridDimension(Abstract2d,AbstractDimension):
    
    def __init__(self,*args,**kwds):
        for key in ['value','bounds']:
            if kwds.get(key) is not None:
                assert(all([isinstance(v,np.ma.MaskedArray) for v in kwds[key]]))
        
        self.row = kwds.pop('row',None)
        self.col = kwds.pop('col',None)
        
        super(SpatialGridDimension,self).__init__(*args,**kwds)
        
    def __iter__(self):
        raise(NotImplementedError)
        
    @property
    def resolution(self):
        raise(NotImplementedError)
    
    @property
    def shape(self):
        return(self.uid.shape)
    
    @property
    def value(self):
        if self._value is None:
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
        
    def get_subset_bbox(self,min_row,min_col,max_row,max_col):
        if self.row is None:
            raise(NotImplementedError)
        else:
            ret = copy(self)
            ret.value = None
            ret.row,row_indices = self.row.get_between(min_row,max_row,return_indices=True)
            ret.col,col_indices = self.col.get_between(min_col,max_col,return_indices=True)
            row_slc = get_slice(row_indices)
            col_slc = get_slice(col_indices)
            ret.uid = ret.uid[row_slc,col_slc]
        return(ret)
        
    def _get_slice_(self,state,slc):

        if self._value is None:
            state._value = None
        else:
            state._value = state.value[:,slc[0],slc[1]]
        if state.row is not None:
            state.row = state.row[slc[0]]
            state.col = state.col[slc[1]]
        
        return(state)
        
    def _get_uid_(self):
        try:
            shp = (self.value.shape[1]*self.value.shape[2])
            ret = np.arange(1,(shp[0]*shp[1])+1,dtype=constants.np_int)
            ret = ret.reshape(shp)
        except:
            try:
                shp = (self.row.shape[0],self.col.shape[0])
                ret = np.arange(1,(shp[0]*shp[1])+1,dtype=constants.np_int)
                ret = ret.reshape(shp)
            except Exception as e:
                ocgis_lh(exc=e)
        return(ret)
    
    
class SpatialGeometryDimension(Abstract2d,AbstractDimension):
    
    def __init__(self,*args,**kwds):
        self.grid = kwds.pop('grid',None)
        self._point = kwds.pop('point',None)
        self._polygon = kwds.pop('polygon',None)
        
        super(SpatialGeometryDimension,self).__init__(*args,**kwds)
    
    def __iter__(self):
        raise(NotImplementedError)
    
    @property
    def point(self):
        if self._point == None and self.grid is not None:
            self._point = SpatialGeometryPointDimension(grid=self.grid,uid=self.grid.uid)
        return(self._point)
    
    @property
    def polygon(self):
        if self._polygon == None and self.grid is not None:
            self._polygon = SpatialGeometryPolygonDimension(grid=self.grid,uid=self.grid.uid)
        return(self._polygon)
    
    @property
    def value(self):
        ocgis_lh(exc=NotImplementedError('Geometry dimensions do not have a direct value. Chose "...geom.point.value" or "...geom.polygon.value" instead.'))
    @value.setter
    def value(self,value):
        self._value = value
        
    def _get_slice_(self,state,slc):
        state._point = get_none_or_slice(state._point,slc)
        state._polygon = get_none_or_slice(state._polygon,slc)
        return(state)
        
    def _get_uid_(self):
        if self.grid is not None:
            ret = self.grid.uid
        elif self._point is not None:
            ret = self._point.uid
        else:
            ret = self._polygon.uid
        return(ret)


class SpatialGeometryPointDimension(Abstract2d,AbstractDimension):
    
    def __init__(self,*args,**kwds):
        self.grid = kwds.pop('grid',None)
        
        super(SpatialGeometryPointDimension,self).__init__(*args,**kwds)
        
    def _format_value_(self,value):
        if value is not None:
            try:
                assert(len(value.shape) == 2)
            except (AssertionError,AttributeError):
                ocgis_lh(exc=ValueError('Geometry values must come in as 2-d NumPy arrays to avoid array interface modifications by shapely.'))
            if not isinstance(value,np.ma.MaskedArray):
                value = np.ma.array(value,mask=False)
        ret = super(self.__class__,self)._format_value_(value)
        return(ret)
    
    def _get_geometry_fill_(self):
        fill = np.ma.array(np.zeros((self.grid.shape[0],self.grid.shape[1])),
                           mask=self.grid.value[0].mask,dtype=object)
        return(fill)
    
    def _get_slice_(self,state,slc):
        state.value = state.value[slc[0],slc[1]]
        return(state)
    
    def _get_value_(self):
        ref_grid = self.grid.value
        fill = self._get_geometry_fill_()
        for idx_row,idx_col in iter_array(ref_grid[0]):
            y = ref_grid[0,idx_row,idx_col]
            x = ref_grid[1,idx_row,idx_col]
            fill[idx_row,idx_col] = Point(x,y)
        return(fill)
    
    
class SpatialGeometryPolygonDimension(SpatialGeometryPointDimension):
    
    def __init__(self,*args,**kwds):
        super(SpatialGeometryPolygonDimension,self).__init__(*args,**kwds)
        
        if self._value is None:
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
        
    def _get_value_(self):
        ref_row_bounds = self.grid.row.bounds
        ref_col_bounds = self.grid.col.bounds
        fill = self._get_geometry_fill_()
        for idx_row,idx_col in itertools.product(range(ref_row_bounds.shape[0]),range(ref_col_bounds.shape[0])):
            row_min,row_max = ref_row_bounds[idx_row,:]
            col_min,col_max = ref_col_bounds[idx_col,:]
            fill[idx_row,idx_col] = Polygon([(col_min,row_min),(col_min,row_max),(col_max,row_max),(col_max,row_min)])
        return(fill)
