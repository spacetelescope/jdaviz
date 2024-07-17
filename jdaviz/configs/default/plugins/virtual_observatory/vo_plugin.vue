<template>
  <j-tray-plugin
    description='Download a data product from the Virtual Observatory'
    :link="'https://www.ivoa.net/astronomers/index.html'"
    :popout_button="popout_button">

    <j-plugin-section-header>Source Selection</j-plugin-section-header>

      <plugin-viewer-select
        :items="viewer_items"
        :selected.sync="viewer_selected"
        label="Viewer"
        :show_if_single_entry="true"
        hint="Select a viewer to autofill center coordinates, or Manual for manual coordinate entry."
      />

      <v-row>
        <v-text-field
          v-model="source"
          label="Source or Coordinates"
          hint="Enter a source name or ICRS coordinates in degrees to center your query on"
          :disabled="viewer_selected !== 'Manual'"
          persistent-hint>
        </v-text-field>
      </v-row>

      <v-row>
        <v-select
          v-model="coordframe_selected"
          :menu-props="{ left: true }"
          attach
          :items="coordframes"
          @change="coordframe_selected"
          label="Coordinate Frame"
          hint="Astronomical Coordinate Frame of the provided Coordinates"
          :disabled="viewer_selected !== 'Manual'"
          persistent-hint
        ></v-select>
      </v-row>

    <j-plugin-section-header>Common Options</j-plugin-section-header>

      <v-row>
        <v-text-field
        v-model.number="radius_deg"
        type="number"
        label="Radius"
        hint="Angular radius of the specified field in degrees"
        persistent-hint>
        </v-text-field>
      </v-row>


    <j-plugin-section-header>Survey Collections</j-plugin-section-header>
      <v-row>
        <j-tooltip tipid='plugin-vo-filter-coverage'>
        <span>
          <v-btn icon @click.stop="resource_filter_coverage = !resource_filter_coverage">
            <v-icon>mdi-filter{{ resource_filter_coverage ? '' : '-remove' }}</v-icon>
          </v-btn>
          Filter by Coverage
        </span>
        </j-tooltip>
      </v-row>
      
      <v-row>
        <v-select
          :menu-props="{ left: true }"
          attach
          :items="wavebands"
          @change="waveband_selected"
          label="Resource Waveband"
          hint="Select a spectral waveband to filter your surveys"
          persistent-hint
        ></v-select>
      </v-row>

      <v-row>
        <div class="row-select">
          <v-select
            :menu-props="{ left: true }"
            attach
            :items="resources"
            :loading="resources_loading"
            @change="resource_selected"
            label="Available Resources"
            hint="Select a SIA resource to query"
            persistent-hint
          ></v-select>
        </div>
        <div style="line-height: 64px; width=32px">
          <v-btn
            id="querybtn"
            @click="query_registry_resources"
            icon
            :loading="resources_loading">
            <v-icon>mdi-refresh</v-icon>
          </v-btn>
        </div>
      </v-row>

    <v-row class="row-no-outside-padding">
      <v-col>
        <v-btn
          block
          color="primary"
          :loading="results_loading"
          :disabled="this.resource_selected === null"
          text
          @click="query_resource">Query Archive</v-btn>
      </v-col>
    </v-row>

    <jupyter-widget :widget="table_widget"></jupyter-widget>

    <v-row class="row-no-outside-padding">
        <v-col>
            <v-btn color="primary" :loading="data_loading" text @click="load_selected_data">Load Data</v-btn>
        </v-col>
    </v-row>

  </j-tray-plugin>
</template>