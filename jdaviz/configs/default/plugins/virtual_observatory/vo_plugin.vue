<template>
  <j-tray-plugin
    description='Download a data product from the Virtual Observatory'
    :link="'https://www.ivoa.net/astronomers/index.html'"
    :popout_button="popout_button">

    <j-plugin-section-header>Survey Collections</j-plugin-section-header>
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
      </v-row>

    <j-plugin-section-header>Source Selection</j-plugin-section-header>

      <v-row>
          <v-text-field
          v-model="source"
          label="Source or Coordinates"
          hint="Enter a source name or ICRS coordinates in degrees to center your query on"
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

    <v-row class="row-no-outside-padding">
        <v-col>
            <v-btn color="primary" :loading="results_loading" text @click="query_resource">Query Archive</v-btn>
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