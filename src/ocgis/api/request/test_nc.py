import unittest
from ocgis.test.base import TestBase
from ocgis.api.request.nc import NcRequestDataset
import netCDF4 as nc
from ocgis.interface.base.crs import WGS84
import numpy as np
from datetime import datetime as dt
from ocgis.interface.base.dimension.spatial import SpatialGeometryPolygonDimension,\
    SpatialGeometryDimension, SpatialDimension
import fiona
from shapely.geometry.geo import shape


class TestNcRequestDataset(TestBase):
    
    def get_2d_state_boundaries(self):
        geoms = []
        build = True
        with fiona.open('/home/local/WX/ben.koziol/Dropbox/nesii/project/ocg/bin/shp/state_boundaries/state_boundaries.shp','r') as source:
            for ii,row in enumerate(source):
                if build:
                    nrows = len(source)
                    dtype = []
                    for k,v in source.schema['properties'].iteritems():
                        if v.startswith('str'):
                            v = str('|S{0}'.format(v.split(':')[1]))
                        else:
                            v = getattr(np,v.split(':')[0])
                        dtype.append((str(k),v))
                    fill = np.empty(nrows,dtype=dtype)
                    ref_names = fill.dtype.names
                    build = False
                fill[ii] = tuple([row['properties'][n] for n in ref_names])
                geoms.append(shape(row['geometry']))
        geoms = np.atleast_2d(geoms)
        return(geoms,fill)
    
    def get_2d_state_boundaries_sdim(self):
        geoms,attrs = self.get_2d_state_boundaries()
        poly = SpatialGeometryPolygonDimension(value=geoms)
        geom = SpatialGeometryDimension(polygon=poly)
        sdim = SpatialDimension(geom=geom,properties=attrs,crs=WGS84())
        return(sdim)

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
        self.assertNumpyAll(slced.value['tas'],to_test)
        
        slced = field[:,2898,:,5,101]
        to_test = ds.variables['tas'][2898,5,101]
        to_test = np.ma.array(to_test.reshape(1,1,1,1,1),mask=False)
        with self.assertRaises(AttributeError):
            slced.variables['tas']._field._value
        self.assertNumpyAll(slced.value['tas'],to_test)
        
        ds.close()
        
    def test_load_time_range(self):
        ref_test = self.test_data['cancm4_tas']
        uri = self.test_data.get_uri('cancm4_tas')
        rd = NcRequestDataset(variable=ref_test['variable'],uri=uri,time_range=[dt(2005,2,15),dt(2007,4,18)])
        field = rd.get()
        self.assertEqual(field.temporal.value_datetime[0],dt(2005, 2, 14, 12, 0))
        self.assertEqual(field.temporal.value_datetime[-1],dt(2007, 4, 18, 12, 0))
        self.assertEqual(field.shape,(1,794,1,64,128))
        
    def test_load_time_region(self):
        ref_test = self.test_data['cancm4_tas']
        uri = self.test_data.get_uri('cancm4_tas')
        ds = nc.Dataset(uri,'r')
        rd = NcRequestDataset(variable=ref_test['variable'],uri=uri,time_region={'month':[8]})
        field = rd.get()
        
        self.assertEqual(field.shape,(1,310,1,64,128))
        
        var = ds.variables['time']
        real_temporal = nc.num2date(var[:],var.units,var.calendar)
        select = [True if x.month == 8 else False for x in real_temporal]
        indices = np.arange(0,var.shape[0])[np.array(select)]
        self.assertNumpyAll(indices,field.temporal._src_idx)
        self.assertNumpyAll(field.temporal.value_datetime,real_temporal[indices])
        self.assertNumpyAll(field.value['tas'].data.squeeze(),ds.variables['tas'][indices,:,:])

        bounds_temporal = nc.num2date(ds.variables['time_bnds'][indices,:],var.units,var.calendar)
        self.assertNumpyAll(bounds_temporal,field.temporal.bounds_datetime)
        
        ds.close()
        
    def test_load_time_region_with_years(self):
        ref_test = self.test_data['cancm4_tas']
        uri = self.test_data.get_uri('cancm4_tas')
        ds = nc.Dataset(uri,'r')
        rd = NcRequestDataset(variable=ref_test['variable'],uri=uri,time_region={'month':[8],'year':[2008,2010]})
        field = rd.get()
        
        self.assertEqual(field.shape,(1,62,1,64,128))

        var = ds.variables['time']
        real_temporal = nc.num2date(var[:],var.units,var.calendar)
        select = [True if x.month == 8 and x.year in [2008,2010] else False for x in real_temporal]
        indices = np.arange(0,var.shape[0])[np.array(select)]
        self.assertNumpyAll(indices,field.temporal._src_idx)
        self.assertNumpyAll(field.temporal.value_datetime,real_temporal[indices])
        self.assertNumpyAll(field.value['tas'].data.squeeze(),ds.variables['tas'][indices,:,:])

        bounds_temporal = nc.num2date(ds.variables['time_bnds'][indices,:],var.units,var.calendar)
        self.assertNumpyAll(bounds_temporal,field.temporal.bounds_datetime)
        
        ds.close()
        
    def test_load_geometry_subset(self):
        ref_test = self.test_data['cancm4_tas']
        uri = self.test_data.get_uri('cancm4_tas')
        ds = nc.Dataset(uri,'r')
        rd = NcRequestDataset(variable=ref_test['variable'],uri=uri,alias='foo')
        field = rd.get()
        
        states = self.get_2d_state_boundaries_sdim()
        ca = states[:,states.properties['STATE_NAME'] == 'California']
        self.assertTrue(ca.properties['STATE_NAME'] == 'California')
        ca.crs.unwrap(ca)
        ca = ca.geom.polygon.value[0,0]
        ca_sub = field.get_intersects(ca)
        self.assertEqual(ca_sub.shape,(1, 3650, 1, 5, 4))
        self.assertFalse(ca_sub.value['foo'].mask.all())


if __name__ == "__main__":
    #import sys;sys.argv = ['', 'Test.testName']
    unittest.main()