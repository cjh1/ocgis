import unittest
from ocgis.test.base import TestBase
from ocgis.api.request.nc import NcRequestDataset
import netCDF4 as nc
from ocgis.interface.base.crs import WGS84
import numpy as np


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
        
        ds.close()
        
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