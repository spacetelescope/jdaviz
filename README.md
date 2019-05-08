# jdaviz

A repository for developing astronomical data analysis tools in the Jupyter
platform. Depending on your point of view, can be "JWST Data Analysis
Visualization Tools", "Jupyter Data Analysis Visualization", or "Jupyter Data
analysis for Astronomy with glue-Viz".


# Notebook Based Cubeviz

## Install requirements

This is probably more than is required to just run in a notebook but for now, try this...

  * Install NPM (https://nodejs.org/en/) system wide (*not* a pip install)
  * `conda create -n jdaviz-dev`
  * `conda activate jdaviz-dev`  if conda is kinda new else: `source activate jdaviz-dev`
  * `pip install specutils`  # Forgot it
  * `git clone https://github.com/<your username>/jdaviz`
  * `cd jdaviz`
  * `pip install -e .`

## Example CubeViz Notebook

There is an example CubeViz notebook in the `examples/` directory to try out.  Change the filename location to point to 
a dataset on your system.

To run the notebook:
  * `conda activate jdaviz-dev`
  * `cd jdaviz/exmaples`
  * `jupyter notebook`
  
Then go into your favorite browser, go into the `cubeviz-example.ipynb` and execute each cell.
