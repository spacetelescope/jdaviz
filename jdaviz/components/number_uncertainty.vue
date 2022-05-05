<template>
  <span>
    {{ valueTrunc }} {{ uncertTrunc ? "&#177; " + uncertTrunc : null}} {{ unit }}
  </span>
</template>

<script>

module.exports = {
  data: function () {
    const defaultDigs = this.defaultDigs || 5;
    return {
      // default to passed values, whenever value or uncertainty are changed
      // updateTruncatedValues will overwrite the displayed values
      defaultDigs: defaultDigs,
      valueTrunc: this.value,
      uncertTrunc: this.uncertainty
    }
  },
  methods: {
    updateTruncatedValues() {
      var nDigs = this.defaultDigs;
      if (this.uncertainty === undefined || parseFloat(this.uncertainty) == 0 || this.uncertainty == '') {
        // then treat as no uncertainty
        this.uncertTrunc = null;
      } else {
        // then uncertainty was provided, so we'll round the uncertainty to 2 significant digits
        this.uncertTrunc = +parseFloat(this.uncertainty).toPrecision(2);

        // we then want to round the value to the same place, we do that by determining the power
        // of both the value and uncertainty and adding the two places that we already showed for 
        // the uncertainty above.
        nDigs = 2 + Math.ceil(Math.log10(Math.abs(parseFloat(this.value)))) - Math.ceil(Math.log10(this.uncertainty));
        if (nDigs < 1) {
          // this should only happen if the uncertainty was larger than the value, make sure to show
          // at least one digit
          nDigs = 1
        }
      }

      this.valueTrunc = +parseFloat(this.value).toPrecision(nDigs);
    },
  },
  watch: {
    value() {
      this.updateTruncatedValues();
    },
    uncertainty() {
      this.updateTruncatedValues();
    }
  },
  mounted() {
    // this should never need to be used in practice, but if using hot-reloading, the UI will
    // fallback on the values defined in data above.  This forces the truncation logic to trigger.
    this.updateTruncatedValues();
  },
  props: ['value', 'uncertainty', 'unit', 'defaultDigs'],
};
</script>
