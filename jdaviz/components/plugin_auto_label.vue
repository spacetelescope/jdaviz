<template>
  <v-row>
    <v-form ref="form" style="width: 100%">
      <v-text-field
        ref="textField"
        :value="displayValue"
        @keyup="if(auto) {if ($event.srcElement._value === displayValue) {return}; $emit('update:auto', false)}; $emit('update:value', $event.srcElement._value)"
        @mouseenter="showIcon = true"
        @mouseleave="showIcon = false"
        :label="label"
        :hint="hint"
        :rules="[(e) => invalid_msg || true]"
        persistent-hint
      >
        <template v-slot:append>
          <j-tooltip v-if="!auto || showIcon" :tooltipcontent="auto ? 'Using default (click to use custom)' : 'Using custom (click to use default)'">
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
  props: ['value', 'default', 'auto', 'label', 'hint', 'invalid_msg'],
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
  }
};
</script>
