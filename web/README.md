# Web-only interface

This directory demonstrates generating javascript from python code and
mounting on a basic html page. It setups up a kernel manager to connect to a
running jupyter kernel instance used to execute the python code. The html
page is hosted using yarn `http-server`.

# Usage

1. Move to the `web` directory and run `yarn run install`.
2. Build the compiled output files by running `yarn run build`.
4. Run `yarn run host`
5. In a new terminal run `python -m notebook --no-browser --NotebookApp.allow_origin="*" --NotebookApp.disable_check_xsrf=True --NotebookApp.token=''`. **WARNING: This starts an insecure Jupyter notebook server. Do not do this in production.**
6. In a web browser, navigate to the address specified by the `yarn run host` command.