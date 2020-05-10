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


def make_psf(vis_dataset, user_grid_parms, user_storage_parms):
    """
    
    Parameters
    ----------
    vis_dataset : xarray.core.dataset.Dataset
        input Visibility Dataset
    grid_parms : dictionary
          keys ('chan_mode','imsize','cell','oversampling','support','to_disk','outfile')
    Returns
    -------
    psf_dataset : xarray.core.dataset.Dataset
    """
    
    print('######################### Start make_psf #########################')
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
    from .._synthesis_utils._remove_padding import _remove_padding
    
    grid_parms = copy.deepcopy(user_grid_parms)
    storage_parms = copy.deepcopy(user_storage_parms)
    
    grid_parms['do_psf'] = True
    
    assert(_check_grid_params(vis_dataset,grid_parms,default_image_name='PSF',default_sum_weight_name='PSF_SUM_WEIGHT')), "######### ERROR: user_grid_parms checking failed"
    assert(_check_storage_parms(storage_parms,'psf.img.zarr')), "######### ERROR: user_storage_parms checking failed"
    
    # Creating gridding kernel
    cgk, correcting_cgk_image = _create_prolate_spheroidal_kernel(grid_parms['oversampling'], grid_parms['support'], grid_parms['imsize_padded'])
    cgk_1D = _create_prolate_spheroidal_kernel_1D(grid_parms['oversampling'], grid_parms['support'])
    
    grids_and_sum_weights = _graph_standard_grid(vis_dataset, cgk_1D, grid_parms)
    uncorrected_psf_image = dafft.fftshift(dafft.ifft2(dafft.ifftshift(grids_and_sum_weights[0], axes=(0, 1)), axes=(0, 1)), axes=(0, 1))
        
    #Remove Padding
    correcting_cgk_image = _remove_padding(correcting_cgk_image,grid_parms['imsize'])
    uncorrected_psf_image = _remove_padding(uncorrected_psf_image,grid_parms['imsize']).real * (grid_parms['imsize_padded'][0] * grid_parms['imsize_padded'][1])
        
            
    #############Move this to Normalizer#############
    def correct_image(uncorrected_psf_image, sum_weights, correcting_cgk):
        sum_weights[sum_weights == 0] = 1
        corrected_image = (uncorrected_psf_image / sum_weights[None, None, :, :]) / correcting_cgk[:, :, None, None]
        return corrected_image

    corrected_psf_image = da.map_blocks(correct_image, uncorrected_psf_image, grids_and_sum_weights[1],correcting_cgk_image)  # ? has to be .data to paralize correctly
   ####################################################

    if grid_parms['chan_mode'] == 'continuum':
        freq_coords = [da.mean(vis_dataset.coords['chan'].values)]
        imag_chan_chunk_size = 1
    elif grid_parms['chan_mode'] == 'cube':
        freq_coords = vis_dataset.coords['chan'].values
        imag_chan_chunk_size = vis_dataset.DATA.chunks[2][0]

    ###Create PSF Image Dataset
    chunks = vis_dataset.DATA.chunks
    n_imag_pol = chunks[3][0]
    image_dict = {}
    coords = {'d0': np.arange(grid_parms['imsize'][0]), 'd1': np.arange(grid_parms['imsize'][1]),
              'chan': freq_coords, 'pol': np.arange(n_imag_pol)}
    image_dict[grid_parms['sum_weight_name']] = xr.DataArray(grids_and_sum_weights[1], dims=['chan','pol'])
    image_dict[grid_parms['image_name']] = xr.DataArray(corrected_psf_image, dims=['d0', 'd1', 'chan', 'pol'])
    image_dataset = xr.Dataset(image_dict, coords=coords)
    
    
    ### Storing psf image code
    if  storage_parms['to_disk']:
        storage_parms['graph_name'] = 'make_psf'
        
        if storage_parms['append']:
            storage_parms['list_data_variable_name'] = [grid_parms['image_name'], grid_parms['sum_weight_name']]
            print('Atempting to add ', storage_parms['list_data_variable_name']   , ' to ', storage_parms['outfile'])
            
            list_arrays = [image_dataset[storage_parms['list_data_variable_name'][0]].data, image_dataset[storage_parms['list_data_variable_name'][1]].data]
            storage_parms['list_array_dimensions'] = [['d0', 'd1', 'chan', 'pol'],['chan', 'pol']]
            #try:
            if True:
                #image_dataset = _add_data_variables_to_dataset(image_dataset,list_arrays,storage_parms)
                image_dataset = append_zarr(image_dataset, storage_parms['outfile'],list_arrays,storage_parms['list_data_variable_name'],storage_parms['list_array_dimensions'],graph_name=storage_parms['graph_name'])
                print('##################### Finished appending psf #####################')
                return image_dataset
            #except Exception:
            #    print('ERROR : Could not append ', storage_parms['list_data_variable_name'], 'to', storage_parms['outfile'])
        else:
            print('Saving dataset to ', storage_parms['outfile'])
            #image_dataset = _to_storage(image_dataset, storage_parms)
            write_zarr(image_dataset, outfile=storage_parms['outfile'], compressor=storage_parms['compressor'], graph_name=storage_parms['graph_name'])
            print('##################### Created new dataset with make_psf #####################')
            return image_dataset
    
    print('##################### created graph for make_psf #####################')
    return image_dataset

