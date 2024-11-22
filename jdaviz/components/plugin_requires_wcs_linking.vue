<template>
  <div>
    <v-alert
      v-if="!wcs_linking_available"
      type='warning'
      class="ignore-api-hints"
      style="margin-left: -12px; margin-right: -12px"
    >
      Please add at least one data with valid WCS to align by sky (WCS).
    </v-alert>

    <v-alert
      v-if="wcs_linking_available && !need_clear_astrowidget_markers &&!need_clear_subsets"
      type='warning'
      class="ignore-api-hints"
      style="margin-left: -12px; margin-right: -12px"
    >
      Switching alignment will reset zoom.
    </v-alert>

    <v-alert
      v-if="plugin_markers_exist && !need_clear_astrowidget_markers &&!need_clear_subsets"
      type='warning'
      style="margin-left: -12px; margin-right: -12px"
    >
      Marker positions may not be pixel-perfect when changing alignment/linking options.
    </v-alert>

    <v-alert v-if="need_clear_astrowidget_markers" type='warning' style="margin-left: -12px; margin-right: -12px">
      Astrowidget markers must be cleared before changing alignment/linking options.
      <v-row justify="end" style="margin-right: 2px; margin-top: 16px">
        <v-btn @click="$emit('reset-astrowidget-markers')">Clear Markers</v-btn>
      </v-row>
    </v-alert>


    <v-alert v-if="need_clear_subsets" type='warning' style="margin-left: -12px; margin-right: -12px">
      Existing subsets must be deleted before changing alignment/linking options.
      <v-row justify="end" style="margin-right: 2px; margin-top: 16px">
        <v-btn @click="$emit('delete-subsets')">
          {{ api_hints_enabled ?
            'plg.delete_subsets()'
            :
            'Clear Subsets'
          }}
        </v-btn>
      </v-row>
    </v-alert>

    <v-alert
      v-if="show_link_by_wcs_button"
      type='warning'
      style="margin-left: -12px; margin-right: -12px"
    >
      cannot plot footprint when aligned by pixels (see Orientation plugin).
      <v-row justify="end" style="margin-right: 2px; margin-top: 16px">
        <v-btn @click="link_by_wcs">
          link by WCS
        </v-btn>
      </v-row>
    </v-alert>
    <v-alert v-if="viewer_items.length===0" type='warning' style="margin-left: -12px; margin-right: -12px">
      no valid viewers (with necessary WCS information) to show footprint overlay.
    </v-alert>

  </div>
</template>

<script>
  module.exports = {
    props: ['api_hints_enabled',
            'wcs_linking_available',
            'need_clear_astrowidget_markers',
            'need_clear_subsets',
            'plugin_markers_exist',
            'show_link_by_wcs_button'],
  };
</script>
