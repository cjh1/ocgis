from ocgis.test.base import TestBase
from ocgis.util.data_scanner.datasets.base import AbstractHarvestDataset
import datetime
from ocgis.util.data_scanner import db
import os
from unittest.case import SkipTest


tdata = TestBase.get_tdata()
class CanCM4TestDataset(AbstractHarvestDataset):
    uri = tdata.get_uri('cancm4_tas')
    variables = ['tas']
    clean_units = ['K']
    clean_variable_standard_name = ['air_temperature']
    clean_variable_long_name = ['Near-Surface Air Temperature']
    dataset = 'CanCM4'
    dataset_category = 'GCMs'
    description = 'This is a test GCM dataset.'
    
    
class AbstractMaurerDataset(AbstractHarvestDataset):
    dataset = 'Maurer 2010'
    dataset_category = 'Observational'
    
    
class MaurerTas(AbstractMaurerDataset):
    uri = '/home/local/WX/ben.koziol/climate_data/maurer/2010-concatenated/Maurer02new_OBS_tas_daily.1971-2000.nc'
    variables = ['tas']
    clean_units = ['C']
    clean_variable_standard_name = ['air_temperature']
    clean_variable_long_name = ['Near-Surface Air Temperature']
    description = 'This is a test Maurer observation data.'


class TestAbstractHarvestDataset(TestBase):
            
    def setUp(self):
        TestBase.setUp(self)
        db.build_database(in_memory=True)
        
    def test_query(self):
        models = [CanCM4TestDataset,MaurerTas]
        session = db.Session()
        try:
            for m in models: m.insert(session)
        finally:
            session.close()

    def test_container(self):
        session = db.Session()
        try:
            container = db.Container(CanCM4TestDataset(session))
            self.assertEqual(container.dataset.name,'CanCM4')
            to_test = container.__dict__.copy()
            to_test.pop('_sa_instance_state')
            to_test.pop('dataset')
            real = {'spatial_res': 2.8125, 'time_start': datetime.datetime(2001, 1, 1, 0, 0), 'spatial_abstraction': 'polygon', 'spatial_proj4': '+proj=longlat +ellps=WGS84 +towgs84=0,0,0,0,0,0,0 +no_defs ', 'time_res_days': 1.0, 'uri': '/usr/local/climate_data/CanCM4/tas_day_CanCM4_decadal2000_r2i1p1_20010101-20101231.nc', 'time_stop': datetime.datetime(2011, 1, 1, 0, 0), 'time_calendar': u'365_day', 'time_frequency': 'day', 'time_units': u'days since 1850-1-1', 'field_shape': '(1, 3650, 1, 64, 128)', 'spatial_envelope': 'POLYGON ((-1.4062500000000000 -90.0000000000000000, -1.4062500000000000 90.0000000000000000, 358.5937500000000000 90.0000000000000000, 358.5937500000000000 -90.0000000000000000, -1.4062500000000000 -90.0000000000000000))'}
            real['uri'] = self.test_data.get_uri('cancm4_tas')
            self.assertDictEqual(to_test,real)
            session.add(container)
            session.commit()
        finally:
            session.close()
        
    def test_raw_variable(self):
        session = db.Session()
        try:
            hd = CanCM4TestDataset(session)
            container = db.Container(hd)
            raw_variable = db.RawVariable(hd,container,hd.variables[0])
            objects,simple = raw_variable.as_dict()
            self.assertDictEqual(simple,{'units': u'K', 'long_name': u'Near-Surface Air Temperature', 'standard_name': u'air_temperature', 'name': 'tas'})
            self.assertEqual(objects['clean_units'].name,'K')
        finally:
            session.close()
        
    def test_insert(self):
        session = db.Session()
        try:
            CanCM4TestDataset.insert(session)
            self.assertEqual(1,session.query(db.Container).count())
            container = session.query(db.Container).one()
            self.assertEqual(container.dataset.name,'CanCM4')
            self.assertEqual(container.dataset.dataset_category.name,'GCMs')
        finally:
            session.close()
            
    def test_to_disk(self):
        raise(SkipTest('dev'))
        path = os.path.join(self._test_dir,'test.sqlite')
        db.build_database(db_path=path)
        session = db.Session()
        try:
            CanCM4TestDataset.insert(session)
        finally:
            session.close()
