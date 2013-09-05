from osgeo.osr import SpatialReference
from fiona.crs import from_string, to_string


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