<template>
  <j-tray-plugin
    :config="config"
    plugin_key="Subset Tools"
    :api_hints_enabled.sync="api_hints_enabled"
    :description="docs_description"
    :link="docs_link || 'https://jdaviz.readthedocs.io/en/'+vdocs+'/'+config+'/plugins.html#subset-tools'"
    :popout_button="popout_button"
    :scroll_to.sync="scroll_to">

    <plugin-loaders-panel
      v-if="dev_loaders"
      :loader_panel_ind.sync="loader_panel_ind"
      :loader_items="loader_items"
      :loader_selected.sync="loader_selected"
      :api_hints_enabled="api_hints_enabled"
    ></plugin-loaders-panel>

    <v-row v-if="api_hints_enabled && config === 'imviz'">
      <span class="api-hint">
        plg.subset.multiselect = {{ boolToString(multiselect) }}
      </span>
    </v-row>
    <v-row v-if="config === 'imviz'">
      <div style="width: calc(100% - 32px)">
      </div>
      <div style="width: 32px">
        <j-tooltip tooltipcontent="Multiselect for recentering subsets">
          <v-btn
            icon
            style="opacity: 0.7"
            @click="() => {multiselect = !multiselect}"
          >
            <img :src="multiselect ? icon_checktoradial : icon_radialtocheck" width="24" class="invert-if-dark"/>
          </v-btn>
        </j-tooltip>
      </div>
    </v-row>

    <v-row align=center>
      <v-col cols=10 justify="left">
        <plugin-subset-select
          :items="subset_items"
          :selected.sync="subset_selected"
          :multiselect="multiselect"
          :show_if_single_entry="true"
          @rename-subset="rename_subset"
          label="Subset"
          api_hint="plg.subset ="
          api_hint_rename="plg.rename_subset"
          :api_hints_enabled="api_hints_enabled"
          hint="Select subset to edit."
        />
      </v-col>

      <v-col justify="center" cols=2>
        <j-tooltip tipid='g-subset-mode'>
          <g-subset-mode></g-subset-mode>
        </j-tooltip>
      </v-col>
    </v-row>

    <v-row v-if="api_hints_enabled" style="margin-top: -32px">
      <span class="api-hint">
        plg.combination_mode = '{{ combination_mode_selected }}'
      </span>
    </v-row>

    <!-- Sub-plugin for recentering of spatial subset (Imviz only) -->
    <v-row v-if="config=='imviz' && is_centerable">
      <v-expansion-panels accordion v-model="subplugins_opened">
        <v-expansion-panel>
          <v-expansion-panel-header >
            <span style="padding: 6px">Recenter</span>
          </v-expansion-panel-header>
          <v-expansion-panel-content class="plugin-expansion-panel-content">
            <plugin-dataset-select
             :items="recenter_dataset_items"
             :selected.sync="recenter_dataset_selected"
             :show_if_single_entry="true"
             label="Data"
             api_hint="plg.recenter_dataset ="
             :api_hints_enabled="api_hints_enabled"
             hint="Select the data for centroiding."
            />
            <v-row justify="end" no-gutters>
              <j-tooltip tooltipcontent="Recenter subset to centroid of selected data">
                <v-btn
                  color="primary"
                  text
                  @click="recenter_subset"
                  :class="api_hints_enabled ? 'api-hint' : null"
                >
                  {{ api_hints_enabled ?
                    'plg.recenter()'
                    :
                    'Recenter'
                  }}
                </v-btn>
              </j-tooltip>
            </v-row>
          </v-expansion-panel-content>
        </v-expansion-panel>
      </v-expansion-panels>
    </v-row>

    <!-- Show all subregions of a subset, including Glue state and subset type. -->
    <div v-for="(region, index) in subset_definitions">
      <j-plugin-section-header style="margin: 0px; margin-left: -12px; text-align: left; font-size: larger; font-weight: bold">
       Subregion {{ index }}</j-plugin-section-header>
      <v-row class="row-no-outside-padding">
        <div style="margin-top: 4px">
            {{ subset_types[index] }} applied with
        </div>
        <div style="margin-top: -2px; padding-bottom: 8px">
            <div v-if="index === 0">
              <img :src="icon_replace" width="20"/>
              replace mode
            </div>
            <div v-else-if="glue_state_types[index] === 'AndState'">
              <img :src="icon_and" width="20"/>
              and mode
            </div>
            <div v-else-if="glue_state_types[index] === 'OrState'">
              <img :src="icon_or" width="20"/>
              add mode
            </div>
            <div v-else-if="glue_state_types[index] === 'AndNotState'">
              <img :src="icon_andnot" width="20"/>
              remove mode
            </div>
            <div v-else-if="glue_state_types[index] === 'XorState'">
              <img :src="icon_xor" width="20"/>
              xor mode
            </div>
        </div>
      </v-row>

      <div v-for="(item, index2) in region">
        <v-row v-if="item.name === 'Parent' || item.name === 'Masked values'" class="row-no-outside-padding">
          <v-text-field
            :label="item.name"
            :value="item.value"
            style="padding-top: 0px; margin-top: 0px; margin-bottom: 10px;"
            :readonly="true"
            :hint="item.name === 'Parent' ? 'Subset was defined with respect to this reference data (read-only)' : 'Number of elements included by mask'"
            persistent-hint
          ></v-text-field>
        </v-row>
        <v-row v-else class="row-no-outside-padding">
          <v-text-field
            :label="api_hints_enabled ? 'plg.update_subset(\'' + subset_selected + '\', subregion=' + index + ', ' + item.att + '=' + item.value + ')' : item.name"
            v-model.number="item.value"
            type="number"
            style="padding-top: 0px; margin-top: 0px; margin-bottom: 10px;"
            :suffix="item.unit ? item.unit.replace('Angstrom', 'A') : ''"
            :class="api_hints_enabled ? 'api-hint' : null"
            persistent-hint
          ></v-text-field>
        </v-row>
      </div>
    </div>

      <v-row v-if="!multiselect" justify="end" no-gutters>
        <j-tooltip v-if="can_freeze" tooltipcontent="Freeze subset to a mask on the underlying data entries">
          <plugin-action-button
            :results_isolated_to_plugin="false"
            @click="freeze_subset"
          >
              Freeze
          </plugin-action-button>
        </j-tooltip>
        <j-tooltip tooltipcontent="Convert composite subset to use only add mode to connect subregions">
          <plugin-action-button
            :disabled="!can_simplify"
            :results_isolated_to_plugin="false"
            @click="simplify_subset"
          >
            Simplify
          </plugin-action-button>
        </j-tooltip>
        <plugin-action-button
          :disabled="subset_selected === 'Create New'"
          :results_isolated_to_plugin="false"
          @click="update_subset"
        >
          Update
        </plugin-action-button>
      </v-row>
  </j-tray-plugin>
</template>

<script>
module.exports = {
  methods: {
    boolToString(b) {
      if (b) {
        return 'True'
      } else {
        return 'False'
      }
    },
  }
}
</script>
