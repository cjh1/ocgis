from ocgis.interface.base.dimension.base import VectorDimension
from ocgis.util.helpers import get_slice


class NcVectorDimension(VectorDimension):
    
    def _get_value_from_source_(self):
        ds = self._data._open_()
        try:
            var = ds.variables[self.meta['name']]
            slc = get_slice(self._src_idx)
            return(var[slc])
        finally:
            ds.close()
