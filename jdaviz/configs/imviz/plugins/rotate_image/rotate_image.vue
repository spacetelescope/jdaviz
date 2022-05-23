<template>
  <j-tray-plugin>
    <v-row>
      <j-docs-link :link="'https://jdaviz.readthedocs.io/en/'+vdocs+'/'+config+'/plugins.html#simple-image-rotation'">Rotate image N-up/E-left.</j-docs-link>
    </v-row>

    <v-row>
      <v-switch
        label="Enable celestial axes rotation"
        hint="Toggle rotation mode on or off"
        v-model="rotate_mode_on"
        persistent-hint>
      </v-switch>
    </v-row>

    <div v-if="rotate_mode_on">
      <plugin-viewer-select
        :items="viewer_items"
        :selected.sync="viewer_selected"
        label="Viewer"
        hint="Select viewer."
      />

      <plugin-dataset-select
        :items="dataset_items"
        :selected.sync="dataset_selected"
        :show_if_single_entry="false"
        label="Data"
        hint="Select the data to rotate."
      />

      <v-row>
        <v-col>
          <v-text-field
            v-model="angle"
            type="number"
            label="Angle"
            hint="Rotation angle of N-axis in degrees clockwise (0 is N-up)"
          ></v-text-field>
        </v-col>
      </v-row>

      <v-row justify="end">
        <v-btn color="primary" text @click="rotate_image">Rotate</v-btn>
      </v-row>
    </div>
  </j-tray-plugin>
</template>
