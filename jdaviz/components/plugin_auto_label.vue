<template>
  <v-row>
    <v-form ref="form" style="width: 100%">
      <v-text-field
        ref="textField"
        :value="displayValue"
        @keyup="if(auto) {$emit('update:auto', false)}; $emit('update:label', $event.srcElement._value)"
        @mouseenter="showIcon = true"
        @mouseleave="showIcon = false"
        :label="label_label"
        :hint="label_hint"
        :rules="[(e) => label_invalid_msg || true]"
        persistent-hint
      >
        <template v-slot:append>
          <j-tooltip v-if="!auto || showIcon" :tooltipcontent="auto ? 'Using default label (click to use custom label)' : 'Using custom label (click to use default label)'">
            <v-btn icon small @click="() => {$emit('update:auto', !auto)}" style="padding-bottom: 4px" @mouseenter="showIcon = true" @mouseleave="showIcon = false">
              <v-icon :color="auto ? 'accent' : ''" style="transform: rotate(180deg);">mdi-label</v-icon>
            </v-btn>
          </j-tooltip>
        </template>
      </v-text-field>   
    </v-form>
  </v-row>
</template>
<script>
module.exports = {
  props: ['label', 'label_default', 'auto', 'label_label', 'label_hint', 'label_invalid_msg'],
  data: function() {
      return {
          displayValue: this.label_default,
          showIcon: false,
      }
  },
  watch: {
       // watching of label_default and label_auto are handled in python
       label() {
          if(this.$props.auto && this.displayValue != this.$props.label && this.$props.label != this.$props.label_default) {
            // then the label traitlet itself was changed (perhaps by the user), so we need to 
            // disable the auto-syncing between label_default -> label
            this.$emit('update:auto', false);
          }
          this.displayValue = this.$props.label;
       },
       label_invalid_msg() {
          this.$refs.form.validate();
       }
  }
};
</script>
