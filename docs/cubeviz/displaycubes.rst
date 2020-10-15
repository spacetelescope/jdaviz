.. _cubeviz-display-cubes:

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

.. _cubeviz-selecting-data:

Selecting Data Set
==================

The data to be displayed in each viewer can be selected and de-selected by 
clicking on the :guilabel:`hammer and screwdriver` icon at the top left of each viewer. 
Then, click the :guilabel:`gear` icon to access the :guilabel:`Data` tab. Here, 
you can click the checkbox next to each listed dataset to make that dataset 
visible (checked) or invisible (unchecked).

 .. image:: img/data_tab_with_2_data.png

Changing Wavelength Slice
=========================

Coming soon

Defining and Selecting Region Subsets
=====================================

Coming soon

Pan/Zoom
========

Coming soon

Defining Spectral Regions
=========================

Coming soon

.. _display-settings:

Display Settings
================

Coming soon
