======
JDAViz
======

.. image:: https://travis-ci.com/spacetelescope/jdaviz.svg?branch=master
    :target: https://travis-ci.com/spacetelescope/jdaviz

.. image:: https://codecov.io/gh/spacetelescope/jdaviz/branch/master/graph/badge.svg
    :target: https://codecov.io/gh/spacetelescope/jdaviz

.. image:: https://readthedocs.org/projects/jdaviz/badge/?version=latest
    :target: https://jdaviz.readthedocs.io/en/latest/?badge=latest
    :alt: Documentation Status

.. image:: https://img.shields.io/badge/powered%20by-AstroPy-orange.svg?style=flat
    :target: https://www.astropy.org
    :alt: Powered by Astropy


``jdaviz`` is a package of astronomical data analysis visualization
tools based on the Jupyter platform.  These GUI-based tools link data
visualization and interactive analysis.  They are designed to work
within a Jupyter notebook cell, as a standalone desktop application,
or as embedded windows within a website -- all with nearly-identical
user interfaces. Note that ``jdaviz`` is under heavy development and should 
not be considered stable or feature-complete. Users who encounter bugs in 
the currently implemented features are encouraged to open an issues in this 
repository.

``jdaviz`` applications currently include tools for interactive
visualization of spectroscopic data.  SpecViz is a tool for
visualization and quick-look analysis of 1D astronomical spectra.
MOSViz is a visualization tool for many astronomical spectra,
typically the output of a multi-object spectrograph (e.g., JWST
NIRSpec), and includes viewers for 1D and 2D spectra as well as
contextual information like on-sky views of the spectrograph slit.
CubeViz provides of view of spectroscopic data cubes (like those to be
produced by JWST MIRI), along with 1D spectra extracted from the cube.


Installing
----------
For details on installing and using JDAViz, see the
`JDAViz documentation <https://jdaviz.readthedocs.io/en/latest/>`_.



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
