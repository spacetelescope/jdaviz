# Web-only interface

This directory demonstrates generating javascript from python code and
mounting on a basic html page. It setups up a kernel manager to connect to a
running jupyter kernel instance used to execute the python code. The html
page is hosted using yarn `http-server`, while the stand-alone app is run
using electron.

# Pre-setup

1. At your command line, clone the `jdaviz` repository via `git clone https://github.com/nmearl/jdaviz`.
2. Install the `jdaviz` python package in your environment by running `pip install -e .` at your command line from the cloned directory.
3. (Optional) Ensure that the `jdaviz` code works properly in your environment by running one of the example notebooks in the `examples` directory of the `jdaviz` repository, or by copy/pasting the widget code in `web/widget_code.json` (with the quotation marks and commas removed) in a jupyter notebook running in the same environment you install the `jdaviz` package. **Note** You must close your Jupyter notebook server after testing these examples as the web-based and electron apps in future steps need to use the `8888` port.
4. Ensure `nodejs` and `npm` are installed following the installation instructions for the *Current Release* [here](https://nodejs.org/en/).
5. Install the `yarn` package manager following the platform-specific install instructions [here](https://yarnpkg.com/en/docs/install).
6. Download the MaNGA data file [here](https://dr15.sdss.org/sas/dr15/manga/spectro/redux/v2_4_3/7495/stack/manga-7495-12704-LOGCUBE.fits.gz), and change the path to the data file within the `web/widget_code.json` file.

# Setup

Currently, the dev versions of the bqplot libraries are required. To install,
please follow the directions below:

1. Clone and install the [bqplot](https://github.com/bloomberg/bqplot) python package.
2. `cd` to the `bqplot/js` directory and run an `npm install`.
3. `cd` to `jdaviz/web`.
4. Install the dev version of the `bqplot` node package: `yarn add /path/to/bqplot/js`.

Also, the `jupyter-vuetify` must also be installed. Because it is not yet on
`npm`, it must also be installed manually:

1. Clone the [ipyvuetify](https://github.com/mariobuikhuizen/ipyvuetify) python package.
2. `cd` to `jdaviz/web`.
3. Install the dev version of `ipyvuetify` node page: `yarn add /path/to/ipyvuetify/js`.

# Browser-based application

1. Move to the `web` directory and run `yarn install`.
2. Build the compiled output files by running `yarn run build`.
3. Run `yarn run host`.
4. In a new terminal run `python -m notebook --no-browser --NotebookApp.allow_origin="*" --NotebookApp.disable_check_xsrf=True --NotebookApp.token=''`. **WARNING: This starts an insecure Jupyter notebook server. Do not do this in production.**
5. In a web browser, navigate to the address specified by the `yarn run host` command.

# Electron-based application

1. Move to the `web` directory and run `yarn install`.
2. In a new terminal run `python -m notebook --no-browser --NotebookApp.allow_origin="*" --NotebookApp.disable_check_xsrf=True --NotebookApp.token=''`. **WARNING: This starts an insecure Jupyter notebook server. Do not do this in production.**
3. Build and start the Electron instance using `yarn run start` in the `web` directory.