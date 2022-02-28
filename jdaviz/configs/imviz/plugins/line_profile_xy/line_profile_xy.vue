<template>
  <j-tray-plugin>
    <v-row>
      <j-docs-link :link="'https://jdaviz.readthedocs.io/en/'+vdocs+'/'+config+'/plugins.html#line-profiles'">
        Plot line profiles across X and Y under cursor.
      </j-docs-link>
    </v-row>

    <v-row>
      <v-select
        :items="viewer_items"
        v-model="selected_viewer"
        label="Viewer"
        hint="Select a viewer to plot."
        persistent-hint
      ></v-select>
    </v-row>

    <v-row v-if="plot_available">
      <!-- NOTE: the internal bqplot widget defaults to 480 pixels, so if choosing something else,
           we will likely need to override that with custom CSS rules in order to avoid the initial
           rendering of the plot from overlapping with content below -->
      <jupyter-widget :widget="line_plot_across_x" style="width: 100%; height: 480px" />
      <br/>
      <jupyter-widget :widget="line_plot_across_y" style="width: 100%; height: 480px" />
    </v-row>

  </j-tray-plugin>
</template>
