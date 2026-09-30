<template>
  <j-flex-row>
    <v-form ref="form" style="width: 100%">
      <v-text-field
        variant="underlined"
        ref="textField"
        :model-value="displayValue"
        @update:modelValue="updateValue"
        @mouseenter="showIcon = true"
        @mouseleave="showIcon = false"
        :label="api_hints_enabled && api_hint ? api_hint : label"
        :class="api_hints_enabled && api_hint ? 'api-hint' : null"
        :hint="hint"
        :rules="[(e) => invalid_msg || true]"
        persistent-hint
      >
        <template v-slot:prepend-inner>
          <slot></slot>
        </template>
        <template v-slot:append-inner>
          <j-tooltip
            :disabled="auto && !showIcon"
            :tooltipcontent="auto ? 'Using default (click to use custom)' : 'Using custom (click to use default)'"
          >
            <v-btn
              variant="text"
              icon
              density="compact"
              class="auto-label-toggle"
              :class="{'auto-label-toggle--hidden': auto && !showIcon}"
              @click="() => {$emit('update:auto', !auto)}"
              @mouseenter="showIcon = true"
              @mouseleave="showIcon = false"
            >
              <v-icon :color="auto ? 'accent' : ''" style="transform: rotate(180deg);">mdi-label</v-icon>
            </v-btn>
          </j-tooltip>
        </template>
      </v-text-field>
    </v-form>
  </j-flex-row>
</template>
<script>
export default {
  props: ['value', 'default', 'auto', 'label', 'hint', 'invalid_msg', 'api_hint', 'api_hints_enabled'],
  data: function() {
      return {
          displayValue: this.auto ? this.default : this.value,
          showIcon: false,
      }
  },
  watch: {
       // watching of label_default and label_auto are handled in python
       value() {
          if(this.$props.auto && this.displayValue != this.$props.value && this.$props.value != this.$props.default) {
            // then the label traitlet itself was changed (perhaps by the user), so we need to
            // disable the auto-syncing between label_default -> label
            this.$emit('update:auto', false);
          }
          this.displayValue = this.$props.value;
       },
       invalid_msg() {
          this.$refs.form.validate();
       }
  },
  methods: {
       updateValue(value) {
          if(this.$props.auto && value === this.displayValue) {
            return;
          }
          if(this.$props.auto) {
            this.$emit('update:auto', false);
          }
          this.$emit('update:value', value);
       }
  }
};
</script>

<style scoped>
.auto-label-toggle {
  width: 32px !important;
  min-width: 32px !important;
  height: 32px !important;
  padding: 0 !important;
}

.auto-label-toggle--hidden {
  visibility: hidden;
  pointer-events: none;
}
</style>
