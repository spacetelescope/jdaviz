<template>
  <j-tray-plugin
    description='Fit an analytic model to data or a subset.'
    :link="'https://jdaviz.readthedocs.io/en/'+vdocs+'/'+config+'/plugins.html#model-fitting'"
    :popout_button="popout_button">

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

    <v-row v-if="!spectral_subset_valid">
      <span class="v-messages v-messages__message text--secondary" style="color: red !important">
          Selected dataset and spectral subset do not overlap
      </span>
    </v-row>

    <j-plugin-section-header>Model Components</j-plugin-section-header>
    <v-form v-model="form_valid_model_component">
      <v-row v-if="model_comp_items">
        <v-select
          attach
          :menu-props="{ left: true }"
          :items="model_comp_items.map(i => i.label)"
          v-model="model_comp_selected"
          label="Model Component"
          hint="Select a model component to add."
          persistent-hint
        ></v-select>
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

      <plugin-auto-label
        :value.sync="comp_label"
        @update:value="sanitizeCompLabel"
        :default="comp_label_default"
        :auto.sync="comp_label_auto"
        :invalid_msg="comp_label_invalid_msg"
        hint="Label for this new model component."
      ></plugin-auto-label>

      <v-row justify="end">
        <j-tooltip tipid='plugin-model-fitting-add-model'>
          <v-btn 
            color="primary" 
            text 
            :disabled="!form_valid_model_component || comp_label_invalid_msg.length > 0"
            @click="add_model"
            >Add Component
          </v-btn>
        </j-tooltip>
      </v-row>
    </v-form>

    <div v-if="component_models.length">
      <j-plugin-section-header>Model Parameters</j-plugin-section-header>
      <v-row justify="end">
        <j-tooltip tipid='plugin-model-fitting-reestimate-all'>
          <v-btn
            tile
            :elevation=0
            x-small
            dense 
            color="turquoise"
            dark
            style="padding-left: 8px; padding-right: 6px;"
            @click="reestimate_model_parameters(null)">
            <v-icon left small dense style="margin-right: 2px">mdi-restart</v-icon>
            Re-estimate free parameters
          </v-btn>
        </j-tooltip>
      </v-row>
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
                <v-col cols=9 class="text--secondary" :style="componentInEquation(item.id) ? '': 'color: #80808087 !important'">
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
              <v-row v-if="!item.compat_display_units">
                <v-alert :type="componentInEquation(item.id) ? 'error' : 'warning'">
                  <b>{{ item.id }}</b> is inconsistent with the current display units so cannot be used in the model equation.
                  Create a new model component or re-estimate the free parameters based on the current display units.
                  <v-row
                    justify="end"
                    style="padding-top: 12px; padding-right: 2px"
                  >
                    <j-tooltip tipid='plugin-model-fitting-reestimate'>
                      <v-btn
                        tile
                        :elevation=0
                        x-small
                        dense 
                        color="turquoise"
                        dark
                        style="padding-left: 8px; padding-right: 6px;"
                        @click="reestimate_model_parameters(item.id)">
                        <v-icon left small dense style="margin-right: 2px">mdi-restart</v-icon>
                        Re-estimate free parameters
                      </v-btn>
                    </j-tooltip>
                  </v-row>
                </v-alert>
              </v-row>
              <v-row v-if="item.compat_display_units && !componentInEquation(item.id)">
                <v-alert type="info">
                  <b>{{ item.id }}</b> model component not in equation
                </v-alert>
              </v-row>
              <v-row v-if="item.compat_display_units"
                justify="end"
                style="padding-top: 12px; padding-right: 2px"
              >
                <j-tooltip tipid='plugin-model-fitting-reestimate'>
                  <v-btn
                    tile
                    :elevation=0
                    x-small
                    dense 
                    color="turquoise"
                    dark
                    style="padding-left: 8px; padding-right: 6px;"
                    @click="reestimate_model_parameters(item.id)">
                    <v-icon left small dense style="margin-right: 2px">mdi-restart</v-icon>
                    Re-estimate free parameters
                  </v-btn>
                </j-tooltip>
              </v-row>
              <v-div
                v-for="param in item.parameters"
                :style="componentInEquation(item.id) ? '': 'opacity: 0.3'"
              >
                <v-row
                  justify="left"
                  align="center"
                  class="py-0 my-0">
                <v-col cols=12 class="py-my-0">
                  <j-tooltip tipid='plugin-model-fitting-param-fixed'>
                    <v-checkbox v-model="param.fixed" :disabled="!componentInEquation(item.id)" dense>
                      <template v-slot:label>
                        <span class="font-weight-bold" style="overflow-wrap: anywhere; font-size: 12pt">
                          {{param.name}}
                        </span>
                      </template>
                    </v-checkbox>
                  </j-tooltip>
                </v-col>
                </v-row>
                <v-row
                  justify="left"
                  align="center"
                  class="py-0 my-0">
                  <v-col class="py-my-0">
                    <v-text-field
                      dense
                      v-model="param.value"
                    >
                    </v-text-field>
                  </v-col>
                  <v-col v-if="param.std" style="padding-bottom: 22px">
                    &#177; {{roundUncertainty(param.std)}}
                  </v-col>
                  <v-col style="font-size: 10pt" class="py-my-0">
                    {{ param.unit.replace("Angstrom", "&#8491;") }}
                  </v-col>
                </v-row>
                <v-divider></v-divider>
              </v-div>
            </v-expansion-panel-content>
          </v-expansion-panel>
        </v-expansion-panels>
      </v-row>
    </div>

    <div v-if="component_models.length">
      <j-plugin-section-header>Equation Editor</j-plugin-section-header>
      <plugin-auto-label
        :value.sync="model_equation"
        :default="model_equation_default"
        :auto.sync="model_equation_auto"
        :invalid_msg="model_equation_invalid_msg"
        hint="Enter an equation specifying how to combine the component models, using their model IDs and basic arithmetic operators (ex. component1+component2)."
      ></plugin-auto-label>

      <j-plugin-section-header>Fit Model</j-plugin-section-header>
      <v-row>
        <v-switch v-if="config=='cubeviz'"
          v-model="cube_fit"
          label="Cube Fit"
          hint="Whether to fit to the collapsed spectrum or entire cube"
          persistent-hint
        ></v-switch>
      </v-row>

      <v-row v-if="cube_fit">
        <span class="v-messages v-messages__message text--secondary">
            Note: cube fit results are not logged to table.
        </span>
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
        :action_disabled="model_equation_invalid_msg.length > 0 || !spectral_subset_valid"
        @click:action="apply"
      >
        <div v-if="config!=='cubeviz' || !cube_fit">
          <v-row>
            <v-switch
              v-model="residuals_calculate"
              label="Calculate residuals"
              hint="Whether to compute and export residuals (data minus model)."
              persistent-hint
            ></v-switch>
          </v-row>

          <plugin-auto-label
            v-if="residuals_calculate"
            :value.sync="residuals_label"
            :default="residuals_label_default"
            :auto.sync="residuals_label_auto"
            :invalid_msg="residuals_label_invalid_msg"
            label="Residuals Data Label"
            hint="Label for the residuals.  Data entry will not be loaded into the viewer automatically."
          ></plugin-auto-label>

          <v-row v-if="!spectral_subset_valid">
            <span class="v-messages v-messages__message text--secondary" style="color: red !important">
                Cannot calculate fit: selected dataset and spectral subset do not overlap
            </span>
          </v-row>

        </div>
      </plugin-add-results>

      <v-row>
        <span class="v-messages v-messages__message text--secondary">
            If fit is not sufficiently converged, click Fit Model again to run additional iterations.
        </span>
      </v-row>

      <j-plugin-section-header>Results History</j-plugin-section-header>
      <jupyter-widget :widget="table_widget"></jupyter-widget> 
    </div>
  </j-tray-plugin>
</template>

<script>
  module.exports = {
    created() {
      this.sanitizeCompLabel = (v) => {
        // strip non-word character entries
        this.comp_label = v.replace(/[\W]+/g, '');
      }
    },
    methods: {
      componentInEquation(componentId) {
        return this.model_equation.replace(/\s/g, '').split(/[+*\/-]/).indexOf(componentId) !== -1
      },
      roundUncertainty(uncertainty) {
        return uncertainty.toPrecision(2)
      }
    }
  }
</script>
