***********************************
Using Cubeviz in a Jupyter Notebook
***********************************

To initialize an instance of the Cubeviz app in a Jupyter notebook, simply run
the following code in a cell of the notebook::

    >>> from jdaviz import CubeViz
    >>> cubeviz = CubeViz()
    >>> cubeviz.app #doctest: +SKIP

After running the code above, you can interact with the Cubeviz application from 
subsequent notebook cells via the API methods attached to the `cubeviz` object,
for example loading data into the app as described in :ref:`cubeviz-import-data`.
