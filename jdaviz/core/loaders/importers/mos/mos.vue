<template>
  <v-container>
    <j-flex-row v-if="product_items.length > 0">
      <v-chip v-for="item in product_items"
        :key="item.product_type"
        variant="outlined"
        label
        style="margin: 4px"
      >
        {{ item.count }} &times; {{ item.label }}
      </v-chip>
    </j-flex-row>

    <plugin-auto-label
      v-model:value="data_label_value"
      :default="data_label_default"
      v-model:auto="data_label_auto"
      :invalid_msg="data_label_invalid_msg"
      label="Data Label Prefix"
      api_hint="ldr.importer.data_label ="
      :api_hints_enabled="api_hints_enabled"
      :hint="data_label_is_prefix ? 'Prefix to assign to the new data entry. Will resolve to the following data labels:' : 'Label to assign to the new data entry.'"
    >
    </plugin-auto-label>
    <j-flex-row v-if="data_label_is_prefix">
        <j-tooltip v-for="(suff, index) in data_label_suffices"
          :key="suff"
          :tooltipcontent="data_label_overwrite_by_index[index] ? 'Will overwrite existing entry' : 'New entry'">
          <v-chip
            variant="outlined"
            label
            style="margin: 4px"
          >
            <v-icon v-if="data_label_overwrite_by_index[index]" small left color="warning">mdi-file-replace</v-icon>
            {{data_label_value}}{{suff}}
          </v-chip>
        </j-tooltip>
    </j-flex-row>

    <plugin-viewer-create-new
      :items="viewer_1d_items"
      v-model:selected="viewer_1d_selected"
      :create_new_items="viewer_1d_create_new_items"
      v-model:create_new_selected="viewer_1d_create_new_selected"
      v-model:new_label_value="viewer_1d_label_value"
      :new_label_default="viewer_1d_label_default"
      v-model:new_label_auto="viewer_1d_label_auto"
      :new_label_invalid_msg="viewer_1d_label_invalid_msg"
      :multiselect="viewer_multiselect"
      :show_multiselect_toggle="false"
      label="1D Spectrum Viewer"
      api_hint="ldr.importer.viewer ="
      :api_hints_enabled="api_hints_enabled"
      :show_if_single_entry="true"
      hint="Select the viewer to use for the imported 1D spectra."
    ></plugin-viewer-create-new>

    <plugin-viewer-create-new
      v-if="product_types.includes('spectrum2d')"
      :items="viewer_2d_items"
      v-model:selected="viewer_2d_selected"
      :create_new_items="viewer_2d_create_new_items"
      v-model:create_new_selected="viewer_2d_create_new_selected"
      v-model:new_label_value="viewer_2d_label_value"
      :new_label_default="viewer_2d_label_default"
      v-model:new_label_auto="viewer_2d_label_auto"
      :new_label_invalid_msg="viewer_2d_label_invalid_msg"
      :multiselect="viewer_multiselect"
      :show_multiselect_toggle="false"
      label="2D Spectrum Viewer"
      api_hint="ldr.importer.viewer_2d ="
      :api_hints_enabled="api_hints_enabled"
      :show_if_single_entry="true"
      hint="Select the viewer to use for the imported 2D spectra."
    ></plugin-viewer-create-new>

    <plugin-switch
      v-if="product_types.includes('spectrum2d')"
      v-model:value="auto_extract_2d"
      label="Extract 1D Spectra"
      api_hint="ldr.importer.auto_extract_2d ="
      :api_hints_enabled="api_hints_enabled"
      hint="Extract a 1D spectrum from each imported 2D spectrum."
    ></plugin-switch>

    <plugin-viewer-create-new
      v-if="product_types.includes('image')"
      :items="viewer_image_items"
      v-model:selected="viewer_image_selected"
      :create_new_items="viewer_image_create_new_items"
      v-model:create_new_selected="viewer_image_create_new_selected"
      v-model:new_label_value="viewer_image_label_value"
      :new_label_default="viewer_image_label_default"
      v-model:new_label_auto="viewer_image_label_auto"
      :new_label_invalid_msg="viewer_image_label_invalid_msg"
      :multiselect="viewer_multiselect"
      :show_multiselect_toggle="false"
      label="Image Viewer"
      api_hint="ldr.importer.viewer_image ="
      :api_hints_enabled="api_hints_enabled"
      :show_if_single_entry="true"
      hint="Select the viewer to use for the imported images."
    ></plugin-viewer-create-new>

    <plugin-viewer-create-new
      v-if="product_types.includes('catalog')"
      :items="viewer_catalog_items"
      v-model:selected="viewer_catalog_selected"
      :create_new_items="viewer_catalog_create_new_items"
      v-model:create_new_selected="viewer_catalog_create_new_selected"
      v-model:new_label_value="viewer_catalog_label_value"
      :new_label_default="viewer_catalog_label_default"
      v-model:new_label_auto="viewer_catalog_label_auto"
      :new_label_invalid_msg="viewer_catalog_label_invalid_msg"
      :multiselect="viewer_multiselect"
      :show_multiselect_toggle="false"
      label="Catalog Viewer"
      api_hint="ldr.importer.viewer_catalog ="
      :api_hints_enabled="api_hints_enabled"
      :show_if_single_entry="true"
      hint="Select the viewer to use for the imported catalogs."
    ></plugin-viewer-create-new>

    <loader-import-button
      :spinner="import_spinner"
      :disabled_msg="import_disabled_msg"
      :api_hints_enabled="api_hints_enabled"
      api_hint="ldr.load()"
      :data_label_overwrite="data_label_overwrite"
      :data_label_is_prefix="data_label_is_prefix"
      :data_label_suffices="data_label_suffices"
      :data_label_overwrite_by_index="data_label_overwrite_by_index"
      @click="import_clicked">
    </loader-import-button>

    <j-loader-banner-messages :items="loader_message_items"></j-loader-banner-messages>
  </v-container>
</template>
