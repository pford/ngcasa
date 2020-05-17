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

def make_pb(vis_dataset,cf_dataset, make_pb_parms,  storage_parms):
    """
    .. todo::
        This function is not yet implemented
        
    Construct a Primary Beam cube containing a weighted sum of primary beams
    
    Option 1 : Evaluate models directly onto the image (for common PBs)
    
    Option 2 : Inverse FT each gridding convolution function (for varying PBs)

    (A cube with 1 channel is a continuum image (nterms=1))
    
    Returns
    -------
    img_xds : xarray.core.dataset.Dataset
    """
