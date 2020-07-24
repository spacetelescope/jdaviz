<template>
  <v-card flat tile>
    <v-container>
      <v-row>
        <v-col class="py-0">
          <v-combobox
            label="Contour on:"
            :items="list_of_viewers"
            v-model="overlayed_viewer"
            hint="Viewer to be overlayed."
            persistent-hint
          ></v-combobox>
        </v-col>
      </v-row>
      <v-row>
        <v-col class="py-0">
          <v-combobox
            label="Contour of:"
            :items="list_of_displays"
            v-model="contour_display"
            hint="Contour to be displayed."
            persistent-hint
          ></v-combobox>
        </v-col>
      </v-row>
      <v-row>
        <v-col class="py-0">
          <v-combobox
            label="Contour type:"
            :items="contour_options"
            v-model="contour_type"
            hint="Type of contour."
            persistent-hint
          ></v-combobox>
        </v-col>
      </v-row>
      <v-row>
        <v-col>
          <v-text-field
            v-model="levels"
            label="Level(s)"
            hint="The level(s) of contouring, separated by commas."
            persistent-hint
          ></v-text-field>
        </v-col>
      </v-row>
      <v-row>
        <v-col>
          <v-text-field
            v-model="slice_index"
            label="Current Slice Number"
            hint="Current slice index."
            persistent-hint
            disabled="True"
          ></v-text-field>
        </v-col>
      </v-row>

      <v-row>
        <v-col>
          <v-checkbox
            v-model="visible"
            label="Visible"
            hint="Contour overlay visibility."
          ></v-checkbox>
        </v-col>
      </v-row>
    </v-container>
    <!-- <v-divider></v-divider> -->

    <v-card-actions>
      <div class="flex-grow-1"></div>
      <v-btn :disabled="levels == ''"
      color="primary" text @click="contour_overlay">Apply</v-btn>
    </v-card-actions>
  </v-card>
</template>
