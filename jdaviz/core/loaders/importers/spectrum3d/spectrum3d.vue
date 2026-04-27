<template>
  <v-container>
    <j-plugin-section-header>Flux Cube</j-plugin-section-header>
    <plugin-select
      :items="extension_items"
      v-model:selected="extension_selected"
      :show_if_single_entry="true"
      :multiselect="multiselect"
      :exists_in_dc="existing_data_in_dc"
      label="Extension"
      api_hint="ldr.importer.extension ="
      :api_hints_enabled="api_hints_enabled"
      hint="Extension from the FITS HDUList to use for the flux/science cube."
    />
    <plugin-auto-label
      v-model:value="data_label_value"
      :default="data_label_default"
      v-model:auto="data_label_auto"
      :invalid_msg="data_label_invalid_msg"
      label="Data Label"
      api_hint="ldr.importer.data_label ="
      :api_hints_enabled="api_hints_enabled"
      hint="Label to assign to the new flux/science cube data entry."
    ></plugin-auto-label>

    <plugin-viewer-create-new
      :items="viewer_items"
      v-model:selected="viewer_selected"
      :create_new_items="viewer_create_new_items"
      v-model:create_new_selected="viewer_create_new_selected"
      v-model:new_label_value="viewer_label_value"
      :new_label_default="viewer_label_default"
      v-model:new_label_auto="viewer_label_auto"
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
        :items="unc_extension_items"
        v-model:selected="unc_extension_selected"
        :show_if_single_entry="true"
        :multiselect="multiselect"
        :nonmultiselect_allow_clear="true"
        :exists_in_dc="existing_data_in_dc"
        label="Uncertainty Extension"
        api_hint="ldr.importer.unc_extension ="
        :api_hints_enabled="api_hints_enabled"
        hint="Extension from the FITS HDUList to use for the uncertainty cube."
      />
      <div v-if="unc_extension_selected.length > 0">
        <plugin-auto-label
          v-model:value="unc_data_label_value"
          :default="unc_data_label_default"
          v-model:auto="unc_data_label_auto"
          :invalid_msg="unc_data_label_invalid_msg"
          label="Data Label for the Uncertainty Cube"
          api_hint="ldr.importer.unc_data_label ="
          :api_hints_enabled="api_hints_enabled"
          hint="Label to assign to the new uncertainty cube data entry."
        ></plugin-auto-label>

        <plugin-viewer-create-new
          :items="unc_viewer_items"
          v-model:selected="unc_viewer_selected"
          :create_new_items="unc_viewer_create_new_items"
          v-model:create_new_selected="unc_viewer_create_new_selected"
          v-model:new_label_value="unc_viewer_label_value"
          :new_label_default="unc_viewer_label_default"
          v-model:new_label_auto="unc_viewer_label_auto"
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
        :items="mask_extension_items"
        v-model:selected="mask_extension_selected"
        :show_if_single_entry="true"
        :multiselect="multiselect"
        :nonmultiselect_allow_clear="true"
        :exists_in_dc="existing_data_in_dc"
        label="Mask Extension"
        api_hint="ldr.importer.mask_extension ="
        :api_hints_enabled="api_hints_enabled"
        hint="Extension from the FITS HDUList to use for the mask cube."
      />
      <div v-if="mask_extension_selected.length > 0">
        <plugin-auto-label
          v-model:value="mask_data_label_value"
          :default="mask_data_label_default"
          v-model:auto="mask_data_label_auto"
          :invalid_msg="mask_data_label_invalid_msg"
          label="Data Label for the Mask Cube"
          api_hint="ldr.importer.mask_data_label ="
          :api_hints_enabled="api_hints_enabled"
          hint="Label to assign to the new mask cube data entry."
        ></plugin-auto-label>

        <plugin-viewer-create-new
          :items="mask_viewer_items"
          v-model:selected="mask_viewer_selected"
          :create_new_items="mask_viewer_create_new_items"
          v-model:create_new_selected="mask_viewer_create_new_selected"
          v-model:new_label_value="mask_viewer_label_value"
          :new_label_default="mask_viewer_label_default"
          v-model:new_label_auto="mask_viewer_label_auto"
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

    <div v-if="dq_extension_items.length >= 1">
      <j-plugin-section-header>DQ (Data Quality) Cube</j-plugin-section-header>
      <plugin-select
        :items="dq_extension_items"
        :selected.sync="dq_extension_selected"
        :show_if_single_entry="true"
        :multiselect="multiselect"
        :nonmultiselect_allow_clear="true"
        :exists_in_dc="existing_data_in_dc"
        label="DQ Extension"
        api_hint="ldr.importer.dq_extension ="
        :api_hints_enabled="api_hints_enabled"
        hint="Extension from the FITS HDUList to use for the data quality cube."
      />
      <div v-if="dq_extension_selected.length > 0">
        <plugin-auto-label
          :value.sync="dq_data_label_value"
          :default="dq_data_label_default"
          :auto.sync="dq_data_label_auto"
          :invalid_msg="dq_data_label_invalid_msg"
          label="Data Label for the DQ Cube"
          api_hint="ldr.importer.dq_data_label ="
          :api_hints_enabled="api_hints_enabled"
          hint="Label to assign to the new DQ cube data entry."
        ></plugin-auto-label>

        <plugin-switch v-if="config == 'deconfigged'"
          :value.sync="dq_add_to_flux_viewer"
          label="Add to Flux Viewer"
          api_hint="ldr.importer.dq_add_to_flux_viewer ="
          :api_hints_enabled="api_hints_enabled"
          hint="Add the DQ cube to the same viewer as the flux cube."
        ></plugin-switch>

        <plugin-viewer-create-new v-if="config === 'cubeviz'"
          :items="dq_viewer_items"
          :selected.sync="dq_viewer_selected"
          :create_new_items="dq_viewer_create_new_items"
          :create_new_selected.sync="dq_viewer_create_new_selected"
          :new_label_value.sync="dq_viewer_label_value"
          :new_label_default="dq_viewer_label_default"
          :new_label_auto.sync="dq_viewer_label_auto"
          :new_label_invalid_msg="dq_viewer_label_invalid_msg"
          :multiselect="dq_viewer_multiselect"
          :show_multiselect_toggle="false"
          label="Viewer for DQ Cube"
          api_hint="ldr.importer.dq_viewer ="
          :api_hints_enabled="api_hints_enabled"
          :show_if_single_entry="true"
          hint="Select the viewer to use for the imported DQ cube."
        ></plugin-viewer-create-new>
      </div>
    </div>

    <j-plugin-section-header>Extracted Spectrum</j-plugin-section-header>
    <plugin-switch
      v-model:value="auto_extract"
      label="Extract 1D Spectrum"
      api_hint="ldr.importer.auto_extract ="
      :api_hints_enabled="api_hints_enabled"
      hint="Extract a 1D spectrum from the entire cube (use the 3D Spectral Extraction Plugin after importing to extract for a particular spatial subset)."
    ></plugin-switch>
    <div v-if="auto_extract">
      <plugin-select
        :items="function_items.map(i => i.label)"
        v-model:selected="function_selected"
        label="Function"
        api_hint="ldr.importer.function ="
        :api_hints_enabled="api_hints_enabled"
        hint="Select the function to apply to the extracted 1D Spectrum."
      ></plugin-select>

      <plugin-auto-label
        v-model:value="ext_data_label_value"
        :default="ext_data_label_default"
        v-model:auto="ext_data_label_auto"
        :invalid_msg="ext_data_label_invalid_msg"
        label="Extracted 1D Spectrum Data Label"
        api_hint="ldr.importer.ext_data_label ="
        :api_hints_enabled="api_hints_enabled"
        hint="Label to assign to the auto-extracted 1D Spectrum."
      ></plugin-auto-label>

      <plugin-viewer-create-new
        :items="ext_viewer_items"
        v-model:selected="ext_viewer_selected"
        :create_new_items="ext_viewer_create_new_items"
        v-model:create_new_selected="ext_viewer_create_new_selected"
        v-model:new_label_value="ext_viewer_label_value"
        :new_label_default="ext_viewer_label_default"
        v-model:new_label_auto="ext_viewer_label_auto"
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

    <loader-import-button
      :spinner="import_spinner"
      :disabled_msg="import_disabled_msg"
      :api_hints_enabled="api_hints_enabled"
      api_hint="ldr.load()"
      :data_label_overwrite="data_label_overwrite"
      @click="import_clicked">
    </loader-import-button>
  </v-container>
</template>