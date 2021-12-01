.. _dev_glue_linking:

***************************
Linking of datasets in glue
***************************

.. note:: The glue documentation includes a page about
          `linking <http://docs.glueviz.org/en/stable/developer_guide/linking.html>`_ but
          the present page should be considered a
          more up-to-date guide with a focus on links useful to Jdaviz.

The 'why' of linking
====================

Why is linking needed in the first place? Linking in glue is a way
to describe the relationship between datasets, with two main goals: to know how
to overplot datasets, and to know how to apply a subset defined in one dataset
(such as a spectral range) to another dataset. Having linking means being able
to show, say, multiple spectra in the same plot, or multiple images that are
aligned in the same image viewer, or contours on top of an image.

There are various ways of setting up links in glue, but the two main ways that
have been discussed and used in Jdaviz are linking by pixel coordinates and
by world coordinates (WCS).

.. _link_by_pixel:

Linking by pixel coordinates with an identity link
==================================================

Linking by pixel coordinates with an identity link means that glue
considers that the datasets' pixel grids are lined up at where the origins of the
datasets overlap. This means that if one has two images, with shape (32,32) and
(128,128), the (0,0) pixels will overlap, and the (32,32) dataset will be lined
up with the first (32,32) pixels of the larger dataset, starting at the origin.
This is equivalent to the "match image" mode in DS9.

An example of setting up an identity link in pixel coordinates between two
n-dimensional datasets where n is the same for both datasets would look like::

    from glue.core.link_helpers import LinkSame

    pix_ids_1 = data1.pixel_component_ids
    pix_ids_2 = data2.pixel_component_ids

    links = []
    for i in range(data1.ndim):
        links.append(LinkSame(pix_ids_1[i], pix_ids_2[i]))

    data_collection.add_link(links)

This can also be used to link, for example, the two spatial dimensions of a
collapsed cube with the original cube, as done in the `cube collapse
functionality <https://github.com/spacetelescope/jdaviz/blob/0553aca6c2e9530d8dff74088e877fc9593c2d3c/jdaviz/configs/default/plugins/collapse/collapse.py>`_
in Jdaviz::

    pix_id_1 = self._selected_data.pixel_component_ids[i1]
    pix_id_1c = self.data_collection[label].pixel_component_ids[i1c]
    pix_id_2 = self._selected_data.pixel_component_ids[i2]
    pix_id_2c = self.data_collection[label].pixel_component_ids[i2c]

    self.data_collection.add_link(LinkSame(pix_id_1, pix_id_1c))
    self.data_collection.add_link(LinkSame(pix_id_2, pix_id_2c))

This linking would then allow the collapsed dataset to be shown
as contours on top of the original sliced cube.

This is by far the fastest way of linking, but it does rely on the datasets
being lined up pixel-wise. This approach can be used in specific
parsers where it is known that the datasets are on the same grid.

It is also possible to link all datasets using pixel links, but users will
need to be aware that this then means specific features (such as stars) in
different datasets will not line up when, e.g., blinking, and making a selection
or region of a certain feature will not necessarily select the same feature
in another dataset.

.. _link_by_wcs:

Linking by WCS
==============

There are two main ways of linking by WCS, as follow.

Using WCSLink (recommended)
---------------------------

The more robust approach for linking datasets by WCS is to use the
:class:`~glue.plugins.wcs_autolinking.wcs_autolinking.WCSLink` class. Given two
datasets, and a list of pixel component IDs to link in each dataset, this class
will set up links between the pixel components by internally representing the
chain of WCS transformations required. As an example::

    from glue.plugins.wcs_autolinking.wcs_autolinking import WCSLink

    link = WCSLink(data1=data1, data2=data2,
                   cids1=data1.pixel_component_ids, cids2=data2.pixel_component_ids)

    data_collection.add_link(link)

The example above will link all pixel axes between the two datasets, taking into account the WCS
of ``data1`` and ``data2``.

Note that this should work with any `APE 14 <https://github.com/astropy/astropy-APEs/blob/main/APE14.rst>`_-compliant WCS, so it could link
both a FITS WCS to a GWCS instance, and vice versa.

Using LinkSame (not recommended)
--------------------------------

The first is to do something similar to how pixel coordinates are linked in :ref:`link_by_pixel`::

    from glue.core.link_helpers import LinkSame

    world_ids_1 = data1.world_component_ids
    world_ids_2 = data2.world_component_ids

    links = []
    for i in range(data1.ndim):
        links.append(LinkSame(world_ids_1[i], world_ids_2[i]))

    data_collection.add_link(links)

or see the `following example in app.py <https://github.com/spacetelescope/jdaviz/blob/d296c6312b020897034e9dd1fc58c84a2559efa5/jdaviz/app.py>`_
from Jdaviz::

    def _link_new_data(self):
        """
        When additional data is loaded, check to see if the spectral axis of
        any components are compatible with already loaded data. If so, link
        them so that they can be displayed on the same profile1D plot.
        """
        new_len = len(self.data_collection)
        # Can't link if there's no world_component_ids
        wc_new = self.data_collection[new_len-1].world_component_ids
        if wc_new == []:
            return

        # Link to the first dataset with compatible coordinates
        for i in range(0, new_len-1):
            wc_old = self.data_collection[i].world_component_ids
            if wc_old == []:
                continue
            else:
                self.data_collection.add_link(LinkSame(wc_old[0], wc_new[0]))
                break

However, this kind of linking is not generally robust because it relies on the
WCS *actually* being the same system between the two datasets - so it
would fail for two images where one image was in equatorial coordinates and the
other one galactic coordinates, because LinkSame would mean that RA was
the *same* as Galactic longitude, which it is not. Likewise, this would result
in, say, wavelength in one dataset being equated wrongly with frequency in another. The
only place this kind of linking could be used is within parsers for specific
data where it is known with certainty that two world coordinate systems are the same.

In general, one should avoid using LinkSame for world coordinates in Jdaviz.

Speeding up WCS links
=====================

In some cases, doing the full WCS transformations can be slow, and may not be
necessary if the two datasets are close to each other and have a similar WCS.
For the best performance, it is possible to approximate the
:class:`~glue.plugins.wcs_autolinking.wcs_autolinking.WCSLink` by a simple affine
transformation between the datasets. This can be done with the
:meth:`~glue.plugins.wcs_autolinking.wcs_autolinking.WCSLink.as_affine_link` method::

    link = WCSLink(data1=data1, data2=data2,
                   cids1=data1.pixel_component_ids,
                   cids2=data2.pixel_component_ids)

    fast_link = link.as_affine_link()

    data_collection.add_link(fast_link)

The :meth:`~glue.plugins.wcs_autolinking.wcs_autolinking.WCSLink.as_affine_link`
method takes a ``tolerance`` argument which defaults to 1 pixel - if no
approximation can be found that transforms all positions in the image to within
that tolerance, an error of type :class:`~glue.plugins.wcs_autolinking.wcs_autolinking.NoAffineApproximation` is returned.

It is recommended that whenever :class:`~glue.plugins.wcs_autolinking.wcs_autolinking.WCSLink` is used
in Jdaviz, affine approximation should be used whenever possible.
For visualization purposes, it should be good enough for most cases.
DS9 uses a similar approach.

.. _need_for_link_speed:

Speeding up adding links to the data collection
===============================================

Each time a link, dataset, or component/attribute is added to the data
collection in glue, the link tree is recalculated. Unnecessary recalculations can be prevented by
using the
:meth:`~glue.core.data_collection.DataCollection.delay_link_manager_update`
context manager. Use this around any block that adds multiple datasets to the
data collection, components/attributes to datasets, or links to the data
collection, e.g.::

    with data_collection.delay_link_manager_update():
        for i in range(10):
            data_collection.append(Data(...))
            data_collection.add_link(...)

See `pull request 762 <https://github.com/spacetelescope/jdaviz/pull/762>`_ for a more concrete example.

Setting or resetting all links in one go
========================================

If you want to prepare and set all links in one go, discarding any previous links,
you can make use of the :meth:`~glue.core.data_collection.DataCollection.set_links`
method, which takes a list of links::

    data_collection.set_links([link1, link2, link3])

It is recommended to use this inside the
:meth:`~glue.core.data_collection.DataCollection.delay_link_manager_update`
context manager, as mentioned in :ref:`need_for_link_speed`.

This method is ideal if you want to, say, switch between using pixel and WCS links
as it will discard any existing links before adding the new ones.

This is necessary because the same two datasets cannot have both
pixel and WCS links, as explained in :ref:`link_mixing`.

.. _link_mixing:

Mixing link types
=================

Glue can handle many different link types in a same session. For instance, if
there are three datasets, two of the datasets could be linked by a
:class:`~glue.plugins.wcs_autolinking.wcs_autolinking.WCSLink` while two other
datasets could be linked by pixel coordinates. However, the same two datasets
should not be linked both by :class:`~glue.plugins.wcs_autolinking.wcs_autolinking.WCSLink`
and pixel coordinates at the same time, as which link takes precedence is not
defined, resulting in ambiguous behavior.
