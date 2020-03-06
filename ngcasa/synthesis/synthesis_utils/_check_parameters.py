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



def _check_gridder_params(grid_parms,vis_dataset):
  import numpy as np
  parms_passed = True
  
  gridder_padding = 1.2
  dtr = np.pi / (3600 * 180)
  
  n_chunks_in_each_dim = vis_dataset.DATA.data.numblocks
  if n_chunks_in_each_dim[3] != 1:
    print("######### ERROR chunking along polarization is not supported")
    return False
    
  
  #Check chan_mode
  if "chan_mode" in grid_parms:
    if grid_parms["chan_mode"] != "continuum" and  grid_parms["chan_mode"] != "cube":
      print("ERROR: Invalid chan_mode. Can only be continuum or cube.")
      parms_passed = False
  else:
    grid_parms["chan_mode"] =  "continuum"
    print("Setting default chan_mode to continuum")
    
  #Check imsize
  if "imsize" in grid_parms:
    if isinstance(grid_parms["imsize"], list) or isinstance(grid_parms["imsize"], np.array):
      if len(grid_parms["imsize"]) != 2:
        print("######### ERROR: Invalid imsize. Must be a list of two integers")
        parms_passed = False
    else:
        print("######### ERROR: Invalid imsize. Must be a list of two integers")
        parms_passed = False
  else:
    grid_parms["imsize"] =  np.array([200,200])
    print("Setting default imsize", grid_parms["imsize"])
      
  #Check cell
  if "cell" in grid_parms:
    if isinstance(grid_parms["cell"], list) or isinstance(grid_parms["cell"], np.array):
      if len(grid_parms["cell"]) != 2:
        print("######### ERROR: Invalid cell. Must be a list of two floats in arcseconds")
        parms_passed = False
    else:
        rint("######### ERROR: Invalid cell. Must be a list of two floats in arcseconds")
        parms_passed = False
  else:
    grid_parms["cell"] =  np.array([0.8,0.8])
    print("Setting default cell", grid_parms["cell"])
    
  #Check oversampling
  if "oversampling" in grid_parms:
    if not(isinstance(grid_parms["oversampling"], np.int)):
        print("######### ERROR: Invalid oversampling. Must be an integers")
        parms_passed = False
  else:
    grid_parms["oversampling"] =  100
    print("Setting default oversampling", grid_parms["oversampling"])
    
  #Check support
  if "support" in grid_parms:
    if not(isinstance(grid_parms["support"], np.int)):
        print("######### ERROR: Invalid support. Must be an integers")
        parms_passed = False
  else:
    grid_parms["support"] =  7
    print("Setting default support", grid_parms["support"])
    
  #Check to_disk and "outfile"
  if "to_disk" in grid_parms:
    if not(isinstance(grid_parms["to_disk"], bool)):
        print("######### ERROR: Invalid to_disk. Must be bool")
        parms_passed = False
    else:
      if grid_parms["to_disk"] == True:
        if "outfile" in grid_parms["outfile"]:
          if isinstance(grid_parms["outfile"], str):
            print("######### ERROR: Invalid outfile. Must be a string")
            parms_passed = False
        else:
          grid_parms["outfile"] =  "dirty_image.img.zarr"
          print("Setting default outfile ", grid_parms["outfile"])
  else:
    grid_parms["to_disk"] =  False
    print("Setting default to_disk ", grid_parms["to_disk"])
    
  
  if parms_passed == True:
    grid_parms["imsize"] = np.array(grid_parms["imsize"]).astype(int)
    grid_parms["imsize_padded"] = (gridder_padding*grid_parms["imsize"]).astype(int)
        
    grid_parms['cell'] = dtr*np.array(grid_parms['cell'])
    grid_parms['cell'][0] = -grid_parms['cell'][0]
    
    grid_parms['gridder_padding'] = gridder_padding
    
  return parms_passed




