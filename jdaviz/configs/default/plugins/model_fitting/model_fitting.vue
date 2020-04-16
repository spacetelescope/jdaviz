<template>
  <v-dialog v-model="dialog" persistent max-width="450" @keydown.stop="">
    <template v-slot:activator="{ on: dialog }">
      <v-tooltip bottom>
        <template v-slot:activator="{ on: tooltip }">
          <v-btn v-on="{...dialog}">
            Model Fitting
          </v-btn>
        </template>
        <span>Model Fitting</span>
      </v-tooltip>
    </template>

    <v-card>
      <v-card-title class="headline blue lighten-4" primary-title>Model Fitting</v-card-title>

      <v-card-text>
        <v-container>
          <v-row>
            <v-col>
              <v-select
                :items="dc_items"
                @change="data_selected"
                label="Data"
                hint="Select the data set to be fitted."
              ></v-select>
            </v-col>
        </v-container>
      </v-card-text>
      <v-divider></v-divider>

      <v-card-text>
        <v-container>
          <v-row>
            <v-col>
              <v-select
                :items="available_models"
                @change="model_selected"
                label="Model"
                hint="Select a model to fit"
              ></v-select>
            </v-col>
            <v-col>
              <v-text-field
                ref="model_name"
                label="Name for model"
                v-model="model_name"
                hint="A unique name for this model, to use in model equation."
                persistent-hint
                :rules="[() => !!model_name || 'This field is required']"
              ></v-text-field>
            </v-col>
          </v-row>
        </v-container>
      </v-card-text>
      <v-divider></v-divider>

      <v-card-actions>
        <div class="flex-grow-1"></div>
        <v-btn color="primary" text @click="dialog = false">Cancel</v-btn>
        <v-btn color="primary" text @click="model_fitting">Fit</v-btn>
      </v-card-actions>
    </v-card>
  </v-dialog>
</template>
