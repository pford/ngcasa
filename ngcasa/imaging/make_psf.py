#   Copyright 2020 AUI, Inc. Washington DC, USA
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

def make_psf(vis_dataset, grid_parms, storage_parms):
    """
    .. todo::
        This function is not yet implemented
        
    Creates a cube or continuum point spread function (psf) image from the user specified uvw and imaging weight data.
    
    Only the prolate spheroidal convolutional gridding function is currently supported. This will change in a future release and
    the input parameter cf_dataset will be added. The user_grid_parms 'oversampling' and 'support' will then be removed.
    
    Parameters
    ----------
    vis_dataset : xarray.core.dataset.Dataset
        Input visibility dataset.
    #cf_dataset : xarray.core.dataset.Dataset
    #    The gridding convolutional functions to use for gridding.
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
        The factor that determines how much the gridded weights are padded before the fft is done.
    user_grid_parms['uvw_name'] : str, default ='UVW'
        The name of uvw data variable that will be used to grid the imaging weights.
    user_grid_parms['imaging_weight_name'] : str, default ='IMAGING_WEIGHT'
        The name of the imaging weights to be gridded.
    user_grid_parms['image_name'] : str, default ='PSF'
        The created image name.
    user_grid_parms['sum_weight_name'] : str, default ='PSF_SUM_WEIGHT'
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
