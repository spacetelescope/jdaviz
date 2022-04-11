<template>
  <j-tray-plugin>
    <v-row>
      <j-docs-link :link="'https://jdaviz.readthedocs.io/en/'+vdocs+'/'+config+'/plugins.html#model-fitting'">Fit an analytic model to data or a subset.</j-docs-link>
    </v-row>

    <!-- for mosviz, the entries change on row change, so we want to always show the dropdown
         to make sure that is clear -->
    <plugin-dataset-select
      :items="dataset_items"
      :selected.sync="dataset_selected"
      :show_if_single_entry="config=='mosviz'"
      label="Data"
      hint="Select the data set to be fitted."
    />

    <plugin-subset-select
      v-if="config=='cubeviz'"
      :items="spatial_subset_items"
      :selected.sync="spatial_subset_selected"
      :show_if_single_entry="true"
      label="Spatial region"
      hint="Select spatial region to fit."
    />

    <plugin-subset-select 
      :items="spectral_subset_items"
      :selected.sync="spectral_subset_selected"
      :show_if_single_entry="true"
      label="Spectral region"
      hint="Select spectral region to fit."
    />

    <j-plugin-section-header>Model Components</j-plugin-section-header>
    <v-form v-model="form_valid_model_component">
      <v-row>
        <v-select
          :items="available_models"
          @change="model_selected"
          label="Model"
          hint="Select a model to fit."
          persistent-hint
        ></v-select>
      </v-row>

      <v-row>
        <v-text-field
          label="Model ID"
          v-model="temp_name"
          @change="sanitizeModelId"
          hint="A unique string label for this component model."
          persistent-hint
          :rules="[() => temp_name!=='' || 'This field is required',
                   () => component_models.map((item) => item.id).indexOf(temp_name) === -1 || 'ID already in use']"
        >
        </v-text-field>
      </v-row>

      <v-row v-if="display_order">
        <v-text-field
          label="Order"
          type="number"
          v-model.number="poly_order"
          :rules="[() => poly_order!=='' || 'This field is required']"
          hint="Order of polynomial to fit."
          persistent-hint
        >
        </v-text-field>
      </v-row>

      <v-row justify="end">
        <j-tooltip tipid='plugin-model-fitting-add-model'>
          <v-btn 
            color="primary" 
            text 
            :disabled="!form_valid_model_component"
            @click="add_model"
            >Add Component
          </v-btn>
        </j-tooltip>
      </v-row>
    </v-form>

    <div v-if="component_models.length">
      <j-plugin-section-header>Model Parameters</j-plugin-section-header>
      <v-row>
        <v-expansion-panels accordion>
          <v-expansion-panel
            v-for="item in component_models" :key="item.id"
          >
            <v-expansion-panel-header v-slot="{ open }">
              <v-row no-gutters align="center">
                <v-col cols=3>
                  <v-btn @click.native.stop="remove_model(item.id)" icon style="width: 60%">
                    <v-icon>mdi-close-circle</v-icon>
                  </v-btn>
                </v-col>
                <v-col cols=9 class="text--secondary">
                  <v-row>
                    <b>{{ item.id }}</b>&nbsp;({{ item.model_type }})
                  </v-row>
                  <v-row v-for="param in item.parameters">
                    <span style="white-space: nowrap; overflow-x: clip; width: calc(100% - 24px); margin-right: -48px">
                      {{ param.name }} = {{ param.value }}                      
                    </span>
                  </v-row>
                </v-col>
              </v-row>
            </v-expansion-panel-header>
            <v-expansion-panel-content>
              <v-row
                justify="left"
                align="center"
                class="row-no-outside-padding"
              >
                <v-col cols=4>
                  <p class="font-weight-bold">Param</p>
                </v-col>
                <v-col cols=8> <!-- covers value and unit in rows -->
                  <p class="font-weight-bold">Value</p>
                </v-col>
              </v-row>
              <v-row
                justify="left"
                align="center"
                class="row-no-outside-padding"
                v-for="param in item.parameters"
              >
                <v-col cols=4>
                  <j-tooltip tipid='plugin-model-fitting-param-fixed'>
                    <v-checkbox v-model="param.fixed">
                      <template v-slot:label>
                        <span class="text--primary" style="overflow-wrap: anywhere; font-size: 10pt">
                          {{param.name}}
                        </span>
                      </template>
                    </v-checkbox>
                  </j-tooltip>
                </v-col>
                <v-col cols=4>
                  <v-text-field
                    v-model="param.value"
                  >
                  </v-text-field>
                </v-col>
                <v-col cols=4 style="font-size: 10pt">
                  {{ param.unit.replace("Angstrom", "&#8491;") }}
                </v-col>
              </v-row>
            </v-expansion-panel-content>
          </v-expansion-panel>
        </v-expansion-panels>
      </v-row>
    </div>

    <div v-if="component_models.length">
      <j-plugin-section-header>Equation Editor</j-plugin-section-header>
      <v-row>
        <v-text-field
          v-model="model_equation"
          hint="Enter an equation specifying how to combine the component models, using their model IDs and basic arithmetic operators (ex. component1+component2)."
          persistent-hint
          :rules="[() => !!model_equation || 'This field is required']"
          @change="equation_changed"
          :error="eq_error"
        >
        </v-text-field>
      </v-row>
    </div>

    <j-plugin-section-header>Fit Model</j-plugin-section-header>
    <v-row>
      <v-switch v-if="config=='cubeviz'"
        v-model="cube_fit"
        label="Cube Fit"
        hint="Whether to fit to the collapsed spectrum or entire cube"
        persistent-hint
      ></v-switch>
    </v-row>
    
    <plugin-add-results
      :label.sync="results_label"
      :label_default="results_label_default"
      :label_auto.sync="results_label_auto"
      :label_invalid_msg="results_label_invalid_msg"
      :label_overwrite="results_label_overwrite"
      label_hint="Label for the model"
      :add_to_viewer_items="add_to_viewer_items"
      :add_to_viewer_selected.sync="add_to_viewer_selected"
      action_label="Fit Model"
      action_tooltip="Fit the model to the data"
      @action-click="apply"
    ></plugin-add-results>

    <v-row>
      <span class="v-messages v-messages__message text--secondary">
          If fit is not sufficiently converged, try clicking fitting again to complete additional iterations.
      </span>
    </v-row>
  </j-tray-plugin>
</template>

<script>
  module.exports = {
    created() {
      this.sanitizeModelId = (v) => {
        // strip non-word character entries
        this.temp_name = v.replace(/[\W]+/g, '');
      }
    },
  }
</script>
