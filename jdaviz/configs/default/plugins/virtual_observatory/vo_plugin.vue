<template>
  <j-tray-plugin
    description='Download a data product from the Virtual Observatory'
    :link="'https://www.ivoa.net/astronomers/index.html'"
    :popout_button="popout_button">
    <v-form v-model="all_fields_filled">

      <j-plugin-section-header>Source Selection</j-plugin-section-header>

      <plugin-viewer-select
        :items="viewer_items"
        :selected.sync="viewer_selected"
        label="Viewer"
        :show_if_single_entry="true"
        hint="Select a viewer to retrieve center coordinates, or Manual for manual coordinate entry."
      />

      <v-row v-if="viewer_selected !== 'Manual'">
        <v-switch
          v-model="coord_follow_viewer_pan"
          label="Follow Viewer Center"
          hint="Automatically adjust coordinates as viewer pans and zooms"
          persistent-hint
        ></v-switch>
      </v-row>

      <v-row>
        <div :style="!(viewer_selected !== 'Manual' && !coord_follow_viewer_pan) ? 'width: 100%' : 'width: calc(100% - 32px)'">
          <v-text-field
            v-model="source"
            label="Source/Coordinates"
            hint="Enter a source name or coordinates in degrees to center your query on"
            :disabled="viewer_selected !== 'Manual'"
            :rules="[() => !!source || 'This field is required']"
            persistent-hint>
          </v-text-field>
        </div>
        <div v-if="viewer_selected !== 'Manual' && !coord_follow_viewer_pan" style="line-height:64px; width:32px">
          <j-tooltip :tipid="viewer_centered ? 'plugin-vo-autocenter-centered' : 'plugin-vo-autocenter-not-centered'">
            <v-btn
              id="autocenterbtn"
              @click="center_on_data"
              :disabled="viewer_centered"
              icon>
              <v-icon>
                {{ viewer_centered ? 'mdi-crosshairs-gps' : 'mdi-crosshairs' }}
              </v-icon>
            </v-btn>
          </j-tooltip>
        </div>
      </v-row>

      <v-row>
        <v-select
          v-model="coordframe_selected"
          :menu-props="{ left: true }"
          attach
          :items="coordframe_choices.map(i => i.label)"
          label="Coordinate Frame"
          hint="Astronomical Coordinate Frame of the provided Coordinates"
          :disabled="viewer_selected !== 'Manual'"
          persistent-hint
        ></v-select>
      </v-row>

      <v-row justify="space-between">
        <div :style="{ width: '55%' }">
          <v-text-field
            v-model.number="radius"
            type="number"
            label="Radius"
            hint="Angular radius around source coordinates, within which to query for data (Default 1 degree)"
            persistent-hint>
          </v-text-field>
        </div>
        <div :style="{ width: '40%' }">
          <v-select
            v-model="radius_unit_selected"
            attach
            :items="radius_unit_items.map(i => i.label)"
            label="Unit">
          </v-select>
        </div>
      </v-row>


    <j-plugin-section-header>Survey Collections</j-plugin-section-header>
      <v-row>
        <j-tooltip tipid='plugin-vo-filter-coverage'>
          <plugin-switch
            :value.sync="resource_filter_coverage"
            label="Filter by Coverage">
          </plugin-switch>
        </j-tooltip>
      </v-row>
      
      <v-row>
        <v-select
          v-model="waveband_selected"
          :menu-props="{ left: true }"
          attach
          :items="waveband_items.map(i => i.label)"
          label="Resource Waveband"
          hint="Select a spectral waveband to filter your surveys"
          persistent-hint
        ></v-select>
      </v-row>

      <v-row>
        <div :style="'width: calc(100% - 32px)'">
          <v-select
            v-model="resource_selected"
            :menu-props="{ left: true }"
            attach
            :items="resource_choices.map(i => i.label)"
            :loading="resources_loading"
            :rules="[() => !!resource_selected || 'This field is required']"
            label="Available Resources"
            hint="Select a SIA resource to query"
            persistent-hint
          ></v-select>
        </div>
        <div style="line-height: 64px; width:32px">
          <j-tooltip tipid='plugin-vo-refresh-resources'>
            <v-btn
              @click="query_registry_resources"
              icon
              :loading="resources_loading">
              <v-icon>mdi-refresh</v-icon>
            </v-btn>
          </j-tooltip>
        </div>
      </v-row>
    </v-form>

    <v-row class="row-no-outside-padding">
      <v-col>
        <plugin-action-button
          :loading="results_loading"
          :disabled="!all_fields_filled"
          @click="query_resource">Query Archive</plugin-action-button>
      </v-col>
    </v-row>

    <jupyter-widget :widget="table_widget"></jupyter-widget>

    <v-row class="row-no-outside-padding">
        <v-col>
          <plugin-action-button
            :loading="data_loading" @click="load_selected_data">Load Data
          </plugin-action-button>
        </v-col>
    </v-row>

  </j-tray-plugin>
</template>

<script>
export default {
  data() {
    return {
      all_fields_filled: false, // Reactive property for form validity
    };
  },
};
</script>
