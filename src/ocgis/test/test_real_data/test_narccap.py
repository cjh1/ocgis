import unittest
from ocgis.test.base import TestBase
import os
from ocgis.api.request.base import RequestDataset
import ocgis
from ocgis.interface.base.crs import CFCoordinateReferenceSystem
from ocgis.util.helpers import itersubclasses


class Test(TestBase):

    def test_read_projections(self):
        
        mp = {}
        for subclass in itersubclasses(CFCoordinateReferenceSystem):
            mp[subclass.grid_mapping_name] = subclass
        
        todo = []
        noattr = []
        data_dir = '/usr/local/climate_data/narccap'
        ocgis.env.DIR_DATA = data_dir
        for uri in os.listdir(data_dir):
            if uri.endswith('nc'):
                variable = uri.split('_')[0]
                rd = RequestDataset(uri=uri,variable=variable)
                print
                print rd.uri
                field = rd.get()
                print field.spatial.crs
                try:
                    grid_mapping = rd._source_metadata['variables'][variable]['attrs']['grid_mapping']
                    self.assertIsInstance(field.spatial.crs,mp[grid_mapping])
                except KeyError:
                    if grid_mapping not in mp:
                        todo.append([grid_mapping,rd.uri])
                    else:
                        noattr.append(rd.uri)
                print
        
        print 'TODO:'
        for t in todo:
            print t
        
        print
        print 'No grid_mapping:'
        for n in noattr:
            print n


if __name__ == "__main__":
    #import sys;sys.argv = ['', 'Test.testName']
    unittest.main()