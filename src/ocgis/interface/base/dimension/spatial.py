import base
import numpy as np
from ocgis.util.logging_ocgis import ocgis_lh
from ocgis.util.helpers import iter_array, get_none_or_slice, get_slice,\
    get_formatted_slice
from shapely.geometry.point import Point
from ocgis import constants
import itertools
from shapely.geometry.polygon import Polygon
from copy import copy
from shapely.prepared import prep
from shapely.geometry.multipoint import MultiPoint
from shapely.geometry.multipolygon import MultiPolygon
from ocgis.exc import EmptySubsetError, ImproperPolygonBoundsError
from osgeo.ogr import CreateGeometryFromWkb
from shapely import wkb


class SpatialDimension(base.AbstractUidDimension):
    _ndims = 2
    _axis = 'SPATIAL'
    _attrs_slice = ('uid','grid','_geom')
    
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
    
    @property
    def geom(self):
        if self._geom is None:
            self._geom = SpatialGeometryDimension(grid=self.grid,uid=self.grid.uid)
        return(self._geom)
    
    @property
    def shape(self):
        if self.grid is None:
            ret = self.geom.shape
        else:
            ret = self.grid.shape
        return(ret)
        
    @property
    def weights(self):
        if self.geom is None:
            ret = self.grid.weights
        else:
            try:
                ret = self.geom.polygon.weights
            except ImproperPolygonBoundsError:
                ret = self.geom.point.weights
        return(ret)
    
    def get_clip(self,polygon,return_indices=False):
        assert(type(polygon) in (Polygon,MultiPolygon))
        
        ret,slc = self.get_intersects(polygon,return_indices=True)
        
        ## clipped geometries have no grid or point representations
        ret.grid = None
        ret.geom.grid = None
        ret.geom._point = None
        
        ref_value = ret.geom.polygon.value
        for (row_idx,col_idx),geom in iter_array(ref_value,return_value=True):
            ref_value[row_idx,col_idx] = geom.intersection(polygon)
        
        if return_indices:
            ret = (ret,slc)
        
        return(ret)
        
    def get_grid_bounds(self):
        if self.geom.polygon is not None:
            shp = list(self.geom.polygon.shape) + [4]
            fill = np.empty(shp)
            fill_mask = np.zeros(fill.shape,dtype=bool)
            r_mask = self.geom.polygon.value.mask
            for (idx_row,idx_col),geom in iter_array(self.geom.polygon.value,use_mask=False,return_value=True):
                fill[idx_row,idx_col,:] = geom.bounds
                fill_mask[idx_row,idx_col,:] = r_mask[idx_row,idx_col]
            fill = np.ma.array(fill,mask=fill_mask)
        else:
            raise(NotImplementedError)
        return(fill)
    
    def get_intersects(self,point_or_polygon,return_indices=False):
        ret = copy(self)
        if type(point_or_polygon) in (Point,MultiPoint):
            raise(NotImplementedError)
        elif type(point_or_polygon) in (Polygon,MultiPolygon):
            ## for a polygon subset, first the grid is subsetted by the bounds
            ## of the polygon object. the intersects operations is then performed
            ## on the polygon/point representation as appropriate.
            minx,miny,maxx,maxy = point_or_polygon.bounds
            if self.grid is None:
                raise(NotImplementedError)
            else:
                ## reset any geometries
                ret._geom = None
                ## subset the grid by its bounding box
                ret.grid,slc = ret.grid.get_subset_bbox(miny,minx,maxy,maxx,return_indices=True)
                ## attempt to mask the polygons
                try:
                    ret.geom._polygon = ret.geom.polygon.get_intersects_masked(point_or_polygon)
                    grid_mask = ret.geom._polygon.value.mask
                except ImproperPolygonBoundsError:
                    ret.geom._point = ret.geom.point.get_intersects_masked(point_or_polygon)
                    grid_mask = ret.geom._point.value.mask
                ## transfer the geometry mask to the grid mask
                ret.grid.value.mask[:,:,:] = grid_mask.copy()
        else:
            raise(NotImplementedError)
        
        if return_indices:
            ret = (ret,slc)
        
        return(ret)
    
    def get_iter(self):
        ocgis_lh(exc=NotImplementedError('Spatial dimensions do not have a direct iterator.'))
    
    def get_mask(self):
        if self.grid is None:
            if self.geom.point is None:
                ret = self.geom.polygon.value.mask
            else:
                ret = self.geom.point.value.mask
        else:
            ret = self.grid.value.mask[0,:,:]
        return(ret.copy())
    
    def update_crs(self,to_crs):
        ## if the crs values are the same, pass through
        if to_crs != self.crs:
            to_sr = to_crs.sr
            from_sr = self.crs.sr
            
            if self.geom.point is not None:
                self.geom.point.update_crs(to_sr,from_sr)
            try:
                self.geom.polygon.update_crs(to_sr,from_sr)
            except ImproperPolygonBoundsError:
                pass
            
            if self.grid is not None:
                r_grid_value = self.grid.value.data
                r_point_value = self.geom.point.value.data
                for (idx_row,idx_col),geom in iter_array(r_point_value,return_value=True):
                    x,y = geom.x,geom.y
                    r_grid_value[0,idx_row,idx_col] = y
                    r_grid_value[1,idx_row,idx_col] = x
            
            self.crs = to_crs
    
    def _format_uid_(self,value):
        return(np.atleast_2d(value))
        
    def _get_uid_(self):
        if self._geom is not None:
            ret = self._geom.uid
        else:
            ret = self.grid.uid
        return(ret)

    
class SpatialGridDimension(base.AbstractUidValueDimension):
    _axis = 'GRID'
    _ndims = 2
    _attrs_slice = None
    
    def __init__(self,*args,**kwds):
        self.row = kwds.pop('row',None)
        self.col = kwds.pop('col',None)
        
        super(SpatialGridDimension,self).__init__(*args,**kwds)
        
    def __getitem__(self,slc):
        slc = get_formatted_slice(slc,2)
        ret = copy(self)
        ret.uid = ret.uid[slc]
        
        if ret._value is not None:
            ret._value = ret._value[:,slc[0],slc[1]]
            
        if ret.row is not None:
            ret.row = ret.row[slc[0]]
            ret.col = ret.col[slc[1]]
            
        return(ret)
        
    @property
    def resolution(self):
        return(np.mean([self.row.resolution,self.col.resolution]))
    
    @property
    def shape(self):
        if self.row is None:
            ret = self.value.shape[1],self.value.shape[2]
        else:
            ret = len(self.row),len(self.col)
        return(ret)
        
    def get_subset_bbox(self,min_row,min_col,max_row,max_col,return_indices=False):
        if self.row is None:
            raise(NotImplementedError('no slicing w/out rows and columns'))
        else:
            ret = copy(self)
            ret._value = None
            ret.row,row_indices = self.row.get_between(min_row,max_row,return_indices=True)
            ret.col,col_indices = self.col.get_between(min_col,max_col,return_indices=True)
            row_slc = get_slice(row_indices)
            col_slc = get_slice(col_indices)
            ret.uid = self.uid[row_slc,col_slc]
        if return_indices:
            ret = (ret,(row_slc,col_slc))
        return(ret)
    
    def _format_private_value_(self,value):
        if value is None:
            ret = None
        else:
            assert(len(value.shape) == 3)
            assert(value.shape[0] == 2)
            assert(isinstance(value,np.ma.MaskedArray))
            ret = value
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
        if self._value is None:
            shp = len(self.row),len(self.col)
        else:
            shp = self._value.shape[1],self._value.shape[2]
        ret = np.arange(1,(shp[0]*shp[1])+1).reshape(shp)
        return(ret)
    
    def _get_value_(self):
        ## fill the centroids
        fill = np.empty((2,self.row.shape[0],self.col.shape[0]),dtype=self.row.value.dtype)
        fill = np.ma.array(fill,mask=False)
        col_coords,row_coords = np.meshgrid(self.col.value,self.row.value)
        fill[0,:,:] = row_coords
        fill[1,:,:] = col_coords
        return(fill)
    
    
class SpatialGeometryDimension(base.AbstractUidDimension):
    _axis = 'GEOM'
    _ndims = 2
    _attrs_slice = ('uid','grid','_point','_polygon')
    
    def __init__(self,*args,**kwds):
        self.grid = kwds.pop('grid',None)
        self._point = kwds.pop('point',None)
        self._polygon = kwds.pop('polygon',None)
        
        super(SpatialGeometryDimension,self).__init__(*args,**kwds)
    
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
    def shape(self):
        if self.point is None:
            ret = self.polygon.shape
        else:
            ret = self.point.shape
        return(ret)
    
    def get_iter(self):
        raise(NotImplementedError)
        
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


class SpatialGeometryPointDimension(base.AbstractUidValueDimension):
    _axis = 'POINT'
    _ndims = 2
    _attrs_slice = ('uid','_value','grid')
    
    def __init__(self,*args,**kwds):
        self.grid = kwds.pop('grid',None)
        
        super(SpatialGeometryPointDimension,self).__init__(*args,**kwds)
        
    @property
    def weights(self):
        ret = np.ones(self.value.shape,dtype=constants.np_float)
        ret = np.ma.array(ret,mask=self.value.mask)
        return(ret)
        
    def get_intersects_masked(self,point_or_polygon):
        
        if type(point_or_polygon) in (Point,MultiPoint):
            keep_touches = True
        elif type(point_or_polygon) in (Polygon,MultiPolygon):
            keep_touches = False
        else:
            raise(NotImplementedError)
        
        ret = copy(self)
        fill = np.ma.array(ret.value,mask=True)
        ref_fill_mask = fill.mask
        ref_touches = point_or_polygon.touches
        prepared = prep(point_or_polygon)

        for (ii,jj),geom in iter_array(self.value,return_value=True):
            if prepared.intersects(geom):
                only_touches = ref_touches(geom)
                fill_mask = False
                if only_touches:
                    if keep_touches == False:
                        fill_mask = True
                ref_fill_mask[ii,jj] = fill_mask
        
        if ref_fill_mask.all():
            ocgis_lh(exc=EmptySubsetError(self.name))
            
        ret._value = fill
        
        return(ret)
    
    def update_crs(self,to_sr,from_sr):
        ## project masked geometries!!
        r_value = self.value.data
        r_loads = wkb.loads
        for (idx_row,idx_col),geom in iter_array(r_value,return_value=True,use_mask=False):
            ogr_geom = CreateGeometryFromWkb(geom.wkb)
            ogr_geom.AssignSpatialReference(from_sr)
            ogr_geom.TransformTo(to_sr)
            r_value[idx_row,idx_col] = r_loads(ogr_geom.ExportToWkb())
        
    def _format_private_value_(self,value):
        if value is not None:
            try:
                assert(len(value.shape) == 2)
                ret = value
            except (AssertionError,AttributeError):
                ocgis_lh(exc=ValueError('Geometry values must come in as 2-d NumPy arrays to avoid array interface modifications by shapely.'))
        else:
            ret = None
        ret = self._get_none_or_array_(ret,masked=True)
        return(ret)
    
    def _get_geometry_fill_(self,shape=None):
        if shape is None:
            shape = (self.grid.shape[0],self.grid.shape[1])
            mask = self.grid.value[0].mask
        else:
            mask = False
        fill = np.ma.array(np.zeros(shape),mask=mask,dtype=object)

        return(fill)
    
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
                ocgis_lh(exc=ImproperPolygonBoundsError('Polygon dimensions require a row and column dimension with bounds.'))
            else:
                if self.grid.row.bounds[0,0] == self.grid.row.bounds[0,1]:
                    ocgis_lh(exc=ImproperPolygonBoundsError('Polygon dimensions require row and column dimension bounds to have delta > 0.'))
    
    @property
    def area(self):
        r_value = self.value
        fill = np.ones(r_value.shape,dtype=constants.np_float)
        fill = np.ma.array(fill,mask=r_value.mask)
        for (ii,jj),geom in iter_array(r_value,return_value=True):
            fill[ii,jj] = geom.area
        return(fill)
    
    @property
    def weights(self):
        return(self.area/self.area.max())
    
    def _get_value_(self):
        ref_row_bounds = self.grid.row.bounds
        ref_col_bounds = self.grid.col.bounds
        fill = self._get_geometry_fill_()
        for idx_row,idx_col in itertools.product(range(ref_row_bounds.shape[0]),range(ref_col_bounds.shape[0])):
            row_min,row_max = ref_row_bounds[idx_row,:].min(),ref_row_bounds[idx_row,:].max()
            col_min,col_max = ref_col_bounds[idx_col,:].min(),ref_col_bounds[idx_col,:].max()
            fill[idx_row,idx_col] = Polygon([(col_min,row_min),(col_min,row_max),(col_max,row_max),(col_max,row_min)])
        return(fill)
