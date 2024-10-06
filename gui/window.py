import gzip
import pickle
from datetime import datetime

import wx
import wx.lib.newevent as wxne

from gui import ElevatorManagerThread
from models import LogMessage, load_algorithms
from utils import ID, Constants, LogLevel


class BaseWindow(wx.Frame):
    def __init__(self, app):
        super().__init__(
            None,
            title='flying things that move vertically',
            pos=wx.Point(0, 0),
            size=wx.Size(1080, 720),
        )
        self.app = app
        self.font = wx.Font(13, wx.DEFAULT, wx.NORMAL, wx.NORMAL, False, 'Segoue UI')
        self.log_tc = None
        self.speed = 1
        self.algo = None
        self.effective_size = wx.Size(1000, 640)

        self.algorithms = load_algorithms()
        self.current_algorithm = self.algorithms[Constants.DEFAULT_ALGORITHM]

        (UpdateAlgorithm, EVT_UPDATE_MANAGER) = wxne.NewEvent()

        self.manager = ElevatorManagerThread(self, UpdateAlgorithm, self.current_algorithm)
        self.algorithm = self.manager.algorithm.copy()

        self.Bind(EVT_UPDATE_MANAGER, self.OnUpdateAlgorithm)
        self.Bind(wx.EVT_CLOSE, self.Close)
        self.SetBackgroundColour('white')
        self.InitMenuBar()

    def _update_gui(self, algo):
        for c in list(self.GetChildren()):
            if hasattr(c, 'OnUpdateAlgorithm'):
                c.OnUpdateAlgorithm(self.algorithm, algo)

        # self.algorithm = copy.deepcopy(algo)
        self.algorithm = algo.copy()

    def _import_simulation(self, fn):
        dt = datetime.now().isoformat()
        skip_bytes = len(f'fourjr/elevator-simulator {dt} fourjr/elevator-simulator\00\00')
        with open(fn, 'rb') as f:
            self.manager.algorithm = pickle.loads(gzip.decompress(f.read()[skip_bytes:-skip_bytes]))

        self.manager.algorithm.manager = self.manager

        for ev in self.manager.algorithm.elevators:
            ev.manager = self.manager

        self._update_gui(self.manager.algorithm)

    def InitMenuBar(self):
        menubar = wx.MenuBar()
        fileMenu = wx.Menu()
        fileMenu.Append(wx.MenuItem(fileMenu, ID.MENU_APP_EXIT, '&Quit\tCtrl+Q'))

        self.Bind(wx.EVT_MENU, self.Close, id=ID.MENU_APP_EXIT)
        menubar.Append(fileMenu, '&File')

        self.SetMenuBar(menubar)
        self.SetFont(self.font)

    def OnUpdateAlgorithm(self, e: wx.Event):
        self._update_gui(e.algorithm)

    def Close(self, *_):
        self.manager.close()
        self.manager.join()
        self.Destroy()

    def WriteToLog(self, level: LogLevel, message):
        self.FindWindowById(ID.PANEL_DEBUG_LOG).OnLogUpdate(
            LogMessage(level, message, self.manager.algorithm.tick_count)
        )

    @property
    def active(self):
        return self.manager.algorithm.active

    @active.setter
    def active(self, value):
        self.manager.set_active(value)

    @property
    def floors(self):
        return self.manager.algorithm.floors

