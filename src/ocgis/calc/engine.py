from collections import OrderedDict
import numpy as np
from ocgis import constants
from ocgis.util.logging_ocgis import ocgis_lh
import logging
from ocgis.interface.base.variable import VariableCollection
from ocgis.interface.base.field import DerivedMultivariateField, DerivedField
from ocgis.calc.base import AbstractMultivariateFunction


class OcgCalculationEngine(object):
    '''
    :type grouping: list of temporal groupings (e.g. ['month','year'])
    :type funcs: list of function dictionaries
    :param raw: If True, perform calculations on raw data values.
    :type raw: bool
    :param agg: If True, data needs to be spatially aggregated (using weights) following a calculation.
    :type agg: bool
    '''
    
    def __init__(self,grouping,funcs,raw=False,agg=False):
        self.raw = raw
        self.agg = agg
        self.grouping = grouping
        self.funcs = funcs
        ## select which value data to pull based on raw and agg arguments
        if self.raw and self.agg is False:
            self.use_raw_values = False
        elif self.raw is False and self.agg is True:
            self.use_raw_values = False
        elif self.raw and self.agg:
            self.use_raw_values = True
        elif not self.raw and not self.agg:
            self.use_raw_values = False
        else:
            raise(NotImplementedError)
#        if self.raw:
#            self.use_agg = False
#        elif self.raw is False and self.agg is True:
#            self.use_agg = True
#        else:
#            self.use_agg = False
        ## store reusable temporal groups
        self.tgds = {}

#    def _get_value_weights_(self,ds,file_only=False):
#        '''
#        :type ds: AbstractDataset
#        '''
#        ## empty data only for the file
#        if file_only:
#            return(None,None)
#        ## select the value source based on raw or aggregated switches
#        if not self.use_agg:
#            try:
#                value = ds.raw_value
#                weights = ds.spatial.vector.raw_weights
#            except AttributeError:
#                value = ds.value
#                weights = ds.spatial.vector.weights
#        else:
#            value = ds.value
#            weights = ds.spatial.vector.weights
#        return(value,weights)
    
    def _check_calculation_members_(self,funcs,klass):
        '''
        Return True if a subclass of type `klass` is contained in the calculation
        list.
        
        :param funcs: Sequence of calculation dictionaries.
        :param klass: `ocgis.calc.base.OcgFunction`
        '''
        check = [issubclass(f['ref'],klass) for f in funcs]
        ret = True if any(check) else False
        return(ret)
        
    def execute(self,coll,file_only=False):
        
        ## switch field type based on the types of calculations present
        if self._check_calculation_members_(self.funcs,AbstractMultivariateFunction):
            klass = DerivedMultivariateField
        else:
            klass = DerivedField
                        
        ## group the variables. if grouping is None, calculations are performed
        ## on each element. array computations are taken advantage of.
        if self.grouping is not None:
            ocgis_lh('setting temporal grouping(s)','calc.engine')
            for v in coll.itervalues():
                for k2,v2 in v.iteritems():
                    if k2 not in self.tgds:
                        self.tgds[k2] = v2.temporal.get_grouping(self.grouping)
#                    import ipdb;ipdb.set_trace()
#        import ipdb;ipdb.set_trace()
#            for ds in coll.variables.itervalues():
#                ds.temporal.set_grouping(self.grouping)

        ## iterate over functions
        for ugid,dct in coll.iteritems():
            for alias_field,field in dct.iteritems():
                new_temporal = self.tgds.get(alias_field)
                out_vc = VariableCollection()
                for f in self.funcs:
                    ocgis_lh('calculating: {0}'.format(f),logger='calc.engine')
                    function = f['ref'](alias=f['name'],dtype=None,field=field,file_only=file_only,vc=out_vc,
                         parms=f['kwds'],tgd=new_temporal,use_raw_values=self.use_raw_values)
                    out_vc = function.execute()
                new_temporal = new_temporal or field.temporal
                new_field = klass(variables=out_vc,temporal=new_temporal,spatial=field.spatial,
                                  level=field.level,realization=field.realization,meta=field.meta,
                                  uid=field.uid)
                coll[ugid][alias_field] = new_field
        return(coll)
#        import ipdb;ipdb.set_trace()
#                    ## change behavior for multivariate functions
#                    if issubclass(f['ref'],OcgCvArgFunction) or (isinstance(ret,MultivariateCalcCollection) and f['ref'] == SampleSize):
#                        ## do not calculated sample size for multivariate calculations
#                        ## yet
#                        if f['ref'] == SampleSize:
#                            ocgis_lh('sample size calculations not implemented for multivariate calculations yet',
#                                     'calc.engine',level=logging.WARN)
#                            continue
#                        ## cv-controlled multivariate functions require collecting
#                        ## data arrays before passing to function.
#                        kwds = f['kwds'].copy()
#                        ## reference the appropriate datasets to pass to the calculation
#                        keyed_datasets = {}
#                        for ii,key in enumerate(f['ref'].keys):
#                            ## the name of the variable passed in the request
#                            ## that should be mapped to the named argument
#                            backref = kwds[key]
#                            ## pull associated data
#                            dref = coll.variables[backref]
#                            ## map the key to a dataset
#                            keyed_datasets.update({key:dref})
#                            value,weights = self._get_value_weights_(dref,file_only=file_only)
#                            ## get the calculation groups and weights.
#                            if ii == 0:
#                                if self.grouping is None:
#                                    dgroups = None
#                                else:
#                                    dgroups = dref.temporal.group.dgroups
#                            ## update dict with properly reference data
#                            kwds.update({key:value})
#                        ## function object instance
#                        ref = f['ref'](agg=self.agg,groups=dgroups,kwds=kwds,weights=weights,
#                                       dataset=keyed_datasets,calc_name=f['name'],file_only=file_only)
#                        calc = ref.calculate()
#                        ## store calculation value
#                        ret.calc[f['name']] = calc
#                    else:
#                        ## perform calculation on each variable
#                        for alias,var in coll.variables.iteritems():
#                            if alias not in ret.calc:
#                                ret.calc[alias] = OrderedDict()
#                            value,weights = self._get_value_weights_(var,file_only=file_only)
#                            ## make the function instance
#                            try:
#                                ref = f['ref'](values=value,agg=self.agg,
#                                               groups=var.temporal.group.dgroups,
#                                               kwds=f['kwds'],weights=weights,
#                                               dataset=var,calc_name=f['name'],
#                                               file_only=file_only)
#                            except AttributeError:
#                                ## if there is no grouping, there is no need to calculate
#                                ## sample size.
#                                if self.grouping is None and f['ref'] == SampleSize:
#                                    break
#                                elif self.grouping is None:
#                                    e = NotImplementedError('Univariate calculations must have a temporal grouping.')
#                                    ocgis_lh(exc=e,logger='calc.engine')
#                                else:
#                                    raise
#                            ## calculate the values
#                            calc = ref.calculate()
#                            ## store the values
#                            ret.calc[alias][f['name']] = calc
#        return(ret)
