import sys


def start_as_kernel():
    # similar to https://github.com/astrofrog/voila-qt-app/blob/master/voila_demo.py
    import sys

    from ipykernel import kernelapp as app
    app.launch_new_instance()
    sys.argv = [app.__file__, sys.argv[3:]]


if __name__ == "__main__":
    # When voila starts a kernel under pyinstaller, it will use sys.executable
    # (which is this entry point again)
    # if called like [sys.argv[0], "-m", "ipykernel_launcher", ...]
    if len(sys.argv) >= 3 and sys.argv[1] == "-m" and sys.argv[2] == "ipykernel_launcher":
        # it is important that we do not import jdaviz top level
        # as that would cause it to import ipywidgets before the kernel is started
        start_as_kernel()
    else:
        import jdaviz.cli
        # should change this to _main, but now it doesn't need arguments
        jdaviz.cli.main(layout="")
