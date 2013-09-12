from ocgis.test.base import TestBase
from datetime import datetime as dt
from ocgis.interface.base.dimension.temporal import TemporalDimension
import numpy as np


class TestTemporalGroupDimension(TestBase):
    
    def test_constructor_by_temporal_dimension(self):
        value = [dt(2012,1,1),dt(2012,1,2)]
        td = TemporalDimension(value=value)
        tgd = td.get_grouping(['month'])
        self.assertEqual(tuple(tgd.value[0]),(None,1,None,None,None,None,None))
        self.assertTrue(tgd.dgroups[0].all())
        self.assertNumpyAll(tgd.uid,np.array([1]))
