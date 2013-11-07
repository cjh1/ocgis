from ocgis.conv.base import OcgConverter
import netCDF4 as nc
from ocgis import constants
from ocgis.util.logging_ocgis import ocgis_lh
from ocgis.interface.base.dimension.temporal import TemporalGroupDimension
import numpy as np
from ocgis.interface.base.crs import CFWGS84

    
class NcConverter(OcgConverter):
    _ext = 'nc'
    
    def _get_fileobject_(self,coll):
        ds = nc.Dataset(self.path,'w',format=self._get_file_format_())
        return(ds)
    
    def _finalize_(self,ds):
        ds.close()
        
    def _build_(self,*args,**kwds):
        pass
        
    def _get_file_format_(self):
        file_format = set()
        for rd in self.ops.dataset:
            rr = rd._source_metadata['file_format']
            if isinstance(rr,basestring):
                tu = [rr]
            else:
                tu = rr
            file_format.update(tu)
        if len(file_format) > 1:
            exc = ValueError('Multiple file formats found: {0}'.format(file_format))
            ocgis_lh(exc=exc,logger='conv.nc')
        else:
            return(list(file_format)[0])
    
    def _write_coll_(self,ds,coll):
        
        ## get the target field from the collection
        arch = coll._archetype_field
        
        ## reference the interfaces
        grid = arch.spatial.grid
        temporal = arch.temporal
        level = arch.level
        meta = arch.meta
        
        ## get or make the bounds dimensions
        try:
            bounds_name = list(set(meta['dimensions'].keys()).intersection(set(constants.name_bounds)))[0]
        except IndexError:
            bounds_name = constants.ocgis_bounds
                
        ## add dataset/global attributes
        for key,value in meta['dataset'].iteritems():
            setattr(ds,key,value)

        ## make dimensions #####################################################
        
        ## time dimensions
        dim_temporal = ds.createDimension(temporal.name)

        ## spatial dimensions
        dim_row = ds.createDimension(grid.row.meta['dimensions'][0],grid.row.shape[0])
        dim_col = ds.createDimension(grid.col.meta['dimensions'][0],grid.col.shape[0])
        if grid.row.bounds is None:
            dim_bnds = None
        else:
            dim_bnds = ds.createDimension(bounds_name,2)
        
        ## set data + attributes ###############################################
        
        ## time variable
        if isinstance(temporal,TemporalGroupDimension):
            raise(NotImplementedError)
            time_nc_value = temporal.get_nc_time(temporal.group.representative_datetime)
        else:
            time_nc_value = arch.temporal.value

        ## if bounds are available for the time vector transform those as well
        if isinstance(temporal,TemporalGroupDimension):
            raise(NotImplementedError)
            if dim_bnds is None:
                dim_bnds = ds.createDimension(bounds_name,2)
            times_bounds = ds.createVariable('climatology_'+bounds_name,time_nc_value.dtype,
                                             (dim_temporal._name,bounds_name))
            times_bounds[:] = temporal.get_nc_time(temporal.group.bounds)
        elif temporal.bounds is not None:
            if dim_bnds is None:
                dim_bnds = ds.createDimension(bounds_name,2)
            time_bounds_nc_value = temporal.bounds
            times_bounds = ds.createVariable(temporal.name_bounds,time_bounds_nc_value.dtype,(dim_temporal._name,bounds_name))
            times_bounds[:] = time_bounds_nc_value
            for key,value in meta['variables'][temporal.name_bounds]['attrs'].iteritems():
                setattr(times_bounds,key,value)
        times = ds.createVariable(temporal.name,time_nc_value.dtype,(dim_temporal._name,))
        times[:] = time_nc_value
        for key,value in meta['variables'][temporal.name]['attrs'].iteritems():
            setattr(times,key,value)
        
        ## add climatology bounds
        if isinstance(temporal,TemporalGroupDimension):
            setattr(times,'climatology','climatology_'+bounds_name)
            
        ## level variable
        ## if there is no level on the variable no need to build one.
        if level is None:
            dim_level = None
        ## if there is a level, create the dimension and set the variable.
        else:
            dim_level = ds.createDimension(level.name,len(arch.level.value))
            levels = ds.createVariable(level.name,arch.level.value.dtype,(dim_level._name,))
            levels[:] = arch.level.value
            for key,value in meta['variables'][level.name]['attrs'].iteritems():
                setattr(levels,key,value)
            if level.bounds is not None:
                if dim_bnds is None:
                    dim_bnds = ds.createDimension(bounds_name,2)
                levels_bounds = ds.createVariable(level.name_bounds,arch.level.value.dtype,(dim_level._name,bounds_name))
                levels_bounds[:] = arch.level.bounds
                for key,value in meta['variables'][level.name_bounds]['attrs'].iteritems():
                    setattr(levels,key,value)
        if dim_level is not None:
            value_dims = (dim_temporal._name,dim_level._name,dim_row._name,dim_col._name)
        else:
            value_dims = (dim_temporal._name,dim_row._name,dim_col._name)
            
        ## spatial variables ###################################################
        
        ## create and fill a spatial variable
        def _make_spatial_variable_(ds,name,values,dimension_tuple,meta):
            ret = ds.createVariable(name,values.dtype,[d._name for d in dimension_tuple])
            ret[:] = values
            ## add variable attributes
            try:
                for key,value in meta['variables'][name]['attrs'].iteritems():
                    setattr(ret,key,value)
            except KeyError:
                pass
            return(ret)
        ## set the spatial data
        _make_spatial_variable_(ds,grid.row.name,grid.row.value,(dim_row,),meta)
        _make_spatial_variable_(ds,grid.col.name,grid.col.value,(dim_col,),meta)
        if grid.row.bounds is not None:
            _make_spatial_variable_(ds,grid.row.meta['axis']['bounds'],grid.row.bounds,(dim_row,dim_bnds),meta)
            _make_spatial_variable_(ds,grid.col.meta['axis']['bounds'],grid.col.bounds,(dim_col,dim_bnds),meta)
        
        ## set the variable(s) #################################################
        
        ## loop through variables
        for variable in arch.variables.itervalues():
            value = ds.createVariable(variable.alias,variable.value.dtype,value_dims,
                                      fill_value=variable.value.fill_value)
            if not self.ops.file_only:
                value[:] = np.squeeze(variable.value)
            value.setncatts(variable.meta['attrs'])
                    
        ## add projection variable if applicable ###############################
        
        if not isinstance(arch.spatial.crs,CFWGS84):
            raise(NotImplementedError)
            arch.spatial.projection.write_to_rootgrp(ds,meta)
