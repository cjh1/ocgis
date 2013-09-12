from ocgis.interface.base.dimension.temporal import TemporalDimension
from ocgis.interface.nc.dimension import NcVectorDimension
import numpy as np
import netCDF4 as nc
import datetime
from ocgis.util.helpers import iter_array, get_none_or_slice


class NcTemporalDimension(NcVectorDimension,TemporalDimension):
    _attrs_slice = ('uid','_value','_src_idx','_value_datetime')
    
    def __init__(self,*args,**kwds):
        self.calendar = kwds.pop('calendar')
        self._value_datetime = None
        self._bounds_datetime = None
        
        NcVectorDimension.__init__(self,*args,**kwds)
        
        assert(self.units != None)
        
    @property
    def bounds_datetime(self):
        if self.bounds is None:
            pass
        else:
            if self._bounds_datetime is None:
                self._bounds_datetime = np.atleast_2d(self.get_datetime(self.bounds))
        return(self._bounds_datetime)
    @bounds_datetime.setter
    def bounds_datetime(self,value):
        if value is None:
            new = None
        else:
            new = np.atleast_2d(value).reshape(-1,2)
        self._bounds_datetime = new
        
    @property
    def value_datetime(self):
        if self._value_datetime is None:
            self._value_datetime = np.atleast_1d(self.get_datetime(self.value))
        return(self._value_datetime)
        
    def get_datetime(self,arr):
        arr = np.atleast_1d(nc.num2date(arr,self.units,calendar=self.calendar))
        dt = datetime.datetime
        for idx,t in iter_array(arr,return_value=True):
            arr[idx] = dt(t.year,t.month,t.day,
                          t.hour,t.minute,t.second)
        return(arr)
    
    def get_nc_time(self,values):
        ret = np.atleast_1d(nc.date2num(values,self.units,calendar=self.calendar))
        return(ret)
    
    def _format_slice_state_(self,state,slc):
        state = NcVectorDimension._format_slice_state_(self,state,slc)
        state.bounds_datetime = get_none_or_slice(state._bounds_datetime,(slc,slice(None)))
        return(state)