from sqlalchemy.schema import MetaData, Column, ForeignKey, UniqueConstraint, CheckConstraint,\
    Table
from sqlalchemy.ext.declarative.api import declarative_base
from sqlalchemy.types import String, Integer, DateTime, Float
from sqlalchemy.orm import relationship


metadata = MetaData()
Base = declarative_base(metadata=metadata)


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
    dcid = Column(Integer,ForeignKey(DatasetCategory.dcid))
    name = Column(String,nullable=False)
    
    dataset_category = relationship(DatasetCategory,backref='dataset')


class Container(Base):
    __tablename__ = 'container'
    __table_args__ = (UniqueConstraint('uri'),CheckConstraint('spatial_abstraction in ("point","polygon")'))
    cid = Column(Integer,primary_key=True)
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
    
    dataset = relationship(Dataset,secondary='assoc_dataset_container')
        
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


class RawVariable(Base):
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
    
    container = relationship('Container',backref='raw_variable')

## TODO: add association between variable and dataset