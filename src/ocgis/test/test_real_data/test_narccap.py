import unittest
from ocgis.test.base import TestBase
import os
from ocgis.api.request.base import RequestDataset
import ocgis
from ocgis.interface.base.crs import CFCoordinateReferenceSystem, CFWGS84
from ocgis.util.helpers import itersubclasses
from collections import OrderedDict
import csv
import webbrowser
from ocgis.api.operations import OcgOperations
import numpy as np
from ocgis.test.test_simple.test_simple import ToTest
from ocgis.exc import DefinitionValidationError, ExtentError


class Test(TestBase):
    
    def test_rotated_pole_intersects(self):
        ## TODO: it cannot be written to netCDF
        rd = self.test_data.get_rd('narccap_rotated_pole',kwds=dict(time_region={'month':[12],'year':[1982]}))
        ops = OcgOperations(dataset=rd,geom='state_boundaries',select_ugid=[16])
        ret = ops.execute()
        ref = ret.gvu(16,'tas')
        self.assertEqual(ref.shape,(1, 248, 1, 31, 22))
        self.assertAlmostEqual(np.ma.mean(ref),269.83076809598742)
        self.assertNumpyAll(ref.mask[0,0,0,0],np.array([ True,  True,  True,  True,  True,  True,  True,  True,  True,
                                                         False, False, False, False, False, False, False, False, False,
                                                         False, False,  True,  True], dtype=bool),)
        
    def test_rotated_pole_clip_aggregate(self):
        rd = self.test_data.get_rd('narccap_rotated_pole',kwds=dict(time_region={'month':[12],'year':[1982]}))
        ops = OcgOperations(dataset=rd,geom='state_boundaries',select_ugid=[16],
                            spatial_operation='clip',aggregate=True,output_format='numpy')
        ret = ops.execute()
        ret = ret.gvu(16,'tas')
        self.assertEqual(ret.shape,(1, 248, 1, 1, 1))
        
    def test_rotated_pole_to_netcdf(self):
        rd = self.test_data.get_rd('narccap_rotated_pole',kwds=dict(time_region={'month':[12],'year':[1982]}))
        with self.assertRaises(DefinitionValidationError):
            OcgOperations(dataset=rd,geom='state_boundaries',select_ugid=[16],output_format='nc')
            
    def test_cf_lambert_conformal(self):
        rd = self.test_data.get_rd('narccap_lambert_conformal')
        field = rd.get()
        crs = field.spatial.crs
        self.assertDictEqual(crs.value,{'lon_0': -97, 'ellps': 'WGS84', 'y_0': 2700000, 'no_defs': True, 'proj': 'lcc', 'x_0': 3325000, 'units': 'm', 'lat_2': 60, 'lat_1': 30, 'lat_0': 47.5})

    def test_read_projections(self):
        
        mp = {}
        for subclass in itersubclasses(CFCoordinateReferenceSystem):
            mp[subclass.grid_mapping_name] = subclass
        
        todo = []
        noattr = []
        data_dir = '/usr/local/climate_data/narccap'
        ocgis.env.DIR_DATA = data_dir
#        ocgis.env.VERBOSE = True
#        ocgis.env.DEBUG = True
        to_write = []
        for uri in os.listdir(data_dir):
            if uri.endswith('nc'):
                
#                if uri != 'pr_WRFG_ccsm_1986010103.nc':
#                    continue
#                
                print
                variable = uri.split('_')[0]
                rd = RequestDataset(uri=uri,variable=variable) #,time_region={'month':[12]})
                
#                rd = RequestDataset(uri=uri,variable=variable)
#                ops = OcgOperations(dataset=rd,output_format='shp',snippet=True,output_crs=CFWGS84())
#                ops.execute()
                
                print rd.uri
                ops = OcgOperations(dataset=rd,calc=None,calc_grouping=['month'],
                                    geom='state_boundaries',select_ugid=[16],
                                    snippet=True)
                try:
                    ret = ops.execute()
                except ExtentError:
                    if 'ECP2_ncep' in rd.uri:
                        pass
                    else:
                        raise
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
            
#        webbrowser.open('/tmp/crs.csv')
            


if __name__ == "__main__":
    #import sys;sys.argv = ['', 'Test.testName']
    unittest.main()