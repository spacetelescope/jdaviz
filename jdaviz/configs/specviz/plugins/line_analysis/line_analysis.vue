<template>
  <v-card flat tile>
    <v-card>
      <v-card-text>
        <v-container>
          <v-row>
            <v-col>
              <v-select
                :items="dc_items"
                @change="data_selected"
                label="Data"
                hint="Select the data set to be fitted."
                persistent-hint
              ></v-select>
            </v-col>
          </v-row>
        </v-container>
      </v-card-text>
      <v-divider></v-divider>

      <v-card-text>
        <v-container>
          <v-row
          align="start"
          justify="center"
          >
            <v-col cols=8>
              <v-select
                :items="available_functions"
                @change="function_selected"
                label="Function"
                hint="Select a function to apply"
                persistent-hint
              ></v-select>
            </v-col>
            <v-col cols = 2>
              <v-btn color="primary" text @click="run_function">Run</v-btn>
            </v-col>
          </v-row>
          <v-row v-if="result_available">
            <v-col cols=4>Result: </v-col>
            <v-col cols=8>{{ result }}</v-col>
          </v-row>
        </v-container>
      </v-card-text>
      <v-divider></v-divider>
    </v-card>
  </v-card>
</template>
