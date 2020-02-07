<template>
  <v-dialog v-model="dialog" persistent max-width="450">
    <template v-slot:activator="{ on: dialog }">
      <v-tooltip bottom>
        <template v-slot:activator="{ on: tooltip }">
          <v-btn v-on="{...tooltip, ...dialog}" icon>
            <v-icon>adjust</v-icon>
          </v-btn>
        </template>
        <span>Gaussian Smooth</span>
      </v-tooltip>
    </template>

    <v-form>
      <v-card>
        <v-card-title class="headline blue lighten-4" primary-title>Gaussian Smoothing</v-card-title>

        <v-card-text>
          <v-container>
            <v-row>
              <v-col>
                <v-select
                  :items="dc_items"
                  @change="data_selected"
                  label="Data"
                  hint="Select the data set to be smoothed."
                ></v-select>
              </v-col>
            </v-row>
            <v-row>
              <v-col>
                <v-text-field
                  ref="stddev"
                  label="Standard deviation"
                  v-model="stddev"
                  hint="The stddev of the kernel, in pixels."
                  persistent-hint
                  :rules="[() => !!stddev || 'This field is required']"
                ></v-text-field>
              </v-col>
            </v-row>
          </v-container>
        </v-card-text>
        <v-divider></v-divider>

        <v-card-actions>
          <div class="flex-grow-1"></div>
          <v-btn color="primary" text @click="dialog = false">Cancel</v-btn>
          <v-btn color="primary" text @click="gaussian_smooth">Apply</v-btn>
        </v-card-actions>
      </v-card>
    </v-form>
  </v-dialog>
</template>