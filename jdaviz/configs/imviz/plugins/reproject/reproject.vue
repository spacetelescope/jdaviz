<template>
  <j-tray-plugin
    description='Perform reprojection for a single image to align display to celestial axes.'
    :link="'https://jdaviz.readthedocs.io/en/'+vdocs+'/'+config+'/plugins.html#reproject'"
    :disabled_msg="disabled_msg"
    :popout_button="popout_button">

    <plugin-dataset-select
      :items="dataset_items"
      :selected.sync="dataset_selected"
      :show_if_single_entry="false"
      label="Data"
      hint="Select the data for reprojection."
    />

    <div v-if='dataset_selected'>
      <v-row>
        <v-col>
          <v-text-field
            v-model='results_label'
            hint="Data label for reprojected data"
            persistent-hint
          ></v-text-field>
        </v-col>
      </v-row>
      <v-row justify="end">
        <v-btn color="primary" text @click="do_reproject">Reproject</v-btn>
      </v-row>
    </div>

    <div v-if="reproject_in_progress"
         class="text-center"
         style="grid-area: 1/1;
                z-index:2;
                margin-left: -24px;
                margin-right: -24px;
                padding-top: 60px;
                background-color: rgb(0 0 0 / 20%)">
      <v-progress-circular
        indeterminate
        color="spinner"
        size="50"
        width="6"
      ></v-progress-circular>
    </div>
  </j-tray-plugin>
</template>
