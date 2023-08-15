<template>
  <div>
    <v-row>
      <v-select
        :menu-props="{ left: true }"
        attach
        :items="items.map(i => i.label)"
        v-model="selected"
        @change="$emit('update:selected', $event)"
        :label="label"
        :hint="hint"
        persistent-hint
      ></v-select>
      <v-chip v-if="selected === 'From File...'"
        close
        close-icon="mdi-close"
        label
        @click:close="() => {this.$emit('click-cancel')}"
        style="margin-top: -50px; width: 100%"
      >
       <!-- @click:close resets from_file and relies on the @observe in python to reset preset 
            to its default, but the traitlet change wouldn't be fired if from_file is already
            empty (which should only happen if setting from the API but not setting from_file) -->
         <span style="overflow-x: hidden; whitespace: nowrap; text-overflow: ellipsis; width: 100%">
           {{from_file.split("/").slice(-1)[0]}}
         </span>
      </v-chip>
    </v-row>
    <v-dialog :value="selected === 'From File...' && from_file.length == 0" height="400" width="600">
      <v-card>
        <v-card-title class="headline" color="primary" primary-title>{{ dialog_title || "Import File" }}</v-card-title>
        <v-card-text>
          {{ dialog_hint }}
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
  </div>
</template>

<script>
module.exports = {
  props: ['items', 'selected', 'label', 'hint', 'rules', 'from_file', 'from_file_message',
          'dialog_title', 'dialog_hint']
};
</script>

<style>
.v-chip__content {
  width: 100%
}
</style>
