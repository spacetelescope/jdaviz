<template>
  <v-tooltip v-if="getTooltipHtml()" bottom :open-delay="getOpenDelay()"
      :nudge-bottom="getNudgeBottom()">
    <template v-slot:activator="{ on, attrs }">
      <span v-bind="attrs" v-on="on" :style="getSpanStyle()">
        <slot></slot>
      </span>
    </template>
    <span v-html="getTooltipHtml()"></span>
  </v-tooltip>
  <span v-else :style="getSpanStyle()">
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
  'app-help': 'Open docs in new tab',
  'app-snackbar-history': 'Toggle logger overlay',
  'app-toolbar-plugins': 'Data analysis plug-ins',
  'app-toolbar-popout': `Display in a new window<br /><br />
    <div style="width: 200px; border: 1px solid gray;" class="pa-2">
      <strong>Note:</strong>
      some ad blockers or browser settings may block popup windows,
      causing this feature not to work.
    </div>`,
  'plugin-popout': `Display in a new window<br /><br />
    <div style="width: 200px; border: 1px solid gray;" class="pa-2">
      <strong>Note:</strong>
      some ad blockers or browser settings may block popup windows,
      causing this feature not to work.
    </div>`, 

  'g-data-tools': 
    'Load data from file',
  'g-subset-tools': 
    'Select, create, and delete subsets',
  'g-subset-mode':
    'Operation performed by subset selection in viewer',
  'g-unified-slider':
    'Grab slider to slice through cube or select slice number',
  'g-redshift-slider':
    'Move the slider to change the redshift of the source and line wavelengths',
  'lock-row-toggle':
    'Use the same display parameters for all images and spectra',
  'create-image-viewer':
    'Create new image viewer',
  'coords-info-cycle': 'Cycle selected layer used for mouseover information and markers plugin',

  // viewer toolbars
  'viewer-toolbar-data': 'Select dataset(s) to display in this viewer',
  'viewer-toolbar-figure': 'Tools: pan, zoom, select region, save',
  'viewer-toolbar-figure-save': 'Save figure',
  'viewer-toolbar-menu': 'Adjust display: contrast, bias, stretch',
  'viewer-toolbar-more': 'More options...',
  'viewer-data-select-enabled': 'Allow multiple entries (click to enable replace)',
  'viewer-data-radio-enabled': 'Replace current entry (click to enable multi-select)',
  'viewer-data-select': 'Toggle visibility of all layers associated with this data entry',
  'viewer-data-radio': 'Switch visibility to layers associated with this data entry',
  'viewer-data-enable': 'Load data entry into this viewer',
  'viewer-data-disable': 'Disable data within this viewer (will be hidden and unavailable from plugins until re-enabled)',
  'viewer-data-delete': 'Remove data entry across entire app',

  'table-prev': 'Select previous row in table',
  'table-next': 'Select next row in table',
  'table-play-pause-toggle': 'Toggle cycling through rows of table',
  'table-play-pause-delay': 'Set delay before cycling to next entry',
  'plugin-plot-options-multiselect-toggle': 'Toggle between simple (single-select) and advanced (multiselect)',
  'plugin-plot-options-mixed-state': 'Current values are mixed, click to sync at shown value',
  'plugin-model-fitting-add-model': 'Create model component',
  'plugin-model-fitting-param-fixed': 'Check the box to freeze parameter value',
  'plugin-model-fitting-reestimate-all': 'Re-estimate initial values based on the current data/subset selection for all free parameters based on current display units',
  'plugin-model-fitting-reestimate': 'Re-estimate initial values based on the current data/subset selection for all free parameters in this component',
  'plugin-unit-conversion-apply': 'Apply unit conversion',
  'plugin-line-lists-load': 'Load list into "Loaded Lines" section of plugin',
  'plugin-line-lists-plot-all-in-list': 'Plot all lines in this list',
  'plugin-line-lists-erase-all-in-list': 'Hide all lines in this list',
  'plugin-line-lists-plot-all': 'Plot all lines from every loaded list',
  'plugin-line-lists-erase-all': 'Hide all lines from every loaded list',
  'plugin-line-lists-line-name': 'Name this whatever you want',
  'plugin-line-lists-custom-rest': 'This is a float or integer',
  'plugin-line-lists-add-custom-line': 'Add line to the custom list',
  'plugin-line-lists-line-identify-chip-active': 'Currently highlighted line.  Click to clear current selection.',
  'plugin-line-lists-line-identify-chip-inactive': 'No line currently highlighted.  Use selection tool in spectrum viewer to identify a line.',
  'plugin-line-lists-line-visible': 'Toggle showing the line in the spectrum viewer',
  'plugin-line-lists-line-identify': 'Highlight this line in the spectrum viewer for easy identification',
  'plugin-line-lists-color-picker': 'Change the color of this list',
  'plugin-line-lists-spectral-range': 'Toggle filter to only lines observable within the range of the Spectrum Viewer',
  'plugin-line-analysis-sync-identify': 'Lock/unlock selection with identified line',
  'plugin-line-analysis-assign': 'Assign the centroid wavelength and update the redshift',
  'plugin-moment-save-fits': 'Save moment map as FITS file',
  'plugin-link-apply': 'Apply linking to data',
}


module.exports = {
  props: ['tooltipcontent', 'tipid', 'delay', 'nudgebottom', 'span_style'],
  methods: {
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
    getSpanStyle() {
      return this.$props.span_style || "height: inherit; display: inherit";
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
