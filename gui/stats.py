from collections import Counter, defaultdict

import wx
import wx.lib.scrolledpanel as scrolled
import wx.aui as aui

from constants import Unicode, LogLevel
from models import Elevator

class StatsPanel(scrolled.ScrolledPanel):
    def __init__(self, window):
        super().__init__(
            id=wx.ID_ANY,
            parent=window,
            size=wx.Size(350, 250),
            pos=wx.Point(730, 0),
            style=wx.TAB_TRAVERSAL | wx.BORDER_THEME,
        )
        self.window = window
        self.nb = aui.AuiNotebook(self, style=wx.aui.AUI_NB_TOP)

        self.InitUI()

    def InitUI(self):
        self.LoadStatsPanel()
        self.LoadElevatorPanel()
        self.LoadFloorPanel()

        sz = wx.BoxSizer()
        sz.Add(self.nb, 1, wx.EXPAND)
        sz.SetDimension(0, 0, 350, 250)
        self.SetSizer(sz)

    def update_stats(self, algorithm):
        self.stats_tc.SetValue(str(algorithm.stats))

    def OnUpdateAlgorithm(self, before, after):
        updated = False
        if str(before.stats) != str(after.stats):
            updated = True
            self.update_stats(after)

        if before.loads != after.loads:
            # floor panel
            updated = True
            floor_fmt = ''
            floors = defaultdict(Counter)
            elevators = defaultdict(Counter)
            for load in after.loads:
                if load.elevator is not None:
                    if isinstance(load.elevator, Elevator):
                        elevators[load.elevator.id][load.destination_floor] += 1
                else:
                    floors[load.current_floor][load.destination_floor] += 1

            elevator_fmt = '\n'.join(
                [
                    f'{k} {Unicode.ARROW} {", ".join(f"{kk} (x{elevators[k][kk]})" for kk in sorted(elevators[k].keys()))}'
                    for k in sorted(elevators.keys())
                ]
            )
            floor_fmt = '\n'.join(
                [
                    f'{k} {Unicode.ARROW} {", ".join(f"{kk} (x{floors[k][kk]})" for kk in sorted(floors[k].keys()))}'
                    for k in sorted(floors.keys())
                ]
            )

            if self.elevator_tc.GetValue() != elevator_fmt:
                self.elevator_tc.SetValue(elevator_fmt)
            if self.floor_tc.GetValue() != floor_fmt:
                self.floor_tc.SetValue(floor_fmt)

        if updated:
            self.window.WriteToLog(LogLevel.TRACE, 'StatsPanel Layout Updated')
            self.Layout()
            self.SetupScrolling()

    def LoadStatsPanel(self):
        panel = wx.Panel(self.nb, wx.ID_ANY)
        sz = wx.BoxSizer(wx.VERTICAL)

        self.stats_tc = wx.TextCtrl(
            panel,
            wx.ID_ANY,
            '',
            style=wx.TE_MULTILINE | wx.TE_READONLY | wx.TE_BESTWRAP,
        )
        self.update_stats(self.window.manager.algorithm)
        sz.Add(self.stats_tc, 1, wx.EXPAND)

        sz.SetDimension(0, 0, 350, 250)

        self.nb.AddPage(panel, 'Stats')

    def LoadFloorPanel(self):
        panel = wx.Panel(self.nb, wx.ID_ANY)
        sz = wx.BoxSizer(wx.VERTICAL)

        self.floor_tc = wx.TextCtrl(
            panel,
            wx.ID_ANY,
            '',
            style=wx.TE_MULTILINE | wx.TE_READONLY | wx.TE_BESTWRAP,
        )
        sz.Add(self.floor_tc, 1, wx.EXPAND)

        sz.SetDimension(0, 0, 350, 250)

        self.nb.AddPage(panel, 'Floors')

    def LoadElevatorPanel(self):
        panel = wx.Panel(self.nb, wx.ID_ANY)
        sz = wx.BoxSizer(wx.VERTICAL)

        self.elevator_tc = wx.TextCtrl(
            panel,
            wx.ID_ANY,
            '',
            style=wx.TE_MULTILINE | wx.TE_READONLY | wx.TE_BESTWRAP,
        )
        sz.Add(self.elevator_tc, 1, wx.EXPAND)

        sz.SetDimension(0, 0, 350, 250)

        self.nb.AddPage(panel, 'Elevators')

