<template>
  <j-tray-plugin>
    <v-row>
      <j-docs-link>Export viewer plot as an image.</j-docs-link>
    </v-row>

    <v-row v-if="viewer_items.length > 1">
      <v-select
        :items="viewer_items"
        v-model="selected_viewer"
        label="Viewer"
        hint="Select the viewer to export."
        persistent-hint
      ></v-select>
    </v-row>

    <div v-if="selected_viewer">
      <v-list>
       <v-list-item>
        <v-btn
         color="primary"
         @click="() => save_figure('png')"
        >
         Export to PNG
        </v-btn>
       </v-list-item>
       <v-list-item>
        <v-btn
         color="primary"
         @click="() => save_figure('svg')"
        >
         Export to SVG
        </v-btn>
       </v-list-item>
      </v-list>
    </div>

  </j-tray-plugin>
</template>
