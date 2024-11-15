<template>
  <j-tray-plugin
    :config="config"
    plugin_key="Metadata"
    :api_hints_enabled.sync="api_hints_enabled"
    :description="docs_description"
    :link="docs_link || 'https://jdaviz.readthedocs.io/en/'+vdocs+'/'+config+'/plugins.html#metadata-viewer'"
    :popout_button="popout_button"
    :scroll_to.sync="scroll_to">

    <!-- for specviz, we'll allow this to hide for a single entry, but since filters are being
         applied on other configs, we'll always show -->
    <plugin-dataset-select
      :items="dataset_items"
      :selected.sync="dataset_selected"
      :show_if_single_entry="config!='specviz'"
      label="Data"
      api_hint='plg.dataset ='
      :api_hints_enabled="api_hints_enabled"
      hint="Select the data to see metadata."
    />

    <v-row v-if="has_primary || api_hints_enabled">
      <plugin-switch
        :value.sync="show_primary"
        label='Show primary header'
        api_hint='plg.show_primary = '
        :api_hints_enabled="api_hints_enabled"
        hint="Show MEF primary header metadata instead."
      />
    </v-row>

    <j-plugin-section-header>Metadata</j-plugin-section-header>
    <div v-if="has_metadata">
      <v-row v-if="api_hints_enabled">
        <span class="api-hint">
          plg.metadata
        </span>
      </v-row>
      <v-row>
        <v-text-field
          v-model='metadata_filter'
          append-icon='mdi-magnify'
          style="padding: 0px 8px"
          clearable
          hide-details
        ></v-text-field>
      </v-row>
      <v-row
        v-for="item in metadata.filter((item) => {return metadata_filter === null || item.join().toLowerCase().indexOf(metadata_filter.toLowerCase()) !== -1})"
        :key="item[0]"
        no-gutters>
        <v-col cols=12><B>{{ item[0] }}</B> | {{ item[1] }}</v-col>
        <v-col v-if="has_comments" cols=12 class="text--secondary">{{ item[2] }}</v-col>
      </v-row>
    </div>
    <v-row v-else>
      <span class="v-messages v-messages__message text--secondary">
          Selected data does not contain any metadata.
      </span>
    </v-row>

  </j-tray-plugin>
</template>
