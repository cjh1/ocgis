from ocgis.interface.base.dimension.temporal import TemporalDimension
from ocgis.interface.nc.dimension import NcVectorDimension


class NcTemporalDimension(NcVectorDimension,TemporalDimension):
    
    def __init__(self,*args,**kwds):
        self.t_units = kwds.pop('t_units')
        self.t_calendar = kwds.pop('t_calendar')
        
        NcVectorDimension.__init__(self,*args,**kwds)