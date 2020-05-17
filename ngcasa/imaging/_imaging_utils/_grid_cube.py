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

def _grid_cube(type):
    """
    Do the gridding

    type=’psf’, ’obs’, ’res’, ’pbweight’..
    
    Use the Gridding convolution function from the cache, and apply phase-gradients for pointing offsets.

            Pointing Offset : Phase gradient across the GCF (from pointing meta-data or pointing_cal_dataset)
                    ( Include support for Heterogeneous Arrays where pointing offset varies with antenna
                      Include support for time-varying offsets : read from Pointing meta-data)

            Mosaic Offset : Phase gradient across the GCF + UVW-rotation to move data to image phasecenter.

    Note : A cube with one channel = mfs with nterms=1

    (TBD : This method has to be call-able from outside of imager, for example, for auto-flagging. Where to locate it ?).
    """
