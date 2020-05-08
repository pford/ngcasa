# Installation
Installation and setup for the Next Generation CASA Prototype  

## Pip Installation

```sh
python3 -m venv ngcasa
source ngcasa/bin/activate
pip install ngcasa
```

## Conda Installation

```sh
conda create -n ngcasa python=3.6
conda activate ngcasa
pip install ngcasa
```


## Installation from Source

```sh
git clone https://github.com/casangi/ngcasa.git
cd ngcasa
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
python setup.py install --root=.
```

## Configure dask.distributed
To avoid thread collisions, when using the Dask.distributed Client, set the following environment variables.

```sh
export OMP_NUM_THREADS=1 
export MKL_NUM_THREADS=1
export OPENBLAS_NUM_THREADS=1 
```

##  Building Documentation from Source
Follow steps to install cngi from source. Then navigate to the docs folder and execute the following:

```sh
sphinx-build -b html . ./build
```
View the documentation in your browser by navigating to:

 ```sh
file:///path/to/ngcasa/ngcasa/docs/build/index.html
```


# Usage
```python
>>> from ngcasa.synthesis.imaging import make_imaging_weights
>>> xds = make_imaging_weights(...)
```


Throughout the documentation we use the variable name `xds` to refer to Xarray DataSets.  
`xda` may be used to refer to Xarray DataArrays.  This is a "loose" convention only. 