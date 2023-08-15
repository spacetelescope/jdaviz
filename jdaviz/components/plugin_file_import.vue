<template>
  <v-dialog :value="show" height="400" width="600">
    <v-card>
      <v-card-title class="headline" color="primary" primary-title>{{ title || "Import File" }}</v-card-title>
      <v-card-text>
        {{ hint }}
        <v-container>
          <v-row>
            <v-col>
              <slot></slot>
            </v-col>
          </v-row>
          <v-row v-if="from_file_message.length > 0" :style='"color: red"'>
            {{from_file_message}}
          </v-row>
          <v-row v-else>
            Valid file
          </v-row>
        </v-container>
      </v-card-text>

      <v-card-actions>
        <div class="flex-grow-1"></div>
        <v-btn color="primary" text @click="$emit('click-cancel')">Cancel</v-btn>
        <v-btn color="primary" text @click="$emit('click-import')" :disabled="from_file_message.length > 0">Load</v-btn>
      </v-card-actions>

    </v-card>
 </v-dialog>
</template>

<script>
module.exports = {
  props: ['title', 'hint', 'show', 'from_file', 'from_file_message'],
};
</script>
