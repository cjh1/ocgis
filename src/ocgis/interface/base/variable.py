from ocgis.util.logging_ocgis import ocgis_lh
import abc


class AbstractValueVariable(object):
    __metaclass__ = abc.ABCMeta
    
    def __init__(self,value=None):
        self._value = value
    
    @property
    def value(self):
        if self._value is None:
            self._value = self._get_value_()
        return(self._value)
    def _get_value_(self):
        return(self._value)
    
    @property
    def _value(self):
        return(self.__value)
    @_value.setter
    def _value(self,value):
        self.__value = self._format_private_value_(value)
    @abc.abstractmethod
    def _format_private_value_(self,value):
        return(value)


class AbstractSourcedVariable(AbstractValueVariable):
    __metaclass__ = abc.ABCMeta
    
    def __init__(self,data,src_idx=None,value=None,debug=False):
        if not debug and value is None and data is None:
            ocgis_lh(exc=ValueError('Sourced variables require a data source if no value is passed.'))
        self._data = data
        self._src_idx = src_idx
        
        super(AbstractSourcedVariable,self).__init__(value=value)
        
    @property
    def _src_idx(self):
        return(self.__src_idx)
    @_src_idx.setter
    def _src_idx(self,value):
        self.__src_idx = self._format_src_idx_(value)
    
    def _format_src_idx_(self,value):
        if value is None:
            ret = value
        else:
            ret = value
        return(ret)
    
    def _get_value_(self):
        if self._data is None and self._value is None:
            ocgis_lh(exc=ValueError('Values were requested from data source, but no data source is available.'))
        elif self._src_idx is None and self._value is None:
            ocgis_lh(exc=ValueError('Values were requested from data source, but no source index source is available.'))
        else:
            self._set_value_from_source_()
        return(self._value)
            
    @abc.abstractmethod
    def _set_value_from_source_(self): pass


class Variable(object):
    
    def __init__(self,name=None,alias=None,units=None,meta=None,uid=None):
        self.name = name
        self.alias = alias or name
        self.units = units
        self.meta = meta or {}
        self.uid = uid
        
    def __repr__(self):
        ret = '{0}(**{1})'.format(self.__class__.__name__,self.__dict__)
        return(ret)
        
        
class DerivedVariable(Variable):
    
    def __init__(self,**kwds):
        self.function = kwds.pop('function')
        
        super(DerivedVariable,self).__init__(**kwds)