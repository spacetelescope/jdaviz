<template>
  <div>
    <div v-if="icon" style="position: absolute; top: 50%; transform: translateY(-50%); -ms-transform: translateY(-50%);">
      <span>
        <j-layer-viewer-icon :icon="icon" color="white" :prevent_invert_if_dark="true"></j-layer-viewer-icon>
      </span>
      <div style="display: inline-block; white-space: nowrap; line-height: 14pt; margin: 0; position: absolute; margin-left: 22px; top: 50%; transform: translateY(-50%); -ms-transform: translateY(-50%);">
        <table>
          <tr>
            <td colspan="4" :style="row1_unreliable ? 'color: #B8B8B8' : ''">
              <b>{{ row1a_title }} </b>{{ row1a_text }}&nbsp;&nbsp;
              <b>{{ row1b_title }} </b>{{ row1b_text }}
            </td>
          </tr>
          <tr :style="row2_unreliable ? 'color: #B8B8B8' : ''">
            <td width="42"><b>{{ row2_title }}</b></td>
            <td>{{ row2_text }}</td>
          </tr>
          <tr :style="row3_unreliable ? 'color: #B8B8B8' : ''">
            <td width="42"><b>{{ row3_title }}</b></td>
            <td>{{ row3_text }}</td>
          </tr>
        </table>
      </div>
    </div>
    <div v-else style="height: 100%">
      <v-toolbar-items>
        <j-tooltip tipid='coords-info-cycle'>
          <v-btn icon tile @click="next_layer()">
            <j-layer-viewer-icon :icon="dataset_icon" color="white" :prevent_invert_if_dark="true"></j-layer-viewer-icon>
          </v-btn>
        </j-tooltip>
        <span style="padding-top: 22px">
          {{dataset_selected}}
        </span>
      </v-toolbar-items>

    </div>
</div>
</template>
