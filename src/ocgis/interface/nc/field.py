from ocgis.interface.base.field import Field
from ocgis.util.helpers import get_slice
import numpy as np
from copy import deepcopy


class NcField(Field):
    
    def _set_value_from_source_(self):
        if self.realization is not None:
            raise(NotImplementedError)
        
        axis_slc = {}
        if self._has_fancy_temporal_indexing:
            axis_slc['T'] = self.temporal._src_idx
        else:
            axis_slc['T'] = get_slice(self.temporal._src_idx)
        axis_slc['Y'] = get_slice(self.spatial.grid.row._src_idx)
        axis_slc['X'] = get_slice(self.spatial.grid.col._src_idx)

        if self.level is not None:
            raise(NotImplementedError)
            
        dim_map = self._data._source_metadata['dim_map']
        slc = [None for v in dim_map.values() if v is not None]
        axes = deepcopy(slc)
        for k,v in dim_map.iteritems():
            if v is not None:
                slc[v['pos']] = axis_slc[k]
                axes[v['pos']] = k
        
        ## ensure axes ordering is as expected
        possible = [['T','Y','X'],['T','Z','Y','X']]
        check = [axes == poss for poss in possible]
        assert(any(check))
        
        ds = self._data._open_()
        self._value = {}
        try:
            for var in self.variables.values():
                var_name = var.alias
                raw = ds.variables[var.name].__getitem__(slc)
                if not isinstance(raw,np.ma.MaskedArray):
                    raw = np.ma.array(raw,mask=False)
                ## reshape the data adding singleton axes where necessary
                if self.level is None:
                    new_shape = [1,raw.shape[0],1,raw.shape[1],raw.shape[2]]
                else:
                    new_shape = [1,raw.shape[0],raw.shape[1],raw.shape[2],raw.shape[3]]
                raw = raw.reshape(new_shape)
                self._value[var_name] = raw
            ## apply any spatial mask if the geometries have been loaded
            if self.spatial._geom is not None:
                self._set_new_value_mask_(self,self.spatial.get_mask())
        finally:
            ds.close()
        ## TODO: remember to apply the geometry mask to fresh values!!