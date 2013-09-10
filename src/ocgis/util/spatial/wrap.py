import numpy as np
from ocgis.util.helpers import make_poly
from shapely.geometry.multipolygon import MultiPolygon
from shapely.geometry.polygon import Polygon
from shapely.geometry.point import Point
from shapely.geometry.linestring import LineString
from shapely.geometry.multipoint import MultiPoint


class Wrapper(object):
    
    def __init__(self,axis=0.0):
        self.axis = float(axis)
        self.right_clip = make_poly((-90,90),(180,360))
        self.left_clip = make_poly((-90,90),(-180,180))
        self.clip1 = make_poly((-90,90),(-180,axis))
        self.clip2 = make_poly((-90,90),(axis,180))
    
    @staticmethod
    def _get_iter_(geom):
        try:
            it = iter(geom)
        except TypeError:
            it = [geom]
        return(it)
    
    @staticmethod
    def _unwrap_shift_(polygon):
        coords = np.array(polygon.exterior.coords)
        coords[:,0] = coords[:,0] + 360
        return(Polygon(coords))
    
    def unwrap_point(self,geom):
        if isinstance(geom,MultiPoint):
            pts = []
            for pt in geom:
                if pt.x < 180:
                    n = Point(pt.x+360,pt.y)
                else:
                    n = pt
                pts.append(n)
            ret = MultiPoint(pts)
        else:
            if geom.x < 180:
                ret = Point(geom.x+360,geom.y)
            else:
                ret = geom
        return(ret)

    def unwrap(self,geom):
        '''geom : shapely.geometry'''
        
        if type(geom) in [MultiPoint,Point]:
            return(self.unwrap_point(geom))

        assert(type(geom) in [Polygon,MultiPolygon])
        
        ## return the geometry iterator
        it = self._get_iter_(geom)
        ## loop through the polygons determining if any coordinates need to be
        ## shifted and flag accordingly.
        adjust = False
        for polygon in it:
            coords = np.array(polygon.exterior.coords)
            if np.any(coords[:,0] < self.axis):
                adjust = True
                break

        ## wrap the polygon if requested
        if adjust:
            ## intersection with the two regions
            left = geom.intersection(self.clip1)
            right = geom.intersection(self.clip2)
            
            ## pull out the right side polygons
            right_polygons = [poly for poly in self._get_iter_(right)]
            
            ## adjust polygons falling the left window
            if isinstance(left,Polygon):
                left_polygons = [self._unwrap_shift_(left)]
            else:
                left_polygons = []
                for polygon in left:
                    left_polygons.append(self._unwrap_shift_(polygon))
            
            ## merge polygons into single unit
            try:
                ret = MultiPolygon(left_polygons + right_polygons)
            except TypeError:
                left = filter(lambda x: type(x) != LineString,left_polygons)
                right = filter(lambda x: type(x) != LineString,right_polygons)
                ret = MultiPolygon(left+right)
        
        ## if polygon does not need adjustment, just return it.
        else:
            ret = geom

        return(ret)

    def wrap(self,geom):
        '''geom : shapely.geometry'''
        
        def _shift_(geom):
            try:
                coords = np.array(geom.exterior.coords)
                coords[:,0] = coords[:,0] - 360
                ret = Polygon(coords)
            except AttributeError:
                polygons = np.empty(len(geom),dtype=object)
                for ii,polygon in enumerate(geom):
                    coords = np.array(polygon.exterior.coords)
                    coords[:,0] = coords[:,0] - 360
                    polygons[ii] = Polygon(coords)
                ret = MultiPolygon(polygons)
            return(ret)
        
        if not isinstance(geom,Point):
            bounds = np.array(geom.bounds)
            ## if the polygon column bounds are both greater than 180 degrees
            ## shift the coordinates of the entire polygon
            if np.all([bounds[0] > 180,bounds[2] > 180]):
                new_geom = _shift_(geom)
            ## if a polygon crosses the 180 axis, then the polygon will need to
            ## be split with intersection and recombined.
            elif bounds[1] <= 180 and bounds[2] > 180:
                left = [poly for poly in self._get_iter_(geom.intersection(self.left_clip))]
                right = [poly for poly in self._get_iter_(_shift_(geom.intersection(self.right_clip)))]
                try:
                    new_geom = MultiPolygon(left+right)
                except TypeError:
                    left = filter(lambda x: type(x) != LineString,left)
                    right = filter(lambda x: type(x) != LineString,right)
                    new_geom = MultiPolygon(left+right)
            ## otherwise, the polygon coordinates are not affected by wrapping
            ## and the geometry may be passed through.
            else:
                new_geom = geom
        else:
            if geom.x > 180:
                new_geom = Point(geom.x-360,geom.y)
            else:
                new_geom = geom
            
        return(new_geom)
