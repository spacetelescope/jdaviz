****************************
Package Release Instructions
****************************

This document outlines the steps for releasing a versioned JDAViz package to PyPI.

This process currently requires high-level access to the JDAViz repository, as it
requires the ability to commit to master directly.

1. Create two commits to master. The first commit should

1. Install the ``twine`` package with::

    $ pip install twine

2. Create a clean environment and install JDAViz. This ensures that the bundle uploaded
   to PyPI is clean and points to the current master.

2. Create a package source distribution bundle. This will be uploaded to PyPI and is
   the self-contained JDAViz package.::

    $ python setup.py
