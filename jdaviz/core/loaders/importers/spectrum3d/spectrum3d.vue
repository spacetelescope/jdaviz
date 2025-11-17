<template>
  <v-container>
    <j-plugin-section-header>Flux Cube</j-plugin-section-header>
    <plugin-select
      :items="extension_items.map(i => i.label)"
      :selected.sync="extension_selected"
      :show_if_single_entry="true"
      label="Extension"
      api_hint="ldr.importer.extension ="
      :api_hints_enabled="api_hints_enabled"
      hint="Extension from the FITS HDUList to use for the flux/science cube."
    />
    <plugin-auto-label
      :value.sync="data_label_value"
      :default="data_label_default"
      :auto.sync="data_label_auto"
      :invalid_msg="data_label_invalid_msg"
      label="Data Label"
      api_hint="ldr.importer.data_label ="
      :api_hints_enabled="api_hints_enabled"
      hint="Label to assign to the new flux/science cube data entry."
    ></plugin-auto-label>

    <plugin-viewer-create-new
      :items="viewer_items"
      :selected.sync="viewer_selected"
      :create_new_items="viewer_create_new_items"
      :create_new_selected.sync="viewer_create_new_selected"
      :new_label_value.sync="viewer_label_value"
      :new_label_default="viewer_label_default"
      :new_label_auto.sync="viewer_label_auto"
      :new_label_invalid_msg="viewer_label_invalid_msg"
      :multiselect="viewer_multiselect"
      :show_multiselect_toggle="false"
      label="Viewer for Flux Cube"
      api_hint="ldr.importer.viewer ="
      :api_hints_enabled="api_hints_enabled"
      :show_if_single_entry="true"
      hint="Select the viewer to use for the imported flux/science cube."
    ></plugin-viewer-create-new>

    <div v-if="unc_extension_items.length >= 1">
      <j-plugin-section-header>Uncertainty Cube</j-plugin-section-header>
      <plugin-select
        :items="unc_extension_items.map(i => i.label)"
        :selected.sync="unc_extension_selected"
        :show_if_single_entry="true"
        label="Uncertainty Extension"
        api_hint="ldr.importer.unc_extension ="
        :api_hints_enabled="api_hints_enabled"
        hint="Extension from the FITS HDUList to use for the uncertainty cube."
      />
      <div v-if="unc_extension_selected !== 'None'">
        <plugin-auto-label
          :value.sync="unc_data_label_value"
          :default="unc_data_label_default"
          :auto.sync="unc_data_label_auto"
          :invalid_msg="unc_data_label_invalid_msg"
          label="Data Label for the Uncertainty Cube"
          api_hint="ldr.importer.unc_data_label ="
          :api_hints_enabled="api_hints_enabled"
          hint="Label to assign to the new uncertainty cube data entry."
        ></plugin-auto-label>

        <plugin-viewer-create-new
          :items="unc_viewer_items"
          :selected.sync="unc_viewer_selected"
          :create_new_items="unc_viewer_create_new_items"
          :create_new_selected.sync="unc_viewer_create_new_selected"
          :new_label_value.sync="unc_viewer_label_value"
          :new_label_default="unc_viewer_label_default"
          :new_label_auto.sync="unc_viewer_label_auto"
          :new_label_invalid_msg="unc_viewer_label_invalid_msg"
          :multiselect="unc_viewer_multiselect"
          :show_multiselect_toggle="false"
          label="Viewer for Uncertainty Cube"
          api_hint="ldr.importer.unc_viewer = "
          :api_hints_enabled="api_hints_enabled"
          :show_if_single_entry="true"
          hint="Select the viewer to use for the imported uncertainty cube."
        ></plugin-viewer-create-new>
      </div>
    </div>

    <div v-if="mask_extension_items.length >= 1">
      <j-plugin-section-header>Mask Cube</j-plugin-section-header>
      <plugin-select
        :items="mask_extension_items.map(i => i.label)"
        :selected.sync="mask_extension_selected"
        :show_if_single_entry="true"
        label="Mask Extension"
        api_hint="ldr.importer.mask_extension ="
        :api_hints_enabled="api_hints_enabled"
        hint="Extension from the FITS HDUList to use for the mask cube."
      />
      <div v-if="mask_extension_selected !== 'None'">
        <plugin-auto-label
          :value.sync="mask_data_label_value"
          :default="mask_data_label_default"
          :auto.sync="mask_data_label_auto"
          :invalid_msg="mask_data_label_invalid_msg"
          label="Data Label for the Mask Cube"
          api_hint="ldr.importer.mask_data_label ="
          :api_hints_enabled="api_hints_enabled"
          hint="Label to assign to the new mask cube data entry."
        ></plugin-auto-label>

        <plugin-viewer-create-new
          :items="mask_viewer_items"
          :selected.sync="mask_viewer_selected"
          :create_new_items="mask_viewer_create_new_items"
          :create_new_selected.sync="mask_viewer_create_new_selected"
          :new_label_value.sync="mask_viewer_label_value"
          :new_label_default="mask_viewer_label_default"
          :new_label_auto.sync="mask_viewer_label_auto"
          :new_label_invalid_msg="mask_viewer_label_invalid_msg"
          :multiselect="mask_viewer_multiselect"
          :show_multiselect_toggle="false"
          label="Viewer for Mask Cube"
          api_hint="ldr.importer.mask_viewer ="
          :api_hints_enabled="api_hints_enabled"
          :show_if_single_entry="true"
          hint="Select the viewer to use for the imported mask cube."
        ></plugin-viewer-create-new>
      </div>
    </div>

    <j-plugin-section-header>Extracted Spectrum</j-plugin-section-header>
    <plugin-switch
      :value.sync="auto_extract"
      label="Extract 1D Spectrum"
      api_hint="ldr.importer.auto_extract ="
      :api_hints_enabled="api_hints_enabled"
      hint="Extract a 1D spectrum from the entire cube (use the 3D Spectral Extraction Plugin after importing to extract for a particular spatial subset)."
    ></plugin-switch>
    <div v-if="auto_extract">
      <plugin-select
        :items="function_items.map(i => i.label)"
        :selected.sync="function_selected"
        label="Function"
        api_hint="ldr.importer.function ="
        :api_hints_enabled="api_hints_enabled"
        hint="Select the function to apply to the extracted 1D Spectrum."
      ></plugin-select>

      <plugin-auto-label
        :value.sync="ext_data_label_value"
        :default="ext_data_label_default"
        :auto.sync="ext_data_label_auto"
        :invalid_msg="ext_data_label_invalid_msg"
        label="Extracted 1D Spectrum Data Label"
        api_hint="ldr.importer.ext_data_label ="
        :api_hints_enabled="api_hints_enabled"
        hint="Label to assign to the auto-extracted 1D Spectrum."
      ></plugin-auto-label>

      <plugin-viewer-create-new
        :items="ext_viewer_items"
        :selected.sync="ext_viewer_selected"
        :create_new_items="ext_viewer_create_new_items"
        :create_new_selected.sync="ext_viewer_create_new_selected"
        :new_label_value.sync="ext_viewer_label_value"
        :new_label_default="ext_viewer_label_default"
        :new_label_auto.sync="ext_viewer_label_auto"
        :new_label_invalid_msg="ext_viewer_label_invalid_msg"
        :multiselect="ext_viewer_multiselect"
        :show_multiselect_toggle="false"
        label="Viewer for Extracted Spectrum"
        api_hint="ldr.importer.ext_viewer ="
        :api_hints_enabled="api_hints_enabled"
        :show_if_single_entry="true"
        hint="Select the viewer to use for the new extracted 1D Spectrum data entry."
      ></plugin-viewer-create-new>
    </div>

    <v-row justify="end">
      <plugin-action-button
        :spinner="import_spinner"
        :disabled="import_disabled"
        :results_isolated_to_plugin="false"
        :api_hints_enabled="api_hints_enabled"
        @click="import_clicked">
        {{ api_hints_enabled ?
          'ldr.load()'
          :
          'Import'
        }}
      </plugin-action-button>
    </v-row>
  </v-container>
</template>