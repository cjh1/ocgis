from ocgis.test.base import TestBase
from ocgis.util.data_scanner.datasets.base import AbstractHarvestDataset
from ocgis.interface.base.field import Field
import datetime
from ocgis.util.data_scanner import db
import os


tdata = TestBase.get_tdata()
class CanCM4TestDataset(AbstractHarvestDataset):
    uri = tdata.get_uri('cancm4_tas')
    variables = ['tas']
    dataset = 'CanCM4'
    dataset_category = 'GCMs'
    clean_units = 'K'
    clean_variable = 'air_temperature'


class TestAbstractHarvestDataset(TestBase):
    
    def run_commit(self,obj,Session=None):
        Session = Session or db.Session
        session = Session()
        try:
            session.add(obj)
            session.commit()
        finally:
            session.close()
            
    def setUp(self):
        TestBase.setUp(self)
        db.build_database(in_memory=True)

    def test_container(self):
        cd = CanCM4TestDataset()
        field = cd.get_field()
        self.assertIsInstance(field,Field)
        container = cd.get_container()
        to_test = container.__dict__.copy()
        to_test.pop('_sa_instance_state')
        self.assertDictEqual(to_test,{'field_shape': '(1, 3650, 1, 64, 128)','spatial_proj4': '+proj=longlat +ellps=WGS84 +towgs84=0,0,0,0,0,0,0 +no_defs ','time_start': datetime.datetime(2001, 1, 1, 0, 0), 'spatial_abstraction': 'polygon', 'time_stop': datetime.datetime(2011, 1, 1, 0, 0), 'time_res_days': 1.0, 'time_units': u'days since 1850-1-1', 'uri': '/usr/local/climate_data/CanCM4/tas_day_CanCM4_decadal2000_r2i1p1_20010101-20101231.nc', 'spatial_res': 2.8125, 'time_calendar': u'365_day', 'spatial_envelope': 'POLYGON ((-1.4062500000000000 -90.0000000000000000, -1.4062500000000000 90.0000000000000000, 358.5937500000000000 90.0000000000000000, 358.5937500000000000 -90.0000000000000000, -1.4062500000000000 -90.0000000000000000))'})
        self.run_commit(container)
        
    def test_raw_variable(self):
        cd = CanCM4TestDataset()
        Session = self.Session
        for raw_variable in cd.iter_raw_variables():
            to_test = raw_variable.__dict__.copy()
            to_test.pop('_sa_instance_state')
            to_test.pop('container')
            self.assertDictEqual(to_test,{'name': 'tas', 'long_name': u'Near-Surface Air Temperature', 'standard_name': u'air_temperature', 'units': u'K'})
            self.run_commit(raw_variable,Session=Session)
            
    def test_insert(self):
        session = self.Session()
        try:
            cd = CanCM4TestDataset()
            cd.insert(session)
            self.assertEqual(1,session.query(db.Container).count())
            container = session.query(db.Container).one()
            self.assertEqual(container.dataset[0].name,'CanCM4')
            self.assertEqual(container.dataset[0].dataset_category.name,'GCMs')
        finally:
            session.close()
            
    def test_to_disk(self):
        path = os.path.join(self._test_dir,'test.sqlite')
        Session = build_database(path=path)
        session = Session()
        cd = CanCM4TestDataset()
        try:
            cd.insert(session)
        finally:
            session.close()
