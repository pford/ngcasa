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

def make_image(vis_dataset, user_grid_parms, user_storage_parms):
    """
    Creates a cube or continuum dirty image from the user specified visibility, uvw and imaging weight data. Only the prolate spheroidal convolutional gridding function is supported (this will change in a future releases.)
    
    Parameters
    ----------
    vis_dataset : xarray.core.dataset.Dataset
        Input visibility dataset.
    user_grid_parms : dictionary
    user_grid_parms['imsize'] : list of int, length = 2
        The image size (no padding).
    user_grid_parms['cell']  : list of number, length = 2, units = arcseconds
        The image cell size.
    user_grid_parms['chan_mode'] : {'continuum'/'cube'}, default = 'continuum'
        Create a continuum or cube image.
    user_grid_parms['oversampling'] : int, default = 100
        The oversampling used for the convolutional gridding kernel. This will be removed in a later release and incorporated in the function that creates gridding convolutional kernels.
    user_grid_parms['support'] : int, default = 7
        The full support used for convolutional gridding kernel. This will be removed in a later release and incorporated in the function that creates gridding convolutional kernels.
    user_grid_parms['fft_padding'] : number, acceptable range [1,100], default = 1.2
        The factor that determines how much the gridded visibilities are padded before the fft is done.
    user_grid_parms['uvw_name'] : str, default ='UVW'
        The name of uvw data variable that will be used to grid the visibilities.
    user_grid_parms['data_name'] : str, default = 'DATA'
        The name of the visibility data to be gridded.
    user_grid_parms['imaging_weight_name'] : str, default ='IMAGING_WEIGHT'
        The name of the imaging weights to be used.
    user_grid_parms['image_name'] : str, default ='DIRTY_IMAGE'
        The created image name.
    user_grid_parms['sum_weight_name'] : str, default ='SUM_WEIGHT'
        The created sum of weights name.
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
    image_dataset : xarray.core.dataset.Dataset
        The image_dataset will contain the image created and the sum of weights.
    """
    print('######################### Start make_dirty_image #########################')
    import numpy as np
    from numba import jit
    import time
    import math
    import dask.array.fft as dafft
    import xarray as xr
    import dask.array as da
    import matplotlib.pylab as plt
    import dask.array.fft as dafft
    import dask
    import copy, os
    from numcodecs import Blosc
    from itertools import cycle
    
    from cngi.dio import write_zarr, append_zarr
    from ngcasa._ngcasa_utils._check_parms import _check_storage_parms
    from ._imaging_utils._check_imaging_parms import _check_grid_params, _check_storage_parms
    from ._imaging_utils._gridding_convolutional_kernels import _create_prolate_spheroidal_kernel, _create_prolate_spheroidal_kernel_1D
    from ._imaging_utils._standard_grid import _graph_standard_grid
    from ._imaging_utils._remove_padding import _remove_padding
    
    grid_parms = copy.deepcopy(user_grid_parms)
    storage_parms = copy.deepcopy(user_storage_parms)
    
    grid_parms['do_psf'] = False
    
    assert(_check_grid_params(vis_dataset,grid_parms)), "######### ERROR: user_grid_parms checking failed"
    assert(_check_storage_parms(storage_parms,'dirty_image.img.zarr','make_dirty_image')), "######### ERROR: user_storage_parms checking failed"
    
    # Creating gridding kernel
    cgk, correcting_cgk_image = _create_prolate_spheroidal_kernel(grid_parms['oversampling'], grid_parms['support'], grid_parms['imsize_padded'])
    cgk_1D = _create_prolate_spheroidal_kernel_1D(grid_parms['oversampling'], grid_parms['support'])
    
    grids_and_sum_weights = _graph_standard_grid(vis_dataset, cgk_1D, grid_parms)
    uncorrected_dirty_image = dafft.fftshift(dafft.ifft2(dafft.ifftshift(grids_and_sum_weights[0], axes=(0, 1)), axes=(0, 1)), axes=(0, 1))
        
    #Remove Padding
    correcting_cgk_image = _remove_padding(correcting_cgk_image,grid_parms['imsize'])
    uncorrected_dirty_image = _remove_padding(uncorrected_dirty_image,grid_parms['imsize']).real * (grid_parms['imsize_padded'][0] * grid_parms['imsize_padded'][1])
        
            
    #############Move this to Normalizer#############
    def correct_image(uncorrected_dirty_image, sum_weights, correcting_cgk):
        sum_weights[sum_weights == 0] = 1
        # corrected_image = (uncorrected_dirty_image/sum_weights[:,:,None,None])/correcting_cgk[None,None,:,:]
        corrected_image = (uncorrected_dirty_image / sum_weights[None, None, :, :]) / correcting_cgk[:, :, None, None]
        return corrected_image

    corrected_dirty_image = da.map_blocks(correct_image, uncorrected_dirty_image, grids_and_sum_weights[1],correcting_cgk_image)
   ####################################################

    if grid_parms['chan_mode'] == 'continuum':
        freq_coords = [da.mean(vis_dataset.coords['chan'].values)]
        imag_chan_chunk_size = 1
    elif grid_parms['chan_mode'] == 'cube':
        freq_coords = vis_dataset.coords['chan'].values
        imag_chan_chunk_size = vis_dataset.DATA.chunks[2][0]

    ###Create Dirty Image Dataset
    chunks = vis_dataset.DATA.chunks
    n_imag_pol = chunks[3][0]
    image_dict = {}
    coords = {'d0': np.arange(grid_parms['imsize'][0]), 'd1': np.arange(grid_parms['imsize'][1]),
              'chan': freq_coords, 'pol': np.arange(n_imag_pol)}
    image_dict[grid_parms['sum_weight_name']] = xr.DataArray(grids_and_sum_weights[1], dims=['chan','pol'])
    image_dict[grid_parms['image_name']] = xr.DataArray(corrected_dirty_image, dims=['d0', 'd1', 'chan', 'pol'])
    image_dataset = xr.Dataset(image_dict, coords=coords)
    
    
    ### Storing dirty image image code
    if  storage_parms['to_disk']:
        #Must be a beter way to convert a sortedDict to dict
        if storage_parms['chunks_return'] is {}:
            chunks_return = {}
            for dim_key in image_dataset.chunks:
                chunks_return[dim_key] = image_dataset.chunks[dim_key][0]
            storage_parms['chunks_return'] = chunks_return
    
        if storage_parms['append']:
            print('Atempting to add ', [grid_parms['image_name'], grid_parms['sum_weight_name']] , ' to ', storage_parms['outfile'])
            
            try:
                #image_dataset = _add_data_variables_to_dataset(image_dataset,list_arrays,storage_parms)
                #image_dataset = append_zarr(image_dataset, storage_parms['outfile'],list_arrays,storage_parms['list_data_variable_name'],storage_parms['list_array_dimensions'],graph_name=storage_parms['graph_name'])
                list_xarray_data_variables = [image_dataset[grid_parms['image_name']],image_dataset[grid_parms['sum_weight_name']]]
                
                image_dataset = append_zarr(list_xarray_data_variables,outfile=storage_parms['outfile'],chunks_return=storage_parms['chunks_return'],graph_name=storage_parms['graph_name'])
                print('##################### Finished appending dirty image #####################')
                return image_dataset
            except Exception:
                print('ERROR : Could not append ', storage_parms['list_data_variable_name'], 'to', storage_parms['outfile'])
        else:
            print('Saving dataset to ', storage_parms['outfile'])
            
            image_dataset = write_zarr(image_dataset, outfile=storage_parms['outfile'], chunks_return=storage_parms['chunks_return'], chunks_on_disk=storage_parms['chunks_on_disk'], compressor=storage_parms['compressor'], graph_name=storage_parms['graph_name'])
            
            print('##################### Created new dataset with make_dirty_image #####################')
            return image_dataset
    
    print('##################### created graph for make_dirty_image #####################')
    return image_dataset
