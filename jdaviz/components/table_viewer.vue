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
        <v-btn
          icon
          small
          color="success"
          @click="commitEdit"
          title="Confirm and move to next row (Enter)"
        >
          <v-icon small>mdi-check</v-icon>
        </v-btn>
        <v-btn
          icon
          small
          color="error"
          @click="cancelEdit"
          title="Cancel (Escape)"
        >
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
      <template v-slot:headers>
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
                @click="onHeaderClick(header.value)"
                @mouseenter="hoverHeader = header.value"
                @mouseleave="hoverHeader = null"
                style="cursor: pointer; user-select: none; padding: 0 8px; white-space: nowrap; position: relative;"
                :style="editingHeader === header.value ? {minWidth: '240px'} : {}"
            >
              {{ header.text }}
              <v-icon v-if="options.sortBy && options.sortBy[0] === header.value">
                {{ options.sortDesc && options.sortDesc[0] ? 'arrow_drop_down' : 'arrow_drop_up' }}
              </v-icon>
              <v-icon size="x-small" v-if="hoverHeader === header.value && editingHeader !== header.value && header.renameable" @click.stop="enterHeaderRename(header.value)" style="cursor:pointer;margin-left:2px" title="Rename column">mdi-pencil</v-icon>
              <v-icon size="x-small" v-if="hoverHeader === header.value && editingHeader !== header.value && header.removable" @click.stop="enterHeaderRemove(header.value)" style="cursor:pointer" title="Delete column">mdi-delete</v-icon>

              <!-- Rename mode: fills the th (min-width ensures it fits) -->
              <span v-if="editingHeader === header.value && headerMode === 'rename'" @click.stop style="position:absolute;top:0;left:0;right:0;bottom:0;display:inline-flex;align-items:center;gap:4px;background:white;padding:0 4px;z-index:1;"><input :data-header="header.value" v-model="headerEditValue" @keyup.enter.stop="acceptHeader(header.value)" @keyup.escape.stop="cancelHeader()" @click.stop class="glue-header-edit-input"/><v-icon size="x-small" @click.stop="cancelHeader()" style="cursor:pointer" title="Cancel (Esc)">mdi-close</v-icon><v-icon size="x-small" @click.stop="acceptHeader(header.value)" style="cursor:pointer" title="Accept (Enter)">mdi-check</v-icon></span>

              <!-- Delete confirmation: fills the th (min-width ensures it fits) -->
              <span v-if="editingHeader === header.value && headerMode === 'remove'" @click.stop style="position:absolute;top:0;left:0;right:0;bottom:0;display:inline-flex;align-items:center;gap:4px;background:#FFF3CD;border:1px solid #FFC107;padding:0 4px;z-index:1;font-size:11px;white-space:nowrap;"><v-icon size="x-small" style="color:#F57C00;">mdi-alert</v-icon><span>remove '{{ header.text }}'?</span><v-icon size="x-small" @click.stop="cancelHeader()" style="cursor:pointer" title="Cancel">mdi-close</v-icon><v-icon size="x-small" @click.stop="deleteHeader(header.value)" style="cursor:pointer" title="Confirm delete">mdi-delete</v-icon></span>
            </th>
          </tr>
      </template>
      <template v-slot:item="props">
        <tr @click="on_row_clicked(props.item.__row__)" :class="{'highlightedRow': props.item.__row__ === highlighted}">
          <td style="padding: 0 10px" class="text-left">
            <i>{{ props.item.__row__ }}</i>
          </td>
          <td style="padding: 0 1px" class="text-left" v-if="selection_enabled">
            <v-checkbox
              hide-details style="margin-top: 0; padding-top: 0"
              :model-value="checked.indexOf(props.item.__row__) != -1"
              :key="props.item.__row__"
              @update:modelValue="(value) => select({checked: value, row: props.item.__row__})"
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
      selectedCell: null,  // { row: number, column: string, editable: boolean }
      editValue: '',
      hoverHeader: null,    // column value currently being hovered
      editingHeader: null,  // column value currently in rename/remove mode
      headerMode: null,     // 'rename' | 'remove' | null
      headerEditValue: ''   // live text in the rename input
    };
  },
  methods: {
    onOptionsUpdate(vuetifyOpts) {
      // Propagate page/itemsPerPage changes to Python; sort is handled by sort_column
      const newPage = vuetifyOpts.page;
      const newIpp = vuetifyOpts.itemsPerPage;
      if (newPage !== this.options.page || newIpp !== this.options.itemsPerPage) {
        this.options = { ...this.options, page: newPage, itemsPerPage: newIpp };
      }
    },
    // ---- header editing ----
    onHeaderClick(column) {
      if (this.editingHeader === null) { this.sort_column(column); }
    },
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
        this.rename_column({ column, newName });
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
      this.remove_column({ column });
    },
    // ---- cell editing ----
    toggleSort(column) {
      this.sort_column(column);
    },
    selectCell(row, column, currentValue, editable) {
      this.selectedCell = { row: row, column: column, editable: editable };
      this.editValue = currentValue !== null && currentValue !== undefined ? String(currentValue) : '';
      // Focus the edit input after Vue updates the DOM (only if editable)
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
        // Commit the edit
        this.cell_edited({
          row: currentRow,
          column: currentColumn,
          value: this.editValue
        });
        // Move to the next row in the same column
        const nextRow = currentRow + 1;
        if (nextRow < this.total_length) {
          // Find the current value for the next cell
          const nextItem = this.items.find(item => item.__row__ === nextRow);
          if (nextItem) {
            this.selectCell(nextRow, currentColumn, nextItem[currentColumn], isEditable);
          } else {
            // Next row might not be in current page, just clear selection
            this.selectedCell = null;
            this.editValue = '';
          }
        } else {
          // No more rows, clear selection
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

<style id="glue_table">
/* Table container */
.glue-table-container {
  display: flex;
  flex-direction: column;
}

/* Edit bar (Excel-style formula bar) */
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

.glue-data-table {
  min-height: 250px;
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
.glue-data-table--scrollable .v-data-table__wrapper > table thead *
{
  background-color: inherit;
}

/* prevent checkboxes overlaying the table header */
.glue-data-table--scrollable .v-data-table__wrapper > table thead {
  position: relative;
  z-index: 1;
}

/* Selectable cell styles */
.glue-selectable-cell {
  cursor: pointer;
}

.glue-selectable-cell:hover {
  background-color: #f5f5f5;
}

/* Visual cue for selected cell */
.glue-cell-selected {
  background-color: #E3F2FD !important;
  box-shadow: inset 0 0 0 2px #1976D2;
}

/* ---- Column header rename / delete styles ---- */
.glue-header-edit-input {
  font-size: 12px;
  border: 1px solid #90CAF9;
  border-radius: 3px;
  padding: 1px 5px;
  width: 110px;
  outline: none;
  vertical-align: middle;
  background: #fff;
}

.glue-header-edit-input:focus {
  border-color: #1976D2;
  box-shadow: 0 0 0 2px rgba(25, 118, 210, 0.2);
}
</style>
