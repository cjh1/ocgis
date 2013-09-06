from osgeo.osr import SpatialReference
from fiona.crs import from_string, to_string
import numpy as np
from ocgis.util.logging_ocgis import ocgis_lh
from ocgis.exc import SpatialWrappingError
from ocgis.util.spatial.wrap import Wrapper
from ocgis.util.helpers import iter_array


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
        if np.any(spatial.grid.col.value > 180.):
            ret = True
        else:
            ret = False
        return(ret)
    
    def get_wrap_axis(self,spatial):
        pm = 0.0
        if spatial.grid.col.bounds is not None:
            ref = spatial.grid.col.bounds
            for idx in range(ref.shape[0]):
                if ref[idx,0] < 0 and ref[idx,1] > 0:
                    pm = ref[idx,0]
                    break
        return(pm)

    def unwrap(self,spatial):
        if not self.get_is_360(spatial):
            unwrap = Wrapper(axis=self.get_wrap_axis(spatial)).unwrap
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
            wrap = Wrapper(axis=self.get_wrap_axis(spatial)).wrap
            to_wrap = [spatial.geom._point,spatial.geom._polygon]
            for tw in to_wrap:
                if tw is not None:
                    geom = tw.value.data
                    for (ii,jj),to_wrap in iter_array(geom,return_value=True):
                        geom[ii,jj] = wrap(to_wrap)
            spatial.grid = None
        else:
            ocgis_lh(exc=SpatialWrappingError('Data does not have a 0 to 360 coordinate system.'))