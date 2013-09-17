from osgeo.osr import SpatialReference
from fiona.crs import from_string, to_string
import numpy as np
from ocgis.util.logging_ocgis import ocgis_lh
from ocgis.exc import SpatialWrappingError
from ocgis.util.spatial.wrap import Wrapper
from ocgis.util.helpers import iter_array
from shapely.geometry.geo import mapping
from shapely.geometry.multipolygon import MultiPolygon


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
            
        sr = SpatialReference()
        sr.ImportFromProj4(to_string(crs))
        self.value = from_string(sr.ExportToProj4())
    
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
        super(WGS84,self).__init__(epsg=4326)

    def get_is_360(self,spatial):
        try:
            if spatial.grid.col.bounds is None:
                check = spatial.grid.col.value
            else:
                check = spatial.grid.col.bounds
        except AttributeError as e:
            ## column dimension is likely missing
            try:
                if spatial.grid.col is None:
                    check = spatial.get_grid_bounds()
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
            to_wrap = [spatial.geom._point,spatial.geom._polygon]
            for tw in to_wrap:
                if tw is not None:
                    geom = tw.value.data
                    for (ii,jj),to_wrap in iter_array(geom,return_value=True):
                        geom[ii,jj] = unwrap(to_wrap)
            spatial.grid = None
        else:
            ocgis_lh(exc=SpatialWrappingError('Data already has a 0 to 360 coordinate system.'))
    
    def wrap(self,spatial):
        if self.get_is_360(spatial):
            wrap = Wrapper().wrap
            to_wrap = [spatial.geom.point,spatial.geom.polygon]
            for tw in to_wrap:
                if tw is not None:
                    geom = tw.value.data
                    for (ii,jj),to_wrap in iter_array(geom,return_value=True):
                        geom[ii,jj] = wrap(to_wrap)
            spatial.grid = None
        else:
            ocgis_lh(exc=SpatialWrappingError('Data does not have a 0 to 360 coordinate system.'))