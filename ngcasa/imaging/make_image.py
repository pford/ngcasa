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

def make_image(vis_dataset, grid_parms, storage_parms):
    """
    Creates a cube or continuum dirty image from the user specified visibility, uvw and imaging weight data. Only the prolate spheroidal convolutional gridding function is supported (this will change in a future releases.)
    
    Parameters
    ----------
    vis_dataset : xarray.core.dataset.Dataset
        Input visibility dataset.
    grid_parms : dictionary
    grid_parms['imsize'] : list of int, length = 2
        The image size (no padding).
    grid_parms['cell']  : list of number, length = 2, units = arcseconds
        The image cell size.
    grid_parms['chan_mode'] : {'continuum'/'cube'}, default = 'continuum'
        Create a continuum or cube image.
    grid_parms['oversampling'] : int, default = 100
        The oversampling used for the convolutional gridding kernel. This will be removed in a later release and incorporated in the function that creates gridding convolutional kernels.
    grid_parms['support'] : int, default = 7
        The full support used for convolutional gridding kernel. This will be removed in a later release and incorporated in the function that creates gridding convolutional kernels.
    grid_parms['fft_padding'] : number, acceptable range [1,100], default = 1.2
        The factor that determines how much the gridded visibilities are padded before the fft is done.
    grid_parms['uvw_name'] : str, default ='UVW'
        The name of uvw data variable that will be used to grid the visibilities.
    grid_parms['data_name'] : str, default = 'DATA'
        The name of the visibility data to be gridded.
    grid_parms['imaging_weight_name'] : str, default ='IMAGING_WEIGHT'
        The name of the imaging weights to be used.
    grid_parms['image_name'] : str, default ='DIRTY_IMAGE'
        The created image name.
    grid_parms['sum_weight_name'] : str, default ='SUM_WEIGHT'
        The created sum of weights name.
    storage_parms : dictionary
    storage_parms['to_disk'] : bool, default = False
        If true the dask graph is executed and saved to disk in the zarr format.
    storage_parms['append'] : bool, default = False
        If storage_parms['to_disk'] is True only the dask graph associated with the function is executed and the resulting data variables are saved to an existing zarr file on disk.
        Note that graphs on unrelated data to this function will not be executed or saved.
    storage_parms['outfile'] : str
        The zarr file to create or append to.
    storage_parms['chunks_on_disk'] : dict of int, default = {}
        The chunk size to use when writing to disk. This is ignored if storage_parms['append'] is True. The default will use the chunking of the input dataset.
    storage_parms['chunks_return'] : dict of int, default = {}
        The chunk size of the dataset that is returned. The default will use the chunking of the input dataset.
    storage_parms['graph_name'] : str
        The time to compute and save the data is stored in the attribute section of the dataset and storage_parms['graph_name'] is used in the label.
    storage_parms['compressor'] : numcodecs.blosc.Blosc,default=Blosc(cname='zstd', clevel=2, shuffle=0)
        The compression algorithm to use. Available compression algorithms can be found at https://numcodecs.readthedocs.io/en/stable/blosc.html.
    
    Returns
    -------
    image_dataset : xarray.core.dataset.Dataset
        The image_dataset will contain the image created and the sum of weights.
    """
    print('######################### Start make_image #########################')
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
    
    from ngcasa._ngcasa_utils._store import _store
    from ngcasa._ngcasa_utils._check_parms import _check_storage_parms
    from ._imaging_utils._check_imaging_parms import _check_grid_params
    from ._imaging_utils._gridding_convolutional_kernels import _create_prolate_spheroidal_kernel, _create_prolate_spheroidal_kernel_1D
    from ._imaging_utils._standard_grid import _graph_standard_grid
    from ._imaging_utils._remove_padding import _remove_padding
    
    _grid_parms = copy.deepcopy(grid_parms)
    _storage_parms = copy.deepcopy(storage_parms)
    
    _grid_parms['do_psf'] = False
    
    assert(_check_grid_params(vis_dataset,_grid_parms)), "######### ERROR: grid_parms checking failed"
    assert(_check_storage_parms(_storage_parms,'dirty_image.img.zarr','make_image')), "######### ERROR: storage_parms checking failed"
    
    # Creating gridding kernel
    cgk, correcting_cgk_image = _create_prolate_spheroidal_kernel(_grid_parms['oversampling'], _grid_parms['support'], _grid_parms['imsize_padded'])
    cgk_1D = _create_prolate_spheroidal_kernel_1D(_grid_parms['oversampling'], _grid_parms['support'])
    
    grids_and_sum_weights = _graph_standard_grid(vis_dataset, cgk_1D, _grid_parms)
    uncorrected_dirty_image = dafft.fftshift(dafft.ifft2(dafft.ifftshift(grids_and_sum_weights[0], axes=(0, 1)), axes=(0, 1)), axes=(0, 1))
        
    #Remove Padding
    correcting_cgk_image = _remove_padding(correcting_cgk_image,_grid_parms['imsize'])
    uncorrected_dirty_image = _remove_padding(uncorrected_dirty_image,_grid_parms['imsize']).real * (_grid_parms['imsize_padded'][0] * _grid_parms['imsize_padded'][1])
        
            
    #############Move this to Normalizer#############
    def correct_image(uncorrected_dirty_image, sum_weights, correcting_cgk):
        sum_weights[sum_weights == 0] = 1
        # corrected_image = (uncorrected_dirty_image/sum_weights[:,:,None,None])/correcting_cgk[None,None,:,:]
        corrected_image = (uncorrected_dirty_image / sum_weights[None, None, :, :]) / correcting_cgk[:, :, None, None]
        return corrected_image

    corrected_dirty_image = da.map_blocks(correct_image, uncorrected_dirty_image, grids_and_sum_weights[1],correcting_cgk_image)
   ####################################################

    if _grid_parms['chan_mode'] == 'continuum':
        freq_coords = [da.mean(vis_dataset.coords['chan'].values)]
        chan_width = da.from_array([da.mean(vis_dataset['chan_width'].data)],chunks=(1,))
        imag_chan_chunk_size = 1
    elif _grid_parms['chan_mode'] == 'cube':
        freq_coords = vis_dataset.coords['chan'].values
        chan_width = vis_dataset['chan_width'].data
        imag_chan_chunk_size = vis_dataset.DATA.chunks[2][0]
    
    ###Create Dirty Image Dataset
    chunks = vis_dataset.DATA.chunks
    n_imag_pol = chunks[3][0]
    image_dict = {}
    coords = {'d0': np.arange(_grid_parms['imsize'][0]), 'd1': np.arange(_grid_parms['imsize'][1]),
              'chan': freq_coords, 'pol': np.arange(n_imag_pol), 'chan_width' : ('chan',chan_width)}
              
    image_dict[_grid_parms['sum_weight_name']] = xr.DataArray(grids_and_sum_weights[1], dims=['chan','pol'])
    image_dict[_grid_parms['image_name']] = xr.DataArray(corrected_dirty_image, dims=['d0', 'd1', 'chan', 'pol'])
    image_dataset = xr.Dataset(image_dict, coords=coords)
    
    list_xarray_data_variables = [image_dataset[_grid_parms['image_name']],image_dataset[_grid_parms['sum_weight_name']]]
    return _store(image_dataset,list_xarray_data_variables,_storage_parms)
