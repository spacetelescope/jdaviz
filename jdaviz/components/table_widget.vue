<template>
  <div class="glue-table-container">
    <!-- Cell display/edit bar (always visible) -->
    <div class="glue-edit-bar elevation-1">
      <div class="edit-bar-cell-ref">
        <v-icon small class="mr-1">{{ selectedCell ? (selectedCell.editable ? 'mdi-table-edit' : 'mdi-table-eye') : 'mdi-table' }}</v-icon>
        <span class="edit-bar-label">{{ selectedCell ? selectedCell.column + ' [' + selectedCell.row + ']' : 'Click a cell to view' }}</span>
      </div>
      <div class="edit-bar-input-container">
        <v-text-field
          ref="editInput"
          v-model="editValue"
          class="edit-bar-input"
          dense
          hide-details
          single-line
          outlined
          :readonly="!selectedCell || !selectedCell.editable"
          :placeholder="selectedCell ? '' : 'Select a cell...'"
          @keyup.enter="commitEdit"
          @keyup.escape="cancelEdit"
        ></v-text-field>
      </div>
      <div class="edit-bar-actions" v-if="selectedCell && selectedCell.editable">
        <v-btn icon small color="success" @click="commitEdit" title="Confirm and move to next row (Enter)">
          <v-icon small>mdi-check</v-icon>
        </v-btn>
        <v-btn icon small color="error" @click="cancelEdit" title="Cancel (Escape)">
          <v-icon small>mdi-close</v-icon>
        </v-btn>
      </div>
    </div>

    <v-slide-x-transition appear>
      <v-data-table
        dense
        hide-default-header
        :headers="[...headers]"
        :items="items"
        :footer-props="{'items-per-page-options': [10,20,50,100]}"
        :options.sync="options"
        :items_per_page.sync="items_per_page"
        :server-items-length="total_length"
        :class="['elevation-1', 'glue-data-table', scrollable && 'glue-data-table--scrollable']"
        :style="scrollable && height != null && `height: ${height}`"
      >
      <template v-slot:header="props">
        <thead>
          <tr>
            <th :style="'padding: 0 10px; width: '+Math.max(1, Math.ceil(Math.log10(total_length)))*20+'px'">#</th>
            <th style="padding: 0 1px; width: 30px" v-if="selection_enabled">
              <v-btn icon color="primary" text small @click="toggle_select_all">
                <v-icon>{{ all_selected ? 'check_box' : (checked.length > 0 ? 'indeterminate_check_box' : 'check_box_outline_blank') }}</v-icon>
              </v-btn>
            </th>
            <th style="padding: 0 1px" v-for="(header, index) in headers_selections" :key="header.text">
              <v-icon style="padding: 0 1px" :key="index" :color="selection_colors[index]">brightness_1</v-icon>
            </th>

            <th v-for="header in headers"
                :key="header.text"
                class="jdaviz-col-header"
                :class="{'jdaviz-col-header--editing': editingHeader === header.value}"
                @click="editingHeader === null && sort_column(header.value)"
            >
              <!-- Normal display: label + sort arrow always visible; hover icons overlay on top-right -->
              <template v-if="editingHeader !== header.value">
                {{ header.text }}
                <v-icon x-small v-if="options.sortBy && options.sortBy[0] === header.value">
                  {{ options.sortDesc && options.sortDesc[0] ? 'arrow_drop_down' : 'arrow_drop_up' }}
                </v-icon>
                <!-- Hover action icons: absolutely positioned so they never push the label or widen the column -->
                <span v-if="non_removable_headers.indexOf(header.value) === -1"
                      class="jdaviz-col-header__actions">
                  <v-icon x-small class="jdaviz-col-header__icon"
                          @click.stop="enterHeaderRename(header.value)"
                          title="Rename column">mdi-pencil</v-icon>
                  <v-icon x-small class="jdaviz-col-header__icon"
                          @click.stop="enterHeaderRemove(header.value)"
                          title="Delete column">mdi-delete</v-icon>
                </span>
              </template>

              <!-- Rename mode: [___input___] [cancel] [accept] -->
              <template v-else-if="headerMode === 'rename'">
                <span style="display: inline-flex; align-items: center; gap: 4px;">
                  <input :data-header="header.value"
                         v-model="headerEditValue"
                         @keyup.enter.stop="acceptHeader(header.value)"
                         @keyup.escape.stop="cancelHeader()"
                         @click.stop
                         class="jdaviz-header-edit-input"
                  />
                  <v-icon x-small @click.stop="cancelHeader()"
                          style="cursor: pointer;" title="Cancel (Esc)">mdi-close</v-icon>
                  <v-icon x-small @click.stop="acceptHeader(header.value)"
                          style="cursor: pointer;" title="Accept (Enter)">mdi-check</v-icon>
                </span>
              </template>

              <!-- Remove confirm mode: warning badge [!] remove 'X'? [cancel] [confirm delete] -->
              <template v-else-if="headerMode === 'remove'">
                <span class="jdaviz-header-remove-confirm">
                  <v-icon x-small style="color: #F57C00;">mdi-alert</v-icon>
                  <span>remove '{{ header.text }}'?</span>
                  <v-icon x-small @click.stop="cancelHeader()"
                          style="cursor: pointer;" title="Cancel">mdi-close</v-icon>
                  <v-icon x-small @click.stop="deleteHeader(header.value)"
                          style="cursor: pointer;" title="Confirm delete">mdi-delete</v-icon>
                </span>
              </template>
            </th>
          </tr>
        </thead>
      </template>

      <template v-slot:item="props">
        <tr @click="on_row_clicked(props.item.__row__)" :class="{'highlightedRow': props.item.__row__ === highlighted}">
          <td style="padding: 0 10px" class="text-xs-left">
            <i>{{ props.item.__row__ }}</i>
          </td>
          <td style="padding: 0 1px" class="text-xs-left" v-if="selection_enabled">
            <v-checkbox
              hide-details style="margin-top: 0; padding-top: 0"
              :input-value="checked.indexOf(props.item.__row__) != -1"
              :key="props.item.__row__"
              @change="(value) => select({checked: value, row: props.item.__row__})"
            />
          </td>
          <td style="padding: 0 1px" :key="header.text" v-for="(header, index) in headers_selections">
            <v-fade-transition leave-absolute>
              <v-icon
                v-if="props.item[header.value]"
                v-model="props.item[header.value]"
                :color="selection_colors[index]"
              >brightness_1</v-icon>
            </v-fade-transition>
          </td>
          <td v-for="header in headers"
              :key="header.text"
              class="text-truncate text-no-wrap glue-selectable-cell"
              :class="{'glue-cell-selected': isSelected(props.item.__row__, header.value)}"
              :title="props.item[header.value]"
              @click.stop="selectCell(props.item.__row__, header.value, props.item[header.value], header.editable)"
          >{{ props.item[header.value] }}</td>
        </tr>
      </template>
      </v-data-table>
    </v-slide-x-transition>
  </div>
</template>

<script>
module.exports = {
  data: function() {
    return {
      selectedCell: null,   // { row, column, editable }
      editValue: '',
      editingHeader: null,  // column value currently in rename/remove mode
      headerMode: null,     // 'rename' | 'remove' | null
      headerEditValue: ''   // live text in the rename input
    };
  },
  watch: {
    header_enter_edit_mode(val) {
      if (!val) return;
      this.editingHeader = val;
      this.headerMode = 'rename';
      this.headerEditValue = val;
      this.$nextTick(() => {
        const input = this.$el.querySelector(`input[data-header="${val}"]`);
        if (input) { input.focus(); input.select(); }
      });
    }
  },
  methods: {
    enterHeaderRename(column) {
      const header = this.headers.find(h => h.value === column);
      this.headerEditValue = header ? header.text : column;
      this.editingHeader = column;
      this.headerMode = 'rename';
      this.$nextTick(() => {
        const input = this.$el.querySelector(`input[data-header="${column}"]`);
        if (input) { input.focus(); input.select(); }
      });
    },
    enterHeaderRemove(column) {
      this.editingHeader = column;
      this.headerMode = 'remove';
    },
    acceptHeader(column) {
      const newName = this.headerEditValue.trim();
      this.editingHeader = null;
      this.headerMode = null;
      this.headerEditValue = '';
      if (newName && newName !== column) {
        this.commit_header_edit({ column, newName });
      }
    },
    cancelHeader() {
      this.editingHeader = null;
      this.headerMode = null;
      this.headerEditValue = '';
    },
    deleteHeader(column) {
      this.editingHeader = null;
      this.headerMode = null;
      this.headerEditValue = '';
      this.delete_header({ column });
    },
    selectCell(row, column, currentValue, editable) {
      this.selectedCell = { row: row, column: column, editable: editable };
      this.editValue = currentValue !== null && currentValue !== undefined ? String(currentValue) : '';
      if (editable) {
        this.$nextTick(() => {
          if (this.$refs.editInput) {
            this.$refs.editInput.focus();
          }
        });
      }
    },
    cancelEdit() {
      this.selectedCell = null;
      this.editValue = '';
    },
    commitEdit() {
      if (this.selectedCell && this.selectedCell.editable) {
        const currentColumn = this.selectedCell.column;
        const currentRow = this.selectedCell.row;
        const isEditable = this.selectedCell.editable;
        this.cell_edited({
          row: currentRow,
          column: currentColumn,
          value: this.editValue
        });
        const nextRow = currentRow + 1;
        if (nextRow < this.total_length) {
          const nextItem = this.items.find(item => item.__row__ === nextRow);
          if (nextItem) {
            this.selectCell(nextRow, currentColumn, nextItem[currentColumn], isEditable);
          } else {
            this.selectedCell = null;
            this.editValue = '';
          }
        } else {
          this.selectedCell = null;
          this.editValue = '';
        }
      }
    },
    isSelected(row, column) {
      return this.selectedCell !== null &&
             this.selectedCell.row === row &&
             this.selectedCell.column === column;
    }
  }
}
</script>

<style id="jdaviz_table_widget">
/* ---- Base table styles (mirrors glue_table) ---- */
.glue-table-container {
  display: flex;
  flex-direction: column;
}

.glue-edit-bar {
  display: flex;
  align-items: center;
  padding: 4px 8px;
  background-color: #f5f5f5;
  border: 1px solid #e0e0e0;
  border-bottom: none;
  border-radius: 4px 4px 0 0;
  gap: 8px;
}

.edit-bar-cell-ref {
  display: flex;
  align-items: center;
  padding: 4px 8px;
  background-color: #fff;
  border: 1px solid #e0e0e0;
  border-radius: 4px;
  min-width: 120px;
  font-size: 12px;
  color: #666;
}

.edit-bar-label {
  font-family: monospace;
  font-weight: 500;
}

.edit-bar-input-container {
  flex: 1;
}

.edit-bar-input {
  margin: 0;
  padding: 0;
}

.edit-bar-input .v-input__slot {
  min-height: 32px !important;
  background-color: #fff !important;
}

.edit-bar-actions {
  display: flex;
  gap: 4px;
}

.highlightedRow {
  background-color: #E3F2FD;
}

.glue-data-table .v-data-table__wrapper {
  overflow-x: auto;
}

.glue-data-table table {
  table-layout: auto;
}

.glue-data-table th,
.glue-data-table td {
  white-space: nowrap;
  max-width: 300px;
  overflow: hidden;
  text-overflow: ellipsis;
}

.glue-data-table--scrollable .v-data-table__wrapper {
  overflow-y: auto;
  height: calc(100% - 59px);
}

.glue-data-table--scrollable thead > tr {
  position: sticky;
  top: 0;
}

.glue-data-table--scrollable .v-data-table__wrapper,
.glue-data-table--scrollable .v-data-table__wrapper > table,
.glue-data-table--scrollable .v-data-table__wrapper > table thead,
.glue-data-table--scrollable .v-data-table__wrapper > table thead * {
  background-color: inherit;
}

.glue-data-table--scrollable .v-data-table__wrapper > table thead {
  position: relative;
  z-index: 1;
}

.glue-selectable-cell {
  cursor: pointer;
}

.glue-selectable-cell:hover {
  background-color: #f5f5f5;
}

.glue-cell-selected {
  background-color: #E3F2FD !important;
  box-shadow: inset 0 0 0 2px #1976D2;
}

/* ---- Column header hover-edit styles ---- */

/* The <th> is relatively positioned so the overlay icons can sit on top.
   overflow: visible is required so the absolutely-positioned actions span
   isn't clipped by the base .glue-data-table th { overflow: hidden } rule.
   color is explicitly set to override the Vuetify theme rule that can make
   thead th text white in some jdaviz theme configurations. */
.jdaviz-col-header {
  position: relative;
  cursor: pointer;
  user-select: none;
  white-space: nowrap;
  padding: 0 8px !important;
  overflow: visible !important;
  color: rgba(0, 0, 0, 0.6) !important;
}

.jdaviz-col-header--editing {
  cursor: default;
  padding: 2px 6px !important;
}

/* Label spans the full cell width; icons will overlay on top.
   No wrapper element needed — text sits directly inside the <th>. */

/* Action icons: hidden by default, revealed on <th> hover via opacity.
   position: absolute keeps them from ever contributing to cell width. */
.jdaviz-col-header__actions {
  position: absolute;
  right: 2px;
  top: 50%;
  transform: translateY(-50%);
  display: inline-flex;
  align-items: center;
  gap: 1px;
  opacity: 0;
  transition: opacity 0.15s;
  background: linear-gradient(to right, transparent, rgba(240,240,240,0.92) 25%);
  padding-left: 8px;
  pointer-events: none;
}

/* Show icons when hovering the <th> (but not when in editing mode) */
.jdaviz-col-header:not(.jdaviz-col-header--editing):hover .jdaviz-col-header__actions {
  opacity: 1;
  pointer-events: auto;
}

.jdaviz-col-header__icon {
  cursor: pointer;
}

/* Rename input — matches plugin-editable-select text field look */
.jdaviz-header-edit-input {
  font-size: 12px;
  border: 1px solid #90CAF9;
  border-radius: 3px;
  padding: 1px 5px;
  width: 110px;
  outline: none;
  vertical-align: middle;
  background: #fff;
}

.jdaviz-header-edit-input:focus {
  border-color: #1976D2;
  box-shadow: 0 0 0 2px rgba(25, 118, 210, 0.2);
}

/* Remove-confirm badge — matches plugin-editable-select v-alert warning look */
.jdaviz-header-remove-confirm {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  background: #FFF3CD;
  border: 1px solid #FFC107;
  border-radius: 3px;
  padding: 2px 6px;
  font-size: 11px;
  white-space: nowrap;
  vertical-align: middle;
}
</style>
