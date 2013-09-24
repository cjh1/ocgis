from ocgis.interface.base.field import Field
import numpy as np
from copy import deepcopy
from ocgis.util.logging_ocgis import ocgis_lh


class NcField(Field):
    
    def _set_value_from_source_(self):
        ## collect the dimension slices
        axis_slc = {}
        axis_slc['T'] = self.temporal._src_idx
        axis_slc['Y'] = self.spatial.grid.row._src_idx
        axis_slc['X'] = self.spatial.grid.col._src_idx
        if self.realization is not None:
            axis_slc['R'] = self.realization._src_idx
        if self.level is not None:
            axis_slc['Z'] = self.level._src_idx
        ## check for singletons in the indices and convert those from NumPy arrays.
        ## an index error is raised otherwise.
        axis_slc = {k:v if len(v) > 1 else slice(v[0],v[0]+1) for k,v in axis_slc.iteritems()}
        
        dim_map = self._data._source_metadata['dim_map']
        slc = [None for v in dim_map.values() if v is not None]
        axes = deepcopy(slc)
        for k,v in dim_map.iteritems():
            if v is not None:
                slc[v['pos']] = axis_slc[k]
                axes[v['pos']] = k
        
        ## ensure axes ordering is as expected
        possible = [['T','Y','X'],['T','Z','Y','X'],['R','T','Y','X'],['R','T','Z','Y','X']]
        check = [axes == poss for poss in possible]
        assert(any(check))
        
        ds = self._data._open_()
        try:
            self._value = {}
            for var in self.variables.values():
                var_name = var.alias
                try:
                    raw = ds.variables[var.name].__getitem__(slc)
                except IndexError:
                    ocgis_lh(logger='nc.field',exc=IndexError('variable: {0}'.format(var.name)))
                if not isinstance(raw,np.ma.MaskedArray):
                    raw = np.ma.array(raw,mask=False)
                ## reshape the data adding singleton axes where necessary
                new_shape = []
                for axis in self._axes:
                    if axis in axes:
                        try:    
                            to_append = raw.shape[axes.index(axis)]
                        except IndexError as e:
                            ## it may be a singleton index request
                            if len(slc[axes.index(axis)]) == 1:
                                to_append = 1
                            else:
                                ocgis_lh(logger='nc.field',exc=e)
                    else:
                        to_append = 1
                    new_shape.append(to_append)
                raw = raw.reshape(new_shape)
                ## insert the value into the dictionary
                self._value[var_name] = raw
            ## apply any spatial mask if the geometries have been loaded
            if self.spatial._geom is not None:
                self._set_new_value_mask_(self,self.spatial.get_mask())
        finally:
            ds.close()
