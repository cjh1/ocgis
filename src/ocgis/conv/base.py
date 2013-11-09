from ocgis.conv.meta import MetaConverter
import os.path
import abc
from abc import ABCMeta
import csv
from ocgis.util.inspect import Inspect
from ocgis.util.logging_ocgis import ocgis_lh
import logging
from collections import OrderedDict
from shapely.geometry.multipolygon import MultiPolygon
from shapely.geometry.polygon import Polygon
from shapely.geometry.point import Point
import fiona
from shapely.geometry.geo import mapping
from csv import DictWriter


class OcgConverter(object):
    __metaclass__ = ABCMeta
    '''Base converter object. Intended for subclassing.
    
    :param colls: A sequence of `~ocgis.OcgCollection` objects.
    :type colls: sequence of `~ocgis.OcgCollection` objects
    
    so :: SubsetOperation
    mode="raw" :: str :: Iterator mode.
    base_name="ocg" :: str :: Prefix for data outputs.
    wd="/tmp" :: str :: Working directory for data outputs. Outputs are nested
        in temporary folders creating in this directory.
    use_dir=None :: str :: If provided, forces outputs into this directory.
    '''
    __metaclass__ = abc.ABCMeta
    _ext = None
    _add_did_file = True ## add a descriptor file for the request datasets
    _add_ugeom = False ## added user geometry in the output folder
    _add_ugeom_nest = True ## nest the user geometry in a shp folder
    _add_source_meta = True ## add a source metadata file
    
#    @abc.abstractmethod
#    def _write_(self): pass # string path or data
    
    def __init__(self,colls,outdir,prefix,mode='raw',ops=None,add_meta=True):
        self.colls = colls
        self.ops = ops
        self.prefix = prefix
        self.outdir = outdir
        self.mode = mode
        self.add_meta = add_meta
        self._log = ocgis_lh.get_logger('conv')
        
        if self._ext is None:
            self.path = self.outdir
        else:
            self.path = os.path.join(self.outdir,prefix+'.'+self._ext)
        ocgis_lh('converter initialized',level=logging.DEBUG,logger=self._log)
        
    def _build_(self,*args,**kwds): raise(NotImplementedError)
    
    def _get_fileobject_(self,*args,**kwds): raise(NotImplementedError)
    
    def _get_return_(self):
        return(self.path)
    
    def _write_coll_(self,f,coll): raise(NotImplementedError)
    
    def _finalize_(self,*args,**kwds): raise(NotImplementedError)
    
    def _get_or_create_shp_folder_(self):
        path = os.path.join(self.outdir,'shp')
        if not os.path.exists(path):
            os.mkdir(path)
        return(path)
    
    def write(self):
        ocgis_lh('starting write method',self._log,logging.DEBUG)
        
        try:
            build = True
            if self._add_ugeom and self.ops.geom is not None:
                write_geom = True
            else:
                write_geom = False
            for coll in iter(self.colls):
                if build:
                    f = self._get_fileobject_(coll)
                    ocgis_lh('got file object',logger=self._log,level=logging.DEBUG)
                    self._build_(f,coll)
                    if write_geom:
                        ugid_shp_name = self.prefix + '_ugid.shp'
                        ugid_csv_name = self.prefix + '_ugid.csv'
                        
                        if self._add_ugeom_nest:
                            fiona_path = os.path.join(self._get_or_create_shp_folder_(),ugid_shp_name)
                            csv_path = os.path.join(self._get_or_create_shp_folder_(),ugid_csv_name)
                        else:
                            fiona_path = os.path.join(self.outdir,ugid_shp_name)
                            csv_path = os.path.join(self.outdir,ugid_csv_name)
                            
                        if coll.meta is None:
                            fiona_properties = {'UGID':'int'}
                            r_geom = coll.geoms.values()[0]
                            if type(r_geom) in [Polygon,MultiPolygon]:
                                geom_type = 'MultiPolygon'
                            elif type(r_geom) == Point:
                                geom_type = 'Point'
                            else:
                                ocgis_lh(exc=NotImplementedError(type(r_geom)),logger='conv.base')
                            fiona_schema = {'geometry':geom_type,
                                            'properties':fiona_properties}
                            fiona_meta = {'crs':coll.crs.value,'schema':fiona_schema,'driver':'ESRI Shapefile'}
                        else:
                            fiona_meta = coll.meta
                        
                        fiona_object = fiona.open(fiona_path,'w',**fiona_meta)
                        csv_file = open(csv_path,'w')
                        
                        from ocgis.conv.csv_ import OcgDialect
                        csv_object = DictWriter(csv_file,fiona_meta['schema']['properties'].keys(),dialect=OcgDialect)
                        csv_object.writeheader()
                        
                    build = False
                self._write_coll_(f,coll)
                if write_geom:
                    ## write the overview geometries to disk
                    r_geom = coll.geoms.values()[0]
                    if isinstance(r_geom,Polygon):
                        r_geom = MultiPolygon([r_geom])
                    to_write = {'geometry':mapping(r_geom),
                                'properties':{k.upper():v for k,v in coll.properties.values()[0].iteritems()}}
                    fiona_object.write(to_write)
                    
                    ## write the geometry attributes to the corresponding shapefile
                    for row in coll.properties.itervalues():
                        csv_object.writerow({k.upper():v for k,v in row.iteritems()})
                    
        finally:
            
            ## errors are masked if the processing failed and file objects, etc.
            ## were not properly created. if there are UnboundLocalErrors pass
            ## them through to capture the error that lead to the objects not
            ## being created.
            
            try:
                try:
                    self._finalize_(f)
                except UnboundLocalError:
                    pass
            except Exception as e:
                ## this the exception we want to log
                ocgis_lh(exc=e,logger=self._log)
            finally:
                if write_geom:
                    try:
                        fiona_object.close()
                    except UnboundLocalError:
                        pass
                    try:
                        csv_file.close()
                    except UnboundLocalError:
                        pass
            
        ## added OCGIS metadata output if requested.
        if self.add_meta:
            ocgis_lh('adding OCGIS metadata file','conv',logging.DEBUG)
            lines = MetaConverter(self.ops).write()
            out_path = os.path.join(self.outdir,self.prefix+'_'+MetaConverter._meta_filename)
            with open(out_path,'w') as f:
                f.write(lines)
        
        ## add the dataset descriptor file if specified
        if self._add_did_file:
            ocgis_lh('writing dataset description (DID) file','conv',logging.DEBUG)
            from ocgis.conv.csv_ import OcgDialect
            
            headers = ['DID','VARIABLE','ALIAS','URI','STANDARD_NAME','UNITS','LONG_NAME']
            out_path = os.path.join(self.outdir,self.prefix+'_did.csv')
            with open(out_path,'w') as f:
                writer = csv.writer(f,dialect=OcgDialect)
                writer.writerow(headers)
                for rd in self.ops.dataset:
                    row = [rd.did,rd.variable,rd.alias,rd.uri]
                    ref_variable = rd._source_metadata['variables'][rd.variable]['attrs']
                    row.append(ref_variable.get('standard_name',None))
                    row.append(ref_variable.get('units',None))
                    row.append(ref_variable.get('long_name',None))
                    writer.writerow(row)
                    
#        ## add user-geometry
#        if self._add_ugeom and self.ops.geom is not None:
#            ocgis_lh('writer user-geometry shapefile','conv',logging.DEBUG)
#            if self._add_ugeom_nest:
#                shp_dir = os.path.join(self.outdir,'shp')
#                try:
#                    os.mkdir(shp_dir)
#                ## catch if the directory exists
#                except OSError:
#                    if os.path.exists(shp_dir):
#                        pass
#                    else:
#                        raise
#            else:
#                shp_dir = self.outdir
#            shp_path = os.path.join(shp_dir,self.prefix+'_ugid.shp')
#            self.ops.geom.write(shp_path)
            
        ## add source metadata if requested
        if self._add_source_meta:
            ocgis_lh('writing source metadata file','conv',logging.DEBUG)
            out_path = os.path.join(self.outdir,self.prefix+'_source_metadata.txt')
            to_write = []
            for rd in self.ops.dataset:
                ip = Inspect(request_dataset=rd)
                to_write += ip.get_report()
            with open(out_path,'w') as f:
                f.writelines('\n'.join(to_write))
        
        ## return the internal path unless overloaded by subclasses.
        ret = self._get_return_()
        
        return(ret)
    
    def OLD_write(self):
        ## call subclass write method
        ocgis_lh('starting subclass write method',self._log,logging.DEBUG)
        ret = self._write_()
        
        ## added OCGIS metadata output if requested.
        if self.add_meta:
            ocgis_lh('adding OCGIS metadata file','conv',logging.DEBUG)
            lines = MetaConverter(self.ops).write()
            out_path = os.path.join(self.outdir,self.prefix+'_'+MetaConverter._meta_filename)
            with open(out_path,'w') as f:
                f.write(lines)
        
        ## add the dataset descriptor file if specified
        if self._add_did_file:
            ocgis_lh('writing dataset description (DID) file','conv',logging.DEBUG)
            from ocgis.conv.csv_ import OcgDialect
            
            headers = ['DID','VARIABLE','ALIAS','URI','STANDARD_NAME','UNITS','LONG_NAME']
            out_path = os.path.join(self.outdir,self.prefix+'_did.csv')
            with open(out_path,'w') as f:
                writer = csv.writer(f,dialect=OcgDialect)
                writer.writerow(headers)
                for rd in self.ops.dataset:
                    row = [rd.did,rd.variable,rd.alias,rd.uri]
                    ref_variable = rd._source_metadata['variables'][rd.variable]['attrs']
                    row.append(ref_variable.get('standard_name',None))
                    row.append(ref_variable.get('units',None))
                    row.append(ref_variable.get('long_name',None))
                    writer.writerow(row)
                    
        ## add user-geometry
        if self._add_ugeom and self.ops.geom is not None:
            ocgis_lh('writer user-geometry shapefile','conv',logging.DEBUG)
            if self._add_ugeom_nest:
                shp_dir = os.path.join(self.outdir,'shp')
                try:
                    os.mkdir(shp_dir)
                ## catch if the directory exists
                except OSError:
                    if os.path.exists(shp_dir):
                        pass
                    else:
                        raise
            else:
                shp_dir = self.outdir
            shp_path = os.path.join(shp_dir,self.prefix+'_ugid.shp')
            self.ops.geom.write(shp_path)
            
        ## add source metadata if requested
        if self._add_source_meta:
            ocgis_lh('writing source metadata file','conv',logging.DEBUG)
            out_path = os.path.join(self.outdir,self.prefix+'_source_metadata.txt')
            to_write = []
            for rd in self.ops.dataset:
                ip = Inspect(request_dataset=rd)
                to_write += ip.get_report()
            with open(out_path,'w') as f:
                f.writelines('\n'.join(to_write))
        
        ## return anything from the overloaded _write_ method. otherwise return
        ## the internal path.
        if ret is None:
            ret = self.path
        
        return(ret)
        
    @classmethod
    def get_converter(cls,output_format):
        '''Return the converter based on output extensions or key.
        
        output_format :: str
        
        returns
        
        OcgConverter'''
        
        from ocgis.conv.shp import ShpConverter
        from ocgis.conv.csv_ import CsvConverter, CsvPlusConverter
        from ocgis.conv.numpy_ import NumpyConverter
#        from ocgis.conv.shpidx import ShpIdxConverter
#        from ocgis.conv.keyed import KeyedConverter
        from ocgis.conv.nc import NcConverter
        
        mmap = {'shp':ShpConverter,
                'csv':CsvConverter,
                'csv+':CsvPlusConverter,
                'numpy':NumpyConverter,
#                'shpidx':ShpIdxConverter,
#                'keyed':KeyedConverter,
                'nc':NcConverter}
        
        return(mmap[output_format])

#    def __iter__(self):
#        '''Iterator over collections stored in the SubsetOperation object.
#        
#        yields
#        
#        OcgCollection
#        dict'''
#        for coll in self.colls:
#            yield(coll)
