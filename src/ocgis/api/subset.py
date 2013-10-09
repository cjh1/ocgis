from ocgis.calc.engine import OcgCalculationEngine
from ocgis import env
from ocgis.exc import EmptyData, ExtentError, MaskedDataError, EmptySubsetError
from ocgis.util.spatial.wrap import Wrapper
from ocgis.util.logging_ocgis import ocgis_lh
import logging
from ocgis.api.collection import SpatialCollection
from ocgis.interface.base.crs import CFWGS84
from shapely.geometry.point import Point


class SubsetOperation(object):
    
    def __init__(self,ops,serial=True,nprocs=1):
        self.ops = ops
        self.serial = serial
        self.nprocs = nprocs
        
        self._subset_log = ocgis_lh.get_logger('subset')

        ## create the calculation engine
        if self.ops.calc is None:
            self.cengine = None
        else:
            ocgis_lh('initializing calculation engine',self._subset_log,level=logging.DEBUG)
            self.cengine = OcgCalculationEngine(self.ops.calc_grouping,
                                           self.ops.calc,
                                           raw=self.ops.calc_raw,
                                           agg=self.ops.aggregate)
            
        ## check for snippet request in the operations dictionary. if there is
        ## on, the time range should be set in the operations dictionary.
        if self.ops.snippet is True:
            raise(NotImplementedError)
            ##TODO: move snippet to iteration
            ocgis_lh('getting snippet bounds',self._subset_log)
            for rd in self.ops.dataset:
                ## snippet is not implemented for time regions
                if rd.time_region is not None:
                    exc = NotImplementedError('snippet is not implemented for time regions')
                    ocgis_lh(exc=exc,logger=self._subset_log)
                
                rd.level_range = [1,1]
                ods = rd.ds
                ## load the first time slice if there is calculation or the 
                ## calculation does not use a temporal group.
                if self.cengine is None or (self.cengine is not None and self.cengine.grouping is None):
                    ##TODO: improve slicing to not load all time values in a more
                    ## elegant way.
                    ods._load_slice.update({'T':slice(0,1)})
                ## snippet for the computation. this currently requires loading
                ## all the data from the time dimension into memory.
                ##TODO: more efficiently pull dates for monthly grouping (for
                ##example).
                else:
                    ods.temporal.set_grouping(self.cengine.grouping)
                    tgdim = ods.temporal.group
                    times = ods.temporal.value[tgdim.dgroups[0]]
                    rd.time_range = list(ods.temporal.get_datetime([times.min(),times.max()]))
        
    def __iter__(self):
        ''':rtype: AbstractCollection'''
        
        ## simple iterator for serial operations
        if self.serial:
            for coll in self._iter_collections_():
                yield(coll)
#            import ipdb;ipdb.set_trace()
#            it = itertools.imap(get_collection,self._iter_proc_args_())
        ## use a multiprocessing pool returning unordered geometries
        ## for the parallel case
        else:
            raise(ocgis_lh(exc=NotImplementedError('multiprocessing is not available')))
            pool = Pool(processes=self.nprocs)
            it = pool.imap_unordered(get_collection,
                                     self._iter_proc_args_())
#        ## the iterator return from the Pool requires calling its 'next'
#        ## method and catching the StopIteration exception
#        while True:
#            try:
#                yld = it.next()
#                yield(yld)
#            except StopIteration:
#                break
        
#    def _iter_proc_args_(self):
#        ''':rtype: tuple'''
#        
#        subset_log = ocgis_lh.get_logger('subset')
#        ## if there is no geometry, yield None.
#        if self.ops.geom is None:
#            ocgis_lh('returning entire spatial domain - no selection geometry',subset_log)
#            yield(self,None,subset_log)
#            
#        ## iterator through geometries in the ShpDataset
#        elif isinstance(self.ops.geom,ShpDataset):
#            ocgis_lh('{0} geometry(s) to process'.format(len(self.ops.geom)),subset_log)
#            for geom in self.ops.geom:
#                yield(self,geom,subset_log)
#                
#        ## otherwise, the data is likely a GeometryDataset with a single value.
#        ## just return it.
#        else:
#            ocgis_lh('1 geometry to process'.format(len(self.ops.geom)),subset_log)
#            yield(self,self.ops.geom,subset_log)
    
    def _iter_collections_(self):
#        '''
#        :type so: SubsetOperation
#        :type geom: None, GeometryDataset, ShpDataset
#        :rtype: AbstractCollection
#        '''
        
        ocgis_lh('{0} request dataset(s) to process'.format(len(self.ops.dataset)),self._subset_log)
        
        for rd in self.ops.dataset:
            alias = rd.alias
            ocgis_lh('processing...',self._subset_log,alias=alias)
            ## return the field object
            try:
                field = rd.get()
            except EmptySubsetError as e:
                ocgis_lh(exc=ExtentError(message=str(e)),alias=rd.alias,logger=self._subset_log)
#            ## if we are working with a slice, get the sliced field
#            if self.ops.slice is not None:
#                sfield = field.__getitem__(self.ops.slice)
#            ## otherwise, begin iterating over the geometries.
            else:
                ## set iterator based on presence of slice
                if self.ops.slice is not None:
                    itr = [{}]
                else:
                    itr = [{}] if self.ops.geom is None else self.ops.geom
                ## loop over the iterator
                for gd in itr:
                    ## initialize the collection object to store the subsetted data.
                    coll = SpatialCollection(crs=field.spatial.crs)
                    
                    ## reference variables from the geometry dictionary
                    geom = gd.get('geom')
                    
                    ## if the geometry is a point, we need to buffer it...
                    if isinstance(geom,Point):
                        ocgis_lh(logger=self._subset_log,msg='buffering point geometry',level=logging.DEBUG)
                        geom = geom.buffer(self.ops.search_radius_mult*field.spatial.grid.resolution)
                    
                    crs = gd.get('crs')
                    try:
                        ugid = gd['properties']['ugid']
                    except KeyError:
                        ugid = 1
                    ocgis_lh('processing',self._subset_log,level=logging.DEBUG,alias=alias,ugid=ugid)
                    
                    ## if there is a slice, use it to subset the field
                    if self.ops.slice is not None:
                        sfield = field.__getitem__(self.ops.slice)
                    else:
                        ## see if the selection
                        if crs is not None and crs != field.spatial.crs:
                            raise(NotImplementedError('project single geometry'))
                        ## unwrap the data if it is geographic and 360
                        if geom is not None and CFWGS84.get_is_360(field.spatial):
                            ocgis_lh('unwrapping selection geometry',self._subset_log,alias=alias,ugid=ugid)
                            geom = Wrapper().unwrap(geom)
                        ## perform the spatial operation
                        if geom is not None:
                            if self.ops.spatial_operation == 'intersects':
                                sfield = field.get_intersects(geom)
                            elif self.ops.spatial_operation == 'clip':
                                sfield = field.get_clip(geom)
                            else:
                                ocgis_lh(exc=NotImplementedError(self.ops.spatial_operation))
                        else:
                            sfield = field
                        
                    ## aggregate if requested
                    if self.ops.aggregate:
                        sfield = sfield.get_spatially_aggregated()
                    
                    ## wrap the returned data.
                    if not env.OPTIMIZE_FOR_CALC:
                        if CFWGS84.get_is_360(sfield.spatial):
                            if self.ops.output_format != 'nc' and self.ops.vector_wrap:
                                ocgis_lh('wrapping output geometries',self._subset_log,alias=alias,ugid=ugid)
                                sfield.spatial.crs.wrap(sfield.spatial)
                                
                    ## check for all masked values
                    if env.OPTIMIZE_FOR_CALC is False and self.ops.file_only is False:
                        for variable in sfield.variables.itervalues():
                            if variable.value.mask.all():
                                ## masked data may be okay depending on other opeartional
                                ## conditions.
                                if self.ops.snippet or self.ops.allow_empty:
                                    if self.ops.snippet:
                                        ocgis_lh('all masked data encountered but allowed for snippet',
                                                 self._subset_log,alias=alias,ugid=ugid,level=logging.WARN)
                                    if self.ops.allow_empty:
                                        ocgis_lh('all masked data encountered but empty returns allowed',
                                                 self._subset_log,alias=alias,ugid=ugid,level=logging.WARN)
                                    pass
                                else:
                                    ## if the geometry is also masked, it is an empty spatial
                                    ## operation.
                                    if sfield.spatial.abstraction_geometry.value.mask.all():
                                        ocgis_lh(exc=EmptyData,logger=self._subset_log)
                                    ## if none of the other conditions are met, raise the masked data error
                                    else:
                                        ocgis_lh(logger=self._subset_log,exc=MaskedDataError(),alias=alias,ugid=ugid)
                    
#                    ## there may be no data returned - this may be real or could be an
#                    ## error. by default, empty returns are not allowed
#                    except EmptyData as ed:
#                        if so.ops.allow_empty:
#                            if ed.origin == 'time':
#                                msg = 'the time subset returned empty but empty returns are allowed'
#                            else:
#                                msg = 'the geometric operations returned empty but empty returns are allowed'
#                            ocgis_lh(msg,logger,alias=alias,ugid=ugid)
#                            continue
#                        else:
#                            if ed.origin == 'time':
#                                msg = 'empty temporal subset operation'
#                            else:
#                                msg = 'empty geometric operation'
#                            ocgis_lh(msg,logger,exc=ExtentError(msg),alias=alias,ugid=ugid)
#                    
#                    import ipdb;ipdb.set_trace()
                        
                    coll.add_field(ugid,geom,alias,sfield,properties=gd.get('properties'))
                    
                    ## if there are calculations, do those now and return a new type of collection
                    if self.cengine is not None:
                        raise(NotImplementedError)
                        ocgis_lh('performing computations',self._subset_log,alias=alias,ugid=ugid)
                        coll = self.cengine.execute(coll,file_only=self.ops.file_only)
                    
                    ## conversion of groups.
                    if self.ops.output_grouping is not None:
                        raise(NotImplementedError)
                    else:
                        ocgis_lh('subset yielding',self._subset_log,level=logging.DEBUG)
                        yield(coll)


################################################################################
#### OLD CODE ##################################################################
################################################################################

                            
#                    if type(ods.spatial.projection) == WGS84 and \
#                       ods.spatial.is_360 and \
#                       so.ops.output_format != 'nc' and \
#                       so.ops.vector_wrap:
#                        ocgis_lh('wrapping output geometries',logger,alias=alias,
#                                 ugid=ugid)
#                        ods.spatial.vector.wrap()
#                        ocgis_lh('geometries wrapped',logger,alias=alias,
#                                 ugid=ugid,level=logging.DEBUG)
#                import ipdb;ipdb.set_trace()
#                    if type(field.spatial.crs) == CFWGS84 and field.spatial.is_360:
#                        ocgis_lh('unwrapping selection geometry with axis={0}'.format(ods.spatial.pm),
#                                 logger,alias=alias,ugid=ugid)
#                        w = Wrapper(axis=ods.spatial.pm)
#                        copy_geom.spatial.geom[0] = w.unwrap(deepcopy(copy_geom.spatial.geom[0]))
#                    igeom = copy_geom.spatial.geom[0]
#                    import ipdb;ipdb.set_trace()
                    
            
#            ## reference the geometry ugid
#            ugid = None if geom is None else geom.spatial.uid[0]
#            for request_dataset in so.ops.dataset:
#                ## reference the request dataset alias
#                alias = request_dataset.alias
#                ocgis_lh('processing',logger,level=logging.INFO,alias=alias,ugid=ugid)
#                ## copy the geometry
#                copy_geom = deepcopy(geom)
#                ## reference the dataset object
#                ods = request_dataset.ds
#                ## return a slice or do the other operations
#                if so.ops.slice is not None:
#                    ods = ods.__getitem__(so.ops.slice)
#                ## other subsetting operations
#                else:
#                    ## if a geometry is passed and the target dataset is 360 longitude,
#                    ## unwrap the passed geometry to match the spatial domain of the target
#                    ## dataset.
#                    if copy_geom is None:
#                        igeom = None
#                    else:
#                        ## check projections adjusting projection the selection geometry
#                        ## if necessary
#                        if type(ods.spatial.projection) != type(copy_geom.spatial.projection):
#                            msg = 'projecting selection geometry to match input projection: {0} to {1}'
#                            msg = msg.format(copy_geom.spatial.projection.__class__.__name__,
#                                             ods.spatial.projection.__class__.__name__)
#                            ocgis_lh(msg,logger,alias=alias,ugid=ugid)
#                            copy_geom.project(ods.spatial.projection)
#                        else:
#                            ocgis_lh('projections match',logger,alias=alias,ugid=ugid)
#                        ## unwrap the data if it is geographic and 360
#                        if type(ods.spatial.projection) == WGS84 and ods.spatial.is_360:
#                            ocgis_lh('unwrapping selection geometry with axis={0}'.format(ods.spatial.pm),
#                                     logger,alias=alias,ugid=ugid)
#                            w = Wrapper(axis=ods.spatial.pm)
#                            copy_geom.spatial.geom[0] = w.unwrap(deepcopy(copy_geom.spatial.geom[0]))
#                        igeom = copy_geom.spatial.geom[0]
#                    ## perform the data subset
#                    try:
#                        ## pull the temporal subset which may be a range or region. if
#                        ## it is a snippet operation, set the temporal subset to None
#                        ## as a slice has already been applied. however, if a calculation
#                        ## is present leave the temporal subset alone.
#                        if so.ops.snippet and so.ops.calc is None:
#                            temporal = None
#                        else:
#                            temporal = request_dataset.time_range or request_dataset.time_region
                        
                        
#                        ocgis_lh('executing get_subset',logger,level=logging.DEBUG)
#                        ods = ods.get_subset(spatial_operation=so.ops.spatial_operation,
#                                             igeom=igeom,
#                                             temporal=temporal,
#                                             level=request_dataset.level_range)
#                        
#                        ## for the case of time range and time region subset, apply the
#                        ## time region subset following the time range subset.
#                        if request_dataset.time_range is not None and request_dataset.time_region is not None:
#                            ods._temporal = ods.temporal.subset(request_dataset.time_region)
#                        
#                        ## aggregate the geometries and data if requested
#                        if so.ops.aggregate:
#                            ocgis_lh('aggregating target geometries and area-weighting values',
#                                     logger,alias=alias,ugid=ugid)
#                            ## the new geometry will have the same id as the passed
#                            ## geometry. if it does not have one, simple give it a value
#                            ## of 1 as it is the only geometry requested for subsetting.
#                            try:
#                                new_geom_id = copy_geom.spatial.uid[0]
#                            except AttributeError:
#                                new_geom_id = 1
#                            ## do the aggregation in place.
#                            clip_geom = None if copy_geom is None else copy_geom.spatial.geom[0]
#                            ods.aggregate(new_geom_id=new_geom_id,
#                                          clip_geom=clip_geom)



#                        ## wrap the returned data depending on the conditions of the
#                        ## operations.
#                        if not env.OPTIMIZE_FOR_CALC:
#                            if type(ods.spatial.projection) == WGS84 and \
#                               ods.spatial.is_360 and \
#                               so.ops.output_format != 'nc' and \
#                               so.ops.vector_wrap:
#                                ocgis_lh('wrapping output geometries',logger,alias=alias,
#                                         ugid=ugid)
#                                ods.spatial.vector.wrap()
#                                ocgis_lh('geometries wrapped',logger,alias=alias,
#                                         ugid=ugid,level=logging.DEBUG)



#                        ## check for all masked values
#                        if env.OPTIMIZE_FOR_CALC is False and so.ops.file_only is False:
#                            if ods.value.mask.all():
#                                ## masked data may be okay depending on other opeartional
#                                ## conditions.
#                                if so.ops.snippet or so.ops.allow_empty:
#                                    if so.ops.snippet:
#                                        ocgis_lh('all masked data encountered but allowed for snippet',
#                                                 logger,alias=alias,ugid=ugid,level=logging.WARN)
#                                    if so.ops.allow_empty:
#                                        ocgis_lh('all masked data encountered but empty returns allowed',
#                                                 logger,alias=alias,ugid=ugid,level=logging.WARN)
#                                    pass
#                                else:
#                                    ## if the geometry is also masked, it is an empty spatial
#                                    ## operation.
#                                    if ods.spatial.vector.geom.mask.all():
#                                        raise(EmptyData)
#                                    else:
#                                        ocgis_lh(None,logger,exc=MaskedDataError(),alias=alias,ugid=ugid)
#                    ## there may be no data returned - this may be real or could be an
#                    ## error. by default, empty returns are not allowed
#                    except EmptyData as ed:
#                        if so.ops.allow_empty:
#                            if ed.origin == 'time':
#                                msg = 'the time subset returned empty but empty returns are allowed'
#                            else:
#                                msg = 'the geometric operations returned empty but empty returns are allowed'
#                            ocgis_lh(msg,logger,alias=alias,ugid=ugid)
#                            continue
#                        else:
#                            if ed.origin == 'time':
#                                msg = 'empty temporal subset operation'
#                            else:
#                                msg = 'empty geometric operation'
#                            ocgis_lh(msg,logger,exc=ExtentError(msg),alias=alias,ugid=ugid)
#                ods.spatial._ugid = ugid
#                coll.variables.update({request_dataset.alias:ods})
#        
#            ## if there are calculations, do those now and return a new type of collection
#            if so.cengine is not None:
#                ocgis_lh('performing computations',logger,alias=alias,ugid=ugid)
#                coll = so.cengine.execute(coll,file_only=so.ops.file_only)
#            
#            ## conversion of groups.
#            if so.ops.output_grouping is not None:
#                raise(NotImplementedError)
#            else:
#                ocgis_lh('subset returning',logger,level=logging.INFO)
#                return(coll)
