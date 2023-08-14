<template>
  <div>
  <v-row>
    <v-select
      v-if="mode=='select'"
      attach
      :menu-props="{ left: true }"
      :items="items"
      v-model="selected"
      @change="$emit('update:selected', $event)"
      :label="label"
      :hint="hint"
      :rules="rules ? rules : []"
      item-text="label"
      item-value="label"
      persistent-hint
    >
      <template v-slot:append>
        <v-icon style="cursor: pointer">mdi-menu-down</v-icon>
        <j-tooltip tooltipcontent="rename">
          <v-icon style="cursor: pointer" @click="modeRename">mdi-pencil</v-icon>
        </j-tooltip>
        <j-tooltip tooltipcontent="remove">
          <v-icon style="cursor: pointer" @click="modeRemove">mdi-delete</v-icon>
        </j-tooltip>
        <j-tooltip tooltipcontent="create new">
          <v-icon style="cursor: pointer" @click="modeAdd">mdi-plus</v-icon>
        </j-tooltip>
      </template>
    </v-select>
    <v-alert
      v-else-if="mode=='remove'"
      type="warning"
      style="width: 100%"
    >
      <span>remove '{{selected}}' {{label.toLowerCase()}}?</span>
      <template v-slot:append>
        <j-tooltip tooltipcontent="cancel">
          <v-icon style="cursor: pointer" @click="changeCancel">mdi-close</v-icon>
        </j-tooltip>
        <j-tooltip :tooltipcontent="'Remove '+selected+' '+label.toLowerCase()">
          <v-icon style="cursor: pointer" @click="changeAccept">mdi-delete</v-icon>
        </j-tooltip>
      </template>
    </v-alert>
    <v-text-field
      v-else
      v-model="edit_value"
      @keyup="$emit('update:edit_value', $event.target.value)"
      :label="label"
      :hint="mode == 'rename' ? 'Rename '+label.toLowerCase() : 'Add '+label.toLowerCase()"
      persistent-hint
    >
      <template v-slot:append>
        <j-tooltip v-if="items.length > 0" tooltipcontent="Cancel change">
          <v-icon style="cursor: pointer" @click="changeCancel">mdi-close</v-icon>
        </j-tooltip>
        <j-tooltip tooltipcontent="Accept change">
          <v-icon style="cursor: pointer" @click="changeAccept">mdi-check</v-icon>
        </j-tooltip>
      </template>
    </v-text-field>
  </v-row>
 </div>
</template>

<script>
module.exports = {
  props: ['mode', 'edit_value', 'items', 'selected', 'label', 'hint', 'rules'],
  methods: {
    changeCancel() {
      this.$emit('update:edit_value', this.selected);
      this.$emit('update:mode', 'select');
    },
    changeAccept() {
      this.$emit('update:mode', this.mode+':accept')
    },
    modeRename() {
      this.$emit('update:mode', 'rename')
    },
    modeRemove() {
      this.$emit('update:mode', 'remove')
    },
    modeAdd() {
      this.$emit('update:edit_value', '')
      this.$emit('update:mode', 'add')
    }
  }
};
</script>

<style scoped>
</style>
