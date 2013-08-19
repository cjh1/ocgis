import unittest
import numpy as np
from base import VectorDimension
from ocgis.interface.base.dimension.spatial import SpatialDimension,\
    SpatialGeometryDimension, SpatialGeometryPolygonDimension,\
    SpatialGridDimension
from ocgis.util.helpers import iter_array
import fiona
from shapely.geometry import mapping, shape


class TestSpatialDimension(unittest.TestCase):

    def assertNumpyAll(self,arr1,arr2):
        return(self.assertTrue(np.all(arr1 == arr2)))
    
    def assertNumpyNotAll(self,arr1,arr2):
        return(self.assertFalse(np.all(arr1 == arr2)))
    
    def get_col(self,bounds=True):
        value = [-100,-99,-98,-97]
        if bounds:
            bounds = [[v-0.5,v+0.5] for v in value]
        else:
            bounds = None
        row = VectorDimension(value=value,bounds=bounds,name='col')
        return(row)
    
    def get_row(self,bounds=True):
        value = [40,39,38]
        if bounds:
            bounds = [[v+0.5,v-0.5] for v in value]
        else:
            bounds = None
        row = VectorDimension(value=value,bounds=bounds,name='row')
        return(row)
    
    def get_sdim(self,bounds=True):
        row = self.get_row(bounds=bounds)
        col = self.get_col(bounds=bounds)
        sdim = SpatialDimension(row=row,col=col)
        return(sdim)

    def test_grid_value(self):
        for b in [True,False]:
            row = self.get_row(bounds=b)
            col = self.get_col(bounds=b)
            sdim = SpatialDimension(row=row,col=col)
            col_test,row_test = np.meshgrid(col.value,row.value)
            self.assertNumpyAll(sdim.grid.value[0].data,row_test)
            self.assertNumpyAll(sdim.grid.value[1].data,col_test)
            self.assertFalse(sdim.grid.value.mask.any())
                
    def test_grid_slice_all(self):
        sdim = self.get_sdim(bounds=True)
        with self.assertRaises(IndexError):
            sdim.grid[:]
    
    def test_grid_slice_1d(self):
        sdim = self.get_sdim(bounds=True)
        sdim_slc = sdim.grid[0,:]
        self.assertEqual(sdim_slc.value.shape,(2,1,4))
        self.assertNumpyAll(sdim_slc.value.data,np.ma.array([[[40,40,40,40]],[[-100,-99,-98,-97]]],mask=False))
        self.assertEqual(sdim_slc.row.value[0],40)
        self.assertNumpyAll(sdim_slc.col.value,np.array([-100,-99,-98,-97]))
    
    def test_grid_slice_2d(self):
        sdim = self.get_sdim(bounds=True)
        sdim_slc = sdim.grid[0,1]
        self.assertNumpyAll(sdim_slc.value,np.ma.array([[[40]],[[-99]]],mask=False))
        self.assertNumpyAll(sdim_slc.row.bounds,np.array([[40.5,39.5]]))
        self.assertEqual(sdim_slc.col.value[0],-99)
    
    def test_grid_slice_2d_range(self):
        sdim = self.get_sdim(bounds=True)
        sdim_slc = sdim.grid[1:3,0:3]
        self.assertNumpyAll(sdim_slc.value,np.ma.array([[[39,39,39],[38,38,38]],[[-100,-99,-98],[-100,-99,-98]]],mask=False))
        self.assertNumpyAll(sdim_slc.row.value,np.array([39,38]))
        
    def test_geom_point(self):
        sdim = self.get_sdim(bounds=True)
        with self.assertRaises(NotImplementedError):
            sdim.geom.value
        pt = sdim.geom.point.value
        fill = np.ma.array(np.zeros((2,3,4)),mask=False)
        for idx_row,idx_col in iter_array(pt):
            fill[0,idx_row,idx_col] = pt[idx_row,idx_col].y
            fill[1,idx_row,idx_col] = pt[idx_row,idx_col].x
        self.assertNumpyAll(fill,sdim.grid.value)
        
    def test_geom_polygon_no_bounds(self):
        sdim = self.get_sdim(bounds=False)
        with self.assertRaises(ValueError):
            sdim.geom.polygon.value
            
    def test_geom_polygon_bounds(self):
        sdim = self.get_sdim(bounds=True)
        poly = sdim.geom.polygon.value
        fill = np.ma.array(np.zeros((2,3,4)),mask=False)
        for idx_row,idx_col in iter_array(poly):
            fill[0,idx_row,idx_col] = poly[idx_row,idx_col].centroid.y
            fill[1,idx_row,idx_col] = poly[idx_row,idx_col].centroid.x
        self.assertNumpyAll(fill,sdim.grid.value)   
        
    def test_grid_shape(self):
        sdim = self.get_sdim()
        shp = sdim.grid.shape
        self.assertEqual(shp,(2,3,4))
        
    def test_empty(self):
        with self.assertRaises(ValueError):
            SpatialDimension()
            
    def test_geoms_only(self):
        geoms = []
        with fiona.open('/home/local/WX/ben.koziol/Dropbox/nesii/project/ocg/bin/shp/state_boundaries/state_boundaries.shp','r') as source:
            for row in source:
                geoms.append(shape(row['geometry']))
        geoms = np.atleast_2d(geoms)
        poly_dim = SpatialGeometryPolygonDimension(value=geoms)
        sg_dim = SpatialGeometryDimension(polygon=poly_dim)
        sdim = SpatialDimension(geom=sg_dim)
        self.assertEqual(sdim.shape,(1,51))
        
    def test_slicing(self):
        sdim = self.get_sdim(bounds=True)
        self.assertEqual(sdim.shape,(3,4))
        self.assertEqual(sdim._geom,None)
        self.assertEqual(sdim.geom.point.shape,(3,4))
        self.assertEqual(sdim.geom.polygon.shape,(3,4))
        self.assertEqual(sdim.grid.shape,(2,3,4))
        with self.assertRaises(IndexError):
            sdim[0]
        sdim_slc = sdim[0,1]
        import ipdb;ipdb.set_trace()
        self.assertNotEqual(sdim_slc,None)
        import ipdb;ipdb.set_trace()
        
    def test_load_from_source_grid_slicing(self):
        row = VectorDimension(src_idx=[10,20,30,40],name='row')
        col = VectorDimension(src_idx=[100,200,300],name='col')
        grid = SpatialGridDimension(row=row,col=col,name='grid')
        self.assertEqual(grid.shape,(4,3))
        self.assertEqual(grid.uid.mean(),6.5)
        self.assertEqual(grid.uid.shape,(4,3))
        grid_slc = grid[1,2]
        import ipdb;ipdb.set_trace()
        

if __name__ == "__main__":
    #import sys;sys.argv = ['', 'Test.testName']
    unittest.main()