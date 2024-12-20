<template>
  <div>
    <v-row>
      <v-select
        :menu-props="{ left: true }"
        attach
        :items="items"
        item-text="label"
        item-value="label"
        v-model="selected"
        @change="$emit('update:selected', $event)"
        :label="api_hints_enabled && api_hint ? api_hint : label"
        :class="api_hints_enabled && api_hint ? 'api-hint' : null"
        :hint="hint"
        persistent-hint
      >
        <template v-slot:selection="{ item, index }">
          <div class="single-line" style="width: 100%">
            <span v-if="api_hints_enabled" class="api-hint" :style="index > 0 ? 'display: none' : null">
              {{'\'' + selected + '\''}}
            </span>
            <span v-else>
              <v-icon v-if="item.icon && item.icon.length < 50" small>{{ item.icon }}</v-icon>
              <img v-else-if="item.icon" :src="item.icon" width="16" class="invert-if-dark" style="opacity: 1.0; margin-bottom: -2px"/>
              {{ selected }}
            </span>
          </div>
        </template>
        <template v-slot:item="{ item }">
          <span style="margin-top: 8px; margin-bottom: 0px">
            <v-icon v-if="item.icon && item.icon.length < 50" small>{{ item.icon }}</v-icon>
            <img v-else-if="item.icon" :src="item.icon" width="16" class="invert-if-dark" style="opacity: 1.0; margin-bottom: -2px"/>
            {{ item.label }}
          </span>
        </template>
    
      </v-select>
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
          'dialog_title', 'dialog_hint', 'api_hint', 'api_hints_enabled']
};
</script>

<style>
.v-chip__content {
  width: 100%
}
</style>
