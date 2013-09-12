from ocgis.interface.base.dimension.temporal import TemporalDimension


class NcTemporalDimension(TemporalDimension):
    
    def __init__(self,*args,**kwds):
        self.t_units = kwds.pop('t_units')
        self.t_calendar = kwds.pop('t_calendar')
        
        super(NcTemporalDimension,self).__init__(*args,**kwds)