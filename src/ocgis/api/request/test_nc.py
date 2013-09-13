import unittest
from ocgis.test.base import TestBase
from ocgis.api.request.nc import NcRequestDataset
import netCDF4 as nc
from ocgis.interface.base.crs import WGS84
import numpy as np
from datetime import datetime as dt


class TestNcRequestDataset(TestBase):

    def test_load(self):
        ref_test = self.test_data['cancm4_tas']
        uri = self.test_data.get_uri('cancm4_tas')
        rd = NcRequestDataset(variable=ref_test['variable'],uri=uri)
        field = rd.get()
        ds = nc.Dataset(uri,'r')
        
        self.assertEqual(field.level,None)
        self.assertEqual(field.spatial.crs,WGS84())
        
        tv = field.temporal.value
        test_tv = ds.variables['time'][:]
        self.assertNumpyAll(tv,test_tv)
        self.assertNumpyAll(field.temporal.bounds,ds.variables['time_bnds'][:])
        
        tdt = field.temporal.value_datetime
        self.assertEqual(tdt[4],dt(2001,1,5,12))
        self.assertNumpyAll(field.temporal.bounds_datetime[1001],[dt(2003,9,29),dt(2003,9,30)])
        
        rv = field.temporal.value_datetime[100]
        rb = field.temporal.bounds_datetime[100]
        self.assertTrue(all([rv > rb[0],rv < rb[1]]))
        
        ds.close()
        
    def test_load_datetime_slicing(self):
        ref_test = self.test_data['cancm4_tas']
        uri = self.test_data.get_uri('cancm4_tas')
        rd = NcRequestDataset(variable=ref_test['variable'],uri=uri)
        field = rd.get()
        
        field.temporal.value_datetime
        field.temporal.bounds_datetime
        
        slced = field[:,239,:,:,:]
        self.assertEqual(slced.temporal.value_datetime,np.array([dt(2001,8,28,12)]))
        self.assertNumpyAll(slced.temporal.bounds_datetime,np.array([dt(2001,8,28),dt(2001,8,29)]))
    
    def test_load_value_datetime_after_slicing(self):
        ref_test = self.test_data['cancm4_tas']
        uri = self.test_data.get_uri('cancm4_tas')
        rd = NcRequestDataset(variable=ref_test['variable'],uri=uri)
        field = rd.get()
        slced = field[:,10:130,:,4:7,100:37]
        self.assertEqual(slced.temporal.value_datetime.shape,(120,))
    
    def test_load_bounds_datetime_after_slicing(self):
        ref_test = self.test_data['cancm4_tas']
        uri = self.test_data.get_uri('cancm4_tas')
        rd = NcRequestDataset(variable=ref_test['variable'],uri=uri)
        field = rd.get()
        slced = field[:,10:130,:,4:7,100:37]
        self.assertEqual(slced.temporal.bounds_datetime.shape,(120,2))
        
    def test_load_slice(self):
        ref_test = self.test_data['cancm4_tas']
        uri = self.test_data.get_uri('cancm4_tas')
        rd = NcRequestDataset(variable=ref_test['variable'],uri=uri)
        field = rd.get()
        ds = nc.Dataset(uri,'r')
        
        slced = field[:,56:345,:,:,:]
        self.assertNumpyAll(slced.temporal.value,ds.variables['time'][56:345])
        self.assertNumpyAll(slced.temporal.bounds,ds.variables['time_bnds'][56:345,:])
        to_test = ds.variables['tas'][56:345,:,:]
        to_test = np.ma.array(to_test.reshape(1,289,1,64,128),mask=False)
        self.assertEqual(slced.variables['tas']._field._value,None)
        self.assertNumpyAll(slced.variables['tas'].value,to_test)
        
        slced = field[:,2898,:,5,101]
        to_test = ds.variables['tas'][2898,5,101]
        to_test = np.ma.array(to_test.reshape(1,1,1,1,1),mask=False)
        self.assertEqual(slced.variables['tas']._field._value,None)
        self.assertNumpyAll(slced.variables['tas'].value,to_test)
        
        ds.close()


if __name__ == "__main__":
    #import sys;sys.argv = ['', 'Test.testName']
    unittest.main()