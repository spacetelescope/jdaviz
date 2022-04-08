<template>
  <v-row>
    <v-form ref="form" style="width: 100%">
      <v-text-field
        ref="textField"
        :value="displayValue"
        @keyup="if(auto) {$emit('update:auto', false)}; $emit('update:label', $event.srcElement._value)"
        :label="label_label"
        :hint="label_hint"
        :rules="[(e) => label_invalid_msg || true]"
        persistent-hint
      >
        <template v-slot:append>
          <j-tooltip tipid='plugin-label-auto'>
            <v-btn icon @click="() => {$emit('update:auto', !auto)}" style="margin-bottom: 6px">
              <v-icon :color="auto ? 'accent' : ''">mdi-auto-fix</v-icon>
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
          // default value is the one that was intially passed
          displayValue: this.label_default
      }
  },
  watch: {
       auto() {
           if(this.$props.auto) {
               // then the label_default/automatic label was changed via the traitlet, and we
               // need to mirror that in the label itself, which will then trigger the watcher
               // below to update the displayed label
               this.$emit('update:label', this.$props.label_default);
           }
       },
       label_default() {
           if(this.$props.auto) {
             this.$emit('update:label', this.$props.label_default);
           }
       },
       label() {
          const currentValue = this.displayValue;
          if(this.$props.auto && currentValue != this.$props.label && this.$props.label != this.$props.label_default) {
            // then the label traitlet itself was changed (perhaps by the user), 
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
