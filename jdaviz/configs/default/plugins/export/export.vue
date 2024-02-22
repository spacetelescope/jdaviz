<template>
  <j-tray-plugin
    description='Export data or plots from the app to a file.'
    :link="docs_link || 'https://jdaviz.readthedocs.io/en/'+vdocs+'/'+config+'/plugins.html#export'"
    :popout_button="popout_button">

    <j-multiselect-toggle
      v-if="dev_multi_support"
      :multiselect.sync="multiselect"
      :icon_checktoradial="icon_checktoradial"
      :icon_radialtocheck="icon_radialtocheck"
    ></j-multiselect-toggle>

    <div v-if="dev_dataset_support">
      <j-plugin-section-header style="margin-top: 12px">Data</j-plugin-section-header>
      <plugin-inline-select
      :items="dataset_items"
      :selected.sync="dataset_selected"
      :multiselect="multiselect"
      :single_select_allow_blank="true"
      >
      </plugin-inline-select>
    </div>

    <j-plugin-section-header style="margin-top: 12px">Viewers</j-plugin-section-header>
    <plugin-inline-select
      :items="viewer_items"
      :selected.sync="viewer_selected"
      :multiselect="multiselect"
      :single_select_allow_blank="true"
    >
    </plugin-inline-select>
    <v-row v-if="viewer_selected.length > 0" class="row-min-bottom-padding">
      <v-select
        :menu-props="{ left: true }"
        attach
        v-model="viewer_format_selected"
        :items="viewer_format_items.map(i => i.label)"
        label="Format"
        hint="Image format for exporting viewers."
        persistent-hint
      >
      </v-select>
    </v-row>

    <div v-if="dev_table_support">
      <j-plugin-section-header style="margin-top: 12px">Plugin Tables</j-plugin-section-header>
      <plugin-inline-select
        :items="table_items"
        :selected.sync="table_selected"
        :multiselect="multiselect"
        :single_select_allow_blank="true"
      >
      </plugin-inline-select>
    </div>

    <v-row>
        <v-text-field
        v-model="filename"
        label="Filename"
        hint="Export to a file on disk"
        :rules="[() => !!filename || 'This field is required']"
        persistent-hint>
        </v-text-field>
    </v-row>

    <v-row justify="end">
      <plugin-action-button :results_isolated_to_plugin="true">
        Export
      </plugin-action-button>
    </v-row>


  </j-tray-plugin>
</template>
