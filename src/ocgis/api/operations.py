from ocgis.api.parms.definition import *  # @UnusedWildImport
from ocgis.api.interpreter import OcgInterpreter
import warnings
from ocgis import env
from ocgis.api.parms.base import OcgParameter
from ocgis.conv.meta import MetaConverter
from ocgis.util.logging_ocgis import ocgis_lh
from ocgis.calc.base import AbstractMultivariateFunction,\
    AbstractKeyedOutputFunction
from ocgis.interface.base.crs import CFWGS84


class OcgOperations(object):
    """Entry point for OCGIS operations.
    
    .. warning:: The object SHOULD NOT be reused following an execution as the software may add/modify attribute contents. Instantiate a new object following an execution.
    
    .. note:: The only required argument is `dataset`.
    
    All keyword arguments are exposed as public attributes which may be 
    arbitrarily set using standard syntax:

    >>> ops = OcgOperations(RequestDataset('/path/to/some/dataset','foo'))
    >>> ops.aggregate = True
        
    The builtins :func:`__getattribute__` and :func:`__setattr__` are overloaded to perform 
    validation and formatting upon assignment and to properly return parameter 
    values from internal objects.
        
    :param dataset: The target dataset(s) for the request. This is the only required parameter.
    :type dataset: :class:`ocgis.RequestDatasetCollection` or :class:`ocgis.RequestDataset`
    :param spatial_operation: The geometric operation to be performed.
    :type spatial_operation: str
    :param geom: The selection geometry(s) used for the spatial subset. If `None`, selection defaults to entire spatial domain.
    :type geom: list of dict, list of float, str
    :param aggregate: If `True`, dataset geometries are aggregated to coincident selection geometries.
    :type aggregate: bool
    :param calc: Calculations to be performed on the dataset subset.
    :type calc: list of dictionaries
    :param calc_grouping: Temporal grouping to apply during calculation.
    :type calc_grouping: list of str
    :param calc_raw: If `True`, perform calculations on the "raw" data regardless of `aggregation` flag.
    :type calc_raw: bool
    :param abstraction: The geometric abstraction to use for the dataset geometries. If `None` (the default), use the highest order geometry available.
    :type abstraction: str
    :param snippet: If `True`, return a data "snippet" composed of the first time point/group, first level (if applicable), and the entire spatial domain.
    :type snippet: bool
    :param backend: The processing backend to use.
    :type backend: str
    :param prefix: The output prefix to prepend to any output data filename.
    :type prefix: str
    :param output_format: The desired output format.
    :type output_format: str
    :param agg_selection: If `True`, the selection geometry will be aggregated prior to any spatial operations.
    :type agg_selection: bool
    :param select_ugid: The unique identifiers of specific geometries contained in canned geometry datasets. These unique identifiers will be selected and used for spatial operations.
    :type select_ugid: list of integers
    :param vector_wrap: If `True`, keep any vector output on a -180 to 180 longitudinal domain.
    :type vector_wrap: bool
    :param allow_empty: If `True`, do not raise an exception in the case of an empty geometric selection.
    :type allow_empty: bool
    :param dir_output: The output directory to which any disk format folders are written. If the directory does not exist, an exception will be raised. This will override :attr:`env.DIR_OUTPUT`.
    :type dir_output: str
    :param headers: A sequence of strings specifying the output headers.
    :type headers: sequence
    """
    
    def __init__(self, dataset=None, spatial_operation='intersects', geom=None, aggregate=False,
                 calc=None, calc_grouping=None, calc_raw=False, abstraction='polygon',
                 snippet=False, backend='ocg', prefix=None,
                 output_format='numpy', agg_selection=False, select_ugid=None, 
                 vector_wrap=True, allow_empty=False, dir_output=None, 
                 slice=None, file_only=False, headers=None, output_crs=None,
                 search_radius_mult=0.75):
        
        # # Tells "__setattr__" to not perform global validation until all
        # # values are set initially.
        self._is_init = True
        
        self.dataset = Dataset(dataset)
        self.spatial_operation = SpatialOperation(spatial_operation)
        self.aggregate = Aggregate(aggregate)
        self.calc = Calc(calc)
        self.calc_grouping = CalcGrouping(calc_grouping)
        self.calc_raw = CalcRaw(calc_raw)
        self.abstraction = Abstraction(abstraction)
        self.snippet = Snippet(snippet)
        self.backend = Backend(backend)
        self.prefix = Prefix(prefix or env.PREFIX)
        self.output_format = OutputFormat(output_format)
        self.agg_selection = AggregateSelection(agg_selection)
        self.select_ugid = SelectUgid(select_ugid)
        self.geom = Geom(geom,select_ugid=self.select_ugid)
        self.vector_wrap = VectorWrap(vector_wrap)
        self.allow_empty = AllowEmpty(allow_empty)
        self.dir_output = DirOutput(dir_output or env.DIR_OUTPUT)
        self.slice = Slice(slice)
        self.file_only = FileOnly(file_only)
        self.headers = Headers(headers)
        self.output_crs = OutputCRS(output_crs)
        self.search_radius_mult = SearchRadiusMultiplier(search_radius_mult)
        
        ## these values are left in to perhaps be added back in at a later date.
        self.output_grouping = None
        
        # # Initial values have been set and global validation should now occur
        # # when any parameters are updated.
        self._is_init = False
        self._validate_()
        
    def __str__(self):
        msg = ['{0}('.format(self.__class__.__name__)]
        for key, value in self.as_dict().iteritems():
            if key == 'geom' and value is not None:
                value = 'custom geometries'
            msg.append(' {0},'.format(self._get_object_(key)))
        msg.append('  )')
        msg = '\n'.join(msg)
        return(msg)
            
    def __getattribute__(self, name):
        attr = object.__getattribute__(self, name)
        if isinstance(attr, OcgParameter):
            ret = attr.value
        else:
            ret = attr
        return(ret)
    
    def __setattr__(self, name, value):
        if isinstance(value, OcgParameter):
            object.__setattr__(self, name, value)
        else:
            try:
                attr = object.__getattribute__(self, name)
                attr.value = value
            except AttributeError:
                object.__setattr__(self, name, value)
        if self._is_init is False:
            self._validate_()
    
    def get_meta(self):
        meta_converter = MetaConverter(self)
        rows = meta_converter.get_rows()
        return('\n'.join(rows))
    
    @classmethod
    def parse_query(cls, query):
        # # TODO: hack
        parms = [SpatialOperation, Geom, Aggregate, Calc, CalcGrouping, CalcRaw,
                 Abstraction, Snippet, Backend, Prefix, OutputFormat,
                 AggregateSelection, SelectUgid, VectorWrap, AllowEmpty]
        
        kwds = {}
        ds = Dataset.parse_query(query)
        kwds.update({ds.name:ds.value})
        
        for parm in parms:
            obj = parm()
            obj.parse_query(query)
            kwds.update({obj.name:obj.value})
            
        ops = OcgOperations(**kwds)
        return(ops)
        
    def as_dict(self):
        """:rtype: dictionary"""
        ret = {}
        for value in self.__dict__.itervalues():
            try:
                ret.update({value.name:value.value})
            except AttributeError:
                pass
        return(ret)
    
    def execute(self):
        """Execute the request using the selected backend.
        
        :rtype: Path to an output file/folder or dictionary composed of :class:`ocgis.api.collection.AbstractCollection` objects.
        """
        interp = OcgInterpreter(self)
        return(interp.execute())
    
    def _get_object_(self, name):
        return(object.__getattribute__(self, name))
    
    def _validate_(self):
        ocgis_lh(logger='operations',msg='validating operations')
        
        def _raise_(msg,obj=OutputFormat):
            e = DefinitionValidationError(OutputFormat,msg)
            ocgis_lh(exc=e,logger='operations')
            
        ## confirm projections are equivalent
        projections = set([])
        for rd in self.dataset:
            crs = rd._get_crs_()
            projections.update([crs])
        if len(set(projections)) > 1 and self.output_format != 'numpy': #@UndefinedVariable
            if self.output_crs is None:
                _raise_('Dataset coordinate reference systems must be equivalent if no output CRS is chosen.',obj=OutputCRS)
        
        if self.snippet:
            if self.calc is not None:
                _raise_('Snippets are not implemented for calculations. Apply a limiting time range for faster responses.',obj=Snippet)
            for rd in self.dataset:
                if rd.time_region is not None:
                    _raise_('Snippets are not implemented for time regions.',obj=Snippet)
        
        if self.slice is not None:
            assert(self.geom is None)
            
        if self.file_only:
            if self.output_format != 'nc':
                _raise_('Only netCDF may be written with file_only as True.',obj=FileOnly)
            if self.calc is None:
                _raise_('File only outputs are only relevant for computations.',obj=FileOnly)
            
        if self.output_format == 'nc':
            if len(self.dataset) > 1 and self.calc is None:
                msg = 'Data packages (i.e. more than one RequestDataset may not be written to netCDF).'
                _raise_(msg,OutputFormat)
            else:
                if self.calc is not None and len(self.dataset) > 1:
                    if sum([issubclass(calc['ref'],AbstractMultivariateFunction) for calc in self.calc]) != 1:
                        msg = 'Data packages (i.e. more than one RequestDataset may not be written to netCDF).'
                        _raise_(msg,OutputFormat)
                
            if self.spatial_operation != 'intersects':
                msg = 'Only "intersects" spatial operation allowed for netCDF output. Arbitrary geometries may not currently be written.'
                _raise_(msg,OutputFormat)
            if self.aggregate:
                msg = 'Data may not be aggregated for netCDF output. The aggregate parameter must be False.'
                _raise_(msg,OutputFormat)
            
            if self.output_crs is not None and not isinstance(self.output_crs,CFWGS84):
                msg = 'CFWGS84 is the only acceptable overloaded output CRS at this time for netCDF output.'
                _raise_(msg,OutputFormat)
                
            if self.calc is not None:
                if self.calc_raw:
                    msg = 'Calculations must be performed on original values (i.e. calc_raw=False) for netCDF output.'
                    _raise_(msg)
                if any([issubclass(c['ref'],AbstractKeyedOutputFunction) for c in self.calc]):
                    msg = 'Keyed function output may not be written to netCDF.'
                    _raise_(msg)
        
        if self.calc is not None:
            for c in self.calc:
                c['ref'].validate(self)
            
