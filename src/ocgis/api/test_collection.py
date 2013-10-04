import unittest
from ocgis.interface.base.test_field import AbstractTestField
from ocgis.api.collection import SpatialCollection
from ocgis.util.shp_cabinet import ShpCabinet
from shapely.geometry.multipolygon import MultiPolygon
import datetime
from ocgis import constants


class TestSpatialCollection(AbstractTestField):

    def test_constructor(self):
        field = self.get_field(with_value=True)
        sc = ShpCabinet()
        meta = sc.get_meta('state_boundaries')
        sp = SpatialCollection(meta=meta,key='state_boundaries')
        for row in sc.iter_geoms('state_boundaries'):
            sp.add_field(row['properties']['UGID'],row['geom'],field.variables.keys()[0],
                         field,properties=row['properties'])
        self.assertEqual(len(sp),51)
        self.assertIsInstance(sp.geoms[25],MultiPolygon)
        self.assertIsInstance(sp.properties[25],dict)
        self.assertEqual(sp[25]['tmax'].variables['tmax'].value.shape,(2, 31, 2, 3, 4))
    
    def test_iteration(self):
        field = self.get_field(with_value=True)
        
        field.temporal.name_uid = 'tid'
        field.level.name_uid = 'lid'
        field.spatial.geom.name_uid = 'gid'
        
        sc = ShpCabinet()
        meta = sc.get_meta('state_boundaries')
        sp = SpatialCollection(meta=meta,key='state_boundaries')
        for row in sc.iter_geoms('state_boundaries'):
            sp.add_field(row['properties']['UGID'],row['geom'],field.variables.keys()[0],
                         field,properties=row['properties'])
        for ii,row in enumerate(sp.get_iter()):
            if ii == 1:
                self.assertEqual(row[1],[None, 1, 1, 1, 1, 2, 'tmax', 'tmax', 
                 datetime.datetime(2000, 1, 1, 12, 0), 50, 0.7203244934421581])
            self.assertIsInstance(row[0],MultiPolygon)
            self.assertEqual(len(row),2)
            self.assertEqual(len(row[1]),len(constants.raw_headers))


if __name__ == "__main__":
    #import sys;sys.argv = ['', 'Test.testName']
    unittest.main()