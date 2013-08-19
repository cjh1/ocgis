import abc
from ocgis.util.logging_ocgis import ocgis_lh


class AbstractSourcedVariable(object):
    __metaclass__ = abc.ABCMeta
    
    def __init__(self,data):
        self._data = data
    
    def _get_value_(self):
        if self._data is None and self._value is None:
            ocgis_lh(exc=ValueError('Values were requested from data source, but no data source is available.'))
        else:
            ret = self._get_value_from_source_()
        return(ret)
            
    @abc.abstractmethod
    def _get_value_from_source_(self): pass


class AbstractVariable(object):
    __metaclass__ = abc.ABCMeta
    
    def __init__(self,name,value,alias=None,realization=None,temporal=None,
                 level=None,spatial=None):
        self.name = name
        self.value = value
        self.alias = alias or name
        self.realization = realization
        self.temporal = temporal
        self.level = level
        self.spatial = spatial
        
    def __getitem__(self,slc):
        raise(NotImplementedError)