from setuptools import setup, find_packages

with open('README.md', "r") as fid:   #encoding='utf-8'
    long_description = fid.read()

setup(
    name='ngcasa',
    version='0.0.7',
    description='Next Generation CASA',
    long_description=long_description,
    long_description_content_type="text/markdown",
    author='National Radio Astronomy Observatory',
    author_email='casa-feedback@nrao.edu',
    url='https://github.com/casangi/ngcasa',
    license='Apache-2.0',
    packages=find_packages(),
    install_requires=['cngi_prototype>=0.0.50',
                      'numpy==1.18.1',
                      'numba==0.48.0',
                      'dask>=2.10.0',
                      'bokeh>=1.4.0',
                      'pandas>=0.25.2',
                      'xarray>=0.14.1',
                      'zarr>=2.3.0',
                      'numcodecs>=0.6.3',
                      'matplotlib>=3.1.2',
                      'sparse>=0.9.1'],
    extras_require={
        'dev': [
            'pylint>=2.4.4'
            #'black>=19.10.b0',
            'pytest>=5.3.5',
            #'pytest-pep8',
            #'pytest-cov'
            's3fs>=0.4.0',
        ]
    }

)
