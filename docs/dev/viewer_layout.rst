Viewer layout
=============

Viewer docking is implemented in ``jdaviz/components/viewer_layout.vue``,
registered as ``j-viewer-layout``. The component renders tabs, splits, splitters,
and the maximize control, and keeps every viewer widget mounted in a flat layer
keyed by viewer ID. Moving a tab changes where its widget is placed, not the
widget itself.

The application owns two pieces of state: ``state.viewer_items``, the flat list of
live viewers with their labels, widget references, and close policy, and
``state.viewer_layout``, the placement tree described below.

Configuration
-------------

Configuration files are unchanged. ``viewer_area`` is a list of containers with
inline viewer specifications::

    viewer_area:
      - container: col
        children:
          - container: row
            viewers:
              - name: Image
                plot: imviz-image-viewer
                reference: image-viewer
              - name: Comparison
                plot: imviz-image-viewer
                reference: comparison-viewer

``row`` places viewers side by side, ``col`` stacks them vertically, and ``stack``
shows them as tabs; a ``stack`` with ``children`` is treated as a column. Multiple
top-level containers are shown in a row. A container's own viewers are created
before its children and displayed after them, as before.

Layout state
------------

The application translates the configuration into ``state.viewer_layout``, which
replaces ``stack_items`` and ``golden_layout_state``. It holds ``version: 1`` and
a ``root`` node, or ``root: null`` for an empty area:

* ``row`` and ``column`` nodes have ordered ``children`` with relative ``weight``
  values that sum to one;
* ``stack`` nodes have an ordered list of viewer IDs in ``viewers`` and an
  ``activeViewerId``.

An optional ``maximizedViewerId`` names the maximized stack's active tab.
``core/viewer_layout.py`` validates a layout against the live viewer IDs, fills
defaults, normalizes weights, prunes empty nodes, and collapses single-child
splits. It also implements adding, removing, and renaming viewers. A new viewer
is appended below the existing layout in configurations with loaders and beside
it otherwise; the top-level split returns to equal shares while nested splits
keep their proportions. Renaming a viewer with ``update_id=True`` updates the
layout as well.

The layout stays in sync for the lifetime of the kernel, including when the
frontend is remounted. It is not persisted across kernel restarts.

Controls
--------

Tabs are selected by clicking or with Left, Right, Home, and End. Dragging a tab
onto a header reorders or joins tabs, onto the middle of a pane joins that stack,
and onto a pane edge or an outer edge of the layout splits it; Escape or dropping
outside the layout cancels. Splitters are dragged or moved with the arrow keys.
Panes have a 50 pixel minimum that shrinks in small containers without changing
the stored weights. Closing or moving the active tab selects its previous
neighbour, or the next one for the first tab. Tabs that do not fit scroll
horizontally, viewers with ``closable: false`` have no close control, and dragging a
tab out of a maximized stack restores the layout. Configurations with
``tab_headers: false`` render panes without headers, so tabs and the maximize
control are unavailable there.

Synchronization with Python
---------------------------

The browser applies an edit immediately and publishes the normalized layout.
Python validates it against the live viewers and stores it, which echoes it back.
An echo of an edit the browser has already applied does not rewind newer local
edits. When Python rejects an edit it increments ``viewer_layout_reset``, which
makes the browser roll back even if the accepted layout did not change.

A close request from the browser carries the post-close layout, so layout and
viewer registry change together; it is refused for protected viewers. The
ID-based removal API can also remove protected viewers, through the same
operation. Plots follow their pane size through bqplot's own resize observers;
the layout sends no resize events.

Dragging or closing a whole stack and floating windows are not implemented. The
outer application panels still use splitpanes, and the popout tools are
independent of docking.

Testing
-------

Python layout and application tests live in ``jdaviz/core/tests/test_viewer_layout*.py``.
The native component's unit and browser tests live in ``tests/frontend``; see its
README for commands. ``tests/integration`` contains a real-widget fixture and
browser smoke checks for Solara and JupyterLab, including resize/reveal, focus,
same-kernel remount, and JupyterLab popout. Its README describes setup and the
limits of the notebook content-visibility check.
