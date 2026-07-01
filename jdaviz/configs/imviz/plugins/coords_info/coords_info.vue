<template>
  <!-- focus/floating mode - normal flow, no position:absolute -->
  <div v-if="focus" style="color: white; white-space: nowrap;">
    <div v-if="icon" style="display: flex; align-items: center; gap: 6px;">
      <j-layer-viewer-icon :icon="icon" color="white" :prevent_invert_if_dark="true"></j-layer-viewer-icon>
      <table style="line-height: 18px; font-size: 12px;">
        <tr :style="row1_unreliable ? 'color: #B8B8B8' : ''">
          <td colspan="4"><b>{{ row1a_title }} </b>{{ row1a_text }}&nbsp;&nbsp;<b>{{ row1b_title }} </b>{{ row1b_text }}</td>
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

  <!-- normal (non-focus) mode -->
  <div v-else @mouseover="show_dataset_selected = true" @mouseleave="show_dataset_selected = false">
    <div v-if="icon" style="position: absolute; height: 100%">
      <v-toolbar-items>
        <v-btn variant="text" color="white" icon rounded="0">
          <j-layer-viewer-icon :icon="icon" color="white" :prevent_invert_if_dark="true"></j-layer-viewer-icon>
        </v-btn>
        <span style="display: inline-block; white-space: nowrap; line-height: 14pt; margin: 0; position: absolute; margin-left: 48px">
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
        </span>
      </v-toolbar-items>
    </div>
    <div v-else style="height: 100%">
      <v-toolbar-items>
        <j-tooltip tipid='coords-info-cycle'>
          <v-btn variant="text" color="white" icon rounded="0" @click="next_layer()">
            <j-layer-viewer-icon :icon="dataset_icon" color="white" :prevent_invert_if_dark="true"></j-layer-viewer-icon>
          </v-btn>
        </j-tooltip>
        <span v-if="show_dataset_selected" style="padding-top: 22px">
          {{dataset_selected}}
        </span>
      </v-toolbar-items>
    </div>
  </div>
</template>

<script>
  export default {
    data: function () {
      return {
        show_dataset_selected: false,
      }
    },
  }
</script>
