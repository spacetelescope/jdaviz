<template>
  <v-dialog v-model="dialog" persistent max-width="450">
    <template v-slot:activator="{ on }">
      <v-btn v-on="on" icon>
        <v-icon>adjust</v-icon>
      </v-btn>
    </template>

    <v-form>
      <v-card>
        <v-card-title class="headline primary" primary-title>Gaussian Smoothing</v-card-title>

        <v-card-text>
          <v-container>
            <v-row>
              <v-col>
                <v-text-field
                  label="Standard Deviation"
                  @change="stddev = $event"
                  hint="The stddev of the kernel, in pixels"
                  persistent-hint
                  outlined
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