<template>
  <j-tray-plugin
    plugin_key="Cross Dispersion Profile"
    :description="docs_description"
    :uses_active_status="uses_active_status"
    :keep_active.sync="keep_active"
    @plugin-ping="plugin_ping($event)"
    :popout_button="popout_button"
    :scroll_to.sync="scroll_to">

    <plugin-dataset-select
      :items="trace_items"
      :selected.sync="trace_selected"
      :show_if_single_entry="true"
      label="Trace"
      hint="Create and export a trace in the Spectral Extraction plugin"
    />

    <j-plugin-section-header v-if="trace_selected != 'Select Trace'">Profile Parameters</j-plugin-section-header>
    <div v-if="trace_selected != 'Select Trace'">

      <v-row>
        <v-col cols="9" style="padding: 0px">
          <v-slider
            :min="0"
            :max="max_pix"
            v-model.number="pixel"
            density="compact"
            hint="Pixel on spectral axis."
            persistent-hint
          >
        </v-col>

        <v-col cols="3" style="padding: 0px">
          <v-text-field
            v-model.number="pixel"
            type="number"
            style="width: 60px"
            label="Pixel"
            hide-details
            dense
            single-line
          />
        </v-col>
      </v-row>

      <plugin-switch
        :value.sync="use_full_width"
        label="Use full cross-dispersion width."
        style="font-size: 10px;"
      />

      <div v-if="!use_full_width">
        <v-text-field
          v-model.number="width"
          type="number"
          dense
          hint="Width of profile window, in pixels."
          persistent-hint
        />
      </div>


    </div>

  </j-tray-plugin>
</template>
