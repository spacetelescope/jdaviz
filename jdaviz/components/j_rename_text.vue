<template>
  <div>
    <!-- Display mode: shows label with hover effects -->
    <span
      v-if="!isEditing"
      style="display: inline-block"
      @mouseenter="hovering = true"
      @mouseleave="hovering = false"
      @dblclick="startEditing"
    >
      <span
        :style="hovering ? 'text-decoration: underline; cursor: pointer;' : ''"
      >
        {{ currentValue }}
      </span>
      <v-icon
        v-if="hovering && showPencil"
        small
        style="margin-left: 4px; cursor: pointer;"
        @click="startEditing"
      >
        mdi-pencil
      </v-icon>
    </span>

    <!-- Edit mode: shows text field with cancel and confirm buttons -->
    <v-text-field
      v-else
      v-model="editValue"
      @keyup="handleKeyup"
      autofocus
      dense
      :hint="editHint"
      persistent-hint
      style="margin-top: -8px"
    >
      <template v-slot:append>
        <j-tooltip tooltipcontent="Cancel change">
          <v-icon style="cursor: pointer" @click="cancelEdit">mdi-close</v-icon>
        </j-tooltip>
        <j-tooltip tooltipcontent="Accept change">
          <v-icon style="cursor: pointer" @click="acceptEdit">mdi-check</v-icon>
        </j-tooltip>
      </template>
    </v-text-field>
  </div>
</template>

<script>
module.exports = {
  props: {
    value: {
      type: String,
      required: true
    },
    editHint: {
      type: String,
      default: 'Rename'
    },
    showPencil: {
      type: Boolean,
      default: true
    },
    autoEdit: {
      type: Boolean,
      default: false
    }
  },
  data() {
    return {
      hovering: false,
      isEditing: this.autoEdit,
      editValue: this.value
    };
  },
  computed: {
    currentValue() {
      return this.value;
    }
  },
  watch: {
    value(newVal) {
      if (!this.isEditing) {
        this.editValue = newVal;
      }
    }
  },
  methods: {
    startEditing() {
      this.isEditing = true;
      this.editValue = this.value;
    },
    cancelEdit() {
      this.isEditing = false;
      this.editValue = this.value;
    },
    acceptEdit() {
      const trimmedValue = this.editValue.trim();
      if (trimmedValue && trimmedValue !== this.value) {
        // Emit with old_label and new_label keys for data_menu.vue handler
        this.$emit('rename', trimmedValue);
        // Keep the new value in editValue so it displays while waiting for backend update
        this.editValue = trimmedValue;
      }
      this.isEditing = false;
    },
    handleKeyup(event) {
      if (event.key === 'Enter') {
        this.acceptEdit();
      } else if (event.key === 'Escape') {
        this.cancelEdit();
      }
    }
  }
};
</script>

<style scoped>
  .v-text-field {
    margin-top: -8px;
  }
</style>

