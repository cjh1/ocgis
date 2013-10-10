import abc
from ocgis.util.shp_cabinet import ShpCabinetIterator


class NoSubcategoryError(Exception):
    pass

class AbstractLabelMaker(object):
    __metaclass__ = abc.ABCMeta
    
    def __init__(self,key):
        self.key = key
        
    def __iter__(self):
        sci = ShpCabinetIterator(self.key)
        for row in sci:
            row['envelope'] = row['geom'].envelope.wkt
            row['geometry_label'] = self.get_geometry_label(row['properties'])
            try:
                row['subcategory_label'] = self.get_subcategory_label(row['properties'])
            except NoSubcategoryError:
                pass
            yield(row)
    
    @abc.abstractmethod
    def get_geometry_label(self,properties): '(subcategory or None, geometry label, ugid, envelope)'
        
    def get_subcategory_label(self,properties):
        raise(NoSubcategoryError)


class StateBoundaries(AbstractLabelMaker):
    
    def get_geometry_label(self,properties):
        ret = '{0} ({1})'.format(properties['STATE_NAME'],properties['STATE_ABBR'])
        return(ret)


class UsCounties(AbstractLabelMaker):
    
    def get_geometry_label(self,properties):
        return(properties['COUNTYNAME'])
    
    def get_subcategory_label(self,properties):
        ret = '{0} Counties'.format(properties['STATE'])
        return(ret)


class WorldCountries(AbstractLabelMaker):
    
    def get_geometry_label(self,properties):
        return(properties['NAME'])
    
    def get_subcategory_label(self,properties):
        ret = properties['REGION']
        if ret == 'NorthAfrica':
            ret = 'North Africa'
        if ret == 'Sub Saharan Africa':
            ret = 'Sub-Saharan Africa'
        return(ret)
        

class ClimateDivisions(AbstractLabelMaker):
    
    def get_geometry_label(self,properties):
        ret = properties['NAME']
        return(ret.title())
    
    def get_subcategory_label(self,properties):
        ret = properties['STATE']
        return(ret)