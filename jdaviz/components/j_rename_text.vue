<template>
  <div style="display: flex; flex-direction: column; min-width: 0; width: 100%;">
    <span v-if="isEditing && apiHintRename && showApiHint" class="api-hint" style="display: block; margin-bottom: 8px;">
      {{ apiHintRename }}
    </span>
    <span @click="onRootClick" @mousedown="onRootMousedown" @keydown.stop style="display: inline-flex; align-items: center; min-width: 0; flex: 1; width: 100%;">
      <!-- Display mode -->
      <span
        v-if="!isEditing"
        @mouseenter="hovering = true"
        @mouseleave="hovering = false"
        @mousedown.stop
        @dblclick.stop="startEditing"
        style="display: inline-flex; align-items: center; min-width: 0; flex: 1; width: 100%;"
      >
        <span
          :style="hovering ? 'cursor: pointer; text-decoration: underline;' : 'cursor: pointer;'"
          style="min-width: 0; overflow-wrap: break-word;"
        >
          {{ value }}
        </span>

        <!-- Pencil icon - visible on hover in display mode, fixed to the right -->
        <v-icon
          v-if="showPencil"
          small
          style="margin-left: auto; cursor: pointer; flex-shrink: 0; visibility: hidden; width: 24px; min-width: 24px;"
          :style="hovering ? 'visibility: visible;' : ''"
          @click.stop="startEditing"
          @mousedown.stop
        >
          mdi-pencil
        </v-icon>
      </span>

      <!-- Edit mode: shows text field with cancel and confirm buttons -->
      <v-text-field
        v-if="isEditing"
        v-model="editValue"
        @keydown.enter.prevent="acceptEdit"
        @keydown.escape.prevent="cancelEdit"
        @click.stop
        @mousedown.stop
        autofocus
        dense
        :hint="renameErrorMessage"
        :error-messages="renameErrorMessage ? [renameErrorMessage] : []"
        persistent-hint
        style="flex-grow: 1; margin: 0; padding: 0; width: 100%;"
      >
        <template v-slot:append>
          <j-tooltip tooltipcontent="Cancel change">
            <v-icon style="cursor: pointer" @click.stop="cancelEdit" @mousedown.stop>mdi-close</v-icon>
          </j-tooltip>
          <j-tooltip :tooltipcontent="renameErrorMessage || 'Accept change'">
            <v-icon
              style="cursor: pointer"
              :style="renameErrorMessage ? 'opacity: 0.5; cursor: not-allowed;' : ''"
              @click.stop="renameErrorMessage ? null : acceptEdit()"
              @mousedown.stop
            >mdi-check</v-icon>
          </j-tooltip>
        </template>
      </v-text-field>
    </span>
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
    },
    renameErrorMessage: {
      type: String,
      default: ''
    },
    apiHintRename: {
      type: String,
      default: ''
    },
    showApiHint: {
      type: Boolean,
      default: false
    }
  },
  data() {
    return {
      hovering: false,
      isEditing: this.autoEdit,
      editValue: this.value,
      suppressPropagation: false
    };
  },
  watch: {
    value(newVal) {
      if (!this.isEditing) {
        this.editValue = newVal;
      }
    },
    editValue(newVal) {
      if (this.isEditing) {
        // Emit input event as user types
        this.$emit('input', newVal);
      }
    }
  },
  methods: {
    startEditing() {

      this.isEditing = true;
      this.editValue = this.value;
      // Suppress propagation when entering edit mode to prevent selection change
      this.suppressPropagation = true;
      this.$nextTick(() => {
        this.suppressPropagation = false;
      });
    },
    cancelEdit() {
      this.suppressPropagation = true;
      this.isEditing = false;
      this.editValue = this.value;
      // Emit cancel event so parent can clear validation errors
      this.$emit('cancel');
      // Clear the flag after the event loop to allow normal behavior again
      this.$nextTick(() => {
        this.suppressPropagation = false;
      });
    },
    acceptEdit() {
      const trimmedValue = this.editValue.trim();
      if (trimmedValue && trimmedValue !== this.value) {
        // Emit with old_label and new_label keys for data_menu.vue handler
        this.$emit('rename', trimmedValue);
        // Keep the new value in editValue so it displays while waiting for backend update
        this.editValue = trimmedValue;
      } else {
        // No change was made, treat as cancel
        this.$emit('cancel');
      }
      this.suppressPropagation = true;
      this.isEditing = false;
      // Clear the flag after the event loop to allow normal behavior again
      this.$nextTick(() => {
        this.suppressPropagation = false;
      });
    },
    onRootClick(event) {
      // Stop propagation when in edit mode or when suppression flag is set
      // (suppression flag prevents selection changes after keyboard-triggered edit completion)
      if (this.isEditing || this.suppressPropagation) {
        event.stopPropagation();
      }
    },
    onRootMousedown(event) {
      // Also stop mousedown propagation when in edit mode or when suppression flag is set
      // Some components handle selection on mousedown rather than click
      if (this.isEditing || this.suppressPropagation) {
        event.stopPropagation();
      }
    }
  }
};
</script>

<style scoped>
</style>

