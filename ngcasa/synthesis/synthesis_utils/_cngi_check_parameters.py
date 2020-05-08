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

#ducting - code is complex and might fail after some time if parameters is wrong (time waisting). Sensable values are also checked. Gives printout of all wrong parameters. Dirty images alone has x parametrs.


#Should this be moved to cngi?
import numpy as np


def _check_parms(parm_dict, string_key, acceptable_data_types, acceptable_data = None, acceptable_range = None, list_acceptable_data_types=None, list_len=None, default=None):
    """

    Parameters
    ----------
    parm_dict: dict
        The dictionary in which the a parameter will be checked
    string_key :
    acceptable_data_types : list
    acceptable_data : list
    acceptable_range : list (length of 2)
    list_acceptable_data_types : list
    list_len : int
    default :
    Returns
    -------
    parm_passed : bool
        
    """

    if string_key in parm_dict:
        if (list in acceptable_data_types) or (np.array in acceptable_data_types):
            if len(parm_dict[string_key]) != list_len:
                print('######### ERROR:Parameter ', string_key, 'must be a list of ', list_acceptable_data_types, ' and length', list_len , '. Wrong length.')
                return False
            else:
                for i in range(list_len):
                    type_check = False
                    for lt in list_acceptable_data_types:
                        if isinstance(parm_dict[string_key][i], lt):
                            type_check = True
                    if not(type_check):
                          print('######### ERROR:Parameter ', string_key, 'must be a list of ', list_acceptable_data_types, ' and length', list_len, '. Wrong type.')
                          return False
                          
                    if acceptable_data is not None:
                        if not(parm_dict[string_key][i] in acceptable_data):
                            print('######### ERROR: Invalid', string_key,'. Can only be one of ',acceptable_data,'.')
                            return False
                            
                    if acceptable_range is not None:
                        if (parm_dict[string_key][i] < acceptable_range[0]) or (parm_dict[string_key][i] > acceptable_range[1]):
                            print('######### ERROR: Invalid', string_key,'. Must be within the range ',acceptable_range,'.')
                            return False
        else:
            type_check = False
            for adt in acceptable_data_types:
                if isinstance(parm_dict[string_key], adt):
                    type_check = True
            if not(type_check):
                print('######### ERROR:Parameter ', string_key, 'must be of type ', acceptable_data_types)
                return False
                    
            if acceptable_data is not None:
                if not(parm_dict[string_key] in acceptable_data):
                    print('######### ERROR: Invalid', string_key,'. Can only be one of ',acceptable_data,'.')
                    return False
                    
            if acceptable_range is not None:
                if (parm_dict[string_key] < acceptable_range[0]) or (parm_dict[string_key] > acceptable_range[1]):
                    print('######### ERROR: Invalid', string_key,'. Must be within the range ',acceptable_range,'.')
                    return False
    else:
        if default is not None:
            parm_dict[string_key] =  default
            print ('Setting default', string_key, ' to ', parm_dict[string_key])
        else:
            print('######### ERROR:Parameter ', string_key, 'must be specified')
            return False
            
    return True

def _check_dataset(vis_dataset,data_variable_name):
    try:
        temp = vis_dataset[data_variable_name]
    except:
        print ('######### ERROR Data array ', data_variable_name,'can not be found in vis_dataset.')
        return False
    return True
    

def _check_storage_parms(storage_parms,default_outfile):
    from numcodecs import Blosc
    parms_passed = True
    
    if not(_check_parms(storage_parms, 'to_disk', [bool], default=False)): parms_passed = False
    
    if storage_parms['to_disk'] == True:
        if not(_check_parms(storage_parms, 'outfile', [str],default=default_outfile)): parms_passed = False
        if not(_check_parms(storage_parms, 'append', [bool],default=False)): parms_passed = False
        if not(_check_parms(storage_parms, 'compressor', [Blosc],default=Blosc(cname='zstd', clevel=2, shuffle=0))): parms_passed = False
    
    return parms_passed
    

def _check_grid_params(vis_dataset, grid_parms, default_image_name='DIRTY_IMAGE', default_sum_weight_name='SUM_WEIGHT'):
    import numbers
    parms_passed = True
    dtr = np.pi / (3600 * 180)

    n_chunks_in_each_dim = vis_dataset.DATA.data.numblocks
    
    if n_chunks_in_each_dim[3] != 1:
        print('######### ERROR chunking along polarization is not supported')
        return False
    
    if not(_check_parms(grid_parms, 'data_name', [str], default='DATA')): parms_passed = False
    if not(_check_dataset(vis_dataset,grid_parms['data_name'])): parms_passed = False
    
    if not(_check_parms(grid_parms, 'uvw_name', [str], default='UVW')): parms_passed = False
    if not(_check_dataset(vis_dataset,grid_parms['uvw_name'])): parms_passed = False
    
    if not(_check_parms(grid_parms, 'imaging_weight_name', [str], default='IMAGING_WEIGHT')): parms_passed = False
    if not(_check_dataset(vis_dataset,grid_parms['imaging_weight_name'])): parms_passed = False
    
    if not(_check_parms(grid_parms, 'image_name', [str], default=default_image_name)): parms_passed = False
    
    if not(_check_parms(grid_parms, 'sum_weight_name', [str], default=default_sum_weight_name)): parms_passed = False
    
    if not(_check_parms(grid_parms, 'chan_mode', [str], acceptable_data=['cube','continuum'], default='continuum')): parms_passed = False
    
    if not(_check_parms(grid_parms, 'imsize', [list], list_acceptable_data_types=[np.int], list_len=2)): parms_passed = False
    
    if not(_check_parms(grid_parms, 'cell', [list], list_acceptable_data_types=[numbers.Number], list_len=2)): parms_passed = False
    
    if not(_check_parms(grid_parms, 'oversampling', [np.int], default=100)): parms_passed = False
    
    if not(_check_parms(grid_parms, 'support', [np.int], default=7)): parms_passed = False
    
    if not(_check_parms(grid_parms, 'fft_padding', [numbers.Number], default=1.2,acceptable_range=[1,100])): parms_passed = False
    
    if parms_passed == True:
        grid_parms['imsize'] = np.array(grid_parms['imsize']).astype(int)
        grid_parms['imsize_padded'] = (grid_parms['fft_padding']* grid_parms['imsize']).astype(int)

        grid_parms['cell'] = dtr * np.array(grid_parms['cell'])
        grid_parms['cell'][0] = -grid_parms['cell'][0]
        
        grid_parms['complex_grid'] = True
    
    return parms_passed


def _check_imaging_weights_parms(vis_dataset, imaging_weights_parms):
    import numbers
    parms_passed = True
    dtr = np.pi / (3600 * 180)
    
    if not(_check_parms(imaging_weights_parms, 'data_name', [str], default='DATA')): parms_passed = False
    if not(_check_dataset(vis_dataset,imaging_weights_parms['data_name'])): parms_passed = False
    
    if not(_check_parms(imaging_weights_parms, 'uvw_name', [str], default='UVW')): parms_passed = False
    if not(_check_dataset(vis_dataset,imaging_weights_parms['uvw_name'])): parms_passed = False
    
    if not(_check_parms(imaging_weights_parms, 'imaging_weight_name', [str], default='IMAGING_WEIGHT')): parms_passed = False

    if not(_check_parms(imaging_weights_parms, 'weighting', [str], acceptable_data=['natural','uniform','briggs','briggs_abs'], default='natural')): parms_passed = False
    
    if imaging_weights_parms['weighting'] == 'briggs_abs':
        if not(_check_parms(imaging_weights_parms, 'briggs_abs_noise', [numbers.Number], default=1.0)): parms_passed = False

    if not(_check_parms(imaging_weights_parms, 'robust', [numbers.Number], default=0.5, acceptable_range=[-2,2])): parms_passed = False

    if not(_check_parms(imaging_weights_parms, 'chan_mode', [str], acceptable_data=['cube','continuum'], default='continuum')): parms_passed = False

    if not(_check_parms(imaging_weights_parms, 'imsize', [list], list_acceptable_data_types=[int,np.int64], list_len=2)): parms_passed = False

    if not(_check_parms(imaging_weights_parms, 'cell', [list], list_acceptable_data_types=[numbers.Number], list_len=2)): parms_passed = False

    if parms_passed == True:
        imaging_weights_parms['imsize'] = np.array(imaging_weights_parms['imsize']).astype(int)

        imaging_weights_parms['cell'] = dtr * np.array(imaging_weights_parms['cell'])
        imaging_weights_parms['cell'][0] = -imaging_weights_parms['cell'][0]
        
    
    return parms_passed
