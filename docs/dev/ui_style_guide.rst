*****************
UI/UX Style Guide
*****************

Tray Plugins
------------

In order to be consistent with layout, styling, and spacing, UI development on plugins should
try to adhere to the following principles:

* Any tray plugin should utilize ``<j-tray-plugin>`` as the outer-container (which provides consistent 
  styling rules).  Any changes to style across all plugins should then take place in the 
  ``j-tray-plugin`` stylesheet (``jdaviz/components/tray_plugin.vue``).
* Each item should be wrapped in a ``v-row``, but avoid any unnecessary additional wrapping-components
  (``v-card-*``, ``v-container``, etc).
* The first entry should be a ``j-docs-link`` component which provides a quick overview of the 
  plugin functionality and a link to the relevant content in the online docs.
* Only use ``v-col`` components (within the ``<v-row class="row-no-outside-padding">``) if multiple 
  components are necessary in a single row.  Always emphasize readability at the default/minimum
  width of the plugin tray, rather than using columns that result in a ton of text overflow.
* Action buttons should have ``color="primary"`` if it loads something into the plugin, or 
  ``color="accent"`` if applying something to the viewers/apps/data.
* To remove vertical padding from rows (i.e., two successive buttons stacked vertically), use 
  ``<v-row class="row-min-bottom-padding">``.
* Use ``<v-row justify="end">`` to align content to the right (such as action buttons).
* Use new ``<j-plugin-section-header>Header Text</j-plugin-section-header>`` to separate content 
  within a plugin (instead of nested cards, ``v-card-subtitle``, etc).

.. code::

    <template>
      <j-tray-plugin>
        <v-row>
          <j-docs-link :link="'https://jdaviz.readthedocs.io/en/'+vdocs+'/'+config+'/plugins.html#plugin-name'">Quick overview of plugin functionality.</j-docs-link>
        </v-row>

        <v-row>
          ....
        </v-row>
      </j-tray-plugin>
    </template>
