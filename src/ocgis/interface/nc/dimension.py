from ocgis.interface.base.dimension.base import VectorDimension
from ocgis.util.helpers import get_slice


class NcVectorDimension(VectorDimension):
    
    def _set_value_from_source_(self):
        ## open the connection to the real dataset connection object
        ds = self._data._open_()
        try:
            ## get the variable
            var = ds.variables[self.meta['name']]
            ## format the slice
            slc = get_slice(self._src_idx)
            ## set the value
            self._value = var[slc]
            ## now, we should check for bounds here as the inheritance for making
            ## this process more transparent is not in place.
            bounds_name = self._data._source_metadata['dim_map'][self._axis].get('bounds')
            if bounds_name is not None:
                self.bounds = ds.variables[bounds_name][slc,:]
        finally:
            ds.close()
