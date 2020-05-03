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

#Allow setting of padding grid_parms['gridder_padding'] = gridder_padding
#Setting to keep grid or correcting
#normalizarion parameters (flat sky, flat noise etc)
#mosaic parameters, etc
#Allow users to append image to existing img.zarr
#storage_parms['append'], user_grid_parms['data_variable_name']

#Units not specified, for example  arcsecond, Jy ect


def make_dirty_image(vis_dataset, user_grid_parms, user_storage_parms):
    """
    Grids visibilities from Visibility Dataset and returns dirty Image Dataset.
    If to_disk is set to true the data is saved to disk.
    Parameters
    ----------
    vis_dataset : xarray.core.dataset.Dataset
        input Visibility Dataset
    grid_parms : dictionary
          keys ('chan_mode','imsize','cell','oversampling','support','to_disk','outfile')
    Returns
    -------
    dirty_image_dataset : xarray.core.dataset.Dataset
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
    
    from ..synthesis_utils._cngi_check_parameters import _check_grid_params, _check_storage_parms
    from ..synthesis_utils._cngi_funcs import _remove_padding, _to_storage, _add_data_variables_to_dataset
    
    from .imaging_utils._standard_grid import _graph_standard_grid
    from .imaging_utils._gridding_convolutional_kernels import _create_prolate_spheroidal_kernel, _create_prolate_spheroidal_kernel_1D
    
    grid_parms = copy.deepcopy(user_grid_parms)
    storage_parms = copy.deepcopy(user_storage_parms)
    
    grid_parms['do_psf'] = False
    
    assert(_check_grid_params(vis_dataset,grid_parms)), "######### ERROR: user_grid_parms checking failed"
    assert(_check_storage_parms(storage_parms,'dirty_image.img.zarr')), "######### ERROR: user_storage_parms checking failed"
    
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
    
    
    ### Storing psf image code
    if  storage_parms['to_disk']:
        storage_parms['function_name'] = 'make_dirty_image'
        
        if storage_parms['append']:
            storage_parms['list_data_variable_name'] = [grid_parms['image_name'], grid_parms['sum_weight_name']]
            print('Atempting to add ', storage_parms['list_data_variable_name']   , ' to ', storage_parms['outfile'])
            
            list_arrays = [image_dataset[storage_parms['list_data_variable_name'][0]].data, image_dataset[storage_parms['list_data_variable_name'][1]].data]
            storage_parms['list_array_dimensions'] = [['d0', 'd1', 'chan', 'pol'],['chan', 'pol']]
            #try:
            if True:
                image_dataset = _add_data_variables_to_dataset(image_dataset,list_arrays,storage_parms)
                print('##################### Finished appending psf #####################')
                return image_dataset
            #except Exception:
            #    print('ERROR : Could not append ', storage_parms['list_data_variable_name'], 'to', storage_parms['outfile'])
        else:
            print('Saving dataset to ', storage_parms['outfile'])
            image_dataset = _to_storage(image_dataset, storage_parms)
            print('##################### Created new dataset with make_psf #####################')
            return image_dataset
    
    print('##################### created graph for make_psf #####################')
    return image_dataset
