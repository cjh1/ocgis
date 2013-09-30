from ocgis.util.logging_ocgis import ocgis_lh
from ocgis.util.helpers import get_default_or_apply, get_none_or_slice,\
    get_formatted_slice, get_reduced_slice, get_iter
import numpy as np
from copy import copy, deepcopy
from collections import deque, OrderedDict
import itertools
from shapely.ops import cascaded_union
from shapely.geometry.multipoint import MultiPoint
from shapely.geometry.multipolygon import MultiPolygon
from ocgis.interface.base.variable import AbstractSourcedVariable, Variable
from ocgis import constants


class FieldCollection(OrderedDict):
    
    def __init__(self,**kwds):
        fields = kwds.pop('fields',None)
        
        super(FieldCollection,self).__init__()
        
        if fields is not None:
            for field in get_iter(fields):
                self.add_field(field)
                
    def add_field(self,field):
        assert(isinstance(field,Field))
        assert(field.variable.alias not in self)
        self.update({field.variable.alias:field})
        

class Field(AbstractSourcedVariable):
    _axis_map = {'realization':0,'temporal':1,'level':2}
    _axes = ['R','T','Z','Y','X']
    _specials = ['variable','value','meta','data']
    
    def __init__(self,variable=None,value=None,realization=None,temporal=None,
                 level=None,spatial=None,data=None,debug=False,meta=None):
#        try:
#            for var in get_iter(variable):
#                assert(isinstance(var,Variable))
#        except AssertionError:
#            ocgis_lh(exc=ValueError('The "variable" keyword must be a Variable object.'))
        
        self.variable = variable
        self.realization = realization
        self.temporal = temporal
        self.level = level
        self.spatial = spatial
        self.value_dimension_names = ('realization','temporal','level','row','column')
        self.meta = meta or {}
        ## holds raw values for aggregated datasets.
        self._raw = None
        
        super(Field,self).__init__(data,src_idx=None,value=value,debug=debug)
        
    def __getattribute__(self,attr):
        if attr in super(Field,self).__getattribute__('_specials'):
            import ipdb;ipdb.set_trace()
        else:
            ret = super(Field,self).__getattribute__(attr)
        return(ret)
                
    def __getitem__(self,slc):
        slc = get_formatted_slice(slc,5)        
        ret = copy(self)
        
        ret.realization = get_none_or_slice(ret.realization,slc[0])
        ret.temporal = get_none_or_slice(ret.temporal,slc[1])
        ret.level = get_none_or_slice(ret.level,slc[2])
        ret.spatial = get_none_or_slice(ret.spatial,(slc[3],slc[4]))
        
        ret._value = get_none_or_slice(self._value,slc)
        
        return(ret)
    
    def __setattribute__(self,attr,value):
        raise(NotImplementedError)
    
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
        slc = get_reduced_slice(indices)
        slc_field = [slice(None)]*5
        slc_field[pos] = slc
        ret._value = get_none_or_slice(ret._value,slc_field)
        return(ret)
    
    def get_clip(self,polygon):
        return(self._get_spatial_operation_('get_clip',polygon))
    
    def get_intersects(self,point_or_polygon):
        return(self._get_spatial_operation_('get_intersects',point_or_polygon))
    
    def get_iter(self,add_masked_value=True):
        
        def _get_dimension_iterator_1d_(target):
            attr = getattr(self,target)
            if attr is None:
                ret = [(0,{})]
            else:
                ret = attr.get_iter()
            return(ret)
        
        name_value = self.variable.name
        name_alias = self.variable.alias
        is_masked = np.ma.is_masked
        masked_value = constants.fill_value
        ref_value = self.value
        
        iters = map(_get_dimension_iterator_1d_,['realization','temporal','level'])
        iters.append(self.spatial.get_geom_iter())
        for [(ridx,rlz),(tidx,t),(lidx,l),(sridx,scidx,geom)] in itertools.product(*iters):
            ref_idx = ref_value[ridx,tidx,lidx,sridx,scidx]
            if is_masked(ref_idx):
                if add_masked_value:
                    ref_idx = masked_value
                else:
                    continue
            rlz.update(t)
            rlz.update(l)
            rlz['var_name'] = name_value
            rlz['alias'] = name_alias
            rlz['value'] = ref_idx
            rlz['geom'] = geom
            
            yield(rlz)
    
    def get_time_region(self,time_region):
        ret = copy(self)
        ret.temporal,indices = self.temporal.get_time_region(time_region,return_indices=True)
        slc = [slice(None),indices,slice(None),slice(None),slice(None)]
        ret._value = get_none_or_slice(ret._value,slc)
        return(ret)
    
    def _get_spatial_operation_(self,attr,point_or_polygon):
        ref = getattr(self.spatial,attr)
        ret = copy(self)
        ret.spatial,slc = ref(point_or_polygon,return_indices=True)
        slc = [slice(None),slice(None),slice(None)] + list(slc)
        ret._value = get_none_or_slice(ret._value,slc)

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

        fill = np.ma.array(np.zeros(shp),mask=False,dtype=ret.value.dtype)
        for idx_r,idx_t,idx_l in itertools.product(*itrs):
            fill[idx_r,idx_t,idx_l] = ref_average(ret.value[idx_r,idx_t,idx_l],weights=weights)
        ret._value = fill
            
        ## we want to keep a copy of the raw data around for later calculations.
        ret._raw = self
            
        return(ret)
        
    def _format_private_value_(self,value):
        if value is None:
            ret = value
        else:
            assert(isinstance(value,np.ndarray))
            assert(value.shape == self.shape)
            ret = value
            if not isinstance(ret,np.ma.MaskedArray):
                ret = np.ma.array(ret,mask=False)
        return(ret)
    
    def _get_value_(self):
        if self._data is None and self._value is None:
            ocgis_lh(exc=ValueError('Values were requested from data source, but no data source is available.'))
        else:
            self._set_value_from_source_()
        return(self._value)
    
    def _set_new_value_mask_(self,field,mask):
        ret_shp = field.shape
        rng_realization = range(ret_shp[0])
        rng_temporal = range(ret_shp[1])
        rng_level = range(ret_shp[2])
        ref_logical_or = np.logical_or
        v = field.value
        for idx_r,idx_t,idx_l in itertools.product(rng_realization,rng_temporal,rng_level):
            ref = v[idx_r,idx_t,idx_l]
            ref.mask = ref_logical_or(ref.mask,mask)
                
    def _set_value_from_source_(self):
        raise(NotImplementedError)
        ## TODO: remember to apply the geometry mask to fresh values!!
        

class DerivedField(Field):
    pass
