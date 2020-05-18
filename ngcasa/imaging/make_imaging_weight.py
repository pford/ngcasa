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


def make_imaging_weight(vis_dataset, user_imaging_weights_parms,user_storage_parms):
    """
    Creates the imaging weight data variable that has dimensions time x baseline x chan x pol (matches the visibility data variable).
    The weight density can be averaged over channels or calculated independently for each channel using imaging_weights_parms['chan_mode'].
    The following imaging weighting schemes are supported 'natural', 'uniform', 'briggs', 'briggs_abs'.
    The imaging_weights_parms['imsize'] and imaging_weights_parms['cell'] should usually be the same values that will be used for subsequent synthesis blocks (for example making the psf).
    To achieve something similar to 'superuniform' weighting in CASA tclean imaging_weights_parms['imsize'] and imaging_weights_parms['cell'] can be varied relative to the values used in subsequent synthesis blocks.
    
    Parameters
    ----------
    vis_dataset : xarray.core.dataset.Dataset
        Input visibility dataset.
    user_imaging_weights_parms : dictionary
    user_imaging_weights_parms['weighting'] : {'natural', 'uniform', 'briggs', 'briggs_abs'}, default = natural
        Weighting scheme used for creating the imaging weights.
    user_imaging_weights_parms['imsize'] : list of int, length = 2
        The size of the grid for gridding the imaging weights. Used when imaging_weights_parms['weighting'] is not 'natural'.
    user_imaging_weights_parms['cell']  : list of number, length = 2, units = arcseconds
        The size of the pixels in the fft of the grid (the image domain pixel size). Used when imaging_weights_parms['weighting'] is not 'natural'.
    user_imaging_weights_parms['robust'] : number, acceptable range [-2,2], default = 0.5
        Robustness parameter for Briggs weighting.
        robust = -2.0 maps to uniform weighting.
        robust = +2.0 maps to natural weighting.
    user_imaging_weights_parms['briggs_abs_noise'] : number, default=1.0
        Noise parameter for imaging_weights_parms['weighting']='briggs_abs' mode weighting.
    user_imaging_weights_parms['chan_mode'] : {'continuum'/'cube'}, default = 'continuum'
        When 'cube' the weights are calculated independently for each channel (perchanweightdensity=True in CASA tclean) and when 'continuum' a common weight density is calculated for all channels.
    user_imaging_weights_parms['uvw_name'] : str, default ='UVW'
        The name of uvw data variable that will be used to grid the weights. Used when imaging_weights_parms['weighting'] is not 'natural'.
    user_imaging_weights_parms['data_name'] : str, default = 'DATA'
        The name of the visibility data variable whose dimensions will be used to construct the imaging weight data variable.
    user_imaging_weights_parms['imaging_weight_name'] : str, default ='IMAGING_WEIGHT'
        The name of that will be used for the imaging weight data variable.
    user_storage_parms : dictionary
    user_storage_parms['to_disk'] : bool, default = False
        If true the dask graph is executed and saved to disk in the zarr format.
    user_storage_parms['append'] : bool, default = False
        If storage_parms['to_disk'] is True only the dask graph associated with the function is executed and the resulting data variables are saved to an existing zarr file on disk.
        Note that graphs on unrelated data to this function will not be executed or saved.
    user_storage_parms['outfile'] : str
        The zarr file to create or append to.
    user_storage_parms['compressor'] : numcodecs.blosc.Blosc,default=Blosc(cname='zstd', clevel=2, shuffle=0)
    
    Returns
    -------
    vis_dataset : xarray.core.dataset.Dataset
        The vis_dataset will contain a new data variable for the imaging weights the name is defined by the input parameter imaging_weights_parms['imaging_weight_name'].
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
    assert(_check_storage_parms(storage_parms,'dataset.vis.zarr','make_imaging_weights')), "######### ERROR: user_storage_parms checking failed"
    
    
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
        #Must be a beter way to convert a sortedDict to dict
        if storage_parms['chunks_return'] is {}:
            chunks_return = {}
            for dim_key in image_dataset.chunks:
                chunks_return[dim_key] = image_dataset.chunks[dim_key][0]
            storage_parms['chunks_return'] = chunks_return
        
        if storage_parms['append']:
            print('Atempting to add ', imaging_weights_parms['imaging_weight_name'] , ' to ', storage_parms['outfile'])
            
            try:
                #vis_dataset = append_zarr(vis_dataset, storage_parms['outfile'],[imaging_weight],[storage_parms['data_variable_name']],[['time', 'baseline', 'chan', 'pol']],graph_name=storage_parms['graph_name'])
                
                list_xarray_data_variables = [vis_dataset[imaging_weights_parms['data_variable_name']]]
                
                image_dataset = append_zarr(list_xarray_data_variables,outfile=storage_parms['outfile'],chunks_return=storage_parms['chunks_return'],graph_name=storage_parms['graph_name'])
                
                print('##################### Finished appending imaging_weights #####################')
                return vis_dataset
            except Exception:
                print('ERROR : Could not append ', imaging_weights_parms['imaging_weight_name'] , 'to', storage_parms['outfile'])
        else:
            print('Saving dataset to ', storage_parms['outfile'])
            
            vis_dataset = write_zarr(vis_dataset, outfile=storage_parms['outfile'], chunks_return=storage_parms['chunks_return'], chunks_on_disk=storage_parms['chunks_on_disk'], compressor=storage_parms['compressor'], graph_name=storage_parms['graph_name'])
            
            #vis_dataset = write_zarr(vis_dataset, outfile=storage_parms['outfile'], compressor=storage_parms['compressor'], graph_name=storage_parms['graph_name'])
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
    import numpy as np
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
    

