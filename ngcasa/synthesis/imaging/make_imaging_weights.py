#   Copyright 2019 AUI, Inc. Washington DC, USA
#
#   Licensed under the Apache License, Version 2.0 (the "License");
#   you may not use this file except in compliance with the License.
#   You may obtain a copy of the License at
#
#       http://www.apache.org/licenses/LICENSE-2.0
#
#   Unless required by applicable law or agreed to in writing, software
#   distributed under the License is distributed on an "AS IS" BASIS,
#   WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#   See the License for the specific language governing permissions and
#   limitations under the License.

#Allow setting of padding
#Setting to keep grid or correcting
#normalizarion parameters (flat sky, flat noise etc)
#mosaic parameters, etc

import numpy as np

#user_imaging_weights_parms
#imaging_weights_parms['weighting'] = 'natural'/'uniform'/'briggs'/'briggs_abs'  ^&^& change
#imaging_weights_parms['robust'] = float, acceptable values [-2,2]
#imaging_weights_parms['uvw_name'] = 'UVW'
#imaging_weights_parms['data_name'] = 'DATA'
#imaging_weights_parms['chan_mode'] = 'continuum'/'cube'
#imaging_weights_parms['imsize'] = 2 element list/array of int
#imaging_weights_parms['cell']  = 2 element list/array of float
#imaging_weights_parms['imaging_weight_name'] = 'IMAGING_WEIGHT'   ^&^& change to imaging_weights_parms and change to

#storage_parms
#storage_parms['to_disk'] = True/Flase
#storage_parms['append'] = True/False
#storage_parms['outfile'] = string file name and path
#storage_parms['compressor'] = Blosc(cname='zstd', clevel=2, shuffle=0)

def make_imaging_weights(vis_dataset, user_imaging_weights_parms,user_storage_parms):
    """
    Parameters
    ----------
    vis_xds : xarray.core.dataset.Dataset
        input Visibility Dataset
    user_imaging_weights_parms : dictionary
          keys ('chan_mode','imsize','cell','oversampling','support','to_disk','outfile')
    Returns
    -------
    dirty_image_xds : xarray.core.dataset.Dataset

    """
    print('######################### Start make_imaging_weights #########################')
    import time
    import math
    import xarray as xr
    import dask.array as da
    import matplotlib.pylab as plt
    import dask.array.fft as dafft
    import dask
    import copy, os
    from numcodecs import Blosc
    from itertools import cycle
    import zarr
    
    from ngcasa._ngcasa_utils._check_parms import _check_storage_parms
    from ._imaging_utils._check_imaging_parms import _check_imaging_weights_parms, _check_storage_parms
    from cngi.dio import write_zarr, append_zarr
    
    imaging_weights_parms =  copy.deepcopy(user_imaging_weights_parms)
    storage_parms =  copy.deepcopy(user_storage_parms)
    
    assert(_check_imaging_weights_parms(vis_dataset,imaging_weights_parms)), "######### ERROR: user_imaging_weights_parms checking failed"
    assert(_check_storage_parms(storage_parms,'dataset.vis.zarr')), "######### ERROR: user_storage_parms checking failed"
    
    
    #Check if weight or weight spectrum present
    #If both default to weight spectrum
    #If none create new
    weight_present = 'WEIGHT' in vis_dataset.data_vars
    weight_spectrum_present = 'WEIGHT_SPECTRUM' in vis_dataset.data_vars
    all_dims_dict = vis_dataset.dims
    
    vis_data_dims = vis_dataset[imaging_weights_parms['data_name']].dims
    vis_data_chunksize = vis_dataset[imaging_weights_parms['data_name']].data.chunksize
    
    
    if weight_present and weight_spectrum_present:
        print('Both WEIGHT and WEIGHT_SPECTRUM data variables found, will use WEIGHT_SPECTRUM to calculate', imaging_weights_parms['imaging_weight_name'])
        imaging_weight = _match_array_shape(vis_dataset.WEIGHT_SPECTRUM,vis_dataset[imaging_weights_parms['data_name']])
    elif weight_present:
        print('WEIGHT data variable found, will use WEIGHT to calculate ', imaging_weights_parms['imaging_weight_name'])
        imaging_weight = _match_array_shape(vis_dataset.WEIGHT,vis_dataset[imaging_weights_parms['data_name']])
    elif weight_spectrum_present:
        print('WEIGHT_SPECTRUM  data variable found, will use WEIGHT_SPECTRUM to calculate ', imaging_weights_parms['imaging_weight_name'])
        imaging_weight = _match_array_shape(vis_dataset.WEIGHT_SPECTRUM,vis_dataset[imaging_weights_parms['data_name']])
    else:
        print('No WEIGHT or WEIGHT_SPECTRUM data variable found,  will assume all weights are unity to calculate ', imaging_weights_parms['imaging_weight_name'])
        imaging_weight = da.ones(vis_dataset[imaging_weights_parms['data_name']].shape,chunks=vis_data_chunksize)
    
    vis_dataset[imaging_weights_parms['imaging_weight_name']] =  xr.DataArray(imaging_weight, dims=vis_dataset[imaging_weights_parms['data_name']].dims)
    
    if imaging_weights_parms['weighting'] != 'natural':
        calc_briggs_weights(vis_dataset,imaging_weights_parms,storage_parms)
        
    
    ### Storing imaging weight code
    if  storage_parms['to_disk']:
        storage_parms['graph_name'] = 'make_imaging_weights'
        storage_parms['data_variable_name'] = imaging_weights_parms['imaging_weight_name']
        
        if storage_parms['append']:
            print('Atempting to add ', storage_parms['data_variable_name']  , ' to ', storage_parms['outfile'])
            imaging_weight = vis_dataset[storage_parms['data_variable_name']].data
            #try:
            if True:
                #storage_parms['array_dimensions'] = ['time', 'baseline', 'chan', 'pol']
                #vis_dataset = _add_data_variable_to_dataset(vis_dataset,imaging_weight,storage_parms)
                vis_dataset = append_zarr(vis_dataset, storage_parms['outfile'],[imaging_weight],[storage_parms['data_variable_name']],[['time', 'baseline', 'chan', 'pol']],graph_name=storage_parms['graph_name'])
                print('##################### Finished appending imaging_weights #####################')
                return vis_dataset
            #except Exception:
            #    print('ERROR : Could not append ', storage_parms['data_variable_name'], 'to', storage_parms['outfile'])
        else:
            print('Saving dataset to ', storage_parms['outfile'])
            #vis_dataset = _to_storage(vis_dataset, storage_parms)
            write_zarr(vis_dataset, outfile=storage_parms['outfile'], compressor=storage_parms['compressor'], graph_name=storage_parms['graph_name'])
            print('##################### Created new dataset with imaging_weights #####################')
            return vis_dataset
            
    print('##################### Created graph for make_imaging_weights #####################')
    return vis_dataset
            
def _match_array_shape(array_to_reshape,array_to_match):
    # Reshape in_weight to match dimnetionality of vis_data (vis_dataset[imaging_weights_parms['data_name']])
    # The order is assumed the same (there can be missing). array_to_reshape is a subset of array_to_match
    import dask.array as da
    import numpy as np
    
    match_array_chunksize = array_to_match.data.chunksize
    
    reshape_dims = np.ones(len(match_array_chunksize),dtype=int)  #Missing dimentions will be added using reshape command
    tile_dims = np.ones(len(match_array_chunksize),dtype=int) #Tiling is used so that number of elements in each dimention match
    
    
    array_to_match_dims = array_to_match.dims
    array_to_reshape_dims = array_to_reshape.dims
    
    for i in range(len(match_array_chunksize)):
        if array_to_match_dims[i] in array_to_reshape_dims:
            reshape_dims[i] = array_to_match.shape[i]
        else:
            tile_dims[i] = array_to_match.shape[i]
            
    return da.tile(da.reshape(array_to_reshape.data,reshape_dims),tile_dims).rechunk(match_array_chunksize)



def calc_briggs_weights(vis_dataset,imaging_weights_parms,storage_parms):
    import dask.array as da
    import xarray as xr
    from ._imaging_utils._standard_grid import _graph_standard_grid, _graph_standard_degrid
    
    
    dtr = np.pi / (3600 * 180)
    grid_parms = {}
    
    grid_parms['chan_mode'] = imaging_weights_parms['chan_mode']
    grid_parms['imsize_padded'] =  imaging_weights_parms['imsize'] #do not need to pad since no fft
    grid_parms['cell'] = imaging_weights_parms['cell']
    grid_parms['do_imaging_weight'] = True
    grid_parms['uvw_name'] = imaging_weights_parms['uvw_name']
    
    grid_parms['oversampling'] = 0
    grid_parms['support'] = 1
    grid_parms['do_psf'] = True
    grid_parms['complex_grid'] = False
    grid_parms['do_imaging_weight'] = True
    grid_parms['imaging_weight_name'] = imaging_weights_parms['imaging_weight_name']
    
    cgk_1D = np.ones((1))
    grid_of_imaging_weights, sum_weight = _graph_standard_grid(vis_dataset, cgk_1D, grid_parms)
    
    #############Calculate Briggs parameters#############
    def calculate_briggs_parms(grid_of_imaging_weights, sum_weight, imaging_weights_parms):
        if imaging_weights_parms['weighting'] == 'briggs':
            robust = imaging_weights_parms['robust']
            briggs_factors = np.ones((2,1,1)+sum_weight.shape)
            squared_sum_weight = (np.sum(grid_of_imaging_weights**2,axis=(0,1)))
            briggs_factors[0,0,0,:,:] =  (np.square(5.0*10.0**(-robust))/(squared_sum_weight/sum_weight))[None,None,:,:]
        elif imaging_weights_parms['weighting'] == 'briggs_abs':
            robust = imaging_weights_parms['robust']
            briggs_factors = np.ones((2,1,1)+sum_weight.shape)
            briggs_factors[0,0,0,:,:] = briggs_factor[0,0,0,:,:]*np.square(robust)
            briggs_factors[1,0,0,:,:] = briggs_factor[1,0,0,:,:]*2.0*np.square(imaging_weights_parms['briggs_abs_noise'])
        else:
            briggs_factors = np.zeros((2,1,1)+sum_weight.shape)
            briggs_factors[0,0,0,:,:] = np.ones((1,1,1)+sum_weight.shape)
            
        return briggs_factors
    
    briggs_factors = da.map_blocks(calculate_briggs_parms,grid_of_imaging_weights,sum_weight, imaging_weights_parms,chunks=(2,1,1)+sum_weight.chunksize,dtype=np.double)[:,0,0,:,:]
    
    imaging_weight = _graph_standard_degrid(vis_dataset, grid_of_imaging_weights, briggs_factors, cgk_1D, grid_parms)
    
    vis_dataset[imaging_weights_parms['imaging_weight_name']] = xr.DataArray(imaging_weight, dims=vis_dataset[imaging_weights_parms['data_name']].dims)
    

