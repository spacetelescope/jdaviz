Known Issues
============

On some platforms, install fails due to `vispy`
-----------------------------------------------

The 0.6.4 version of `vispy` fails to build for some combinations of
platform/OS and Python versions.  `vispy` 0.6.5 has resolved this, but a
workaround if you have an older version of vispy is to ensure you have a
compatible version:

  % conda create -n jdaviz python=3.8
  % conda activate jdaviz
  % pip install vispy>=0.6.5
  % pip install jdaviz --no-cache-dir

See `Issue #305 <https://github.com/spacetelescope/jdaviz/issues/305>`_ for
updates on this topic.

Collapse Plugin spectral bounds don't match selected region
-----------------------------------------------------------

Spectral bounds are off in the plugin compared to the spectrum viewer.


Specviz Unit Conversion with subset selected
--------------------------------------------

Trying to convert units with a subset selected in the spectrum viewer results
in error messages, but works when there is no subset selected.

The bug doesn't happen when a subset is selected before the first conversion,
but does happen when a subset is selected after the first conversion and a
second conversion is applied. It doesn't happen when no subset is selected
and successive conversions are applied.


Ghost subsets and models in spectrum viewer
-------------------------------------------

Mysterious extra subsets and models appear in the Specviz spectrum viewer
after fitting a model. Pan/zoom and resize were also used, but it is unclear
if they play a role or not in this bug.


Cubeviz Collapse and Moment Maps: Spectral bounds do not match Region selection
-------------------------------------------------------------------------------

When trying to do a second collapse with the same spectral region, but with
resized bounds: change to Region=None, resize the region, then reselect Region 1,
the region bounds are correct. However, applying Collapse again, it errors out and
the image viewer that contained the intial collapse goes blank.


Flashing display when data is added or removed too quickly
----------------------------------------------------------

If data addition/removal is done too quickly, the front-end can get "desynced" from
the kernel. The stopgap solution for this is to just restart the kernel or restart
jupyter notebook entirely if the bug persists.


Cubeviz cube viewer colormap printed out
----------------------------------------

When changing the colormap in the Cubeviz cube viewer-->Layer-->colormap,
the colormap name is printed in the cell output.


Cubeviz cube viewer contrast changes when collapsing jupyter scroll window
---------------------------------------------------------------------------

In order to see the full Cubeviz app in a Jupyter notebook, one can click on
the side of the cell output to collapse or expand the scrollable window. This
has the unintended consequence of changing the contrast of the image displayed
in the Cubeviz cube viewer.


Gaussian smooth crashes after selecting smoothed data in spectrum viewer
------------------------------------------------------------------------

Attempting to apply the Gaussian Smooth functionality on a spectrum that is
itself the result of a previous application of Gaussian Smooth, results in
an error dump.


Reporting a bug
---------------

You can report a bug in the Jdaviz GitHub issues:

https://github.com/spacetelescope/jdaviz/issues/new
