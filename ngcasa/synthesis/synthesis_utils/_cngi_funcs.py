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

import dask.array as da
import dask
from numcodecs import Blosc
import xarray as xr
import zarr
import time
from itertools import cycle
import numpy as np

def _remove_padding(image_dask_array,image_size):
    #Check that image_size < image_size
    #Check parameters
    
    image_size_padded= np.array(image_dask_array.shape[0:2])
    start_xy = (image_size_padded // 2 - image_size // 2)
    end_xy = start_xy + image_size
    
    image_dask_array = image_dask_array[start_xy[0]:end_xy[0], start_xy[1]:end_xy[1]]
    return image_dask_array

##########################################################################################################################################
##########################################################################################################################################
######################################################### Storage Functions ##############################################################
##########################################################################################################################################
##########################################################################################################################################

def _to_storage(dataset, to_storage_parms):
    outfile = to_storage_parms['outfile']

    compressor = to_storage_parms['compressor']
    encoding = dict(zip(list(dataset.data_vars), cycle([{'compressor': compressor}])))
    start = time.time()
    xr.Dataset.to_zarr(dataset, store=outfile, mode='w', encoding=encoding,consolidated=True)
    time_to_calc_and_store = time.time() - start
    print('time_to_calc_and_store ', time_to_calc_and_store)
    
    dataset_group = zarr.open_group(to_storage_parms['outfile'],mode='a')
    dataset_group.attrs[to_storage_parms['function_name']+'_time'] = time_to_calc_and_store
    

    dataset = xr.open_zarr(outfile,consolidated=True,overwrite_encoded_chunks=True)
    return dataset


##########################################################################################################################################
#The problem https://stackoverflow.com/questions/58042559/adding-new-xarray-dataarray-to-an-existing-zarr-store-without-re-writing-the-who
#see https://docs.dask.org/en/latest/array-creation.html for Zarr, Dask, S3 instructions
# From xarray source code
# Zarr arrays do not have dimenions. To get around this problem, we add
# an attribute that specifies the dimension. We have to hide this attribute
# when we send the attributes to the user.
# zarr_obj can be either a zarr group or zarr array
# '_ARRAY_DIMENSIONS' must be specified so that xarray.open_zarr works (contains all the dimension and coord info related to tha array)
#Limitations only works if dask_array dimentions are a subset of the dimentions in the to_storage_parms['outfile'] dataset.
#Will overwrite
#The data variable to append must have the same dimentionality and chunking as an existing data variable (storage_parms['data_variable_to_pattern'])
def _add_data_variable_to_dataset(dataset,dask_array,storage_parms):
    from fsspec import get_mapper
    start = time.time()
    #Rechunk dask_array to match chunking on disk
    disk_dataset = xr.open_zarr(storage_parms['outfile'])
    chunksize_on_disk =[]
    for array_dim in storage_parms['array_dimensions']:
        chunksize_on_disk.append(disk_dataset.chunks[array_dim][0])
    dask_array = dask_array.rechunk(chunksize_on_disk)
    

    mapper = get_mapper(storage_parms['outfile']+'/'+storage_parms['data_variable_name'])
    
    z = dask.delayed(zarr.create)(
        shape=dask_array.shape,
        chunks=chunksize_on_disk,
        dtype=dask_array.dtype,
        store=mapper,
        overwrite=True) #Hopefully one day use ,attrs={'_ARRAY_DIMENSIONS':storage_parms['array_dimensions']}
   
    #Cant do this since delayed objects are immutable
    #Zarr does not currently support attrs being specified with zarr.create (see https://github.com/zarr-developers/zarr-python/issues/538)
    #z.attrs['_ARRAY_DIMENSIONS'] = storage_parms['array_dimensions']
    ############

    da.store(dask_array,z,compute=True,flush=True)
    
    #Save dask array to disk
    #da.to_zarr(dask_array,storage_parms['outfile']+'/'+storage_parms['data_variable_name'],compressor=storage_parms['compressor'],overwrite=True)
    
    #Add array dimention labels so that xarray.open_zarr works
    dataset_group = zarr.open_group(storage_parms['outfile'],mode='a')
    dataset_group[storage_parms['data_variable_name']].attrs['_ARRAY_DIMENSIONS'] = storage_parms['array_dimensions']
    time_to_calc_and_store = time.time() - start
    
    
    print('time_to_calc_and_store ', time_to_calc_and_store)
    dataset_group.attrs[storage_parms['function_name']+'_time'] = time_to_calc_and_store
    
    # Current Chunk Shape. Must be a beter way to get dict from SortedKeyDict
    current_dataset_chunk_size = {}
    for dim_key in dataset.chunks:
        current_dataset_chunk_size[dim_key] = dataset.chunks[dim_key][0]
    
    return xr.open_zarr(storage_parms['outfile'],chunks=current_dataset_chunk_size,overwrite_encoded_chunks=True)

# print(vis_group['DATA'].attrs["_ARRAY_DIMENSIONS"])
# print(vis_group['DATA'].attrs.asdict())



def _add_data_variables_to_dataset(dataset,list_dask_array,storage_parms):
    '''
    storage_parms['list_data_variable_name']
    storage_parms['list_array_dimensions']
    list_dask_array
    '''
    from fsspec import get_mapper
    
    start = time.time()
    n_arrays = len(list_dask_array)
    disk_dataset = xr.open_zarr(storage_parms['outfile'])
    
    list_target_zarr = []
    for i in range(n_arrays):
        #Rechunk
        #storage_parms['list_array_dimensions'] list of lists [['time', 'baseline','chan', 'pol'],['chan','pol'],['d0','d1']]. Must be in right order
        chunksize_on_disk =[]
        for array_dim in storage_parms['list_array_dimensions'][i]:
            chunksize_on_disk.append(disk_dataset.chunks[array_dim][0])
        
        dask_array = list_dask_array[i].rechunk(chunksize_on_disk[i])
        
        #Create list_target_zarr
        mapper = get_mapper(storage_parms['outfile']+'/'+storage_parms['list_data_variable_name'][i])
        
        list_target_zarr.append(dask.delayed(zarr.create)(
             shape=dask_array.shape,
             chunks=chunksize_on_disk,
             dtype=dask_array.dtype,
             store=mapper,
             overwrite=True)) #Hopefully one day use ,attrs={'_ARRAY_DIMENSIONS':storage_parms['array_dimensions']}
    da.store(list_dask_array,list_target_zarr,compute=True,flush=True)
    
    #Add array dimention labels so that xarray.open_zarr works
    #Give all reasons why we can't do this earlier
    dataset_group = zarr.open_group(storage_parms['outfile'],mode='a')
    
    for i in range(n_arrays):
        dataset_group[storage_parms['list_data_variable_name'][i]].attrs['_ARRAY_DIMENSIONS'] = storage_parms['list_array_dimensions'][i]
    
    time_to_calc_and_store = time.time() - start
    print('time_to_calc_and_store ', time_to_calc_and_store)
    dataset_group.attrs[storage_parms['function_name']+'_time'] = time_to_calc_and_store
    
    # Current Chunk Shape. Must be a beter way to get dict from SortedKeyDict
    current_dataset_chunk_size = {}
    for dim_key in dataset.chunks:
        current_dataset_chunk_size[dim_key] = dataset.chunks[dim_key][0]
    
    #time_to_calc_and_store = time.time() - start
    return xr.open_zarr(storage_parms['outfile'],chunks=current_dataset_chunk_size,overwrite_encoded_chunks=True)
    
    
    
    
    

''' from dask core.py to_zarr (dask/array/core.py)
z = delayed(zarr.create)(
    shape=arr.shape,
    chunks=chunks,
    dtype=arr.dtype,
    store=mapper,
    path=component,
    overwrite=overwrite,
    **kwargs,
)
return arr.store(z, lock=False, compute=compute, return_stored=return_stored)
'''
'''
xarray/backends/common.py

delayed_store = da.store(
           self.sources,
           self.targets,
           lock=self.lock,
           compute=compute,
           flush=True,
           regions=self.regions,
       )
       self.sources = []
       self.targets = []
       self.regions = []
       return delayed_store
'''
