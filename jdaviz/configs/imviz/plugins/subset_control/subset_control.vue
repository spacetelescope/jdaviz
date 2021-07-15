<template><v-card flat tile>
  <v-card-text>
    <v-container>
      <v-row>
        <v-col>
          <v-select
            :items="subset_items"
            @change="subset_selected"
            label="Subset"
            hint="Select the Subset to be modified."
            persistent-hint
          ></v-select>
        </v-col>
      </v-row>
    </v-container>
  </v-card-text>
  <v-divider></v-divider>

  <v-card-text>
    <v-container>
      <v-row>
        <v-col>
          <v-text-field
            ref="new_subset_angle"
            label="New Angle"
            v-model="new_subset_angle"
            v-show="has_subset_angle"
            hint="New angle in degrees for subset."
            persistent-hint
          ></v-text-field>
        </v-col>
      </v-row>
      <v-row>
        <v-col>
          <v-text-field
            ref="new_subset_x"
            label="New X"
            v-model="new_subset_x"
            hint="New 0-indexed X for subset center."
            persistent-hint
          ></v-text-field>
        </v-col>
      </v-row>
      <v-row>
        <v-col>
          <v-text-field
            ref="new_subset_y"
            label="New Y"
            v-model="new_subset_y"
            hint="New 0-indexed Y for subset center."
            persistent-hint
          ></v-text-field>
        </v-col>
      </v-row>
      <v-row justify="end">
        <v-btn color="primary" text @click="update_subset">Apply</v-btn>
      </v-row>
    </v-container>
  </v-card-text>
</v-card></template>
