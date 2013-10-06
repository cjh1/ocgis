import unittest
from ocgis.interface.base.test_field import AbstractTestField
from ocgis.api.collection import SpatialCollection, CalculationCollection
from ocgis.util.shp_cabinet import ShpCabinet
from shapely.geometry.multipolygon import MultiPolygon
import datetime
from ocgis import constants
from ocgis.calc.library.statistics import Mean
from ocgis.interface.base.variable import Variable
from ocgis.interface.base.field import DerivedField
from copy import copy
from ocgis.calc.library.math import Threshold


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
                self.assertEqual(row[1],[None, 1, 1, 1, 1, 2, 'tmax', 'tmax', datetime.datetime(2000, 1, 1, 12, 0), 2000, 1, 1, 50, 0.7203244934421581])
            self.assertIsInstance(row[0],MultiPolygon)
            self.assertEqual(len(row),2)
            self.assertEqual(len(row[1]),len(constants.raw_headers))
            
            
class TestCalculationCollection(AbstractTestField):
    
    def test_iteration(self):
        field = self.get_field(with_value=True,month_count=2)
        field.variables.add_variable(Variable(value=field.variables['tmax'].value+5,
                                              name='tmin',alias='tmin'))
        field.temporal.name_uid = 'tid'
        field.level.name_uid = 'lid'
        field.spatial.geom.name_uid = 'gid'
        
        grouping = ['month']
        tgd = field.temporal.get_grouping(grouping)
        mu = Mean(field=field,tgd=tgd,alias='my_mean')
        ret = mu.execute()
        
        kwds = copy(field.__dict__)
        kwds.pop('_raw')
        kwds.pop('_variables')
        kwds['temporal'] = tgd
        kwds['variables'] = ret
        cfield = DerivedField(**kwds)
        cfield.temporal.name_uid = 'tid'
        cfield.temporal.name_value = 'time'
                        
        sc = ShpCabinet()
        meta = sc.get_meta('state_boundaries')
        sp = CalculationCollection(meta=meta,key='state_boundaries')
        for row in sc.iter_geoms('state_boundaries'):
            sp.add_field(row['properties']['UGID'],row['geom'],cfield.variables.keys()[0],
                         cfield,properties=row['properties'])
        for ii,row in enumerate(sp.get_iter()):
            if ii == 0:
                self.assertEqual(row[0].bounds,(-100.5, 39.5, -99.5, 40.5))
                self.assertEqual(row[1],[None, 1, 1, 1, 1, 1, 1, 'tmax', 'tmax', 'mean', 'my_mean_tmax', datetime.datetime(2000, 1, 16, 0, 0), 2000, 1, 16, 50, 0.44808476666433006])
            self.assertEqual(len(row),2)
            self.assertEqual(len(row[1]),len(constants.calc_headers))
            
    def test_iteration_two_calculations(self):
        field = self.get_field(with_value=True,month_count=2)
        field.variables.add_variable(Variable(value=field.variables['tmax'].value+5,
                                              name='tmin',alias='tmin'))
        field.temporal.name_uid = 'tid'
        field.level.name_uid = 'lid'
        field.spatial.geom.name_uid = 'gid'
        
        grouping = ['month']
        tgd = field.temporal.get_grouping(grouping)
        mu = Mean(field=field,tgd=tgd,alias='my_mean')
        ret = mu.execute()
        thresh = Threshold(field=field,vc=ret,tgd=tgd,alias='a_treshold',parms={'operation':'gte','threshold':0.5})
        ret = thresh.execute()
                
        kwds = copy(field.__dict__)
        kwds.pop('_raw')
        kwds.pop('_variables')
        kwds['temporal'] = tgd
        kwds['variables'] = ret
        cfield = DerivedField(**kwds)
        cfield.temporal.name_uid = 'tid'
        cfield.temporal.name_value = 'time'
                        
        sc = ShpCabinet()
        meta = sc.get_meta('state_boundaries')
        sp = CalculationCollection(meta=meta,key='state_boundaries')
        for row in sc.iter_geoms('state_boundaries'):
            sp.add_field(row['properties']['UGID'],row['geom'],cfield.variables.keys()[0],
                         cfield,properties=row['properties'])
        
        cids = set()
        for ii,row in enumerate(sp.get_iter()):
            dct = dict(zip(sp.headers,row[1]))
            cids.update([dct['cid']])
            if ii == 0:
                self.assertEqual(row[0].bounds,(-100.5, 39.5, -99.5, 40.5))
                self.assertEqual(row[1],[None, 1, 1, 1, 1, 1, 1, 'tmax', 'tmax', 'mean', 'my_mean_tmax', datetime.datetime(2000, 1, 16, 0, 0), 2000, 1, 16, 50, 0.44808476666433006])
            self.assertEqual(len(row),2)
            self.assertEqual(len(row[1]),len(constants.calc_headers))
        self.assertEqual(ii+1,2*2*2*3*4*51*4)
        self.assertEqual(len(cids),4)


if __name__ == "__main__":
    #import sys;sys.argv = ['', 'Test.testName']
    unittest.main()
