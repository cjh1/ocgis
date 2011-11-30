from osgeo import ogr, osr
import datetime
from shapely.geometry.multipolygon import asMultiPolygon
from util.helpers import get_temp_path
from shapely.geometry.polygon import Polygon
import zipfile
import io
import os
import copy
import csv
import geojson
from util.ncconv.experimental.helpers import get_sr, get_area

import logging
logger = logging.getLogger(__name__)


class OcgConverter(object):
    
    def __init__(self,db,base_name):
        self.db = db
        self.base_name = base_name
        
    def convert(self,*args,**kwds):
        return(self._convert_(*args,**kwds))
    
    def _convert_(self,*args,**kwds):
        raise(NotImplementedError)
    
    def response(self,*args,**kwds):
        payload = self.convert(*args,**kwds)
        try:
            return(self._response_(payload))
        finally:
            self.cleanup()
    
    def _response_(self,payload):
        return(payload)
    
    def cleanup(self):
        pass
    
    
class GeojsonConverter(OcgConverter):
    
    def _convert_(self):
        features = []
        s = self.db.Session()
        try:
            for obj in s.query(self.db.Value):
                attrs = dict(time=str(obj.time.time),
                             geometry=obj.geometry.wkt,
                             level=obj.level,
                             value=obj.value)
                features.append(attrs)
            fc = geojson.FeatureCollection(features)
            return(geojson.dumps(fc))
        finally:
            s.close()
    

class CsvConverter(OcgConverter):
    __headers__ = ['OCGID','TIME','LEVEL','VALUE','AREA_M2','WKT','WKB']
    
    def __init__(self,*args,**kwds):
        self.as_wkt = self._pop_(kwds,'as_wkt',False)
        self.as_wkb = self._pop_(kwds,'as_wkb',False)
        self.add_area = self._pop_(kwds,'add_area',True)
        self.area_srid = self._pop_(kwds,'area_srid',3005)
        self.headers = self._clean_headers_()
        self.to_disk = self._pop_(kwds,'to_disk',False)
        
        ## call the superclass
        super(CsvConverter,self).__init__(*args,**kwds)
    
    def get_DictWriter(self,buffer,headers=None):
        writer = csv.writer(buffer)
        if headers is None: headers = self.headers
        writer.writerow(headers)
        writer = csv.DictWriter(buffer,headers)
        return(writer)
    
    def _clean_headers_(self):
        map = [[self.as_wkt,'WKT'],
               [self.as_wkb,'WKB'],
               [self.add_area,'AREA_M2']]
        headers = copy.copy(self.__headers__)
        for m in map:
            if not m[0]:
                headers.remove(m[1])
        return(headers)
    
    def _convert_(self,request):
        if self.add_area:
            sr_orig = get_sr(4326)
            sr_dest = get_sr(self.area_srid)
        buffer = io.BytesIO()
        writer = self.get_DictWriter(buffer)
        for ii,attrs in enumerate(self.sub_ocg_dataset,start=1):
            geom = attrs['geometry']
            row = dict(OCGID=ii,
                       VALUE=attrs['value'],
                       LEVEL=attrs['level'],
                       TIME=attrs['time'])
            if self.add_area:
                row.update(AREA_M2=get_area(geom,sr_orig,sr_dest))
            if self.as_wkt:
                row.update(WKT=geom.wkt)
            if self.as_wkb:
                row.update(WKB=geom.wkb)
            writer.writerow(row)
        buffer.flush()
        return(buffer.getvalue())
    
    
class LinkedCsvConverter(CsvConverter):
    
    def __init__(self,*args,**kwds):
        self._db = None
        super(LinkedCsvConverter,self).__init__(*args,**kwds)
        
    @property
    def db(self):
        if self._db is None:
            self._db = self.sub_ocg_dataset.as_sqlite()
        return(self._db)
    
    def _convert_(self,request,tables=['Geometry','Time','Value'],include_wkt=True):
        ## database tables to write
        tables = [getattr(self.db,tbl) for tbl in tables]
        ## generate the info for writing
        info = []
        for table in tables:
            headers = [h.upper() for h in table.__mapper__.columns.keys()]
            if table == self.db.Geometry and not include_wkt:
                headers.remove('WKT')
            arcname = '{0}_{1}.csv'.format(self.base_name,table.__tablename__)
            buffer = io.BytesIO()
            writer = self.get_DictWriter(buffer,
                                         headers=headers)
            info.append(dict(headers=headers,
                             writer=writer,
                             arcname=arcname,
                             table=table,
                             buffer=buffer))
        ## write the tables
        s = self.db.Session()
        try:
            for i in info:
                ## loop through each database record
                q = s.query(i['table']).all()
                for obj in q:
                    row = dict()
                    for h in i['headers']:
                        row.update({h:getattr(obj,h.lower())})
                    i['writer'].writerow(row)
                i['buffer'].flush()
        finally:
            s.close()

        return(info)
    
    def _response_(self,payload):
        buffer = io.BytesIO()
        zip = zipfile.ZipFile(buffer,'w',zipfile.ZIP_DEFLATED)
        for info in payload:
            zip.writestr(info['arcname'],info['buffer'].getvalue())
        zip.close()
        buffer.flush()
        zip_stream = buffer.getvalue()
        buffer.close()
        return(zip_stream)


class KmlConverter(OcgConverter):
    '''Converts data to a KML string'''
    
    def __init__(self,*args,**kwds):
        self.to_disk = self._pop_(kwds,'to_disk',False)
        ## call the superclass
        super(KmlConverter,self).__init__(*args,**kwds)
    
    def _convert_(self,request):
        from pykml.factory import KML_ElementMaker as KML
        from lxml import etree
        
        ## create the database
        db = self.sub_ocg_dataset.as_sqlite()
        
        meta = request.ocg
        if request.environ['SERVER_PORT']=='80':
            portstr = ''
        else:
            portstr = ':{port}'.format(port=request.environ['SERVER_PORT'])
        
        url='{protocol}://{server}{port}{path}'.format(
            protocol='http',
            port=portstr,
            server=request.environ['SERVER_NAME'],
            path=request.environ['PATH_INFO'],
        )
        description = (
            '<table border="1">'
              '<tbody>'
                '<tr><th>Archive</th><td>{archive}</td></tr>'
                '<tr><th>Emissions Scenario</th><td>{scenario}</td></tr>'
                '<tr><th>Climate Model</th><td>{model}</td></tr>'
                '<tr><th>Run</th><td>{run}</td></tr>'
                '<tr><th>Output Variable</th><td>{variable}</td></tr>'
                '<tr><th>Units</th><td>{units}</td></tr>'
                '<tr><th>Start Time</th><td>{start}</td></tr>'
                '<tr><th>End Time</th><td>{end}</td></tr>'
                '<tr>'
                  '<th>Request URL</th>'
                  '<td><a href="{url}">{url}</a></td>'
                '</tr>'
                '<tr>'
                  '<th>Other Available Formats</th>'
                  '<td>'
                    '<a href="{url}">KML</a> - Keyhole Markup Language<br/>'
                    '<a href="{url_kmz}">KMZ</a> - Keyhole Markup Language (zipped)<br/>'
                    '<a href="{url_shz}">Shapefile</a> - ESRI Shapefile<br/>'
                    '<a href="{url_csv}">CSV</a> - Comma Separated Values (text file)<br/>'
                    '<a href="{url_json}">JSON</a> - Javascript Object Notation'
                  '</td>'
                '</tr>'
              '</tbody>'
            '</table>'
        ).format(
            archive=meta.archive.name,
            scenario=meta.scenario,
            model=meta.climate_model,
            run=meta.run,
            variable=meta.variable,
            units=meta.variable.units,
            simout=meta.simulation_output.netcdf_variable,
            start=meta.temporal[0],
            end=meta.temporal[-1],
            operation=meta.operation,
            url=url,
            url_kmz=url.replace('.kml', '.kmz'),
            url_shz=url.replace('.kml', '.shz'),
            url_csv=url.replace('.kml', '.csv'),
            url_json=url.replace('.kml', '.geojson'),
        )
        
        doc = KML.kml(
          KML.Document(
            KML.name('Climate Simulation Output'),
            KML.open(1),
            KML.description(description),
            KML.snippet(
                '<i>Click for metadata!</i>',
                maxLines="2",
            ),
            KML.StyleMap(
              KML.Pair(
                KML.key('normal'),
                KML.styleUrl('#style-normal'),
              ),
              KML.Pair(
                KML.key('highlight'),
                KML.styleUrl('#style-highlight'),
              ),
              id="smap",
            ),
            KML.Style(
              KML.LineStyle(
                KML.color('ff0000ff'),
                KML.width('2'),
              ),
              KML.PolyStyle(
                KML.color('400000ff'),
              ),
              id="style-normal",
            ),
            KML.Style(
              KML.LineStyle(
                KML.color('ff00ff00'),
                KML.width('4'),
              ),
              KML.PolyStyle(
                KML.color('400000ff'),
              ),
              id="style-highlight",
            ),
            #Time Folders will be appended here
          ),
        )
        
        try:
            s = db.Session()
            for time in s.query(db.Time).all():
                # create a folder for the time
                timefld = KML.Folder(
#                    KML.Style(
#                      KML.ListStyle(
#                        KML.listItemType('checkHideChildren'),
#                        KML.bgColor('00ffffff'),
#                        KML.maxSnippetLines('2'),
#                      ),
#                    ),
                    KML.name(time.as_xml_date()),
                    # placemarks will be appended here
                )
                for val in time.value:
                    poly_desc = (
                        '<table border="1">'
                          '<tbody>'
                            '<tr><th>Variable</th><td>{variable}</td></tr>'
                            '<tr><th>Date/Time (UTC)</th><td>{time}</td></tr>'
                            '<tr><th>Value</th><td>{value:.{digits}f} {units}</td></tr>'
                          '</tbody>'
                        '</table>'
                    ).format(
                        variable=meta.variable.name,
                        time=val.time.as_xml_date(),
                        value=val.value,
                        digits=3,
                        units=meta.variable.units,
                    )
                    
                    coords = val.geometry.as_kml_coords()
                    timefld.append(
                      KML.Placemark(
                        KML.name('Geometry'),
                        KML.description(poly_desc),
                        KML.styleUrl('#smap'),
                        KML.Polygon(
                          KML.tessellate('1'),
                          KML.outerBoundaryIs(
                            KML.LinearRing(
                              KML.coordinates(coords),
                            ),
                          ),
                        ),
                      )
                    )
                doc.Document.append(timefld)
            pass
        finally:
            s.close()
        
        # return the pretty print sting
        return(etree.tostring(doc, pretty_print=True))


class KmzConverter(KmlConverter):
    
    def _response_(self,payload):
        '''Get the KML response and zip it up'''
        logger.info("starting KmzConverter._response_()...")
        #kml = super(KmzConverter,self)._response_(payload)
        
        iobuffer = io.BytesIO()
        zf = zipfile.ZipFile(
            iobuffer, 
            mode='w',
            compression=zipfile.ZIP_DEFLATED, 
        )
        try:
            zf.writestr('doc.kml',payload)
        finally:
            zf.close()
        iobuffer.flush()
        zip_stream = iobuffer.getvalue()
        iobuffer.close()
        logger.info("...ending KmzConverter._response_()")
        return(zip_stream)


class ShpConverter(OcgConverter):
    __exts__ = ['shp','shx','prj','dbf']
    
    def __init__(self,*args,**kwds):
        self.layer = self._pop_(kwds,'layer','lyr')
        self.srid = self._pop_(kwds,'srid',4326)
        
        ## call the superclass
        super(ShpConverter,self).__init__(*args,**kwds)
        
        ## generate dataset path
        self.path = get_temp_path(name=self.base_name,nest=True)
        
        ## create shapefile base attributes
        self.fcache = FieldCache()
        self.ogr_fields = []
        self._set_ogr_fields_()
        
        ## get the geometry in order
#        self.ogr_geom = OGRGeomType(self.sub_ocg_dataset.geometry[0].geometryType()).num
        self.ogr_geom = 6 ## assumes multipolygon
        self.srs = osr.SpatialReference()
        self.srs.ImportFromEPSG(self.srid)
    
    def _set_ogr_fields_(self):
        ## create shapefile base attributes
        self.ogr_fields.append(OgrField(self.fcache,'ocgid',int))
        self.ogr_fields.append(OgrField(self.fcache,'gid',int))
        self.ogr_fields.append(OgrField(self.fcache,'time',datetime.datetime))
        self.ogr_fields.append(OgrField(self.fcache,'level',int))
        self.ogr_fields.append(OgrField(self.fcache,'value',float))
        self.ogr_fields.append(OgrField(self.fcache,'area_m2',float))
        
    def _get_iter_(self):
        ## returns an iterator instance that generates a dict to match
        ## the ogr field mapping. must also return a geometry wkt attribute.
        return(self.sub_ocg_dataset.iter_with_area())
        
    def _convert_(self,request,geom_is_shapely=True):
        """is "geom_is_shapely" is False, then it must be WKT."""
        dr = ogr.GetDriverByName('ESRI Shapefile')
        ds = dr.CreateDataSource(self.path)
        if ds is None:
            raise IOError('Could not create file on disk. Does it already exist?')
        
        layer = ds.CreateLayer(self.layer,srs=self.srs,geom_type=self.ogr_geom)
        
        for ogr_field in self.ogr_fields:
            check_err(layer.CreateField(ogr_field.ogr_field))
                
        feature_def = layer.GetLayerDefn()
        
        for ii,attr in enumerate(self._get_iter_(),start=1):
            feat = ogr.Feature(feature_def)
            ## pull values 
            for o in self.ogr_fields:
                val = None
                if o.orig_name == 'ocgid':
                    val = ii
                elif o.orig_name == 'gid':
                    ## the iterator may not generate a cell_id entry. in this
                    ## case, pass and let the subclass fill in the gid
                    if 'cell_id' in attr:
                        val = attr['cell_id']
                if val is None:
                    val = attr[o.orig_name]
                args = [o.ogr_name,val]
                try:
                    feat.SetField(*args)
                except NotImplementedError:
                    args[1] = str(args[1])
                    feat.SetField(*args)
            if geom_is_shapely:
                wkt = attr['geometry'].wkt
            else:
                wkt = attr['geometry']
            check_err(feat.SetGeometry(ogr.CreateGeometryFromWkt(wkt)))
            check_err(layer.CreateFeature(feat))
            
        return(self.path)
    
    def _response_(self,payload):
        buffer = io.BytesIO()
        zip = zipfile.ZipFile(buffer,'w',zipfile.ZIP_DEFLATED)
        for item in self.__exts__:
            filepath = payload.replace('shp',item)
            zip.write(filepath,arcname=os.path.split(filepath)[1])
        zip.close()
        buffer.flush()
        zip_stream = buffer.getvalue()
        buffer.close()
        return(zip_stream)
    
    
class LinkedShpConverter(ShpConverter):
    
    def __init__(self,*args,**kwds):
        args = list(args)
        args[1] = os.path.splitext(args[1])[0]+'.shp'
        super(LinkedShpConverter,self).__init__(*args,**kwds)
    
    def _convert_(self,request):
        ## get the payload dictionary from the linked csv converter. we also
        ## want to store the database module.
        lcsv = LinkedCsvConverter(self.sub_ocg_dataset,os.path.splitext(self.base_name)[0])
        self.db = lcsv.db
        info = lcsv._convert_(request,include_wkt=False)
        ## get the shapefile path (and write in the process)
        path = super(LinkedShpConverter,self)._convert_(request,geom_is_shapely=False)
        return(info,path)
        
    def _response_(self,payload):
        info,path = payload
        buffer = io.BytesIO()
        zip = zipfile.ZipFile(buffer,'w',zipfile.ZIP_DEFLATED)
        for item in self.__exts__:
            filepath = path.replace('shp',item)
            zip.write(filepath,arcname='shp/'+os.path.split(filepath)[1])
        for ii in info:
            zip.writestr('csv/'+ii['arcname'],ii['buffer'].getvalue())
        zip.close()
        buffer.flush()
        zip_stream = buffer.getvalue()
        buffer.close()
        return(zip_stream)

        
    def _get_iter_(self):
        def lcsv_iter():
            s = self.db.Session()
            try:
                for obj in s.query(self.db.Geometry).all():
                    yield(dict(gid=obj.gid,
                               geometry=obj.wkt,
                               area_m2=obj.area_m2))
            finally:
                s.close()
        return(lcsv_iter())

    def _set_ogr_fields_(self):
        ## create shapefile base attributes
        self.ogr_fields.append(OgrField(self.fcache,'gid',int))
        self.ogr_fields.append(OgrField(self.fcache,'area_m2',float))

class OgrField(object):
    """
    Manages OGR fields mapping to correct Python types and configuring field
    definitions.
    """
    
    _mapping = {int:ogr.OFTInteger,
                datetime.date:ogr.OFTDate,
                datetime.datetime:ogr.OFTDateTime,
                float:ogr.OFTReal,
                str:ogr.OFTString}
    
    def __init__(self,fcache,name,data_type,precision=6,width=255):
        self.orig_name = name
        self._data_type = data_type
        
        self.ogr_name = fcache.add(name)
        
        try:
            self.ogr_type = self._mapping[data_type]
        except KeyError:
            self.ogr_type = self._mapping[type(data_type)]
        except:
            raise
        
        self.ogr_field = ogr.FieldDefn(self.ogr_name,self.ogr_type)
        if self.ogr_type == ogr.OFTReal: self.ogr_field.SetPrecision(precision)
        if self.ogr_type == ogr.OFTString: self.ogr_field.SetWidth(width)
        
        
class FieldCache(object):
    """Manage shapefile fields names."""
    
    def __init__(self):
        self._cache = []
    
    def add(self,name):
        name = str(name).upper()
        if len(name) > 10:
            name = name[0:10]
        if name not in self._cache:
            self._cache.append(name)
        else:
            raise ValueError('"{0}" is not a unique name.'.format(name))
        return name