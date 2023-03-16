<template>
  <j-tray-plugin
    description='Create and export markers.  Press "m" with the cursor over a viewer to log the mouseover information.  To change the selected layer, click the layer cycler in the mouseover information section of the app-level toolbar.'
    :link="'https://jdaviz.readthedocs.io/en/'+vdocs+'/'+config+'/plugins.html#markers'"
    :popout_button="popout_button">

    <jupyter-widget :widget="table_widget"></jupyter-widget> 

  </j-tray-plugin>
</template>
