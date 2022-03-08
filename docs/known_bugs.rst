Known Issues
============

You can `report an issue to the Jdaviz GitHub issues <https://github.com/spacetelescope/jdaviz/issues/new>`_.

Some currently known but unresolved common issues that users encounter
are as follow in their respective categories. This list is not exhaustive,
so please also consult `existing Jdaviz GitHub issues <https://github.com/spacetelescope/jdaviz/issues/>`_
as well if you are unable to find your issue here:

* :ref:`known_issues_installation`
* :ref:`known_issues_cubeviz`
* :ref:`known_issues_imviz`
* :ref:`known_issues_specviz`

.. _known_issues_installation:

Installation
------------

On MacOS versions 10.13 and older, install fails due to scikit-image
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

This can be fixed by reinstalling scikit-image::

    pip uninstall scikit-image
    conda install scikit-image

The reason for this issue is that prebuilt binaries for scikit-image don't
work on Mac versions of 10.13 or older and conda installs an older
version of scikit-image that works with those versions.
Another way to get the up-to-date scikit-image version is::

    pip install -U --no-binary scikit-image scikit-image.

Although this solution takes much longer (~5 minutes) to install than the
first solution.

On some platforms, install fails due to vispy
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

The 0.6.4 version of vispy fails to build for some combinations of
platform/OS and Python versions. vispy 0.6.5 has resolved this, but a
workaround if you have an older version of vispy is to ensure you have a
compatible version::

    conda create -n jdaviz python=3.8
    conda activate jdaviz
    pip install vispy>=0.6.5
    pip install jdaviz --no-cache-dir

See `Issue #305 <https://github.com/spacetelescope/jdaviz/issues/305>`_ for
updates on this topic.

On some platforms, install fails due to bottleneck
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

In a conda environment, where numpy was installed using conda, installing
jdaviz using pip will attempt to pull bottleneck from PyPI. This might result
in bottleneck trying to build numpy from source and crash, stalling the
installation altogether. When this happens, exit the installation, install
bottleneck with conda, and try to install jdaviz again.

.. _known_issues_cubeviz:

Cubeviz
-------

Collapse and Moment Maps: Spectral bounds do not match Region selection
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

When trying to do a second collapse with the same spectral region, but with
resized bounds: change to Region=None, resize the region, then reselect Region 1,
the region bounds are correct. However, applying Collapse again, it errors out and
the image viewer that contained the initial collapse goes blank.


Cube viewer contrast changes when collapsing Jupyter scroll window
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

In order to see the full Cubeviz app in a Jupyter notebook, one can click on
the side of the cell output to collapse or expand the scrollable window. This
has the unintended consequence of changing the contrast of the image displayed
in the Cubeviz cube viewer.

.. _known_issues_imviz:

Imviz
-----

add_markers may not show markers
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

In some OS/browser combinations, ``imviz.add_markers(...)`` might take a few tries
to show the markers, or not at all. This is a known bug reported in
https://github.com/glue-viz/glue-jupyter/issues/243 . If you encounter this,
try a different OS/browser combo.

Simple Aperture Photometry Plugin and dithered images
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Due to a known bug reported in https://github.com/glue-viz/glue-astronomy/issues/52 ,
aperture photometry and radial profile will report inaccurate results when you
calculate them on dithered images linked by WCS *unless* you are on the reference image
(this is usually the first loaded image).

.. _known_issues_specviz:

Specviz
-------

Line List Plugin redshift and radial velocity do not roundtrip to full precision
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Giving a redshift value will report a converted radial velocity, which if entered manually will not 
convert to the exact same redshift value.  Note that the redshift value is always treated as the
true value and used when plotting lines, etc.
