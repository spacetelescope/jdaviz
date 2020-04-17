<template>
  <v-dialog v-model="dialog" persistent max-width="600" @keydown.stop="">
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
                persistent-hint
              ></v-select>
            </v-col>
        </v-container>
      </v-card-text>
      <v-divider></v-divider>

      <v-card-text>
        <v-container>
          <v-row
          align="start"
          >
            <v-col>
              <v-select
                :items="available_models"
                @change="model_selected"
                label="Model"
                hint="Select a model to fit"
                persistent-hint
              ></v-select>
            </v-col>
            <v-col>
            <v-text-field
              label="Model ID"
              v-model="temp_name"
              hint="A unique ID for this component model"
              persistent-hint
              :rules="[() => !!temp_name || 'This field is required']"
            >
            </v-text-field>
            </v-col>
          </v-row>
          <v-row
          justify="end">
            <v-btn color="primary" text @click="add_model">Add Model</v-btn>
          </v-row>
        </v-container>
      </v-card-text>
      <v-divider></v-divider>

      <v-card-subtitle>Model Parameters<v-card-subtitle>
      <v-expansion-panels>
        <v-expansion-panel
          v-for="item in component_models" :key="item.id"
        >
          <v-expansion-panel-header>
            <v-row n-gutters>
              <v-col cols="4">{{ item.id }}</v-col>
              <v-col cols="8" class="text--secondary">
                <v-fade-transition leave-absolute>
                  <v-row 
                    no-gutters 
                    style="width: 100%"
                  >
                    <v-col cols="6">
                      This is a test!
                    </v-col>
                  </v-row>
                </v-fade-transition>
              </v-col>
            </v-row>
          </v-expansion-panel-header>
          <v-expansion-panel-content>
            <v-row
              justify="space-around"
              no-gutters
              v-for="param in item.parameters"
            >
              <v-col>
                {{ param.name }}
              </v-col>
            </v-row>
          </v-expansion-panel-content>
        </v-expansion-panel>
      </v-expansion-panels>
      <v-divider></v-divider>

      <v-card-actions>
        <div class="flex-grow-1"></div>
        <v-btn color="primary" text @click="dialog = false">Cancel</v-btn>
        <v-btn color="primary" text @click="model_fitting">Fit</v-btn>
      </v-card-actions>
    </v-card>
  </v-dialog>
</template>
