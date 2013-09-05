import unittest
from ocgis.interface.base.crs import CoordinateReferenceSystem
from ocgis.interface.base.dimension.base import VectorDimension
from ocgis.interface.base.dimension.spatial import SpatialGridDimension


class TestCoordinateReferenceSystem(unittest.TestCase):

    def test_constructor(self):
        crs = CoordinateReferenceSystem(epsg=4326)
        self.assertEqual(crs.sr.ExportToProj4(),'+proj=longlat +ellps=WGS84 +towgs84=0,0,0,0,0,0,0 +no_defs ')
        
        crs2 = CoordinateReferenceSystem(prjs='+proj=longlat +ellps=WGS84 +towgs84=0,0,0,0,0,0,0 +no_defs ')
        self.assertTrue(crs == crs2)
        self.assertFalse(crs != crs2)
        
    def test_wrap(self):
        row = VectorDimension(value=40,bounds=[38,42])
        col = VectorDimension(value=0,bounds=[-1,1])
        grid = SpatialGridDimension(row=row,col=col)
        grid.resolution
        import ipdb;ipdb.set_trace()


if __name__ == "__main__":
    #import sys;sys.argv = ['', 'Test.testName']
    unittest.main()