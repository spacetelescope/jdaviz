<template>
  <j-tray-plugin
    :description="docs_description || 'Plot spectral lines.'"
    :link="docs_link"
    :irrelevant_msg="irrelevant_msg"
    :disabled_msg="disabled_msg"

  >

    <j-plugin-section-header>Add Spectral Lines</j-plugin-section-header>

    <plugin-loaders-panel
      v-if="!server_is_remote"
      v-model:loader_panel_ind="loader_panel_ind"
      :loader_items="loader_items"
      v-model:loader_selected="loader_selected"
      :api_hints_enabled="api_hints_enabled"
      :api_hints_obj="api_hints_obj"
      style="margin-bottom: 12px"
    ></plugin-loaders-panel>

    <j-plugin-section-header>Select Component to Modify</j-plugin-section-header>
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

    <j-plugin-section-header>Set Component Redshift</j-plugin-section-header>

    <v-row>
      <v-text-field
        v-model.number="component_redshift"
        type="number"
        step="0.0001"
        min="0"
        label="Redshift"
        hint="Redshift for all lines in the currently selected component."
        persistent-hint
      ></v-text-field>
    </v-row>

    <div v-if="component_lines.length">
      <j-plugin-section-header>Lines in Component</j-plugin-section-header>

      <div v-for="(line, line_ind) in component_lines" :key="line_ind" style="width: 100%">
        <v-row class="row-no-vertical-padding-margin vuetify2" style="margin: 0px">
          <v-col cols=9 style="padding: 0">
            <span class='text--primary' style="overflow-wrap: anywhere; font-size: 16pt; padding-top: 3px;">
              <b>{{ line.linename }}</b>
            </span>
          </v-col>
          <v-col cols=3 align="right" style="padding: 0">
            <v-btn
              :color="line.show ? 'accent' : 'inherit'"
              icon
              variant="text"
              density="compact"
              @click="toggle_line_visibility(line_ind)">
              <v-icon>{{ line.show ? "mdi-eye" : "mdi-eye-off" }}</v-icon>
            </v-btn>
          </v-col>
        </v-row>
        <v-row class="row-min-bottom-padding vuetify2">
          <v-col cols=6 style="padding-bottom: 3px; padding-top: 0px">
            <v-subheader class="pl-0 slider-label" style="height: 16px"><b>Rest</b></v-subheader>
            <v-text-field
              :model-value="line.rest"
              class="mt-0 pt-0"
              density="compact"
              :hint="line.unit"
              persistent-hint
              disabled
            ></v-text-field>
          </v-col>
          <v-col cols=6 style="padding-top: 0px">
            <v-subheader class="pl-0 slider-label" style="height: 16px"><b>Observed</b></v-subheader>
            <v-text-field
              :model-value="line.obs"
              class="mt-0 pt-0"
              density="compact"
              :hint="line.unit"
              persistent-hint
              disabled
            ></v-text-field>
          </v-col>
        </v-row>
      </div>
    </div>

  </j-tray-plugin>
</template>