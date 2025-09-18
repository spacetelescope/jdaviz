<template>
  <j-viewer-creator
    :title="viewer_type"
    :popout_button="popout_button"
    :dataset_items="dataset_items"
    :dataset_selected.sync="dataset_selected"
    :dataset_multiselect="true"
    :viewer_label_value.sync="viewer_label_value"
    :viewer_label_default="viewer_label_default"
    :viewer_label_auto.sync="viewer_label_auto"
    :viewer_label_invalid_msg="viewer_label_invalid_msg"
    :api_hints_enabled="api_hints_enabled"
    @create-clicked="create_clicked"
  >
    <plugin-select
      :items="xatt_items.map(i => i.label)"
      :selected.sync="xatt_selected"
      :show_if_single_entry="true"
      label="X Attribute"
      api_hint="vc.xatt ="
      :api_hints_enabled="api_hints_enabled"
      hint="Select the attribute for the x-axis."
    ></plugin-select>
    <plugin-select
      :items="yatt_items.map(i => i.label)"
      :selected.sync="yatt_selected"
      :show_if_single_entry="true"
      label="Y Attribute"
      api_hint="vc.yatt ="
      :api_hints_enabled="api_hints_enabled"
      hint="Select the attribute for the y-axis."
    ></plugin-select>
  </j-viewer-creator>
</template>
