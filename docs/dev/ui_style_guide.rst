*****************
UI/UX Style Guide
*****************

.. include:: ../_templates/deprecated_config_banner.rst

Tray Plugins
------------

In order to be consistent with layout, styling, and spacing, UI development on plugins should
try to adhere to the following principles:

* CSS intended to be applied app-wide should live in ``main_styles.vue`` so that they are available
  to all popout instances via ``PopoutStyleWrapper`` (exists on anything that inherits ``TemplateMixin``).
* Any tray plugin should utilize ``<j-tray-plugin :disabled_msg='disabled_msg' :popout_button="popout_button" :scroll_to.sync="scroll_to">`` as the
  outer-container (which provides consistent styling rules).  If the plugin makes use of active status
  (live-preview marks or viewer callbacks), then also pass ``:uses_active_status="uses_active_status" @plugin-ping="plugin_ping($event)"``.
  To enable the "Keep active" check, pass ``:uses_active_status="uses_active_status" @plugin-ping="plugin_ping($event)" :keep_active.sync="keep_active"``.
  Any changes to style across all plugins should then take place in the
  ``j-tray-plugin`` stylesheet (``jdaviz/components/tray_plugin.vue``).
* ``disabled_msg`` should be set to replace the UI with a message explaining why the plugin is disabled.
  ``irrelevant_msg`` should be set to skip the plugin in the UI entirely where the user would not need an explanation
  (for example, when cube data is not present, the slice plugin is irrelevant).
* Each item should be wrapped in a ``v-row``, but avoid any unnecessary additional wrapping-components
  (``v-card-*``, ``v-container``, etc).
* Only use ``v-col`` components (within a ``<v-row class="row-no-outside-padding">``) if multiple
  components are necessary in a single row.  Always emphasize readability at the default/minimum
  width of the plugin tray, rather than using columns that result in a ton of text overflow.
* Use ``<v-row justify="end">`` to align content to the right (such as action buttons).
* Action buttons should use ``<plugin-action-button :results_isolated_to_plugin="true/false">text</plugin-action-button>``
  to control the color depending on whether the button affects things outside the plugin itself
  (adding/modifying data collection or subset entries, etc) or are isolated to within the plugin
  (adding model components in model fitting, etc).  These buttons can be wrapped in tooltip components
  and also have the capability of adding spinners (by passing a traitlet to ``:spinner``) or disabling
  (by passing a traitlet to ``:disabled``).
* To remove vertical padding from rows (i.e., two successive buttons stacked vertically), use
  ``<v-row class="row-min-bottom-padding">``.
* Use new ``<j-plugin-section-header>Header Text</j-plugin-section-header>`` to separate content
  within a plugin (instead of nested cards, ``v-card-subtitle``, etc).
* Plugin settings should use ``<v-expansion-panels popout>`` immediately at the top of the plugin.
  Optional "sections" of a plugin or editing dynamically-created components should use
  ``<v-expansion-panels accordion>`` to make most use of horizontal and vertical space.
* Number entries should use a ``<v-text-field type="number" v-model.number="traitlet_name">`` component
  *unless* requiring support for scientific notation (in which case
  ``<v-text-field @change="python_method">`` can be used with stripping invalid characters and
  type-casting in python).  To handle emptying the input component without raising a traceback,
  use an ``IntHandleEmpty`` or ``FloatHandleEmpty`` traitlet instead, along with form-validation
  (see below) and/or checks on the python-side to handle the case of an empty string.
* Use form validation wherever possible, and disable action buttons if the relevant validation
  does not pass.  This is preferred to raising errors through snackbars after pressing an action
  button. To do this, wrap the relevant section in a ``<v-form v-model="form_valid_section_name">``,
  create a ``form_valid_section_name = Bool(False).tag(sync=True)`` in the python class for the
  plugin, add rules to any relevant inputs, and set ``:disabled="!form_valid_section_name"`` to any
  action buttons.
* When validation requires checking multiple inputs simultaneously, the validation error message
  can be displayed as its own element using ``<v-row v-if="condition"><span class="v-messages v-messages__message text--secondary">
  <b style="color: red !important">WARNING:</b> warning message</span></v-row>``.
  This should be positioned where the error makes most sense in the flow of the input elements
  and/or immediately above the action button to explain why it is disabled.
  For warnings/errors that require more attention, use a ``<v-alert>`` instead.
* Select input elements should default whenever possible (not start as empty), and self-hide if only
  one valid option. Whenever possible, inputs should use form validation rules with red text
  explaining the error and disabling action buttons. When one selection/check makes others
  contextually irrelevant, those irrelevant items should be hidden entirely.  When order needs to be
  enforced, future inputs should be hidden.
* Re-usable components should be implemented in ``template_mixin.py`` by inheriting from
  ``BasePluginComponent`` along with an accompanying mixin and vue template file in
  ``jdaviz/components`` (which in turn are made available through ``ipyvue.register_component_from_file``
  calls in ``app.py``.  These components allow the traitlets to live in the plugin-level so they
  can easily be observed, and separating per-component logic from the plugin logic itself.

UI/UX Example Code
~~~~~~~~~~~~~~~~~~~~~~~~

.. code::

    <template>
      <j-tray-plugin
        :description="docs_description || 'Plugin description.'"
        :link="docs_link || 'https://jdaviz.readthedocs.io/en/'+vdocs+'/'+config+'/plugins.html#plugin-name'"
        :irrelevant_msg="irrelevant_msg"
        :disabled_msg="disabled_msg"
        :uses_active_status="uses_active_status"
        @plugin-ping="plugin_ping($event)"
        :keep_active.sync="keep_active"
        :popout_button="popout_button"
        :scroll_to.sync="scroll_to">

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

          <v-row justify="end">
            <plugin-action-button
              :results_isolated_to_plugin="false"
              :disabled="!form_valid"
              @click="(e) => {add_model(e); validate()}"
              >Action Text
            </plugin-action-button>
          </v-row>
        </v-form>
      </j-tray-plugin>
    </template>
