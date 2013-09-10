import unittest
from ocgis.interface.base.crs import CoordinateReferenceSystem, WGS84
from ocgis.interface.base.dimension.base import VectorDimension
from ocgis.interface.base.dimension.spatial import SpatialGridDimension,\
    SpatialDimension
from ocgis.exc import SpatialWrappingError
from ocgis.test.base import TestBase
import numpy as np
from copy import deepcopy
from shapely.geometry.multipolygon import MultiPolygon
import tempfile
from ocgis.util.helpers import get_temp_path


class TestCoordinateReferenceSystem(TestBase):

    def test_constructor(self):
        crs = CoordinateReferenceSystem(epsg=4326)
        self.assertEqual(crs.sr.ExportToProj4(),'+proj=longlat +ellps=WGS84 +towgs84=0,0,0,0,0,0,0 +no_defs ')
        
        crs2 = CoordinateReferenceSystem(prjs='+proj=longlat +ellps=WGS84 +towgs84=0,0,0,0,0,0,0 +no_defs ')
        self.assertTrue(crs == crs2)
        self.assertFalse(crs != crs2)
        
class TestWGS84(TestBase):
    
    def test_wrap_normal_differing_data_types(self):
        row = VectorDimension(value=40.,bounds=[38.,42.])
        col = VectorDimension(value=0,bounds=[-1,1])
        with self.assertRaises(ValueError):
            SpatialGridDimension(row=row,col=col).value
            
    def test_wrap_normal(self):
        row = VectorDimension(value=40.,bounds=[38.,42.])
        col = VectorDimension(value=0.,bounds=[-1.,1.])
        grid = SpatialGridDimension(row=row,col=col)   
        self.assertEqual(grid.resolution,3.0)
        sdim = SpatialDimension(grid=grid,crs=WGS84())
        with self.assertRaises(SpatialWrappingError):
            sdim.crs.wrap(sdim)
        sdim.crs.unwrap(sdim)
        self.assertNotEqual(sdim.grid,None)
        self.assertNumpyAll(sdim.grid.value,np.ma.array(data=[[[40.0]],[[0.0]]],mask=[[[False]],[[False]]],))
    
    def test_wrap_360(self):
        row = VectorDimension(value=40.,bounds=[38.,42.])
        col = VectorDimension(value=181.5,bounds=[181.,182.])
        grid = SpatialGridDimension(row=row,col=col)
        self.assertEqual(grid.value[1,0,0],181.5)
        sdim = SpatialDimension(grid=grid,crs=WGS84())
        orig_sdim = deepcopy(sdim)
        orig_grid = deepcopy(sdim.grid)
        sdim.crs.wrap(sdim)
        self.assertNumpyAll(np.array(sdim.geom.point.value[0,0]),np.array([-178.5,40.]))
        self.assertEqual(sdim.geom.polygon.value[0,0].bounds,(-179.0,38.0,-178.0,42.0))
        self.assertNumpyNotAll(orig_grid.value,sdim.grid.value)
        sdim.crs.unwrap(sdim)
        to_test = ([sdim.grid.value,orig_sdim.grid.value],[sdim.get_grid_bounds(),orig_sdim.get_grid_bounds()])
        for tt in to_test:
            self.assertNumpyAll(*tt)
    
    def test_wrap_360_cross_axis(self):
        row = VectorDimension(value=40,bounds=[38,42])
        col = VectorDimension(value=180,bounds=[179,181])
        grid = SpatialGridDimension(row=row,col=col)
        sdim = SpatialDimension(grid=grid,crs=WGS84())
        orig_sdim = deepcopy(sdim)
        sdim.crs.wrap(sdim)
        self.assertIsInstance(sdim.geom.polygon.value[0,0],MultiPolygon)
        sdim.crs.unwrap(sdim)
        self.assertEqual(orig_sdim.geom.polygon.value[0,0].bounds,sdim.geom.polygon.value[0,0].bounds)
        for target in ['point','polygon']:
            path = get_temp_path(name=target,suffix='.shp',wd=self._test_dir)
            sdim.write_fiona(path,target)

if __name__ == "__main__":
    #import sys;sys.argv = ['', 'Test.testName']
    unittest.main()