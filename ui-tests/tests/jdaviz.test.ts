// Copyright (c) Jupyter Development Team.
// Distributed under the terms of the Modified BSD License.

import { galata, describe, test } from '@jupyterlab/galata';
import * as path from 'path';
const klaw = require('klaw-sync');

jest.setTimeout(600000);

const filterUpdateNotebooks = item => {
  const basename = path.basename(item.path);
  return basename.includes('_update');
}

describe('jdaviz Visual Regression', () => {
  beforeAll(async () => {
    await galata.resetUI();
  });

  afterAll(async () => {
    galata.context.capturePrefix = '';
  });

  test('Upload files to JupyterLab', async () => {
    await galata.contents.moveDirectoryToServer(
      path.resolve(__dirname, `./notebooks`),
      'uploaded'
    );
    expect(
      await galata.contents.fileExists('uploaded/app.ipynb')
    ).toBeTruthy();
  });

  test('Refresh File Browser', async () => {
    await galata.filebrowser.refresh();
  });

  test('Open directory uploaded', async () => {
    await galata.filebrowser.openDirectory('uploaded');
    expect(
      await galata.filebrowser.isFileListedInBrowser('app.ipynb')
    ).toBeTruthy();
  });

  test('Check jdaviz first renders', async () => {
    const paths = klaw('tests/notebooks', {filter: item => !filterUpdateNotebooks(item), nodir: true});
    const notebooks = paths.map(item => path.basename(item.path));

    let results = [];

    for (const notebook of notebooks) {
      galata.context.capturePrefix = notebook;

      await galata.notebook.open(notebook);
      expect(await galata.notebook.isOpen(notebook)).toBeTruthy();
      await galata.notebook.activate(notebook);
      expect(await galata.notebook.isActive(notebook)).toBeTruthy();

      let numCellImages = 0;

      const getCaptureImageName = (id: number): string => {
        return `cell-${id}`;
      };

      await galata.notebook.runCellByCell({
        onAfterCellRun: async (cellIndex: number) => {
          const cell = await galata.notebook.getCellOutput(cellIndex);
          if (cell) {
            if (
              await galata.capture.screenshot(
                getCaptureImageName(numCellImages),
                cell
              )
            ) {
              numCellImages++;
            }
          }
        }
      });

      for (let c = 0; c < numCellImages; ++c) {
        results.push(await galata.capture.compareScreenshot(getCaptureImageName(c)));
      }

      await galata.notebook.close(true);
    }

    for (const result of results) {
      expect(result).toBe('same');
    }
  });

  test('Check jdaviz update plot properties', async () => {
    const paths = klaw('tests/notebooks', {filter: item => filterUpdateNotebooks(item), nodir: true});
    const notebooks = paths.map(item => path.basename(item.path));

    let results = [];

    for (const notebook of notebooks) {
      galata.context.capturePrefix = notebook;

      await galata.notebook.open(notebook);
      expect(await galata.notebook.isOpen(notebook)).toBeTruthy();
      await galata.notebook.activate(notebook);
      expect(await galata.notebook.isActive(notebook)).toBeTruthy();

      let numCellImages = 0;

      const getCaptureImageName = (id: number): string => {
        return `cell-${id}`;
      };

      await galata.notebook.runCellByCell({
        onAfterCellRun: async (cellIndex: number) => {
          // Always get first cell output which must contain the plot
          const cell = await galata.notebook.getCellOutput(0);
          if (cell) {
            if (
              await galata.capture.screenshot(
                getCaptureImageName(numCellImages),
                cell
              )
            ) {
              numCellImages++;
            }
          }
        }
      });

      for (let c = 0; c < numCellImages; ++c) {
        results.push(await galata.capture.compareScreenshot(getCaptureImageName(c)));
      }

      await galata.notebook.close(true);
    }

    for (const result of results) {
      expect(result).toBe('same');
    }
  });

  test('Open home directory', async () => {
    await galata.filebrowser.openHomeDirectory();
  });

  test('Delete uploaded directory', async () => {
    await galata.contents.deleteDirectory('uploaded');
  });
});
