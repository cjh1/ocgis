import unittest
from ocgis.test.base import TestBase
import os
from ocgis.api.request.base import RequestDataset
import ocgis


class Test(TestBase):

    def test_read_projections(self):
        data_dir = '/usr/local/climate_data/narccap'
        ocgis.env.DIR_DATA = data_dir
        for uri in os.listdir(data_dir):
            if uri.endswith('nc'):
                variable = uri.split('_')[0]
                rd = RequestDataset(uri=uri,variable=variable)
                field = rd.get()
                print
                print rd.uri
                print field.spatial.crs
                try:
                    print rd._source_metadata['variables'][variable]['attrs']['grid_mapping']
                except KeyError:
                    print 'no grid_mapping'
                print


if __name__ == "__main__":
    #import sys;sys.argv = ['', 'Test.testName']
    unittest.main()