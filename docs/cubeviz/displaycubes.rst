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

To change the wavelength slice, click and drag the :guilabel:`slider` at the top of the Cubeviz User Interface (UI)
to the left or right in order to get a lower or higher slice number, respectively. Another option is to
click the :guilabel:`circle` that controls the location on the :guilabel:`slider` and use the
:guilabel:`left` or :guilabel:`right` arrow keys on your keyboard to find a slice number with more precision.
A third option is to type a slice number into the :guilabel:`text box` to the right of the :guilabel:`slider`
and press :guilabel:`enter` on your keyboard. A fourth option is to use the :guilabel:`up/down arrows` inside
the :guilabel:`text box` to raise/lower the slice number.

Defining Spatial Regions
========================

Regions can be created by first clicking the :guilabel:`hammer and screwdriver` icon and
selecting either the :guilabel:`rectangular region of interest` icon or the
:guilabel:`circular region of interest` icon, then clicking and dragging (using the mouse) until the
desired region is covered by a colored shape, after which you release the mouse button.
Once you have completed the action of clicking and dragging, there is an opportunity to reposition
the region of interest by clicking on it and moving the region to a different location in the image viewer.
If you are satisfied with the positioning of your region of interest, simply click another part of the
viewer to lock it in place. Once a region is selected, the cube will be collapsed in wavelength space over the region,
and the resulting spectrum will be displayed in the 1d spectrum viewer at the bottom of the UI.

.. image:: img/subset_creation.png

There are other options available for region of interest. At the top of the User Interface,
there is a section that says either "+ No selection (create new)" or "Subset n" where n is an integer
that tells you which Subset is currently selected. To the right of this area, are red circles that allow
you to change the method of region selection. The options are `replace`, `add`, `and`, `xor`, and `remove`.
You can use these options to further adjust the region of interest and adapt it to your use case.

.. seealso::

    `Defining subsets using Glue <http://docs.glueviz.org/en/stable/getting_started/#defining-subsets>`_
        Glueviz documentation on defining and refining subsets. Slightly different UI but same approach.

There are options available in the :guilabel:`Layer` tab to make subsets visible or invisible,
to change their color, and to change their opacity.

.. image:: img/subset_layer_tab.png


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
