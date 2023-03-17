<template>
  <j-tray-plugin
    description='Histogram of selected data shown in viewer. Pop it out to see full plot.'
    :link="'https://jdaviz.readthedocs.io/en/'+vdocs+'/'+config+'/plugins.html#histogram'"
    :popout_button="popout_button">

     <plugin-viewer-select
       :items="viewer_items"
       :selected.sync="viewer_selected"
       label="Viewer"
       :show_if_single_entry="false"
       hint="Select a viewer to search."
     />

    <plugin-dataset-select
      :items="dataset_items"
      :selected.sync="dataset_selected"
      :show_if_single_entry="false"
      label="Data"
      hint="Select the data set."
    />

    <v-row justify="end">
      <v-btn color="primary" text @click="plot_histogram">Plot</v-btn>
    </v-row>

    <v-row v-if="plot_available">
      <!-- NOTE: the internal bqplot widget defaults to 480 pixels, so if choosing something else,
           we will likely need to override that with custom CSS rules in order to avoid the initial
           rendering of the plot from overlapping with content below -->
      <jupyter-widget :widget="histogram" style="width: 100%; height: 480px" />
    </v-row>

  </j-tray-plugin>
</template>
