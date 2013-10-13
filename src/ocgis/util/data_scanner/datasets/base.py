import abc
from ocgis.api.request.nc import NcRequestDataset
from ocgis.util import helpers
from ocgis.util.data_scanner import db
from ocgis.util.shp_scanner.shp_scanner import get_or_create


class AbstractHarvestDataset(object):
    __metaclass__ = abc.ABCMeta
    clean_units = None
    clean_variable = None
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
    
    def __init__(self,session=None):
        if session is not None:
            if self.clean_units is not None:
                self.clean_units = get_or_create(session,db.CleanUnits,name=self.clean_units)
            if self.clean_variable is not None:
                self.clean_variable = get_or_create(session,db.CleanVariable,standard_name=self.clean_variable)
        
        self._field = None
    
    @property
    def field(self):
        if self._field is None:
            self._field = self.get_field()
        return(self._field)
    
    def get_container(self,dataset=None):
        field = self.get_field()
        kwds = {'uri':self.uri}
        kwds['time_start'],kwds['time_stop'] = field.temporal.extent_datetime
        kwds['time_res_days'] = field.temporal.resolution
        kwds['time_units'] = field.temporal.units
        kwds['time_calendar'] = field.temporal.calendar
        kwds['spatial_abstraction'] = field.spatial.abstraction_geometry._axis.lower()
        kwds['spatial_envelope'] = helpers.bbox_poly(*field.spatial.grid.extent).wkt
        kwds['spatial_res'] = field.spatial.grid.resolution
        kwds['spatial_proj4'] = field.spatial.crs.sr.ExportToProj4()
        kwds['field_shape'] = str(field.shape)
        if dataset is not None:
            kwds['dataset'] = dataset
        return(db.Container(**kwds))
    
    def get_field(self,variable=None):
        variable = variable or self.variables[0]
        field = NcRequestDataset(uri=self.uri,variable=variable).get()
        return(field)

    def get_variables(self):
        raise(NotImplementedError)
    
    def insert(self,session):
        dataset_category = get_or_create(session,db.DatasetCategory,name=self.dataset_category)
        dataset = get_or_create(session,db.Dataset,name=self.dataset,dcid=dataset_category.dcid)
        for raw_variable in self.iter_raw_variables(dataset=[dataset]):
            session.add(raw_variable)
        session.commit()
    
    def iter_raw_variables(self,variables=None,dataset=None):
        variables = variables or self.variables
        meta = self.field.meta
        container = self.get_container(dataset=dataset)
        for variable in variables:
            kwds = {'name':variable}
            for attr in ['standard_name','long_name','units']:
                kwds[attr] = meta['variables'][variable]['attrs'].get(attr)
            kwds['container'] = container
            kwds['clean_units'] = self.clean_units
            kwds['clean_variable'] = self.clean_variable
            rv = db.RawVariable(**kwds)
            yield(rv)