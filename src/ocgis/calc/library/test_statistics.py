import unittest
from ocgis.calc.library.statistics import Mean
from ocgis.interface.base.test_field import AbstractTestField
from ocgis.interface.base.variable import DerivedVariable, Variable
from ocgis.interface.base.field import Field
import numpy as np


class Test(AbstractTestField):

    def test_Mean(self):
        field = self.get_field(with_value=True,month_count=2)
        grouping = ['month']
        tgd = field.temporal.get_grouping(grouping)
        mu = Mean(field=field,tgd=tgd,alias='my_mean')
        dvc = mu.execute()
        self.assertEqual(dv.name,'mean')
        self.assertEqual(dv.alias,'my_mean')
        self.assertIsInstance(dv,DerivedVariable)
        self.assertEqual(dv.value.shape,(2,2,2,3,4))
        self.assertNumpyAll(np.ma.mean(field.variables['tmax'].value[1,tgd.dgroups[1],0,:,:],axis=0),dv.value[1,1,0,:,:])
        
    def test_Mean_two_variables(self):
        field = self.get_field(with_value=True,month_count=2)
        field.variables.add_variable(Variable(value=field.variables['tmax'].value,
                                              name='tmin',alias='tmin'))
        grouping = ['month']
        tgd = field.temporal.get_grouping(grouping)
        mu = Mean(field=field,tgd=tgd,alias='my_mean')
        ret = mu.execute()
        self.assertEqual(len(ret),2)
        import ipdb;ipdb.set_trace()


if __name__ == "__main__":
    #import sys;sys.argv = ['', 'Test.testName']
    unittest.main()