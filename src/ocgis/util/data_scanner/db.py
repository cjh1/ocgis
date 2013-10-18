from sqlalchemy.schema import MetaData, Column, ForeignKey, UniqueConstraint, CheckConstraint,\
    Table
from sqlalchemy.ext.declarative.api import declarative_base
from sqlalchemy.types import String, Integer, DateTime, Float, Text
from sqlalchemy.orm import relationship
from sqlalchemy.engine import create_engine
from sqlalchemy.orm.session import sessionmaker
from sqlalchemy.orm.exc import NoResultFound
from contextlib import contextmanager


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
    
def connect(db_path):
    connstr = 'sqlite:///{0}'.format(db_path)
    engine = create_engine(connstr)
    metadata.bind = engine
    Session.configure(bind=engine)
    
def get_or_create(session,Model,**kwargs):
    try:
        obj = session.query(Model).filter_by(**kwargs).one()
    except NoResultFound:
        commit = kwargs.pop('commit',True)
        obj = Model(**kwargs)
        if commit:
            session.add(obj)
            session.commit()
    return(obj)

def get_temporal_frequency(res):
    mp = {'day':[1,2],
          'month':[28,31],
          'year':[359,366]}
    ret = None
    for k,v in mp.iteritems():
        if res >= v[0] and res <= v[1]:
            ret = k
            break
    if ret is None:
        raise(NotImplementedError(res))
    return(ret)

@contextmanager
def session_scope(commit=False):
    """Provide a transactional scope around a series of operations."""
    session = Session()
    try:
        yield(session)
        if commit:
            session.commit()
    except:
        session.rollback()
        raise
    finally:
        session.close()
    
################################################################################
    
class DictConversion(object):
    
    def as_dict(self):
        simple = {}
        for k,v in self.__dict__.iteritems():
            if isinstance(v,Base) or k == '_sa_instance_state':
                continue
            else:
                simple[k] = v
        return(simple)


class DataPackage(Base):
    __tablename__ = 'package'
    dpid = Column(Integer,primary_key=True)
    name = Column(String,nullable=True)
    description = Column(Text,nullable=True)
    
    raw_variable = relationship('Field',secondary='assoc_dp_rv')


class DatasetCategory(Base):
    __tablename__ = 'category'
    __table_args__ = (UniqueConstraint('name'),)
    dcid = Column(Integer,primary_key=True)
    name = Column(String,nullable=False)
    description = Column(Text,nullable=False)


class Dataset(Base):
    __tablename__ = 'dataset'
    __table_args__ = (UniqueConstraint('name'),)
    did = Column(Integer,primary_key=True)
    dcid = Column(Integer,ForeignKey(DatasetCategory.dcid),nullable=False)
    name = Column(String,nullable=False)
    description = Column(Text,nullable=False)
    
    dataset_category = relationship(DatasetCategory,backref='dataset')
    
    
class Uri(Base):
    __tablename__ = 'uri'
    __table_args__ = (UniqueConstraint('value'),)
    uid = Column(Integer,primary_key=True)
    cid = Column(Integer,ForeignKey('container.cid'),nullable=False)
    value = Column(String,nullable=False)
    
    container = relationship("Container",backref='uri')
    

class Container(Base):
    __tablename__ = 'container'
    __table_args__ = (CheckConstraint('spatial_abstraction in ("point","polygon")'),
                      CheckConstraint('time_frequency in ("day","month","year")'))
    cid = Column(Integer,primary_key=True)
    did = Column(Integer,ForeignKey(Dataset.did),nullable=False)
    time_start = Column(DateTime,nullable=False)
    time_stop = Column(DateTime,nullable=False)
    time_res_days = Column(Float,nullable=False)
    time_frequency = Column(String,nullable=False)
    time_units = Column(String,nullable=False)
    time_calendar = Column(String,nullable=False)
    spatial_abstraction = Column(String,nullable=False)
    spatial_envelope = Column(String,nullable=False)
    spatial_res = Column(String,nullable=False)
    spatial_proj4 = Column(String,nullable=False)
    field_shape = Column(String,nullable=False)
    description = Column(Text,nullable=True)
    
    dataset = relationship(Dataset,backref='container')
    
    def __init__(self,session,hd,field=None):
        ## no need to make ocgis a required installation for this unless data
        ## is being loaded from source.
        from ocgis.util import helpers
        
        
        field = field or hd.get_field()
        self.uri = hd.uri
        self.time_start,self.time_stop = field.temporal.extent_datetime
        self.time_res_days = field.temporal.resolution
        self.time_frequency = get_temporal_frequency(self.time_res_days)
        self.time_units = field.temporal.units
        self.time_calendar = field.temporal.calendar
        self.spatial_abstraction = field.spatial.abstraction_geometry._axis.lower()
        self.spatial_envelope = helpers.bbox_poly(*field.spatial.grid.extent).wkt
        self.spatial_res = field.spatial.grid.resolution
        self.spatial_proj4 = field.spatial.crs.sr.ExportToProj4()
        self.field_shape = str(field.shape)
        
        dataset_category = get_or_create(session,DatasetCategory,**hd.dataset_category)
        kwds = hd.dataset.copy()
        kwds['dataset_category'] = dataset_category
        self.dataset = get_or_create(session,Dataset,**kwds)
        
    def touch(self):
        raise(NotImplementedError)


class CleanUnits(Base):
    __tablename__ = 'clean_units'
    __table_args__ = (UniqueConstraint('standard_name'),)
    cuid = Column(Integer,primary_key=True)
    standard_name = Column(String,nullable=False)
    long_name = Column(String,nullable=False)
    description = Column(Text,nullable=True)


class CleanVariable(Base):
    __tablename__ = 'clean_variable'
    __table_args__ = (UniqueConstraint('standard_name'),)
    cvid = Column(Integer,primary_key=True)
    standard_name = Column(String,nullable=False)
    long_name = Column(String,nullable=False)
    description = Column(Text,nullable=False)


class Field(Base,DictConversion):
    __tablename__ = 'field'
    __table_args__ = (UniqueConstraint('name','cid'),
                      CheckConstraint('type in ("index","variable")'))
    fid = Column(Integer,primary_key=True)
    cuid = Column(Integer,ForeignKey(CleanUnits.cuid),nullable=False)
    cvid = Column(Integer,ForeignKey(CleanVariable.cvid),nullable=False)
    cid = Column(Integer,ForeignKey(Container.cid),nullable=False)
    name = Column(String,nullable=False)
    type = Column(String,nullable=False)
    standard_name = Column(String,nullable=True)
    long_name = Column(String,nullable=True)
    units = Column(String,nullable=True)
    description = Column(Text,nullable=True)
    
    clean_units = relationship(CleanUnits,backref='raw_variable')
    clean_variable = relationship(CleanVariable,backref='raw_variable')
    container = relationship('Container',backref='raw_variable')
    
    def __init__(self,hd,container,variable_name,clean_units,clean_variable):
        source_metadata = hd.get_field().meta
        self.name = variable_name
        for attr in ['standard_name','long_name','units']:
            setattr(self,attr,source_metadata['variables'][variable_name]['attrs'].get(attr))
        self.container = container
        self.type = hd.type
        self.clean_units = clean_units
        self.clean_variable = clean_variable
        
    def get_alias(self):
        return(self.name)


assoc_dp_rv = Table('assoc_dp_rv',Base.metadata,Column('dpid',ForeignKey(DataPackage.dpid)),
                    Column('fid',ForeignKey(Field.fid)))
