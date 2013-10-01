from collections import OrderedDict


class SpatialCollection(OrderedDict):
    
    def __init__(self,meta=None,key=None):
        self.meta = meta
        self.key = key
        
        self.geoms = {}
        self.properties = {}
        
        super(SpatialCollection,self).__init__()
        
    def add_field(self,ugid,geom,alias,field,properties=None):
        self.geoms.update({ugid:geom})
        if properties is not None:
            self.properties.update({ugid:properties})
        if ugid not in self:
            self.update({ugid:{}})
        assert(alias not in self[ugid])
        self[ugid].update({alias:field})
