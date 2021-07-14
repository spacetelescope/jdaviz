<template>
  <v-card flat tile>
    <v-container>
      <v-row>
        <v-col>
          <v-text-field
            ref="new_subset_angle"
            label="New Angle"
            v-model="new_subset_angle"
            hint="New angle for subset."
            persistent-hint
            disabled="True"
          ></v-text-field>
        </v-col>
      </v-row>
      <v-row>
        <v-col>
          <v-text-field
            ref="new_subset_x"
            label="New X"
            v-model="new_subset_x"
            hint="New X for subset."
            persistent-hint
            disabled="True"
          ></v-text-field>
        </v-col>
      </v-row>
      <v-row>
        <v-col>
          <v-text-field
            ref="new_subset_y"
            label="New Y"
            v-model="new_subset_y"
            hint="New Y for subset."
            persistent-hint
            disabled="True"
        </v-col>
      </v-row>
    </v-container>
  </v-card>
</template>
