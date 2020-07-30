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
                hint="A unique string label for this component model"
                persistent-hint
                :rules="[() => !!temp_name || 'This field is required']"
              >
              </v-text-field>
            </v-col>
            <v-col v-if="display_order">
              <v-text-field
                label="Order"
                type="number"
                v-model.number="poly_order"
                hint="Order of polynomial to fit"
                persistent-hint
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

      <v-card-subtitle>Model Parameters</v-card-subtitle>
      <v-card-text>
        <v-container>
        <v-expansion-panels>
          <v-expansion-panel
            v-for="item in component_models" :key="item.id"
          >
            <v-expansion-panel-header v-slot="{ open }">
              <v-row no-gutters>
                <v-col cols=1>
                  <v-btn @click.native.stop="remove_model(item.id)" icon>
                    <v-icon>mdi-close-circle</v-icon>
                  </v-btn>
                </v-col>
                <v-col cols="3">{{ item.id }} ({{ item.model_type }})</v-col>
                <v-col cols="8" class="text--secondary">
                  <v-fade-transition leave-absolute>
                    <span v-if="open">Enter parameters for model initialization</span>
                    <v-row
                      v-else
                      no-gutters
                      style="width: 100%"
                    >
                      <v-col cols="4" v-for="param in item.parameters">
                      {{ param.name }} : {{ param.value }}
                      </v-col>
                    </v-row>
                  </v-fade-transition>
                </v-col>
              </v-row>
            </v-expansion-panel-header>
            <v-expansion-panel-content>
              <v-row
                justify="left"
                align="center"
                no-gutters
              >
                <v-col cols=2>
                  <p class="font-weight-bold">Parameter</p>
                </v-col>
                <v-col cols=3>
                  <p class="font-weight-bold">Value</p>
                </v-col>
                <v-col cols=4>
                  <p class="font-weight-bold">Unit</p>
                </v-col>
                <v-col cols=2>
                  <p class="font-weight-bold">Fixed?</p>
                </v-col>
              </v-row>
              <v-row
                justify="left"
                align="center"
                no-gutters
                v-for="param in item.parameters"
              >
                <v-col cols = 2>
                  {{ param.name }}
                </v-col>
                <v-col cols = 2>
                  <v-text-field
                    v-model="param.value"
                  >
                  </v-text-field>
                </v-col>
                <v-col cols=1></v-col>
                <v-col cols=3>
                  {{ param.unit }}
                </v-col>
                <v-col cols=1></v-col>
                <v-col cols=2>
                  <v-checkbox v-model="param.fixed">
                  </v-checkbox>
                </v-col>
              </v-row>
            </v-expansion-panel-content>
          </v-expansion-panel>
        </v-expansion-panels>
        </v-container>
      </v-card-text>
      <v-divider></v-divider>

      <v-card-subtitle>Model Equation Editor</v-card-subtitle>
      <v-card-text>
        <v-container>
          <v-text-field
            v-model="model_equation"
            hint="Equation specifying how to combine the component models, using their model IDs and basic arithmetic operators"
            persistent-hint
            :rules="[() => !!model_equation || 'This field is required']"
            @change="equation_changed"
            :error="eq_error"
          >
          </v-text-field>
        </v-container>
      </v-card-text>
      <v-divider></v-divider>

      <v-card-actions>
        <div class="flex-grow-1"></div>
        <v-text-field
          v-model="model_label"
          label="Model Label"
          hint="Label for the modeled spectrum in the data dropdown menus"
          persistent-hint
        >
        </v-text-field>
        <c-col cols=1><v-col>
        <v-text-field
          v-model="model_save_path"
          label="Filepath"
          hint="Path to save output file [Model Label].pkl"
          persistent-hint
        >
        </v-text-field>
      </v-card-actions>
      <v-card-actions>
        <div class="flex-grow-1"></div>
        <v-row
          justify="left"
          align="center"
          no-gutters
        >
        <v-btn color="primary" text @click="model_fitting">Fit</v-btn>
        <v-btn color="primary" text @click="fit_model_to_cube">Apply to Cube</v-btn>
        <v-btn color="primary" text @click="register_spectrum">Add to Viewer</v-btn>
        <v-btn
           color="primary"
           text
           @click="save_model">
           Save to File
         </v-btn>
        </v-row>
      </v-card-actions>
    </v-card>
  </v-card>
</template>
