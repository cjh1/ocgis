import unittest
from ocgis.test.base import TestBase
from ocgis.api.request.nc import NcRequestDataset
import netCDF4 as nc


class TestNcRequestDataset(TestBase):

    def test_load(self):
        ref_test = self.test_data['cancm4_tas']
        uri = self.test_data.get_uri('cancm4_tas')
        rd = NcRequestDataset(variable=ref_test['variable'],uri=uri)
        field = rd.get()
        ds = nc.Dataset(uri,'r')
        
        tv = field.temporal.value
        test_tv = ds.variables['time'][:]
        self.assertNumpyAll(tv,test_tv)
        self.assertNotEqual(field.temporal.bounds,None)
        import ipdb;ipdb.set_trace()


if __name__ == "__main__":
    #import sys;sys.argv = ['', 'Test.testName']
    unittest.main()