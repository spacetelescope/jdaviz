<template>
  <div @click="onRootClick" @mousedown="onRootMousedown" @keydown.stop="onRootKeydown">
    <!-- Display mode -->
    <div
      v-if="!isEditing"
      @mouseenter="hovering = true"
      @mouseleave="hovering = false"
      @click="handleClick"
      @dblclick.stop="startEditing"
      style="display: flex; align-items: center; justify-content: space-between; width: 100%; min-height: 48px;"
    >
      <div style="display: flex; align-items: center; flex-grow: 1;">
        <span
          :style="hovering ? 'cursor: pointer; text-decoration: underline;' : 'cursor: pointer;'"
        >
          {{ currentValue }}
        </span>
      </div>

      <!-- Pencil icon - visible on hover in display mode -->
      <v-icon
        v-if="hovering && showPencil"
        small
        style="margin-left: 8px; cursor: pointer; flex-shrink: 0;"
        @click.stop="startEditing"
        @mousedown.stop
      >
        mdi-pencil
      </v-icon>
    </div>

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
      :hint="editHint"
      persistent-hint
      style="margin-top: -8px; flex-grow: 1;"
    >
      <template v-slot:append>
        <j-tooltip tooltipcontent="Cancel change">
          <v-icon style="cursor: pointer" @click.stop="cancelEdit" @mousedown.stop>mdi-close</v-icon>
        </j-tooltip>
        <j-tooltip tooltipcontent="Accept change">
          <v-icon style="cursor: pointer" @click.stop="acceptEdit" @mousedown.stop>mdi-check</v-icon>
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
      editValue: this.value,
      clickTimer: null,
      clickCount: 0,
      suppressPropagation: false
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
    handleClick(event) {
      this.clickCount++;

      // Clear any existing timer
      if (this.clickTimer) {
        clearTimeout(this.clickTimer);
        this.clickTimer = null;
      }

      // If this is the second click, stop propagation to prevent selection toggle
      if (this.clickCount > 1) {
        event.stopPropagation();
        return;
      }

      // First click - set timer to reset count after double-click window
      this.clickTimer = setTimeout(() => {
        this.clickCount = 0;
        this.clickTimer = null;
      }, 250);
    },
    startEditing() {
      // Clear the click timer and reset count when editing starts
      if (this.clickTimer) {
        clearTimeout(this.clickTimer);
        this.clickTimer = null;
      }
      this.clickCount = 0;
      this.isEditing = true;
      this.editValue = this.value;
    },
    cancelEdit() {
      this.suppressPropagation = true;
      this.isEditing = false;
      this.editValue = this.value;
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
    },
    onRootKeydown() {
      // Stop keydown propagation when in edit mode or when suppression flag is set
      // This prevents the v-list-item-group from processing Enter/Escape keys
      if (this.isEditing || this.suppressPropagation) {
        // Already stopped by @keydown.stop, but keep the logic explicit
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

