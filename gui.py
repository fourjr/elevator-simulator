from gui import BaseApp


def start_gui(*args):
    app = BaseApp(*args)
    app.MainLoop()
    return app


if __name__ == '__main__':
    start_gui()
