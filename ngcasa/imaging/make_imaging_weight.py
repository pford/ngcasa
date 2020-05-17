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


def make_imaging_weight(vis_dataset, imaging_weights_parms, storage_parms):
    """
    .. todo::
        This function is not yet implemented
        
    Creates the imaging weight data variable that has dimensions time x baseline x chan x pol (matches the visibility data variable).
    The weight density can be averaged over channels or calculated independently for each channel using imaging_weights_parms['chan_mode'].
    The following imaging weighting schemes are supported 'natural', 'uniform', 'briggs', 'briggs_abs'.
    
    The imaging_weights_parms['imsize'] and imaging_weights_parms['cell'] should usually be the same values that will be used for
    subsequent synthesis blocks (for example making the psf).
    
    To achieve something similar to 'superuniform' weighting in CASA tclean imaging_weights_parms['imsize'] and
    imaging_weights_parms['cell'] can be varied relative to the values used in subsequent synthesis blocks.
    
    Support for radial weighting and uvtapering will be added in a future release.
    
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
  

