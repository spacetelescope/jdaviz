<template>
  <tippy v-if="getDoctipHtml()" interactive ignoreAttributes 
      touch=false touchHold=false 
      distance="5" placement="bottom" :delay="getOpenDelay()" 
      duration="100" animation="scale">
    <template v-slot:trigger>
      <span style="display: inherit; height: inherit; outline: 1px dashed #c75109">
        <slot></slot>
      </span>
    </template>
    <span v-html="getDoctipHtml()"></span>
  </tippy>
  <v-tooltip v-else-if="getTooltipHtml()" bottom :open-delay="getOpenDelay()"
      :nudge-bottom="getNudgeBottom()">
    <template v-slot:activator="{ on, attrs }">
      <span v-bind="attrs" v-on="on" style="height: inherit">
        <slot></slot>
      </span>
    </template>
    <span v-html="getTooltipHtml()"></span>
  </v-tooltip>
  <span v-else style="height: inherit">
    <!-- in the case where there is no tooltip, just pass through the wrapped element -->
    <slot></slot>
  </span>
</template>

<script>
// define all tooltip content here.  Each key can be passed as tipid to
// any j-tooltip element.  The values must be a string, but can contain (valid)
// html.  If enabling a new tooltip, wrap the element in <j-tooltip tipid='...'>,
// pass doctips from state/props, and test to make sure layout isn't adversely
// affected by the wrapping divs.
const tooltips = {
  // app toolbar
  'app-toolbar-doctips': 'Toggle extended documentation tooltips',
  'app-toolbar-plugins': 'Toggle plugin menu',

  // viewer toolbars
  'viewer-toolbar-data': 'Toggle data menu',
  'viewer-toolbar-figure': 'Toggle zoom/pan/save options',
  'viewer-toolbar-figure-save': 'Save figure',
  'viewer-toolbar-menu': 'Toggle layer/viewer menu',
  'viewer-toolbar-more': 'More options...',

}
const doctips = {
  // app toolbar
  'g-data-tools': 
    'expanded explanation and link to docs for importing data',
  'g-subset-tools': 
    'expanded explanation and link to docs for creating subsets',
  'g-unified-slider':
    'expanded explanation and link to docs for using the slider',
  
  // viewer toolbars
  'viewer-toolbar-data': 
    'Change which data layers are enabled',
  'viewer-toolbar-layer': 
    'layer tab',
  'viewer-toolbar-viewer': 
    'viewer tab',
    
  // plugins menu
  'g-gaussian-smooth':
    // do some of these urls need to be viz-dependent?  If gaussian-smooth docs differ between specviz and cubeviz, for example.
    'gaussian smoothing plugin (<a href="https://jdaviz.readthedocs.io/en/latest/specviz/plugins.html#gaussian-smooth" target="_blank">read docs</a>)',
  'g-collapse':
    'model fitting plugin (<a href="https://jdaviz.readthedocs.io/en/latest/cubeviz/plugins.html#collapse" target="_blank">read docs</a>)',
  'g-model-fitting':
    'model fitting plugin (<a href="https://jdaviz.readthedocs.io/en/latest/specviz/plugins.html#model-fitting" target="_blank">read docs</a>)',
};

module.exports = {
  props: ['doctips', 'tooltipcontent', 'tipid', 'delay', 'nudgebottom'],
  methods: {
    getDoctipHtml() {
      if (!this.$props.doctips) {
        // fallback on (non-interactive) tooltip if either tooltipcontent
        // is provided or tipid is in tooltips dict, otherwise will not
        // show anything.
        return false;
      }
      return doctips[this.$props.tipid];
    },
    getTooltipHtml() {
      // use tooltipcontent if provided, default to tooltips dictionary
      // with passed tipid as the key
      
      if (this.$props.tooltipcontent) {
        return this.$props.tooltipcontent;
      }
      
      // Enable the following line to help determine ids to add to dictionary 
      // above.  This will show the tooltip id (in the tooltip) if no entry is 
      // in the tooltips dictionary above.
      //return tooltips[this.$props.tipid] || "tipid: "+this.$props.tipid;
      return tooltips[this.$props.tipid];
    },
    getOpenDelay() {
      return this.$props.delay || "0";
    },
    getNudgeBottom() {
      // useful for cases where some tooltips in a toolbar are wrapped around 
      // buttons but others around just the icon.  Only applies to tooltip,
      // not doctip.
      return this.$props.nudgebottom || 0;
    },
  }
};
</script>
