from collections import OrderedDict
from ocgis.interface.base.crs import CFWGS84
from ocgis import constants


class SpatialCollection(OrderedDict):
    _default_headers = constants.raw_headers
    
    def __init__(self,meta=None,key=None,crs=None,headers=None):
        self.meta = meta
        self.key = key
        self.crs = crs or CFWGS84()
        self.headers = headers or self._default_headers
        
        self.geoms = {}
        self.properties = {}
        
        super(SpatialCollection,self).__init__()
        
    def add_field(self,ugid,geom,alias,field,properties=None):
        self.geoms.update({ugid:geom})
        self.properties.update({ugid:properties})
        if ugid not in self:
            self.update({ugid:{}})
        assert(alias not in self[ugid])
        self[ugid].update({alias:field})

    def get_iter(self):
        r_headers = self.headers
        for ugid,field in self.iteritems():
            for row in field.values()[0].get_iter():
                row['ugid'] = ugid
                tup = [row[h] for h in r_headers]
                yield(row['geom'],tup)
                
    def gvu(self,ugid,alias_variable,alias_field=None):
        ref = self[ugid]
        if alias_field is None:
            field = ref.values()[0]
        else:
            field = ref[alias_field]
        return(field.variables[alias_variable].value)
