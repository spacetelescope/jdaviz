<template>
  <j-tray-plugin
    :description="docs_description"
    v-model:scroll_to="scroll_to">

    <j-flex-row>
      <j-docs-link :link="'https://jdaviz.readthedocs.io/en/'+vdocs+'/'" linktext="Jdaviz Documentation">
      </j-docs-link>
    </j-flex-row>

    <j-flex-row>
      <v-text-field class="v-messages v-messages__message text--secondary"
        v-model="jdaviz_version"
        label="Version"
        hint="Version of installed Jdaviz."
        readonly>
      </v-text-field>
    </j-flex-row>

    <j-flex-row v-if="not_is_latest">
      <span class="v-messages v-messages__message text--secondary" style="color: red !important">
        A newer version ({{ jdaviz_pypi }}) is available from PyPI.
      </span>
      <j-docs-link link="https://pypi.org/project/jdaviz/" linktext="Go to PyPI">
        Please update Jdaviz and restart your session.
      </j-docs-link>
    </j-flex-row>

    <j-flex-row>
      <j-docs-link link="https://github.com/spacetelescope/jdaviz/blob/main/CHANGES.rst" linktext="Change Log">
        To see list of changes, go to your version section in the

      </j-docs-link>
    </j-flex-row>

    <j-flex-row>
      <j-docs-link link="https://jwsthelp.stsci.edu" linktext="JWST Help Desk">
        For further assistance, please contact the

      </j-docs-link>
    </j-flex-row>

  </j-tray-plugin>
</template>
