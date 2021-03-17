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

Data can also be accessed via the lower-level application interface that
connects to the ``glue-jupyter`` application level. This is accessed via the ``.app``
attribute of the `~jdaviz.configs.cubeviz.helper.CubeViz` helper class. For example::

     cubeviz.app.get_data_from_viewer('spectrum-viewer')
     cubeviz.app.get_data_from_viewer('flux-viewer')

This code can be used to access data from the different viewers, which is returned as a dictionary.
The viewer options in the `cubeviz` configuration are `spectrum-viewer`, `flux-viewer`,
`uncert-viewer`, and `mask-viewer`.
Using the appropriate data label, the data in its native type can be returned from this dictionary like
so::

    cubeviz.app.get_data_from_viewer('spectrum-viewer')['Subset 1']
    cubeviz.app.get_data_from_viewer('flux-viewer')['contents[FLUX]']

Data can also be accessed directly from ``data_collection`` using the following code::

    cubeviz.app.data_collection[0]

Which is returned as a `~glue.core.data.Data` object. The `data_collection` object
can be indexed to return all available data (i.e. not just using `0` like in the
previous example).
