*****************
UI/UX Style Guide
*****************

Tray Plugins
------------

In order to be consistent with layout, styling, and spacing, UI development on plugins should
try to adhere to the following principles:

* Any tray plugin should utilize ``<j-tray-plugin :disabled_msg='disabled_msg'>`` as the 
  outer-container (which provides consistent styling rules).  Any changes to style 
  across all plugins should then take place in the 
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
* Number entries should use a ``<v-text-field type="number" v-model="traitlet_name">`` component 
  *unless* requiring support for scientific notation (in which case 
  ``<v-text-field @change="python_method">`` can be used with stripping invalid characters and
  type-casting in python).  To handle emptying the input component without raising a traceback,
  use an ``IntHandleEmpty`` traitlet instead, along with form-validation (see below) and/or
  checks on the python-side to handle the case of an empty string.
* Use form validation wherever possible, and disable action buttons if the relevant validation
  does not pass.  This is preferred to raising errors through snackbars after pressing an action
  button.  To do this, wrap the relevant section in a ``<v-form v-model="form_valid_section_name">``,
  create a ``form_valid_section_name = Bool(False).tag(sync=True)`` in the python class for the 
  plugin, add rules to any relevant inputs, and set ``:disabled="!form_valid_section_name"`` to any
  action buttons.

.. code::

    <template>
      <j-tray-plugin>
        <v-row>
          <j-docs-link :link="'https://jdaviz.readthedocs.io/en/'+vdocs+'/'+config+'/plugins.html#plugin-name'">Quick overview of plugin functionality.</j-docs-link>
        </v-row>

        <v-row>
          ....
        </v-row>

        <v-form v-model="form_valid">
          <v-row>
            <v-text-field
              label="Label"
              type="number"
              v-model.number="int_handle_empty_traitlet"
              :rules="[() => int_handle_empty_traitlet!=='' || 'This field is required']"
              hint="Hint text."
              persistent-hint
            >
            </v-text-field>
          </v-row>

          <v-row jutify="end">
            <v-btn 
              color="primary" 
              text 
              :disabled="!form_valid"
              @click="(e) => {add_model(e); validate()}"
              >Action Text
            </v-btn>
          </v-row>
        </v-form>
      </j-tray-plugin>
    </template>
