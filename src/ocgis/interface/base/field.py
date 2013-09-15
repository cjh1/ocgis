import abc
from ocgis.util.logging_ocgis import ocgis_lh
from ocgis.util.helpers import get_default_or_apply, get_none_or_slice,\
    get_none_or_1d, get_formatted_slice, get_slice
import numpy as np
from copy import copy, deepcopy
from collections import OrderedDict, deque
import itertools
from shapely.ops import cascaded_union
from shapely.geometry.multipoint import MultiPoint
from shapely.geometry.multipolygon import MultiPolygon


class AbstractValueVariable(object):
    __metaclass__ = abc.ABCMeta
    
    def __init__(self,value=None):
        self._value = value
    
    @property
    def value(self):
        if self._value is None:
            self._value = self._get_value_()
        return(self._value)
    def _get_value_(self):
        return(self._value)
    
    @property
    def _value(self):
        return(self.__value)
    @_value.setter
    def _value(self,value):
        self.__value = self._format_private_value_(value)
    @abc.abstractmethod
    def _format_private_value_(self,value):
        return(value)


class AbstractSourcedVariable(AbstractValueVariable):
    __metaclass__ = abc.ABCMeta
    
    def __init__(self,data,src_idx=None,value=None,debug=False):
        if not debug and value is None and data is None:
            ocgis_lh(exc=ValueError('Sourced variables require a data source if no value is passed.'))
        self._data = data
        self._src_idx = src_idx
        
        super(AbstractSourcedVariable,self).__init__(value=value)
        
    @property
    def _src_idx(self):
        return(self.__src_idx)
    @_src_idx.setter
    def _src_idx(self,value):
        self.__src_idx = self._format_src_idx_(value)
    
    def _format_src_idx_(self,value):
        if value is None:
            ret = value
        else:
            ret = value
        return(ret)
    
    def _get_value_(self):
        if self._data is None and self._value is None:
            ocgis_lh(exc=ValueError('Values were requested from data source, but no data source is available.'))
        elif self._src_idx is None and self._value is None:
            ocgis_lh(exc=ValueError('Values were requested from data source, but no source index source is available.'))
        else:
            self._set_value_from_source_()
        return(self._value)
            
    @abc.abstractmethod
    def _set_value_from_source_(self): pass


class Variable(object):
    
    def __init__(self,name,alias=None,units=None,meta=None,uid=None):
        self.name = name
        self.alias = alias or name
        self.units = units
        self.meta = meta or {}
        self.uid = uid
        self._field = None
    
    @property
    def field(self):
        return(self._field)
    
    @property
    def value(self):
        return(self.field.value[self.alias])
        
        
class VariableCollection(OrderedDict):
    
    def __init__(self,*args,**kwds):
        variables = kwds.pop('variables',None)
        
        super(VariableCollection,self).__init__()
        
        if variables is not None:
            for variable in variables:
                self.add_variable(variable)
                
    def add_variable(self,variable):
        assert(isinstance(variable,Variable))
        assert(variable.alias not in self)
        self.update({variable.alias:variable})


class Field(AbstractSourcedVariable):
    _axis_map = {'realization':0,'temporal':1,'level':2}
    
    def __init__(self,variables=None,value=None,realization=None,temporal=None,
                 level=None,spatial=None,units=None,data=None,debug=False,meta=None):
        try:
            assert(isinstance(variables,VariableCollection))
        except AssertionError:
            ocgis_lh(exc=ValueError('The "variables" keyword must be a VariableCollection.'))
        
        self.variables = variables
        self.realization = self._format_dimension_(realization)
        self.temporal = self._format_dimension_(temporal)
        self.level = self._format_dimension_(level)
        self.spatial = self._format_dimension_(spatial)
        self.units = units
        self.value_dimension_names = ('realization','temporal','level','row','column')
        self.meta = meta or {}
        self._raw = None
        
        super(Field,self).__init__(data,src_idx=None,value=value,debug=debug)
        
        for v in self.variables.itervalues(): v._field = self
        
    def __getitem__(self,slc):
        slc = get_formatted_slice(slc,5)        
        ret = copy(self)
        ret.realization = get_none_or_1d(get_none_or_slice(ret.realization,slc[0]))
        ret.temporal = get_none_or_slice(ret.temporal,slc[1])
        ret.level = get_none_or_slice(ret.level,slc[2])
        ret.spatial = get_none_or_slice(ret.spatial,(slc[3],slc[4]))
        
        ret._value = self._get_value_slice_or_none_(self._value,slc)
        
        ## update the field backref for the variables
        for v in ret.variables.itervalues(): v._field = ret
        
        return(ret)
    
    @property
    def shape(self):
        shape_realization = get_default_or_apply(self.realization,len,1)
        shape_temporal = get_default_or_apply(self.temporal,len,1)
        shape_level = get_default_or_apply(self.level,len,1)
        shape_spatial = get_default_or_apply(self.spatial,lambda x: x.shape,(1,1))
        ret = (shape_realization,shape_temporal,shape_level,shape_spatial[0],shape_spatial[1])
        return(ret)
    
    def get_between(self,dim,lower,upper):
        pos = self._axis_map[dim]
        ref = getattr(self,dim)
        new_dim,indices = ref.get_between(lower,upper,return_indices=True)
        ret = copy(self)
        setattr(ret,dim,new_dim)
        slc = get_slice(indices)
        slc_field = [slice(None)]*5
        slc_field[pos] = slc
        ret._value = self._get_value_slice_or_none_(ret._value,slc_field)
        return(ret)
    
    def get_clip(self,polygon):
        return(self._get_spatial_operation_('get_clip',polygon))
    
    def get_intersects(self,point_or_polygon):
        return(self._get_spatial_operation_('get_intersects',point_or_polygon))
    
    def get_time_region(self,time_region):
        import ipdb;ipdb.set_trace()
    
    def _get_spatial_operation_(self,attr,point_or_polygon):
        ref = getattr(self.spatial,attr)
        ret = copy(self)
        ret.spatial,slc = ref(point_or_polygon,return_indices=True)
        slc = [slice(None),slice(None),slice(None)] + list(slc)
        ret._value = self._get_value_slice_or_none_(ret._value,slc)

        ## we need to update the value mask with the geometry mask
        if ret._value is not None:
            self._set_new_value_mask_(ret,ret.spatial.get_mask())
        
        return(ret)
    
    def get_spatially_aggregated(self,new_spatial_uid=None):

        def _get_geometry_union_(value):
            to_union = [geom for geom in value.compressed().flat]
            processed_to_union = deque()
            for geom in to_union:
                if isinstance(geom,MultiPolygon) or isinstance(geom,MultiPoint):
                    for element in geom:
                        processed_to_union.append(element)
                else:
                    processed_to_union.append(geom)
            unioned = cascaded_union(processed_to_union)
            ret = np.ma.array([[None]],mask=False,dtype=object)
            ret[0,0] = unioned
            return(ret)
        
        ret = copy(self)
        ## the spatial dimension needs to be deep copied so the grid may be
        ## dereferenced.
        ret.spatial = deepcopy(self.spatial)
        ## this is the new spatial identifier for the spatial dimension.
        new_spatial_uid = new_spatial_uid or 1
        ## aggregate the geometry containers if possible.
        if ret.spatial.geom.point is not None:
            unioned = _get_geometry_union_(ret.spatial.geom.point.value)
            ret.spatial.geom.point._value = unioned
            ret.spatial.geom.point.uid = new_spatial_uid
        if ret.spatial.geom.polygon is not None:
            unioned = _get_geometry_union_(ret.spatial.geom.polygon.value)
            ret.spatial.geom.polygon._value = _get_geometry_union_(ret.spatial.geom.polygon.value)
            ret.spatial.geom.polygon.uid = new_spatial_uid
        ## there are no grid objects for aggregated spatial dimensions.
        ret.spatial.grid = None
        ret.spatial._geom_to_grid = False
        ## next the values are aggregated.
        shp = list(ret.shape)
        shp[-2] = 1
        shp[-1] = 1
        itrs = [range(dim) for dim in shp[0:3]]
        weights = self.spatial.weights
        ref_average = np.ma.average
        for k,v in ret.value.iteritems():
            fill = np.ma.array(np.zeros(shp),mask=False,dtype=v.dtype)
            for idx_r,idx_t,idx_l in itertools.product(*itrs):
                fill[idx_r,idx_t,idx_l] = ref_average(v[idx_r,idx_t,idx_l],weights=weights)
            ret.value[k] = fill
            
        ## we want to keep a copy of the raw data around for later calculations.
        ret._raw = self
            
        return(ret)
            
    def _format_dimension_(self,dim):
        if dim is not None:
            dim._field = self
        return(dim)
        
    def _format_private_value_(self,value):
        if value is None:
            ret = value
        else:
            assert(isinstance(value,dict))
            ret = value
            for k,v in ret.iteritems():
                assert(k in self.variables)
                assert(v.shape == self.shape)
                if not isinstance(v,np.ma.MaskedArray):
                    ret[k] = np.ma.array(v,mask=False)
        return(ret)
    
    def _get_value_(self):
        if self._data is None and self._value is None:
            ocgis_lh(exc=ValueError('Values were requested from data source, but no data source is available.'))
        else:
            self._set_value_from_source_()
        return(self._value)
    
    def _get_value_slice_or_none_(self,value,slc):
        if value is None:
            ret = value
        else:
            ret = {k:v[slc] for k,v in value.iteritems()}
        return(ret)
    
    def _set_new_value_mask_(self,field,mask):
        ret_shp = field.shape
        rng_realization = range(ret_shp[0])
        rng_temporal = range(ret_shp[1])
        rng_level = range(ret_shp[2])
        ref_logical_or = np.logical_or
        for v in field._value.itervalues():
            for idx_r,idx_t,idx_l in itertools.product(rng_realization,rng_temporal,rng_level):
                ref = v[idx_r,idx_t,idx_l]
                ref.mask = ref_logical_or(ref.mask,mask)
                
    def _set_value_from_source_(self):
        raise(NotImplementedError)
        ## TODO: remember to apply the geometry mask to fresh values!!
