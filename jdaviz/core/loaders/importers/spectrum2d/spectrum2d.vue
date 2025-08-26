<template>
  <v-container>
    <plugin-select
      v-if="input_hdulist"
      :items="extension_items.map(i => i.label)"
      :selected.sync="extension_selected"
      :show_if_single_entry="true"
      label="Extension"
      api_hint="ldr.extension ="
      :api_hints_enabled="api_hints_enabled"
      hint="Extension to use from the FITS HDUList."
    />
    <plugin-auto-label
      :value.sync="data_label_value"
      :default="data_label_default"
      :auto.sync="data_label_auto"
      :invalid_msg="data_label_invalid_msg"
      label="Data Label"
      api_hint="ldr.importer.data_label ="
      :api_hints_enabled="api_hints_enabled"
      hint="Label to assign to the new data entry."
    ></plugin-auto-label>

    <plugin-viewer-select
      :items="viewer_items"
      :selected.sync="viewer_selected"
      :multiselect="false"
      :show_multiselect_toggle="false"
      label="Viewer"
      api_hint='ldr.importer.viewer = '
      :api_hints_enabled="api_hints_enabled"
      :show_if_single_entry="true"
      hint="Select the viewer to use for the new data entry."
    ></plugin-viewer-select>

    <v-row v-if="viewer_selected === 'Create New...'">
      <plugin-auto-label
        :value.sync="viewer_label_value"
        :default="viewer_label_default"
        :auto.sync="viewer_label_auto"
        :invalid_msg="viewer_label_invalid_msg"
        label="Viewer Label"
        api_hint="ldr.importer.viewer_label ="
        :api_hints_enabled="api_hints_enabled"
        hint="Label to assign to the new viewer."
      ></plugin-auto-label>
    </v-row>

    <plugin-switch
      :value.sync="auto_extract"
      label="Extract 1D Spectrum"
      api_hint="ldr.importer.auto_extract ="
      :api_hints_enabled="api_hints_enabled"
      hint="Extract a 1D spectrum from the 2D data."
    ></plugin-switch>
    <v-row v-if="auto_extract">
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
    </v-row>

    <!-- TODO: options for auto-extracted viewer -->
  </v-container>
</template>