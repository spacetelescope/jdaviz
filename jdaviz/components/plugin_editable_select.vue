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
      :label="api_hints_enabled && api_hint ? api_hint : label"
      :class="api_hints_enabled && api_hint ? 'api-hint' : null"
      :hint="hint"
      :rules="rules ? rules : []"
      item-text="label"
      item-value="label"
      persistent-hint
    >
      <template slot="selection" slot-scope="data">
        <div class="single-line" style="width: 100%">
          <span :class="api_hints_enabled ? 'api-hint' : null">
            {{ api_hints_enabled ?
              '\'' + data.item.label + '\''
              :
              data.item.label
            }}
          </span>
        </div>
      </template>
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
      style="width: 100%; padding-top: 16px; padding-bottom: 16px"
    >
      <span v-if="api_hints_enabled && api_hint_remove" class="api-hint">
        {{api_hint_remove}}('{{selected}}')
      </span>
      <span v-else>
        remove '{{selected}}' {{label.toLowerCase()}}?
      </span>
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
      v-else-if="['rename', 'add'].indexOf(mode) !== -1"
      v-model="edit_value"
      @keyup="$emit('update:edit_value', $event.target.value)"
      :label="textFieldLabel"
      :class="textFieldClass"
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
    <span v-else>
      <v-alert
        type="success"
        style="width: 100%; padding-top: 16px; padding-bottom: 16px"
      >
        Applying changes...
      </v-alert>
    </span>
  </v-row>
 </div>
</template>

<script>
module.exports = {
  props: ['mode', 'edit_value', 'items', 'selected', 'label', 'hint', 'rules',
          'api_hint', 'api_hint_add', 'api_hint_rename', 'api_hint_remove', 'api_hints_enabled'
  ],
  computed: {
    textFieldLabel() {
      if (this.api_hints_enabled && this.mode == 'rename' && this.api_hint_rename) {
        return this.api_hint_rename+'(\''+this.selected+'\', \''+this.edit_value+'\')';
      } else if (this.api_hints_enabled && this.mode == 'add' && this.api_hint_add) {
        return this.api_hint_add+'(\''+this.edit_value+'\')';
      } else {
        return this.label;
      }
    },
    textFieldClass() {
      if (this.api_hints_enabled && this.mode == 'rename' && this.api_hint_rename) {
        return 'api-hint';
      } else if (this.api_hints_enabled && this.mode == 'add' && this.api_hint_add) {
        return 'api-hint';
      } else {
        return null;
      }
    }
  },
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
