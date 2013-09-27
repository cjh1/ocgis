import unittest
from datetime import datetime as dt
from ocgis.util.helpers import get_date_list, make_poly
from ocgis.interface.base.dimension.base import VectorDimension
import datetime
from ocgis.interface.base.dimension.spatial import SpatialGridDimension,\
    SpatialDimension
from ocgis.interface.base.field import Field, DerivedField
import numpy as np
import itertools
from ocgis.test.base import TestBase
from ocgis.exc import EmptySubsetError
from shapely import wkt
from shapely.ops import cascaded_union
from ocgis.interface.base.variable import Variable
from ocgis.interface.base.dimension.temporal import TemporalDimension


class AbstractTestField(TestBase):
    
    def setUp(self):
        np.random.seed(1)
        super(AbstractTestField,self).setUp()
    
    def get_col(self,bounds=True):
        value = [-100.,-99.,-98.,-97.]
        if bounds:
            bounds = [[v-0.5,v+0.5] for v in value]
        else:
            bounds = None
        row = VectorDimension(value=value,bounds=bounds,name='longitude')
        return(row)
    
    def get_row(self,bounds=True):
        value = [40.,39.,38.]
        if bounds:
            bounds = [[v+0.5,v-0.5] for v in value]
        else:
            bounds = None
        row = VectorDimension(value=value,bounds=bounds,name='latitude')
        return(row)
    
    def get_field(self,with_bounds=True,with_value=False,with_level=True,with_temporal=True,
                     with_realization=True,month_count=1):
        
        if with_temporal:
            temporal_start = dt(2000,1,1,12)
            if month_count == 1:
                temporal_stop = dt(2000,1,31,12)
            elif month_count == 2:
                temporal_stop = dt(2000,2,29,12)
            else:
                raise(NotImplementedError)
            temporal_value = get_date_list(temporal_start,temporal_stop,1)
            delta_bounds = datetime.timedelta(hours=12)
            if with_bounds:
                temporal_bounds = [[v-delta_bounds,v+delta_bounds] for v in temporal_value]
            else:
                temporal_bounds = None
            temporal = TemporalDimension(value=temporal_value,bounds=temporal_bounds,name='time',
                                         units='days')
        else:
            temporal = None
        
        if with_level:
            level_value = [50,150]
            if with_bounds:
                level_bounds = [[0,100],[100,200]]
            else:
                level_bounds = None
            level = VectorDimension(value=level_value,bounds=level_bounds,name='level',
                                    units='meters')
        else:
            level = None
        
        row = self.get_row(bounds=with_bounds)
        col = self.get_col(bounds=with_bounds)
        grid = SpatialGridDimension(row=row,col=col)
        spatial = SpatialDimension(grid=grid)
        
        if with_realization:
            realization = VectorDimension(value=[1,2],name='realization')
        else:
            realization = None
            
        if with_value:
            data = None
        else:
            data = 'foo'
        
        var = Variable('tmax',units='C')
        field = Field(variable=var,temporal=temporal,level=level,realization=realization,
                    spatial=spatial,data=data,debug=True)
        
        if with_value:
            field._value = np.random.rand(*field.shape)
        
        return(field)


class TestField(AbstractTestField):
    
    def test_get_iter(self):
        field = self.get_field(with_value=True)
        rows = list(field.get_iter())
        self.assertEqual(len(rows),2*31*2*3*4)
        rows[100]['geom'] = rows[100]['geom'].bounds
        self.assertEqual(rows[100],{'realization_bnds_lower': None, 'level': 150, 'level_bnds_lower': 100, 'var_name': 'tmax', 'time': datetime.datetime(2000, 1, 31, 12, 0), 'value': 0.94615239545676533, 'time_bnds_upper': datetime.datetime(2000, 2, 1, 0, 0), 'alias': 'tmax', 'realization_bnds_upper': None, 'realization_uid': 1, 'realization': 1, 'time_uid': 31, 'level_uid': 2, 'level_bnds_upper': 200, 'time_bnds_lower': datetime.datetime(2000, 1, 31, 0, 0), 'geom': (-97.5, 37.5, -96.5, 38.5)})
        
    def test_get_intersects_domain_polygon(self):
        regular = make_poly((36.61,41.39),(-101.41,-95.47))
        field = self.get_field(with_value=True)
        ret = field.get_intersects(regular)
        self.assertNumpyAll(ret.value,field.value)
        self.assertNumpyAll(field.spatial.grid.value,ret.spatial.grid.value)
    
    def test_get_intersects_irregular_polygon(self):
        irregular = wkt.loads('POLYGON((-100.106049 38.211305,-99.286894 38.251591,-99.286894 38.258306,-99.286894 38.258306,-99.260036 39.252035,-98.769886 39.252035,-98.722885 37.734583,-100.092620 37.714440,-100.106049 38.211305))')
        field = self.get_field(with_value=True)
        ret = field.get_intersects(irregular)
        self.assertEqual(ret.shape,(2,31,2,2,2))
        self.assertNumpyAll(ret.value.mask[0,2,1,:,:],np.array([[True,False],[False,False]]))
        self.assertEqual(ret.spatial.uid[ret.spatial.get_mask()][0],5)
        
    def test_get_clip_single_cell(self):
        single = wkt.loads('POLYGON((-97.997731 39.339322,-97.709012 39.292322,-97.742584 38.996888,-97.668726 38.641026,-98.158876 38.708170,-98.340165 38.916316,-98.273021 39.218463,-97.997731 39.339322))')
        field = self.get_field(with_value=True)
        ret = field.get_clip(single)
        self.assertEqual(ret.shape,(2,31,2,1,1))
        self.assertEqual(ret.spatial.grid,None)
        self.assertEqual(ret.spatial.geom.point,None)
        self.assertTrue(ret.spatial.geom.polygon.value[0,0].almost_equals(single))
        self.assertEqual(ret.spatial.uid,np.array([[7]]))
        
    def test_get_clip_irregular(self):
        for wv in [True,False]:
            single = wkt.loads('POLYGON((-99.894355 40.230645,-98.725806 40.196774,-97.726613 40.027419,-97.032258 39.942742,-97.681452 39.626613,-97.850806 39.299194,-98.178226 39.643548,-98.844355 39.920161,-99.894355 40.230645))')
            field = self.get_field(with_value=wv)
            ret = field.get_clip(single)
            self.assertEqual(ret.shape,(2,31,2,2,4))
            unioned = cascaded_union([geom for geom in ret.spatial.geom.polygon.value.compressed().flat])
            self.assertAlmostEqual(unioned.area,single.area)
            self.assertAlmostEqual(unioned.bounds,single.bounds)
            self.assertAlmostEqual(unioned.exterior.length,single.exterior.length)
            self.assertAlmostEqual(ret.spatial.weights[1,2],0.064016424)
            self.assertAlmostEqual(ret.spatial.weights.sum(),1.776435)
            if not wv:
                with self.assertRaises(NotImplementedError):
                    ret.value
                    
    def test_get_aggregated_irregular(self):
        single = wkt.loads('POLYGON((-99.894355 40.230645,-98.725806 40.196774,-97.726613 40.027419,-97.032258 39.942742,-97.681452 39.626613,-97.850806 39.299194,-98.178226 39.643548,-98.844355 39.920161,-99.894355 40.230645))')
        field = self.get_field(with_value=True)
        ret = field.get_clip(single)
        agg = ret.get_spatially_aggregated()
        to_test = agg.spatial.geom.polygon.value[0,0]
        self.assertAlmostEqual(to_test.area,single.area)
        self.assertAlmostEqual(to_test.bounds,single.bounds)
        self.assertAlmostEqual(to_test.exterior.length,single.exterior.length)
            
    def test_get_aggregated_all(self):
        for wv in [True,False]:
            field = self.get_field(with_value=wv)
            try:
                agg = field.get_spatially_aggregated()
            except NotImplementedError:
                if not wv:
                    continue
                else:
                    raise
            self.assertNotEqual(field.spatial.grid,None)
            self.assertEqual(agg.spatial.grid,None)
            self.assertEqual(agg.shape,(2,31,2,1,1))
            self.assertNumpyAll(field.value,agg._raw.value)
            self.assertTrue(np.may_share_memory(field.value,agg._raw.value))
            
            to_test = field.value[0,0,0,:,:].mean()
            self.assertNumpyAll(to_test,agg.value[0,0,0,0,0])
        
    def test_subsetting(self):
        for wv in [True,False]:
            field = self.get_field(with_value=wv)
            self.assertNotIsInstance(field.temporal.value,np.ma.MaskedArray)
            
            temporal_start = dt(2000,1,1,12)
            temporal_stop = dt(2000,1,31,12)
            ret = field.temporal.get_between(temporal_start,temporal_stop)
            self.assertIsInstance(ret,VectorDimension)
            self.assertNumpyAll(ret.value,field.temporal.value)
            self.assertNumpyAll(ret.bounds,field.temporal.bounds)
            
            ret = field.get_between('temporal',temporal_start,temporal_stop)
            self.assertIsInstance(ret,Field)
            self.assertEqual(ret.shape,field.shape)
            if wv:
                self.assertNumpyAll(field.value,ret.value)
            else:
                with self.assertRaises(NotImplementedError):
                    ret.value
                    
            ## try empty subset
            with self.assertRaises(EmptySubsetError):
                field.get_between('level',100000,2000000000)
                
            ret = field.get_between('realization',1,1)
            self.assertEqual(ret.shape,(1, 31, 2, 3, 4))
            if wv:
                self.assertNumpyAll(ret.value,field.value[0:1,:,:,:,:])
                
            ret = field.get_between('temporal',dt(2000,1,15),dt(2000,1,30))
            self.assertEqual(ret.temporal.value[0],dt(2000,1,14,12))
            self.assertEqual(ret.temporal.value[-1],dt(2000,1,30,12))
    
    def test_empty(self):
        with self.assertRaises(ValueError):
            Field()

    def test_constructor(self):
        for b in [True,False]:
            var = self.get_field(with_bounds=b)
            ref = var.shape
            self.assertEqual(ref,(2,31,2,3,4))
            value = np.random.rand(*var.shape)
            var._value = value
            self.assertNotIsInstance(var.value,dict)
            self.assertIsInstance(var.value,np.ma.MaskedArray)
            value = np.random.rand(3)
            with self.assertRaises(AssertionError):
                var._value = value
                
    def test_slicing_general(self):
        ibounds = [True,False]
        ivalue = [True,False]
        ilevel = [True,False]
        itemporal = [True,False]
        irealization = [True,False]
        for ib,iv,il,it,ir in itertools.product(ibounds,ivalue,ilevel,itemporal,irealization):
            var = self.get_field(with_bounds=ib,with_value=iv,with_level=il,
                                 with_temporal=it,with_realization=ir)
            
            if il:
                self.assertEqual(var.shape[2],2)
            else:
                self.assertEqual(var.shape[2],1)
            
            ## try a bad slice
            with self.assertRaises(IndexError):
                var[0]
                
            ## now good slices
            
            ## if data is loaded prior to slicing then memory is shared
            var.spatial.geom.point.value
            var_slc = var[:,:,:,:,:]
            self.assertTrue(np.may_share_memory(var.spatial.grid.value,var_slc.spatial.grid.value))
            self.assertTrue(np.may_share_memory(var.spatial.geom.point.value,var_slc.spatial.geom.point.value))
            
            if iv:
                self.assertNumpyAll(var._value,var_slc._value)
            else:
                self.assertNumpyAll(var._value,var_slc._value)
                
            if iv == True:
                self.assertTrue(np.may_share_memory(var._value,var_slc._value))
            else:
                self.assertEqual(var_slc._value,None)
            
            var_slc = var[0,0,0,0,0]
            self.assertEqual(var_slc.shape,(1,1,1,1,1))
            if iv:
                self.assertEqual(var_slc.value.shape,(1,1,1,1,1))
                self.assertNumpyAll(var_slc.value,var.value[0,0,0,0,0])
            else:
                self.assertEqual(var_slc._value,None)
                self.assertEqual(var_slc._value,var._value)
    
    def test_slicing_specific(self):
        var = self.get_field(with_value=True)
        var_slc = var[:,0:2,0,:,:]
        self.assertEqual(var_slc.shape,(2,2,1,3,4))
        self.assertEqual(var_slc.value.shape,(2,2,1,3,4))
        ref_var_real_slc = var.value[:,0:2,0,:,:]
        self.assertNumpyAll(ref_var_real_slc.flatten(),var_slc.value.flatten())
        
    def test_fancy_indexing(self):
        field = self.get_field(with_value=True)
        sub = field[:,(3,5,10,15),:,:,:]
        self.assertEqual(sub.shape,(2,4,2,3,4))
        self.assertNumpyAll(sub.value,field.value[:,(3,5,10,15),:,:,:])
        
        sub = field[:,(3,15),:,:,:]
        self.assertEqual(sub.shape,(2,2,2,3,4))
        self.assertNumpyAll(sub.value,field.value[:,(3,15),:,:,:])
        
        sub = field[:,3:15,:,:,:]
        self.assertEqual(sub.shape,(2,12,2,3,4))
        self.assertNumpyAll(sub.value,field.value[:,3:15,:,:,:])


class TestDerivedField(AbstractTestField):
    
    def test_constructor(self):
        field = self.get_field(with_value=True,month_count=2)
        tgd = field.temporal.get_grouping(['month'])
        new_data = np.random.rand(2,2,2,3,4)
        mu = Variable('mu')
        df = DerivedField(variable=mu,value=new_data,temporal=tgd,spatial=field.spatial,
                          level=field.level,realization=field.realization)
        self.assertIsInstance(df.temporal.value[0],datetime.datetime)
        self.assertEqual(df.temporal.value.tolist(),[datetime.datetime(2000, 1, 16, 0, 0),datetime.datetime(2000, 2, 16, 0, 0)])
        self.assertEqual(df.temporal.bounds[1,1],datetime.datetime(2000, 3, 1, 0, 0))


if __name__ == "__main__":
    #import sys;sys.argv = ['', 'Test.testName']
    unittest.main()
