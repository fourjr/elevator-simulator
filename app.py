import math
from enum import IntEnum

import wx
import wx.lib.scrolledpanel as scrolled
import wx.aui as aui


class BaseFrame(wx.Frame):
    def __init__(self, title, *, size=wx.DefaultSize, pos=wx.DefaultPosition, window=None):
        super().__init__(window, title=title, size=size, pos=pos)


class ID(IntEnum):
    PANEL_ELEVATORS = 110
    PANEL_DEBUG_CONTROL = 121
    PANEL_DEBUG_LOG = 122

    BUTTON_ADD_PASSENGER = 21

    MENU_APP_EXIT = 310

class Unicode:
    UP = '\u2191'
    DOWN = '\u2193'


class BaseWindow(BaseFrame):
    def __init__(self):
        super().__init__('Control Panel', pos=wx.Point(0, 0), size=wx.Size(1080, 720))
        self.elevators = [(5, 7), (9, 1), (3, 6), (2, 10), (8, 2), (7, 4), (1, 6), (4, 9), (6, 10), (10, 1), (7, 3), (3, 5), (9, 7), (6, 3), (2, 8), (1, 3), (4, 7), (8, 5), (5, 8), (10, 4)]
        self.font = wx.Font(13, wx.DEFAULT, wx.NORMAL, wx.NORMAL, False, 'Segoue UI')
        self.positions = {
            'elevators': wx.Point(0, 0),
            'debug': None,
        }
        self.log_tc = None
        self.speed = 1
        self.algo = None
        self.floors = 25
        self.InitUI()

    def InitUI(self):
        menubar = wx.MenuBar()
        fileMenu = wx.Menu()
        fileMenu.Append(wx.MenuItem(fileMenu, ID.MENU_APP_EXIT, '&Quit\tCtrl+Q'))

        self.Bind(wx.EVT_MENU, self.OnQuit, id=ID.MENU_APP_EXIT)
        menubar.Append(fileMenu, '&File')

        self.SetMenuBar(menubar)
        self.SetFont(self.font)

    def OnQuit(self, e):
        self.Close()

    def AddPassenger(self, e, floor, direction):
        self.WriteToLog(f'Add passenger on floor {floor} going {direction}')

    def AddElevator(self, e, floor):
        self.elevators.append((floor, floor))
        self.WriteToLog(f'Add elevator on floor {floor}')

    def SetAlgorithm(self,e, algo):
        self.WriteToLog(f'Set algorithm to {algo}')
        self.algo = algo

    def Pause(self, e):
        self.WriteToLog('Pause')

    def Play(self, e):
        self.WriteToLog('Play')

    def Save(self, e):
        self.WriteToLog('Save')

    def SetSpeed(self, e, speed):
        self.WriteToLog(f'Set speed to {speed}')
        self.speed = speed

    def WriteToLog(self, message):
        if self.log_tc is None:
            return
        dt = wx.DateTime.Now().FormatISOCombined()
        self.log_tc.AppendText(f'{dt}: {message}\n')

class ElevatorsPanel(scrolled.ScrolledPanel):
    def __init__(self, window):
        self.window = window
        super().__init__(id=wx.ID_ANY, parent=window, style=wx.TAB_TRAVERSAL | wx.BORDER_THEME)
        self.InitUI()

    def InitUI(self):
        num_elevators = len(self.window.elevators)
        if num_elevators <= 6:
            rows = 2
            cols = 3
        else:
            rows = 3
            cols = math.ceil(num_elevators / 3)

        sz = wx.GridSizer(rows, cols, gap=wx.Size(5, 5))
        for n, (curr, going) in enumerate(self.window.elevators):
            elevator_box = wx.StaticBox(self, label="Elevator " + str(n + 1), pos=wx.Point(0, 0), size=wx.Size(125, 100))
            top_border, other_border = elevator_box.GetBordersForSizer()

            text_sizer = wx.BoxSizer(wx.VERTICAL)
            text_sizer.AddSpacer(top_border)

            text = wx.StaticText(elevator_box, wx.ID_ANY, f'{curr} → {going}')
            font = wx.Font(self.window.font)
            font.SetPointSize(21)
            text.SetFont(font)
            text_sizer.Add(text, 1, wx.ALL | wx.CENTER, other_border+10)
            elevator_box.SetSizer(text_sizer)

            sz.Add(elevator_box, 1, wx.ALL | wx.CENTRE, 10)
 
        _, height = sz.CalcMin()
        self.size = wx.Size(540, height)
        self.SetSize(self.size)
        self.window.positions['debug'] = wx.Point(0, height + 20)
        self.SetSizer(sz)

        self.SetupScrolling(scroll_y=False)



class DebugPanel(wx.Panel):
    def __init__(self, window):
        self.window = window
        super().__init__(id=wx.ID_ANY, parent=window, size=wx.Size(540, 400), style=wx.TAB_TRAVERSAL | wx.BORDER_THEME, pos=self.window.positions['debug'])
        self.nb = aui.AuiNotebook(self, style=wx.aui.AUI_NB_TOP)
        self.InitUI()

    def InitUI(self):
        self.LoadControlPanel()
        self.LoadLogPanel()

        sz = wx.BoxSizer()
        sz.Add(self.nb, 1, wx.EXPAND)
        sz.SetDimension(0, 0, 540, 400)
        self.SetSizer(sz)

    def LoadControlPanel(self):
        panel = wx.Panel(self.nb, wx.ID_ANY)
        sz = wx.BoxSizer(wx.VERTICAL)
        sz.AddSpacer(10)

        # add elevator
        elevator_sz = wx.BoxSizer(wx.HORIZONTAL)
        elevator_sz.Add(wx.StaticText(panel, wx.ID_ANY, 'Add Elevator (starting floor)'), 1)
        ef_selection = wx.SpinCtrl(panel, initial=1, min=1, max=self.window.floors)
        elevator_sz.Add(ef_selection, 1, wx.FIXED_MINSIZE)

        # # button
        elevator_sz.AddSpacer(10)
        add_elevator_btn = wx.Button(panel, ID.BUTTON_ADD_PASSENGER, 'Add')
        add_elevator_btn.Bind(wx.EVT_BUTTON, lambda e: self.window.AddElevator(
            e, ef_selection.GetValue())
        )
        elevator_sz.Add(add_elevator_btn, 1, wx.FIXED_MINSIZE)

        sz.Add(elevator_sz, 0, wx.FIXED_MINSIZE | wx.TOP)
        sz.AddSpacer(5)

        # passenger adding
        passenger_sz = wx.BoxSizer(wx.HORIZONTAL)
        passenger_sz.Add(wx.StaticText(panel, wx.ID_ANY, 'Add Passenger'), 1)
        passenger_sz.AddSpacer(10)
        pf_selection = wx.SpinCtrl(panel, initial=1, min=1, max=self.window.floors)
        passenger_sz.Add(pf_selection, 1, wx.FIXED_MINSIZE)

        passenger_sz.AddSpacer(10)

        dir_selection = wx.Choice(panel, choices=[Unicode.UP, Unicode.DOWN])
        dir_selection.SetSelection(0)
        passenger_sz.Add(dir_selection, 1, wx.FIXED_MINSIZE)

        # # button
        passenger_sz.AddSpacer(10)
        add_passenger_btn = wx.Button(panel, ID.BUTTON_ADD_PASSENGER, 'Add')
        add_passenger_btn.Bind(wx.EVT_BUTTON, lambda e: self.window.AddPassenger(
            e, pf_selection.GetValue(), dir_selection.GetString(dir_selection.GetCurrentSelection()))
        )
        passenger_sz.Add(add_passenger_btn, 1, wx.FIXED_MINSIZE)

        sz.Add(passenger_sz, 0, wx.FIXED_MINSIZE | wx.TOP)
        sz.AddSpacer(5)

        # algorithm selection
        algo_sz = wx.BoxSizer(wx.HORIZONTAL)
        algo_sz.Add(wx.StaticText(panel, wx.ID_ANY, 'Select Algorithm'), 1)
        algo_sz.AddSpacer(10)

        algo_selection = wx.Choice(panel, choices=['no algo', 'type 1', 'type 2'])
        algo_selection.SetSelection(0)
        algo_sz.Add(algo_selection, 1, wx.FIXED_MINSIZE)

        # # button
        algo_sz.AddSpacer(10)
        set_btn = wx.Button(panel, ID.BUTTON_ADD_PASSENGER, 'Set')
        set_btn.Bind(wx.EVT_BUTTON, lambda e: self.window.SetAlgorithm(
            e, algo_selection.GetString(algo_selection.GetCurrentSelection()))
        )
        algo_sz.Add(set_btn, 1, wx.FIXED_MINSIZE)

        sz.Add(algo_sz, 0, wx.FIXED_MINSIZE | wx.TOP)
        sz.AddSpacer(5)

        # speed
        speed_sz = wx.BoxSizer(wx.HORIZONTAL)
        speed_sz.Add(wx.StaticText(panel, wx.ID_ANY, 'Speed'), 1)
        speed_sz.AddSpacer(10)

        speed_selection = wx.SpinCtrlDouble(panel, initial=1, min=0.01, max=10, inc=0.01)
        speed_sz.Add(speed_selection, 1, wx.FIXED_MINSIZE)

        # # button
        speed_sz.AddSpacer(10)
        set_btn = wx.Button(panel, ID.BUTTON_ADD_PASSENGER, 'Set Speed')
        set_btn.Bind(wx.EVT_BUTTON, lambda e: self.window.SetSpeed(
            e, speed_selection.GetValue())
        )
        speed_sz.Add(set_btn, 1, wx.FIXED_MINSIZE)

        sz.Add(speed_sz, 0, wx.FIXED_MINSIZE | wx.TOP)
        sz.AddSpacer(5)

        # control
        ctrl_sz = wx.BoxSizer(wx.HORIZONTAL)
        play_btn = wx.Button(panel, ID.BUTTON_ADD_PASSENGER, 'Play')
        play_btn.Bind(wx.EVT_BUTTON, self.window.Play)
        ctrl_sz.Add(play_btn, 1, wx.FIXED_MINSIZE)

        pause_btn = wx.Button(panel, ID.BUTTON_ADD_PASSENGER, 'Pause')
        pause_btn.Bind(wx.EVT_BUTTON, self.window.Pause)
        ctrl_sz.Add(pause_btn, 1, wx.FIXED_MINSIZE)
        ctrl_sz.AddSpacer(10)

        pause_btn = wx.Button(panel, ID.BUTTON_ADD_PASSENGER, 'Save')
        pause_btn.Bind(wx.EVT_BUTTON, self.window.Save)
        ctrl_sz.Add(pause_btn, 1, wx.FIXED_MINSIZE)
        ctrl_sz.AddSpacer(10)


        sz.Add(ctrl_sz, 0, wx.FIXED_MINSIZE | wx.TOP)

        # end
        sz.SetDimension(0, 0, 540, 400)
        self.nb.AddPage(panel, "Controls")

    def LoadLogPanel(self):
        panel = wx.Panel(self.nb, wx.ID_ANY)
        sz = wx.BoxSizer(wx.VERTICAL)

        self.window.log_tc = wx.TextCtrl(panel, wx.ID_ANY, '', style=wx.TE_MULTILINE | wx.TE_READONLY | wx.HSCROLL)
        self.window.WriteToLog('Log started')
        sz.Add(self.window.log_tc, 1, wx.EXPAND)

        sz.SetDimension(0, 0, 540, 400)
        self.nb.AddPage(panel, "Log")

def main():
    app = wx.App()
    control_panel = BaseWindow()
    control_panel.Show()

    current_elevators = ElevatorsPanel(window=control_panel)
    current_elevators.Show()

    debug_panel = DebugPanel(window=control_panel)
    debug_panel.Show()
    app.MainLoop()


main()
