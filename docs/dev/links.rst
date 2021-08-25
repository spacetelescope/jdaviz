***************************
Linking of datasets in glue
***************************

.. note:: The glue documentation includes a page about
          `linking <http://docs.glueviz.org/en/stable/developer_guide/linking.html>`_ but
          it is somewhat out of date - the present page should be considered a
          more up-to-date guide with a focus on links useful to jdaviz.

The 'why' of linking
====================

First, why is linking needed in the first place? Linking in glue is simply a way
to describe the relationship between datasets, with two main goals: to know how
to overplot datasets, and to know how to apply a subset defined in one dataset
(such as a spectral range) to another dataset. Having linking means being able
to show e.g. multiple spectra in the same plot, or multiple images that are
aligned in the same image viewer, or contours on top of an image.

There are various ways of setting up links in glue, but the two main ways that
have been discussed and used in jdaviz are linking by pixel coordinates, and
linking by world coordinates.

Linking by pixel coordinates with an identity link
==================================================

Linking by pixel coordinates with an identity link with a means that glue
considers that the datasets' pixel grids are lined up at that the origins of the
datasets overlap. This means that if one has two images, with shape (32,32) and
(128,128), the (0,0) pixels will overlap, and the (32,32) dataset will be lined
up with the first (32,32) pixels of the larger dataset, starting at the origin.
This is equivalent to the **Match image** mode in DS9.

An example of setting up an identity link in pixel coordinates between two
datasets with equal dimensionality would look like::

    from glue.core.link_helpers import LinkSame

    pix_ids_1 = data1.pixel_component_ids
    pix_ids_2 = data2.pixel_component_ids

    for i in range(data1.ndim):
        data_collection.add_link(LinkSame(pix_ids_1[i], pix_ids_2[i]))

This can also be used to link for example the two spatial dimensions of a
collapsed cube with the original cube, as done in the `cube collapse
functionality <https://github.com/spacetelescope/jdaviz/blob/0553aca6c2e9530d8dff74088e877fc9593c2d3c/jdaviz/configs/default/plugins/collapse/collapse.py#L146-L152>`_
in jdaviz. This linking would then allow e.g. the collapsed dataset to be shown
as contours on top of the original sliced cube.

This is by far the fastest way of linking, but it does rely on the datasets
being exactly lined up pixel-wise. This approach can likely be used in specific
parsers where it is known that the datasets are on the same grid.

Linking by world coordinates
============================

Using LinkSame
--------------

There are two main ways of linking by world coordinates. The first is to do
something similar to how pixel coordinates are linked::

    from glue.core.link_helpers import LinkSame

    world_ids_1 = data1.world_component_ids
    world_ids_2 = data2.world_component_ids

    for i in range(data1.ndim):
        data_collection.add_link(LinkSame(world_ids_1[i], world_ids_2[i]))

or see the `following example <https://github.com/spacetelescope/jdaviz/blob/d296c6312b020897034e9dd1fc58c84a2559efa5/jdaviz/app.py#L241-L260>`_
from jdaviz.

However, this kind of linking is not generally robust because it relies on the
world coordinates *actually* being the same between the two datasets - so it
would fail for two images where one image was in equatorial coordinates and the
other one was in galactic coordinates, because LinkSame would mean that RA was
the *same* as Galactic longitude, which it is not. Likewise, this would result
in e.g. wavelength in one dataset being equated with frequency in another. The
only place this kind of linking could be used is within parsers for specific
data where it is known with certainty that two world coordinates are the same.
But in general, wherever possible I think we should phase out any use of
LinkSame for world coordinates from jdaviz.

Using WCSLink
-------------

A more robust approach for linking datasets by world coordinates is to use the
``WCSLink`` class. Given two datasets, and a list of pixel component IDs to link
in each dataset, this class will set up links between the pixel components by
internally representing the chain of WCS transformations required. As an
example::

    from glue.plugins.wcs_autolinking.wcs_autolinking import WCSLink

    link = WCSLink(data1=data1, data2=data2,
                cids1=data1.pixel_component_ids, cids2=data2.pixel_component_ids)

    data_collection.add_link(link)

will link all pixel axes between the two datasets, taking into account the WCS
of ``data1`` and ``data2``.

Note that this should work with any APE 14-compliant WCS, so could link for
example a FITS WCS to a GWCS instance.

Speeding up WCS links
=====================

In some cases, doing the full WCS transformations can be slow, and may not be
necessary if the two datasets are close to each other or overlap significantly.
For the best performance, it is possible to approximate the WCSLink by a simple
affine transformation between the datasets. This can be done with the
``as_affine_link`` method::

    link = WCSLink(data1=data1, data2=data2,
                   cids1=data1.pixel_component_ids,
                   cids2=data2.pixel_component_ids)

    fast_link = link.as_affine_transform()

    data_collection.add_link(fast_link)

The ``as_affine_link`` method takes a ``tolerance`` argument which defaults
to 1 pixel - if no approximation can be found that transforms all positions in
the image to within that tolerance, an error of type ``NoAffineApproximation``
is returned (this exception is defined in
``glue.plugins.wcs_autolinking.wcs_autolinking``).

I think whenever we use WCSLink in jdaviz we should then use an affine
approximation whenever one can be calculated, as for visualization purposes it
should be good enough (as a side note, I think DS9 uses a similar approach).

Speeding up adding links to the data collection
===============================================

Each time a link, dataset, or component/attribute is added to the data
collection in glue, the link tree is recalculated. This can be prevented by
using the
`WCSLink.delay_link_manager_update <http://docs.glueviz.org/en/latest/api/glue.core.data_collection.DataCollection.html?highlight=delay#glue.core.data_collection.DataCollection.delay_link_manager_update>`_
context manager. Use this around any block that adds multiple datasets to the
data collection, components/attributes to datasets, or links to the data
collection, e.g.::

    with data_collection.delay_link_manager_update():
        for i in range(10):
            data_collection.append(Data(...)) data_collection.add_link(...)

Mixing link types
=================

Glue can handle many different link types in a same session, so for instance if
one had three datasets, two of the datasets could be linked by a ``WCSLink``
while two other datasets could be linked by pixel coordinates. However, the same
two datasets should not be linked both by ``WCSLink`` and pixel coordinates at
the same time as which link takes precedence is not defined.



