#################
Installing JDAViz
#################

Installing can be done using pip::

   pip install git+https://github.com/spacetelescope/jdaviz --upgrade

Or from source::

   git clone https://github.com/spacetelescope/jdaviz.git
   cd jdaviz
   pip install -e .

Once installed, to start the browser app version, run the following in your terminal::

    jdaviz /path/to/data/file --layout=cubeviz

For the notebook version, start the jupyter kernel with the path to the Example.ipynb notebook::

    jupyter notebook /path/to/jdaviz/notebooks/Example.ipynb

Note that to load data in the notebook version, uncomment the cell in the notebook and
provide the path to your data.
