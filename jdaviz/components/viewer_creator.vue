<template>
    <v-card flat>
      <v-card-title class="headline" color="primary" primary-title style="display: block; width: 100%">
        <span style="float: right">
          <j-plugin-popout :popout_button="popout_button"></j-plugin-popout>
        </span>
      </v-card-title>
      <v-card-text>
        <v-container>
          <slot/>
        </v-container>

        <plugin-auto-label
          :value.sync="viewer_label_value"
          @update:value="$emit('update:viewer_label_value', $event)"
          :default="viewer_label_default"
          :auto.sync="viewer_label_auto"
          @update:auto="$emit('update:viewer_label_auto', $event)"
          :invalid_msg="viewer_label_invalid_msg"
          label="Viewer Label"
          api_hint="vc.viewer_label ="
          :api_hints_enabled="api_hints_enabled"
          hint="Label to assign to the new viewer."
        ></plugin-auto-label>

      </v-card-text>
      <v-card-actions>
          <v-spacer></v-spacer>
          <plugin-action-button
            :disabled="viewer_label_value.length===0"
            :results_isolated_to_plugin="false"
            :api_hints_enabled="api_hints_enabled"

            @click="$emit('create-clicked')">
            {{ api_hints_enabled ?
                'vc()'
                :
                'Create Viewer'
            }}
            </plugin-action-button>
      </v-card-actions>
    </v-card>
  </template>

  <script>
  module.exports = {
    props: ['title', 'popout_button',
            'viewer_label_value', 'viewer_label_default', 'viewer_label_auto', 'viewer_label_invalid_msg',
            'api_hints_enabled'],
  }
  </script>