import unittest
from ocgis.test.base import TestBase
from ocgis.api.request.nc import NcRequestDataset


class TestNcRequestDataset(TestBase):

    def test_load(self):
        ref_test = self.test_data['cancm4_tas']
        rd = NcRequestDataset(variable=ref_test['variable'],uri=self.test_data.get_uri('cancm4_tas'))
        field = rd.get()
        field.temporal.value
        import ipdb;ipdb.set_trace()


if __name__ == "__main__":
    #import sys;sys.argv = ['', 'Test.testName']
    unittest.main()