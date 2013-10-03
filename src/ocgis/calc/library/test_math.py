import unittest
from ocgis.calc.library.statistics import Mean, FrequencyPercentile
from ocgis.interface.base.test_field import AbstractTestField
from ocgis.interface.base.variable import DerivedVariable, Variable
import numpy as np
from ocgis.calc.library.math import NaturalLogarithm


class Test(AbstractTestField):
    
    def test_NaturalLogarithm(self):
        field = self.get_field(with_value=True,month_count=2)
#        grouping = ['month']
#        tgd = field.temporal.get_grouping(grouping)
        ln = NaturalLogarithm(field=field)
        ret = ln.execute()
        self.assertEqual(ret['ln_tmax'].value.shape,(2, 60, 2, 3, 4))
        self.assertNumpyAllClose(ret['ln_tmax'].value,np.log(field.variables['tmax'].value))
#        import ipdb;ipdb.set_trace()


if __name__ == "__main__":
    #import sys;sys.argv = ['', 'Test.testName']
    unittest.main()