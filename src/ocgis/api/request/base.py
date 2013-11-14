from nc import NcRequestDataset
from ocgis.util.logging_ocgis import ocgis_lh
import ocgis
from collections import OrderedDict
from ocgis.util.helpers import get_iter


class RequestDataset(NcRequestDataset):
    pass


class RequestDatasetCollection(object):
    '''Contains business logic ensuring multiple :class:`ocgis.RequestDataset` objects are
    compatible.
    
    >>> from ocgis import RequestDatasetCollection, RequestDataset
    >>> uris = ['http://some.opendap.dataset1', 'http://some.opendap.dataset2']
    >>> variables = ['tasmax', 'tasmin']
    >>> request_datasets = [RequestDatset(uri,variable) for uri,variable in zip(uris,variables)]
    >>> rdc = RequestDatasetCollection(request_datasets)
    ...
    >>> # Update object in place.
    >>> rdc = RequestDatasetCollection()
    >>> for rd in request_datasets:
    ...     rdc.update(rd)
    
    :param request_datasets: A sequence of :class:`ocgis.RequestDataset` objects.
    :type request_datasets: sequence of :class:`ocgis.RequestDataset` objects
    '''
    
    def __init__(self,request_datasets=[]):
        self._s = OrderedDict()
        self._did = []     
        for rd in get_iter(request_datasets):
            self.update(rd)
            
    def __eq__(self,other):
        if isinstance(other,self.__class__):
            return(self.__dict__ == other.__dict__)
        else:
            return(False)
        
    def __len__(self):
        return(len(self._s))
        
    def __str__(self):
        msg = '{0}([{1}])'
        fill = [str(rd) for rd in self]
        msg = msg.format(self.__class__.__name__,','.join(fill))
        return(msg)
        
    def __iter__(self):
        for value in self._s.itervalues():
            yield(value)
            
    def __getitem__(self,index):
        try:
            ret = self._s[index]
        except KeyError:
            key = self._s.keys()[index]
            ret = self._s[key]
        return(ret)
    
    def keys(self):
        return(self._s.keys())
    
    def update(self,request_dataset):
        """Add a :class:`ocgis.RequestDataset` to the collection.
        
        :param request_dataset: The :class:`ocgis.RequestDataset` to add.
        :type request_dataset: :class:`ocgis.RequestDataset`
        """
        try:
            alias = request_dataset.alias
        except AttributeError:
            request_dataset = RequestDataset(**request_dataset)
            alias = request_dataset.alias
            
        if request_dataset.did is None:
            if len(self._did) == 0:
                did = 1
            else:
                did = max(self._did) + 1
            self._did.append(did)
            request_dataset.did = did
        else:
            self._did.append(request_dataset.did)
            
        if alias in self._s:
            raise(KeyError('Alias "{0}" already in collection. Attempted to add dataset with URI "{1}".'\
                           .format(request_dataset.alias,request_dataset.uri)))
        else:
            self._s.update({request_dataset.alias:request_dataset})
            
    def _get_meta_rows_(self):
        rows = ['* dataset=']
        for value in self._s.itervalues():
            rows += value._get_meta_rows_()
            rows.append('')
        return(rows)
