import unittest
from ocgis.test.base import TestBase
import os
from ocgis.api.request.base import RequestDataset
import ocgis
from ocgis.interface.base.crs import CFCoordinateReferenceSystem
from ocgis.util.helpers import itersubclasses
from collections import OrderedDict
import csv
import webbrowser


class Test(TestBase):

    def test_read_projections(self):
        
        mp = {}
        for subclass in itersubclasses(CFCoordinateReferenceSystem):
            mp[subclass.grid_mapping_name] = subclass
        
        todo = []
        noattr = []
        data_dir = '/usr/local/climate_data/narccap'
        ocgis.env.DIR_DATA = data_dir
        to_write = []
        for uri in os.listdir(data_dir):
            if uri.endswith('nc'):
                
#                if uri != 'pr_WRFG_ccsm_1986010103.nc':
#                    continue
                
                variable = uri.split('_')[0]
                rd = RequestDataset(uri=uri,variable=variable)
                print
                print rd.uri
                field = rd.get()
                print field.spatial.crs
                try:
                    grid_mapping = rd._source_metadata['variables'][variable]['attrs']['grid_mapping']
                    print grid_mapping
                    to_write.append(OrderedDict([['uri',rd.uri],['class',field.spatial.crs.__class__.__name__],['grid_mapping',grid_mapping]]))
                except KeyError:
                    noattr.append(rd.uri)
                print
        
        print 'TODO:'
        for t in todo:
            print t
        
        print
        print 'No grid_mapping:'
        for n in noattr:
            print n
            
        with open('/tmp/crs.csv','w') as f:
            writer = csv.DictWriter(f,to_write[0].keys())
            writer.writeheader()
            writer.writerows(to_write)
            
        webbrowser.open('/tmp/crs.csv')
            


if __name__ == "__main__":
    #import sys;sys.argv = ['', 'Test.testName']
    unittest.main()