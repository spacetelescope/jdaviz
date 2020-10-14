.. _mosviz-notebook:

***********************************
Using Mosviz in a Jupyter Notebook 
***********************************

To initialize an instance of the Mosviz app in a Jupyter notebook, simply run
the following code in a cell of the notebook::

    >>> from jdaviz import MosViz
    >>> mosviz = MosViz()
    >>> mosviz.app #doctest: +SKIP

After running the code above, you can interact with the Mosviz application from 
subsequent notebook cells via the API methods attached to the `mosviz` object,
for example loading data into the app as described in :ref:`mosviz-import-data`.

