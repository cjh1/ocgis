import unittest
from base import VectorDimension
import numpy as np
from ocgis.exc import EmptyIterationError


class TestVectorDimension(unittest.TestCase):
    
    def assertNumpyAll(self,arr1,arr2):
        return(self.assertTrue(np.all(arr1 == arr2)))
    
    def assertNumpyNotAll(self,arr1,arr2):
        return(self.assertFalse(np.all(arr1 == arr2)))

    def test_one_value(self):
        values = [5,np.array([5])]
        for value in values:
            vdim = VectorDimension(value=value,src_idx=10)
            self.assertEqual(vdim.value[0],5)
            self.assertEqual(vdim.uid[0],1)
            self.assertEqual(len(vdim.uid),1)
            self.assertEqual(vdim.shape,(1,))
            self.assertNumpyAll(vdim.bounds,np.array([[5,5]]))
            self.assertEqual(vdim[0].value[0],5)
            self.assertEqual(vdim[0].uid[0],1)
            self.assertEqual(vdim[0]._src_idx[0],10)
            self.assertNumpyAll(vdim[0].bounds,np.array([[5,5]]))
            self.assertEqual(vdim.resolution,None)
    
    def test_with_bounds(self):
        vdim = VectorDimension(value=[4,5,6],bounds=[[3,5],[4,6],[5,7]])
        self.assertNumpyAll(vdim.bounds,np.array([[3,5],[4,6],[5,7]]))
        self.assertNumpyAll(vdim.uid,np.array([1,2,3]))
        self.assertTrue(len(list(vdim)),3)
        self.assertEqual(vdim.resolution,(2.0,None))
    
    def test_resolution_with_units(self):
        vdim = VectorDimension(value=[5,10,15],units='large')
        self.assertEqual(vdim.resolution,(5.0,'large'))
    
    def test_load_from_source(self):
        vdim = VectorDimension(src_idx=[0,1,2,3],data='foo')
        self.assertNumpyAll(vdim.uid,np.array([1,2,3,4]))
        with self.assertRaises(NotImplementedError):
            vdim.value
        with self.assertRaises(NotImplementedError):
            vdim.resolution

    def test_empty(self):
        vdim = VectorDimension()
        self.assertTrue(len(vdim.uid) == 0)
        
    def test_get_between_empty(self):
        vdim = VectorDimension()
        vdim_between = vdim.get_between(0,100)
        self.assertNotEqual(id(vdim),id(vdim_between))
        
    def test_get_between(self):
        vdim = VectorDimension(value=[0])
        vdim_between = vdim.get_between(100,200)
        self.assertTrue(vdim_between.isempty)
        
        vdim = VectorDimension(value=[100,200,300,400])
        vdim_between = vdim.get_between(100,200)
        self.assertEqual(len(vdim_between),2)
    
    def test_get_between_bounds(self):
        vdim = VectorDimension(value=[0,5,10],bounds=[[-2.5,2.5],[2.5,7.5],[7.5,12.5]])
        vdim_between = vdim.get_between(1,3)
        self.assertEqual(len(vdim_between),2)
        self.assertEqual(vdim.resolution,(5.0,None))
        
    def test_iter_empty(self):
        vdim = VectorDimension()
        with self.assertRaises(EmptyIterationError):
            list(vdim)
        

if __name__ == "__main__":
    #import sys;sys.argv = ['', 'Test.testName']
    unittest.main()