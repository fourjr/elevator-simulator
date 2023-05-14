import wx

from gui import BaseWindow, ElevatorsPanel, ControlPanel, ElevatorStatusPanel, StatsPanel, LogPanel


class BaseApp(wx.App):
    def __init__(self):
        self.ready = False
        super().__init__()

    def OnInit(self):
        self.window = BaseWindow(app=self)
        self.window.Show()

        self.current_elevators = ElevatorsPanel(window=self.window)
        self.current_elevators.Show()

        self.control_panel = ControlPanel(window=self.window)
        self.control_panel.Show()

        self.elevator_status_panel = ElevatorStatusPanel(window=self.window)
        self.elevator_status_panel.Show()

        self.stats_panel = StatsPanel(window=self.window)
        self.stats_panel.Show()

        self.log_panel = LogPanel(window=self.window)
        self.log_panel.Show()

        self.SetTopWindow(self.window)

        return True
