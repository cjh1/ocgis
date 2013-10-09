from osgeo.osr import SpatialReference
from fiona.crs import from_string, to_string
import numpy as np
from ocgis.util.logging_ocgis import ocgis_lh
from ocgis.exc import SpatialWrappingError, ProjectionCoordinateNotFound,\
    ProjectionDoesNotMatch, ImproperPolygonBoundsError
from ocgis.util.spatial.wrap import Wrapper
from ocgis.util.helpers import iter_array, assert_raise
from shapely.geometry.multipolygon import MultiPolygon
import abc
import logging


class CoordinateReferenceSystem(object):
    
    def __init__(self,crs=None,prjs=None,epsg=None):
        if crs is None:
            if prjs is not None:
                crs = from_string(prjs)
            elif epsg is not None:
                sr = SpatialReference()
                sr.ImportFromEPSG(epsg)
                crs = from_string(sr.ExportToProj4())
            else:
                raise(NotImplementedError)
        else:
            ## remove unicode and change to python types
            for k,v in crs.iteritems():
                if type(v) == unicode:
                    crs[k] = str(v)
                else:
                    try:
                        crs[k] = v.tolist()
                    except AttributeError:
                        continue
            
        sr = SpatialReference()
        sr.ImportFromProj4(to_string(crs))
        self.value = from_string(sr.ExportToProj4())
    
        try:
            assert(self.value != {})
        except AssertionError:
            ocgis_lh(logger='crs',exc=ValueError('Empty CRS: The conversion to PROJ4 may have failed. The CRS value is: {0}'.format(crs)))
    
    def __eq__(self,other):
        return(self.value == other.value)
    
    def __ne__(self,other):
        return(not self.value == other.value)
    
    @property
    def sr(self):
        sr = SpatialReference()
        sr.ImportFromProj4(to_string(self.value))
        return(sr)
    
    
class WGS84(CoordinateReferenceSystem):
    
    def __init__(self):
        CoordinateReferenceSystem.__init__(self,epsg=4326)

    @classmethod
    def get_is_360(cls,spatial):
        if not isinstance(spatial.crs,cls):
            return(False)
        
        try:
            if spatial.grid.col.bounds is None:
                check = spatial.grid.col.value
            else:
                check = spatial.grid.col.bounds
        except AttributeError as e:
            ## column dimension is likely missing
            try:
                if spatial.grid.col is None:
                    try:
                        check = spatial.get_grid_bounds()
                    except ImproperPolygonBoundsError:
                        check = spatial.grid.value[1,:,:]
                else:
                    ocgis_lh(exc=e)
            except AttributeError as e:
                ## there may be no grid, access the geometries directly
                for geom in spatial.geom.polygon.value.compressed():
                    if isinstance(geom,MultiPolygon):
                        it = geom
                    else:
                        it = [geom]
                    for sub_geom in it:
                        if np.any(np.array(sub_geom.exterior.coords) > 180.):
                            return(True)
                return(False)
        if np.any(check > 180.):
            ret = True
        else:
            ret = False
        return(ret)

    def unwrap(self,spatial):
        if not self.get_is_360(spatial):
            unwrap = Wrapper().unwrap
            if spatial._grid is not None:
                ref = spatial.grid.value[1,:,:]
                select = ref < 0.
                ref[select] = ref[select] + 360.
                if spatial.grid.col is not None:
                    ref = spatial.grid.col.value
                    select = ref < 0.
                    ref[select] = ref[select] + 360.
                    if spatial.grid.col.bounds is not None:
                        ref = spatial.grid.col.bounds
                        select = ref < 0.
                        ref[select] = ref[select] + 360.
            to_wrap = [spatial.geom._point,spatial.geom._polygon]
            for tw in to_wrap:
                if tw is not None:
                    geom = tw.value.data
                    for (ii,jj),to_wrap in iter_array(geom,return_value=True):
                        geom[ii,jj] = unwrap(to_wrap)
        else:
            ocgis_lh(exc=SpatialWrappingError('Data already has a 0 to 360 coordinate system.'))
    
    def wrap(self,spatial):
        if self.get_is_360(spatial):
            wrap = Wrapper().wrap
            if spatial._grid is not None:
                ref = spatial.grid.value[1,:,:]
                select = ref > 180.
                ref[select] = ref[select] - 360.
                if spatial.grid.col is not None:
                    ref = spatial.grid.col.value
                    select = ref > 180.
                    ref[select] = ref[select] - 360.
                    if spatial.grid.col.bounds is not None:
                        ref = spatial.grid.col.bounds
                        select = ref > 180.
                        ref[select] = ref[select] - 360.
            to_wrap = [spatial.geom._point,spatial.geom._polygon]
            for tw in to_wrap:
                if tw is not None:
                    geom = tw.value.data
                    for (ii,jj),to_wrap in iter_array(geom,return_value=True):
                        geom[ii,jj] = wrap(to_wrap)
        else:
            ocgis_lh(exc=SpatialWrappingError('Data does not have a 0 to 360 coordinate system.'))
            
            
class CFCoordinateReferenceSystem(CoordinateReferenceSystem):
    __metaclass__ = abc.ABCMeta
    
    def __init__(self,**kwds):
        self.projection_x_coordinate = kwds.pop('projection_x_coordinate',None)
        self.projection_y_coordinate = kwds.pop('projection_y_coordinate',None)
        
        assert_raise(set(kwds.keys()) == set(self.map_parameters.keys()),logger='crs',
                     exc=ValueError('Proper keyword arguments are: {0}'.format(self.map_parameters.keys())))
        
        self.map_parameters_values = kwds
        crs = {'proj':self.proj_name}
        for k,v in kwds.iteritems():
            if k in self.iterable_parameters:
                v = getattr(self,self.iterable_parameters[k])(v)
                crs.update(v)
            else:
                crs.update({self.map_parameters[k]:v})
                
        super(CFCoordinateReferenceSystem,self).__init__(crs=crs)
            
    @abc.abstractproperty
    def grid_mapping_name(self): str
    
    @abc.abstractproperty
    def iterable_parameters(self): dict
    
    @abc.abstractproperty
    def map_parameters(self): dict
    
    @abc.abstractproperty
    def proj_name(self): str
    
    def format_standard_parallel(self,value):
        if isinstance(value,np.ndarray):
            value = value.tolist()
            
        ret = {}
        try:
            it = iter(value)
        except TypeError:
            it = [value]
        for ii,v in enumerate(it,start=1):
            ret.update({self.map_parameters['standard_parallel'].format(ii):v})
        return(ret)
    
    @classmethod
    def load_from_metadata(cls,var,meta):
        
        def _get_projection_coordinate_(target,meta):
            key = 'projection_{0}_coordinate'.format(target)
            for k,v in meta['variables'].iteritems():
                if 'standard_name' in v['attrs']:
                    if v['attrs']['standard_name'] == key:
                        return(k)
            ocgis_lh(logger='crs',exc=ProjectionCoordinateNotFound(key))
            
        r_var = meta['variables'][var]
        
        try:
            ## look for the grid_mapping attribute on the target variable
            r_grid_mapping = meta['variables'][r_var['attrs']['grid_mapping']]
        except KeyError:
            raise(ProjectionDoesNotMatch)
        try:
            grid_mapping_name = r_grid_mapping['attrs']['grid_mapping_name']
        except KeyError:
            ocgis_lh(logger='crs',level=logging.WARN,msg='"grid_mapping" variable "{0}" does not have a "grid_mapping_name" attribute'.format(r_grid_mapping['name']))
            raise(ProjectionDoesNotMatch)
        if grid_mapping_name != cls.grid_mapping_name:
            raise(ProjectionDoesNotMatch)
        pc_x,pc_y = [_get_projection_coordinate_(target,meta) for target in ['x','y']]
        
        kwds = r_grid_mapping['attrs']
        kwds.pop('grid_mapping_name',None)
        kwds['projection_x_coordinate'] = pc_x
        kwds['projection_y_coordinate'] = pc_y
        
        cls._load_from_metadata_finalize_(kwds,var,meta)

        return(cls(**kwds))
    
    @classmethod
    def _load_from_metadata_finalize_(cls,kwds,var,meta):
        pass


class CFWGS84(WGS84,CFCoordinateReferenceSystem,):
    grid_mapping_name = 'latitude_longitude'
    iterable_parameters = None
    map_parameters = None
    proj_name = None
    
    def __init__(self):
        WGS84.__init__(self)
    
    @classmethod
    def load_from_metadata(cls,var,meta):
        try:
            r_grid_mapping = meta['variables'][var]['attrs']['grid_mapping']
            if r_grid_mapping == cls.grid_mapping_name:
                return(cls())
            else:
                raise(ProjectionDoesNotMatch)
        except KeyError:
            raise(ProjectionDoesNotMatch)
    
    
class CFAlbersEqualArea(CFCoordinateReferenceSystem):
    grid_mapping_name = 'albers_conical_equal_area'
    iterable_parameters = {'standard_parallel':'format_standard_parallel'}
    map_parameters = {'standard_parallel':'lat_{0}',
                      'longitude_of_central_meridian':'lon_0',
                      'latitude_of_projection_origin':'lat_0',
                      'false_easting':'x_0',
                      'false_northing':'y_0'}
    proj_name = 'aea'


class CFLambertConformal(CFCoordinateReferenceSystem):
    grid_mapping_name = 'lambert_conformal_conic'
    iterable_parameters = {'standard_parallel':'format_standard_parallel'}
    map_parameters = {'standard_parallel':'lat_{0}',
                      'longitude_of_central_meridian':'lon_0',
                      'latitude_of_projection_origin':'lat_0',
                      'false_easting':'x_0',
                      'false_northing':'y_0',
                      'units':'units'}
    proj_name = 'lcc'
    
    @classmethod
    def _load_from_metadata_finalize_(cls,kwds,var,meta):
        kwds['units'] = meta['variables'][kwds['projection_x_coordinate']]['attrs'].get('units')
