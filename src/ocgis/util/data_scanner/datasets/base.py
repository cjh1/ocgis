import abc
from ocgis.api.request.nc import NcRequestDataset
from ocgis.util.data_scanner import db


class AbstractHarvestDataset(object):
    __metaclass__ = abc.ABCMeta
    @abc.abstractproperty
    def clean_units(self): dict
    @abc.abstractproperty
    def clean_variable(self): dict
    @abc.abstractproperty
    def dataset(self): dict
    @abc.abstractproperty
    def dataset_category(self): dict
    spatial_crs = None
    time_calendar = None
    time_units = None
    @abc.abstractproperty
    def uri(self): pass
    variables = None
    
    @classmethod
    def get_field(cls,variable=None):
        variable = variable or cls.variables[0]
        field = NcRequestDataset(uri=cls.uri,variable=variable).get()
        return(field)

    @classmethod
    def get_variables(cls):
        raise(NotImplementedError)
    
    @classmethod
    def insert(cls,session):
        container = db.Container(session,cls)
        for variable_name in cls.variables:
            rv = db.RawVariable(session,cls,container,variable_name)
            session.add(rv)
        session.commit()
