****************
Displaying Cubes
****************

The Cubeviz layout includes three image viewers (at the top of the app)
and one spectrum viewer (at the bottom of the app), which it attempts to 
populate automatically when the first dataset is loaded. By default, cubeviz
attempts to parse and display the flux in the top left viewer, the uncertainty
in the top middle viewer, and the mask into the top right viewer. The spectrum
viewer is populated by default by collapsing the spatial axes using the `max`
function. The indicators that the load machinery looks for in each HDU to 
populate the viewers are below (note that in all cases, header values are
converted to lower case):

    - Flux viewer: `hdu.name` is in the set `['flux', 'sci']`
    - Uncertainty viewer: `hdu.header.keys()` includes "errtype" or `hdu.name` 
      is in the set `['ivar', 'err', 'var', 'uncert']`
    - Mask viewer: `hdu.data.dtype` is `np.int`, `np.uint` or `np.uint32`, or
      `hdu.name` is in the set `['mask', 'dq']`

If any viewer fails to populate automatically, or if displaying 
different data is desired, the user can manually select data for each viewer
as described in the next section. Different statistics for collapsing the 
spectrum displayed in the spectrum viewer can be chosen as described in 
:ref:`Display Settings<display-settings>`. Note that any spatial subsets will 
also be collapsed into a spectrum using the same statistic and displayed in 
the spectrum viewer along with the spectrum resulting from collapsing all the
data in each spectral slice.


Selecting Data Set
==================

More words...

Changing Wavelength Slice
=========================

Defining and Selecting Region Subsets
=====================================

Pan/Zoom
========

More words...

Defining Spectral Regions
=========================

More words...

.. _display-settings:

Display Settings
================

More words...
