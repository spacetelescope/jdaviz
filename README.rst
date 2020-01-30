JWST Data Analysis Visualization Development
--------------------------------------------

.. image:: http://img.shields.io/badge/powered%20by-AstroPy-orange.svg?style=flat
    :target: http://www.astropy.org
    :alt: Powered by Astropy Badge

Usage
-----

Clone the repository, move into the directory, and install the package using::

    $ pip install .

Developers can add the ``-e`` flag to install in editable mode.

Alternatively, the package can be installed directly from the repository using::

    $ pip install git+https://github.com/spacetelescope/jdaviz.git

Notebook
^^^^^^^^

Open the provided Jupyter notebook and run the cell containing the code. *Note*
there is currently an issue with the live rendering in the notebook. If, after
running the cell, no icons or plugins load, save the notebook and refresh the page
(there is no need to re-run the notebook).

Browser
^^^^^^^

The easiest way to start up the browser version of the app is to do::

    $ jdaviz filename.fits

If you want to use a non-default layout, you can specify the layout name with::

    $ jdaviz filename.fits --layout=cubeviz

The browser version of the app can also be accessed by running the provided
notebook with `voila
<https://github.com/voila-dashboards/voila/tree/master/voila>`_ package. This
will open and render the results of the cell in a new browser window::

    $ voila notebooks/Example.ipynb

It is recommended that users also install the `voila-vuetify
<https://github.com/voila-dashboards/voila-vuetify>`_ nbconvert template to review
the css spacing in the default nbconvert template utilized by voila. To use the
template, include it in the start up command::

    $ voila notebooks/Example.ipynb --template=jdaviz-default

License
-------

This project is Copyright (c) JDADF Developers and licensed under
the terms of the BSD 3-Clause license. This package is based upon
the `Astropy package template <https://github.com/astropy/package-template>`_
which is licensed under the BSD 3-clause licence. See the licenses folder for
more information.


Contributing
------------

We love contributions! jdaviz is open source,
built on open source, and we'd love to have you hang out in our community.

**Imposter syndrome disclaimer**: We want your help. No, really.

There may be a little voice inside your head that is telling you that you're not
ready to be an open source contributor; that your skills aren't nearly good
enough to contribute. What could you possibly offer a project like this one?

We assure you - the little voice in your head is wrong. If you can write code at
all, you can contribute code to open source. Contributing to open source
projects is a fantastic way to advance one's coding skills. Writing perfect code
isn't the measure of a good developer (that would disqualify all of us!); it's
trying to create something, making mistakes, and learning from those
mistakes. That's how we all improve, and we are happy to help others learn.

Being an open source contributor doesn't just mean writing code, either. You can
help out by writing documentation, tests, or even giving feedback about the
project (and yes - that includes giving feedback about the contribution
process). Some of these contributions may be the most valuable to the project as
a whole, because you're coming to the project with fresh eyes, so you can see
the errors and assumptions that seasoned contributors have glossed over.

Note: This disclaimer was originally written by
`Adrienne Lowe <https://github.com/adriennefriend>`_ for a
`PyCon talk <https://www.youtube.com/watch?v=6Uj746j9Heo>`_, and was adapted by
jdaviz based on its use in the README file for the
`MetPy project <https://github.com/Unidata/MetPy>`_.
