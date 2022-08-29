<template>
  <div v-if="pixel">
    <span style="position: absolute; top: 50%; transform: translateY(-50%); -ms-transform: translateY(-50%);">
      <j-layer-viewer-icon :icon="icon" color="white" :prevent_invert_if_dark="true"></j-layer-viewer-icon>
    </span>
    <div style="display: inline-block; white-space: nowrap; line-height: 14pt; margin: 0; position: absolute; margin-left: 26px; top: 50%; transform: translateY(-50%); -ms-transform: translateY(-50%);">
      <table>
        <tr v-if="value">
          <td width="60px"><b>Value&nbsp;</b></td>
          <td>{{ value }}</td>
          </td>
        </tr>
        <tr v-if="coords_type === 'Pixel' && pixel" style="height: 38px; vertical-align: middle">
          <td width="60px"><b>Pixel&nbsp;</b></td>
          <td>{{ pixel }}</td>
        </tr>
        <tr v-if="coords_type === 'World (ICRS)' && world_ra" style="height: 38px; vertical-align: middle">
          <td width="60px"><b>{{ world_label_prefix }}&nbsp;</b><br/>{{ world_label_icrs }}&nbsp;</td>
          <td>{{ world_ra }}<br/>{{world_dec}}</td>
          <td></td>
        </tr>
        <tr v-if="coords_type === 'World (deg)' && world_ra_deg" style="height: 38px; vertical-align: middle">
          <td width="60px"><b>{{ world_label_prefix }}&nbsp;</br></b> {{ world_label_deg }}&nbsp;</td>
          <td>{{ world_ra_deg }}<br/>{{world_dec_deg}}</td>
          <td></td>
        </tr>
      </table>
    </div>
  </div>
  <div v-else style="height: inherit">
    <v-toolbar-items>
      <j-tooltip tipid='coords-info-cycle'>
        <v-btn icon tile @click="next_coords_type()">
          <v-icon>mdi-crosshairs-gps</v-icon>
        </v-btn>
      </j-tooltip>
      <span style="padding-top: 22px">
        {{coords_type}}
      </span>
    </v-toolbar-items>

  </div>
</template>
