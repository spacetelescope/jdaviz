<template>
  <j-tray-plugin
    :description="docs_description || 'Plot spectral lines.'"
    :link="docs_link"
    :irrelevant_msg="irrelevant_msg"
    :disabled_msg="disabled_msg"
  >

    <plugin-editable-select
      v-model:mode="component_mode"
      v-model:edit_value="component_edit_value"
      :items="component_items"
      v-model:selected="component_selected"
      label="Component"
      api_hint="plg.component ="
      api_hint_add="plg.component.add_choice"
      api_hint_rename="plg.component.rename_choice"
      api_hint_remove="plg.component.remove_choice"
      :api_hints_enabled="api_hints_enabled"
      hint="Current selected kinematic component. Select or create new to modify."
    ></plugin-editable-select>

    <j-plugin-section-header>Add Spectral Lines to Component</j-plugin-section-header>

    <plugin-loaders-panel
      v-if="!server_is_remote"
      v-model:loader_panel_ind="loader_panel_ind"
      :loader_items="loader_items"
      v-model:loader_selected="loader_selected"
      :api_hints_enabled="api_hints_enabled"
      style="margin-bottom: 12px"
    ></plugin-loaders-panel>

    <j-plugin-section-header>Redshift</j-plugin-section-header>

    <v-row>
      <v-text-field
        v-model.number="component_redshift"
        type="number"
        label="Redshift"
        hint="Redshift of the currently selected component."
        persistent-hint
      ></v-text-field>
    </v-row>

  </j-tray-plugin>
</template>