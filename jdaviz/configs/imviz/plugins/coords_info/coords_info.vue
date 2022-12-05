<template>
  <div v-if="pixel">
    <span style="position: absolute; top: 50%; transform: translateY(-50%); -ms-transform: translateY(-50%);">
      <j-layer-viewer-icon :icon="icon" color="white" :prevent_invert_if_dark="true"></j-layer-viewer-icon>
    </span>
    <div style="display: inline-block; white-space: nowrap; line-height: 14pt; margin: 0; position: absolute; margin-left: 26px; top: 50%; transform: translateY(-50%); -ms-transform: translateY(-50%);">
      <table>
        <tr>
          <td colspan="4" :style="unreliable_pixel ? 'color: #B8B8B8' : ''">
            <b v-if="pixel">Pixel </b>{{ pixel }}&nbsp;&nbsp;
            <b v-if="value">Value </b>{{ value }}
          </td>
        </tr>
        <tr :style="unreliable_world ? 'color: #B8B8B8' : ''">
          <td width="42"><b>{{ world_label_prefix }}</b></td>
          <td :width="world_label_prefix == 'Wave' ? 85 : 115">{{ world_ra }}</td>
          <td width="120">{{ world_dec }}</td>
          <td>{{ world_label_icrs }}</td>
        </tr>
        <tr :style="unreliable_world ? 'color: #B8B8B8' : ''">
          <td width="42" :style="unreliable_world ? '' : 'font-weight: bold'">{{ world_label_prefix_2 }}</td>
          <td :width="world_label_prefix == 'Wave' ? 85 : 115">{{ world_ra_deg }}</td>
          <td width="120">{{ world_dec_deg }}</td>
          <td>{{ world_label_deg }}</td>
        </tr>
      </table>
    </div>
</div>
</template>
