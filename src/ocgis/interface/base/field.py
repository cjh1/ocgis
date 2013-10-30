from ocgis.util.helpers import get_default_or_apply, get_none_or_slice,\
    get_formatted_slice, get_reduced_slice, assert_raise
import numpy as np
from copy import copy, deepcopy
from collections import deque
import itertools
from shapely.ops import cascaded_union
from shapely.geometry.multipoint import MultiPoint
from shapely.geometry.multipolygon import MultiPolygon
from ocgis.interface.base.variable import Variable, VariableCollection
from ocgis import constants
        

class Field(object):
    _axis_map = {'realization':0,'temporal':1,'level':2}
    _axes = ['R','T','Z','Y','X']
    _value_dimension_names = ('realization','temporal','level','row','column')
    
    def __init__(self,variables=None,realization=None,temporal=None,level=None,
                 spatial=None,meta=None,uid=None):
        
        self.realization = realization
        self.temporal = temporal
        self.uid = uid
        self.level = level
        self.spatial = spatial
        self.meta = meta or {}
        ## holds raw values for aggregated datasets.
        self._raw = None
        ## add variables - dimensions are needed first for shape checking
        self.variables = variables
                        
    def __getitem__(self,slc):
        slc = get_formatted_slice(slc,5)
        ret = copy(self)
        ret.realization = get_none_or_slice(self.realization,slc[0])
        ret.temporal = get_none_or_slice(self.temporal,slc[1])
        ret.level = get_none_or_slice(self.level,slc[2])
        ret.spatial = get_none_or_slice(self.spatial,(slc[3],slc[4]))
        
        ret.variables = self.variables._get_sliced_variables_(slc)

        return(ret)
    
    @property
    def shape(self):
        shape_realization = get_default_or_apply(self.realization,len,1)
        shape_temporal = get_default_or_apply(self.temporal,len,1)
        shape_level = get_default_or_apply(self.level,len,1)
        shape_spatial = get_default_or_apply(self.spatial,lambda x: x.shape,(1,1))
        ret = (shape_realization,shape_temporal,shape_level,shape_spatial[0],shape_spatial[1])
        return(ret)
    
    @property
    def variables(self):
        return(self._variables)
    @variables.setter
    def variables(self,value):
        if isinstance(value,Variable):
            value = VariableCollection(variables=[value])
        assert_raise(isinstance(value,VariableCollection),exc=ValueError('The "variables" keyword must be a Variable object.'))
        self._variables = value
        for v in value.itervalues():
            v._field = self
            if v._value is not None:
                assert(v._value.shape == self.shape)
    
    def get_between(self,dim,lower,upper):
        pos = self._axis_map[dim]
        ref = getattr(self,dim)
        ## TODO: minor redundancy in slicing and returning dimension
        new_dim,indices = ref.get_between(lower,upper,return_indices=True)
        slc = get_reduced_slice(indices)
        slc_field = [slice(None)]*5
        slc_field[pos] = slc
        ret = self[slc_field]
        return(ret)
    
    def get_clip(self,polygon):
        return(self._get_spatial_operation_('get_clip',polygon))
    
    def get_intersects(self,polygon):
        return(self._get_spatial_operation_('get_intersects',polygon))
    
    def get_iter(self,add_masked_value=True):
        
        def _get_dimension_iterator_1d_(target):
            attr = getattr(self,target)
            if attr is None:
                ret = [(0,{})]
            else:
                ret = attr.get_iter()
            return(ret)
        
        is_masked = np.ma.is_masked
        masked_value = constants.fill_value
        
        r_gid_name = self.spatial.name_uid
        for variable in self.variables.itervalues():
            yld = self._get_variable_iter_yield_(variable)
            ref_value = variable.value
            iters = map(_get_dimension_iterator_1d_,['realization','temporal','level'])
            iters.append(self.spatial.get_geom_iter())
            for [(ridx,rlz),(tidx,t),(lidx,l),(sridx,scidx,geom,gid)] in itertools.product(*iters):
                to_yld = deepcopy(yld)
                ref_idx = ref_value[ridx,tidx,lidx,sridx,scidx]
                if is_masked(ref_idx):
                    if add_masked_value:
                        ref_idx = masked_value
                    else:
                        continue
                to_yld.update(rlz)
                to_yld.update(t)
                to_yld.update(l)
                to_yld['value'] = ref_idx
                to_yld['geom'] = geom
                to_yld[r_gid_name] = gid
                                
                yield(to_yld)
                
    def get_shallow_copy(self):
        return(copy(self))
    
    def get_time_region(self,time_region):
        ret = copy(self)
        ret.temporal,indices = self.temporal.get_time_region(time_region,return_indices=True)
        slc = [slice(None),indices,slice(None),slice(None),slice(None)]
        variables = self.variables._get_sliced_variables_(slc)
        ret.variables = variables
        return(ret)
    
    def _get_spatial_operation_(self,attr,polygon):
        ref = getattr(self.spatial,attr)
        ret = copy(self)
        ret.spatial,slc = ref(polygon,return_indices=True)
        slc = [slice(None),slice(None),slice(None)] + list(slc)
        ret.variables = self.variables._get_sliced_variables_(slc)

        ## we need to update the value mask with the geometry mask
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
        ## update the spatial uid
        ret.spatial.uid = new_spatial_uid
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
        
        ## old values for the variables will be stored in the _raw container, but
        ## to avoid reference issues, we need to copy the variables
        new_variables = []
        for variable in ret.variables.itervalues():
            r_value = variable.value
            fill = np.ma.array(np.zeros(shp),mask=False,dtype=variable.value.dtype)
            for idx_r,idx_t,idx_l in itertools.product(*itrs):
                fill[idx_r,idx_t,idx_l] = ref_average(r_value[idx_r,idx_t,idx_l],weights=weights)
            new_variable = copy(variable)
            new_variable._value = fill
            new_variables.append(new_variable)
        ret.variables = VariableCollection(variables=new_variables)
                            
        ## we want to keep a copy of the raw data around for later calculations.
        ret._raw = copy(self)
                
        return(ret)

    def _get_value_from_source_(self,*args,**kwds):
        raise(NotImplementedError)
        ## TODO: remember to apply the geometry mask to fresh values!!

    def _set_new_value_mask_(self,field,mask):
        ret_shp = field.shape
        rng_realization = range(ret_shp[0])
        rng_temporal = range(ret_shp[1])
        rng_level = range(ret_shp[2])
        ref_logical_or = np.logical_or
        
        for var in field.variables.itervalues():
            if var._value is not None:
                v = var._value
                for idx_r,idx_t,idx_l in itertools.product(rng_realization,rng_temporal,rng_level):
                    ref = v[idx_r,idx_t,idx_l]
                    ref.mask = ref_logical_or(ref.mask,mask)
                    
    def _get_variable_iter_yield_(self,variable):
        yld = {}
        yld['did'] = variable.uid
        yld['variable'] = variable.name
        yld['alias'] = variable.alias
        yld['vid'] = variable.uid
        return(yld)


class DerivedField(Field):
    
    def _get_variable_iter_yield_(self,variable):
        yld = {}
        yld['cid'] = variable.uid
        yld['calc_key'] = variable.name
        yld['calc_alias'] = variable.alias
        
        raw_variable = variable.parents.values()[0]
        yld['did'] = raw_variable.uid
        yld['variable'] = raw_variable.name
        yld['alias'] = raw_variable.alias
        yld['vid'] = raw_variable.uid
        return(yld)


class DerivedMultivariateField(Field):
    
    def _get_variable_iter_yield_(self,variable):
        yld = {}
        yld['cid'] = variable.uid
        yld['calc_key'] = variable.name
        yld['calc_alias'] = variable.alias
        yld['did'] = None
        return(yld)