import unittest
from datetime import datetime as dt
from ocgis.util.helpers import get_date_list
from ocgis.interface.base.dimension.base import VectorDimension
import datetime
from ocgis.interface.base.dimension.spatial import SpatialGridDimension,\
    SpatialDimension
from ocgis.interface.base.field import Field
import numpy as np
import itertools
from ocgis.test.base import TestBase


class TestField(TestBase):
    
    def setUp(self):
        np.random.seed(1)
        super(TestField,self).setUp()
    
    def get_col(self,bounds=True):
        value = [-100,-99,-98,-97]
        if bounds:
            bounds = [[v-0.5,v+0.5] for v in value]
        else:
            bounds = None
        row = VectorDimension(value=value,bounds=bounds,name='longitude')
        return(row)
    
    def get_row(self,bounds=True):
        value = [40,39,38]
        if bounds:
            bounds = [[v+0.5,v-0.5] for v in value]
        else:
            bounds = None
        row = VectorDimension(value=value,bounds=bounds,name='latitude')
        return(row)
    
    def get_field(self,with_bounds=True,with_value=False,with_level=True,with_temporal=True,
                     with_realization=True):
        
        if with_temporal:
            temporal_start = dt(2000,1,1,12)
            temporal_stop = dt(2000,1,31,12)
            temporal_value = get_date_list(temporal_start,temporal_stop,1)
            delta_bounds = datetime.timedelta(hours=12)
            if with_bounds:
                temporal_bounds = [[v-delta_bounds,v+delta_bounds] for v in temporal_value]
            else:
                temporal_bounds = None
            temporal = VectorDimension(value=temporal_value,bounds=temporal_bounds,name='time',
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
            realization = ['r1','r2']
        else:
            realization = None
        
        var = Field(name='tmax',units='C',temporal=temporal,level=level,realization=realization,
                       spatial=spatial)
        
        if with_value:
            var.value = np.random.rand(*var.shape)
        
        return(var)
    
    def test_empty(self):
        with self.assertRaises(ValueError):
            Field()

    def test_constructor(self):
        for b in [True,False]:
            var = self.get_field(with_bounds=b)
            ref = var.shape
            self.assertEqual(ref,(2,31,2,3,4))
            value = np.random.rand(*var.shape)
            var.value = value
            self.assertIsInstance(var.value,np.ma.MaskedArray)
            value = np.random.rand(3)
            with self.assertRaises(AssertionError):
                var.value = value
                
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


if __name__ == "__main__":
    #import sys;sys.argv = ['', 'Test.testName']
    unittest.main()