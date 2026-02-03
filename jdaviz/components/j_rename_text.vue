<template>
  <div :style="'display: flex; flex-direction: column; min-width: 0; width: 100%;' + (fontSize ? ' font-size: ' + fontSize + ';' : '')">
    <span v-if="isEditing && apiHintRename && showApiHint" class="api-hint" style="display: block; margin-bottom: 8px;">
      {{ apiHintRename }}('{{ value }}', '{{ editValue }}')
    </span>
    <span @click="onRootClick" @mousedown="onRootMousedown" @keydown.stop style="display: inline-flex; align-items: center; min-width: 0; flex: 1; width: 100%;">
      <!-- Display mode -->
      <span
        v-if="!isEditing"
        @mouseenter="hovering = true"
        @mouseleave="hovering = false"
        @mousedown.stop
        @dblclick.stop="startEditing"
        style="display: inline-flex; align-items: center; min-width: 0; flex: 1; width: 100%; caret-color: transparent;"
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
          style="margin-left: auto; cursor: pointer; flex-shrink: 0; visibility: hidden; width: 48px; min-width: 48px; text-align: right;"
          :style="hovering ? 'visibility: visible;' : ''"
          @click.stop="startEditing"
          @mousedown.stop
        >
          mdi-pencil
        </v-icon>
      </span>

      <!-- Edit mode: shows text field with cancel and confirm buttons -->
      <span
        v-if="isEditing"
        style="display: inline-flex; align-items: center; min-width: 0; flex: 1; width: 100%;"
      >
        <input
          ref="editInput"
          v-model="editValue"
          @keydown.enter.prevent="acceptEdit"
          @keydown.escape.prevent="cancelEdit"
          @click.stop
          @mousedown.stop
          class="rename-inline-input"
        />
        <span :style="'display: inline-flex; align-items: center; flex-shrink: 0; margin-left: auto; justify-content: flex-end;' + (smallIcons ? ' min-width: 48px;' : ' min-width: 56px;')">
          <j-tooltip tooltipcontent="Cancel change">
            <v-icon :small="smallIcons" style="cursor: pointer" @click.stop="cancelEdit" @mousedown.stop>mdi-close</v-icon>
          </j-tooltip>
          <j-tooltip :tooltipcontent="renameErrorMessage || 'Accept change'">
            <v-icon
              :small="smallIcons"
              style="cursor: pointer"
              :style="renameErrorMessage ? 'opacity: 0.5; cursor: not-allowed;' : ''"
              @click.stop="renameErrorMessage ? null : acceptEdit()"
              @mousedown.stop
            >mdi-check</v-icon>
          </j-tooltip>
        </span>
      </span>
    </span>
    <div v-if="isEditing && renameErrorMessage" class="rename-error-message">
      {{ renameErrorMessage }}
    </div>
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
    },
    fontSize: {
      type: String,
      default: ''
    },
    smallIcons: {
      type: Boolean,
      default: true
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
        // Focus the input element
        if (this.$refs.editInput) {
          this.$refs.editInput.focus();
          this.$refs.editInput.select();
        }
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
/* Inline input styled to match static text display */
.rename-inline-input {
  font-size: inherit;
  font-family: inherit;
  font-weight: inherit;
  line-height: inherit;
  color: inherit;
  background: transparent;
  border: none;
  border-bottom: 1px solid currentColor;
  outline: none;
  padding: 0;
  margin: 0;
  min-width: 50px;
  flex: 1;
}

.rename-inline-input:focus {
  border-bottom: 1px solid #1976d2;
}

/* Error message styling */
.rename-error-message {
  color: #ff5252;
  font-size: 12px;
  margin-top: 2px;
}

/* Ensure display mode text doesn't show any input cursor */
.rename-display-text {
  caret-color: transparent;
  user-select: text;
}
</style>

