import abc
from ocgis.api.request.nc import NcRequestDataset
from ocgis.util.data_scanner import db
from ocgis.util.shp_scanner.shp_scanner import get_or_create


class AbstractHarvestDataset(object):
    __metaclass__ = abc.ABCMeta
    clean_units = None
    clean_variable_standard_name = None
    clean_variable_long_name = None
    @abc.abstractproperty
    def dataset(self): str
    @abc.abstractproperty
    def dataset_category(self): str
    spatial_crs = None
    time_calendar = None
    time_units = None
    @abc.abstractproperty
    def uri(self): pass
    variables = None

    def __init__(self,session):
        self.dataset_category = get_or_create(session,db.DatasetCategory,name=self.dataset_category)
        self.dataset = get_or_create(session,db.Dataset,name=self.dataset,dcid=self.dataset_category.dcid)
        if self.clean_units is not None:
            self.clean_units = [get_or_create(session,db.CleanUnits,name=cu) for cu in self.clean_units]
        if self.clean_variable_standard_name is not None:
            self.clean_variable = [get_or_create(session,db.CleanVariable,
             standard_name=cvsn,long_name=cvln) for cvsn,cvln in zip(self.clean_variable_standard_name,self.clean_variable_long_name)]
        self.source_metadata = self.get_field().meta

    def get_field(self,variable=None):
        variable = variable or self.variables[0]
        field = NcRequestDataset(uri=self.uri,variable=variable).get()
        return(field)

    def get_variables(self):
        raise(NotImplementedError)
    
    @classmethod
    def insert(cls,session):
        hd = cls(session)
        container = db.Container(hd)
        for variable_name in cls.variables:
            rv = db.RawVariable(hd,container,variable_name)
            session.add(rv)
        session.commit()
