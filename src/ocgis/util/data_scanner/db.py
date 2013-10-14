from sqlalchemy.schema import MetaData, Column, ForeignKey, UniqueConstraint, CheckConstraint,\
    Table
from sqlalchemy.ext.declarative.api import declarative_base
from sqlalchemy.types import String, Integer, DateTime, Float
from sqlalchemy.orm import relationship
from sqlalchemy.engine import create_engine
from sqlalchemy.orm.session import sessionmaker
from ocgis.util import helpers
from ocgis.util.shp_scanner.shp_scanner import get_or_create


metadata = MetaData()
Base = declarative_base(metadata=metadata)
Session = sessionmaker()


def build_database(in_memory=False,db_path=None):
    if in_memory:
        connstr = 'sqlite://'
    else:
        connstr = 'sqlite:///{0}'.format(db_path)
    engine = create_engine(connstr)
    metadata.bind = engine
    metadata.create_all()
    Session.configure(bind=engine)
    
    
class DictConversion(object):
    
    def as_dict(self):
        objects = {}
        simple = {}
        for k,v in self.__dict__.iteritems():
            if isinstance(v,Base) or k == '_sa_instance_state':
                objects[k] = v
            else:
                simple[k] = v
        return(objects,simple)

class DataPackage(Base):
    __tablename__ = 'package'
    dpid = Column(Integer,primary_key=True)


class DatasetCategory(Base):
    __tablename__ = 'category'
    __table_args__ = (UniqueConstraint('name'),)
    dcid = Column(Integer,primary_key=True)
    name = Column(String,nullable=False)


class Dataset(Base):
    __tablename__ = 'dataset'
    __table_args__ = (UniqueConstraint('name'),)
    did = Column(Integer,primary_key=True)
    dcid = Column(Integer,ForeignKey(DatasetCategory.dcid),nullable=False)
    name = Column(String,nullable=False)
    
    dataset_category = relationship(DatasetCategory,backref='dataset')


class Container(Base):
    __tablename__ = 'container'
    __table_args__ = (UniqueConstraint('uri'),CheckConstraint('spatial_abstraction in ("point","polygon")'))
    cid = Column(Integer,primary_key=True)
    did = Column(Integer,ForeignKey(Dataset.did),nullable=True)
    uri = Column(String,nullable=False)
    time_start = Column(DateTime,nullable=False)
    time_stop = Column(DateTime,nullable=False)
    time_res_days = Column(Float,nullable=False)
    time_units = Column(String,nullable=False)
    time_calendar = Column(String,nullable=False)
    spatial_abstraction = Column(String,nullable=False)
    spatial_envelope = Column(String,nullable=False)
    spatial_res = Column(String,nullable=False)
    spatial_proj4 = Column(String,nullable=False)
    field_shape = Column(String,nullable=False)
    
    dataset = relationship(Dataset,backref='container')
    
    def __init__(self,hd,field=None):
        field = field or hd.get_field()
        self.uri = hd.uri
        self.time_start,self.time_stop = field.temporal.extent_datetime
        self.time_res_days = field.temporal.resolution
        self.time_units = field.temporal.units
        self.time_calendar = field.temporal.calendar
        self.spatial_abstraction = field.spatial.abstraction_geometry._axis.lower()
        self.spatial_envelope = helpers.bbox_poly(*field.spatial.grid.extent).wkt
        self.spatial_res = field.spatial.grid.resolution
        self.spatial_proj4 = field.spatial.crs.sr.ExportToProj4()
        self.field_shape = str(field.shape)
        self.dataset = hd.dataset
        
    def touch(self):
        raise(NotImplementedError)


adc = Table('assoc_dataset_container',Base.metadata,
            Column('did',Integer,ForeignKey(Dataset.did)),
            Column('cid',Integer,ForeignKey(Container.cid)))


class CleanUnits(Base):
    __tablename__ = 'clean_units'
    __table_args__ = (UniqueConstraint('name'),)
    cuid = Column(Integer,primary_key=True)
    name = Column(String,nullable=False)


class CleanVariable(Base):
    __tablename__ = 'clean_variable'
    __table_args__ = (UniqueConstraint('standard_name','long_name'),)
    cvid = Column(Integer,primary_key=True)
    standard_name = Column(String,nullable=False)
    long_name = Column(String,nullable=False)


class RawVariable(Base,DictConversion):
    __tablename__ = 'raw_variable'
    __table_args__ = (UniqueConstraint('name','cid'),)
    rvid = Column(Integer,primary_key=True)
    cuid = Column(Integer,ForeignKey(CleanUnits.cuid),nullable=True)
    cvid = Column(Integer,ForeignKey(CleanVariable.cvid),nullable=True)
    cid = Column(Integer,ForeignKey(Container.cid),nullable=False)
    name = Column(String,nullable=False)
    standard_name = Column(String,nullable=True)
    long_name = Column(String,nullable=True)
    units = Column(String,nullable=True)
    
    clean_units = relationship(CleanUnits,backref='raw_variable')
    clean_variable = relationship(CleanVariable,backref='raw_variable')
    container = relationship('Container',backref='raw_variable')
    
    def __init__(self,hd,container,variable_name):
        self.name = variable_name
        for attr in ['standard_name','long_name','units']:
            setattr(self,attr,hd.source_metadata['variables'][variable_name]['attrs'].get(attr))
        self.container = container
        session = Session()
        try:
            if hd.clean_units is not None:
                self.clean_units = hd.clean_units
            if hd.clean_variable is not None:
                self.clean_variable = hd.clean_variable
        finally:
            session.close()

## TODO: add association between variable and dataset
