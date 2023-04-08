import copy
import math
from enum import IntEnum

import threading
import wx
import wx.lib.scrolledpanel as scrolled
import wx.lib.newevent as wxne
import wx.aui as aui

from elevators import ElevatorManagerThread

class BaseFrame(wx.Frame):
    def __init__(self, title, *, size=wx.DefaultSize, pos=wx.DefaultPosition, window=None):
        super().__init__(window, title=title, size=size, pos=pos)

# This creates a new Event class and a EVT binder function
(UpdateElevators, EVT_UPDATE_ELEVATORS) = wxne.NewEvent()


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
        super().__init__('flying things that move vertically', pos=wx.Point(0, 0), size=wx.Size(1080, 720))
        self.font = wx.Font(13, wx.DEFAULT, wx.NORMAL, wx.NORMAL, False, 'Segoue UI')
        self.positions = {
            'elevators': wx.Point(0, 0),
            'debug': None,
        }
        self.log_tc = None
        self.speed = 1
        self.algo = None
        self.floors = 25
        self.effective_size = wx.Size(1000, 640)


        self.manager_thread = ElevatorManagerThread(self, UpdateElevators)
        self.manager = self.manager_thread.manager

        self.Bind(EVT_UPDATE_ELEVATORS, self.OnUpdateElevators)
        self.SetBackgroundColour('white')
        self.InitUI()

    def OnUpdateElevators(self, e: wx.Event):
        for c in list(self.GetChildren()):
            if hasattr(c, 'OnUpdateElevators'):
                c.OnUpdateElevators(self.manager, e.manager)
            else:
                self.WriteToLog(f"OnUpdateElevators function not in {c}")
        self.manager = copy.deepcopy(e.manager)  ## TODO

    def InitUI(self):
        menubar = wx.MenuBar()
        fileMenu = wx.Menu()
        fileMenu.Append(wx.MenuItem(fileMenu, ID.MENU_APP_EXIT, '&Quit\tCtrl+Q'))

        self.Bind(wx.EVT_MENU, self.OnQuit, id=ID.MENU_APP_EXIT)
        menubar.Append(fileMenu, '&File')

        self.SetMenuBar(menubar)
        self.SetFont(self.font)

    def Close(self, *args):
        # TODO
        self.manager_thread.join()
        super().Close(*args)

    def OnQuit(self, e):
        self.Close()

    def AddPassenger(self, e, floor_i, floor_f):
        self.WriteToLog(f'Add passenger on floor {floor_i} to {floor_f}')

    def AddElevator(self, e, floor):
        self.manager_thread.add_elevator(floor)
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
        dt = wx.DateTime.Now().FormatISOTime()
        self.log_tc.AppendText(f'{dt}: {message}\n')

class ElevatorsPanel(scrolled.ScrolledPanel):
    def __init__(self, window):
        self.window = window
        super().__init__(id=wx.ID_ANY, parent=window, style=wx.TAB_TRAVERSAL | wx.BORDER_THEME)
        self.texts = {}  # id : text
        self.InitUI()
        self.SetupScrolling(scroll_y=False)

    def _add_elevator(self, ev):
        elevator_box = wx.StaticBox(self, label=f"Elevator {ev.id}", pos=wx.Point(0, 0), size=wx.Size(125, 100))
        top_border, other_border = elevator_box.GetBordersForSizer()

        text_sizer = wx.BoxSizer(wx.VERTICAL)
        text_sizer.AddSpacer(top_border)

        fmt_text = f'{ev.current_floor}'
        if ev.destination is not None:
            fmt_text += f' → {ev.destination}'

        text = wx.StaticText(elevator_box, wx.ID_ANY, fmt_text)
        self.texts[ev.id] = text

        font = wx.Font(self.window.font)
        font.SetPointSize(21)
        text.SetFont(font)
        text_sizer.Add(text, 1, wx.ALL | wx.CENTER, other_border+10)
        elevator_box.SetSizer(text_sizer)

        self.sz.Add(elevator_box, 1, wx.ALL | wx.CENTRE, 10)

    def OnUpdateElevators(self, before, after):
        # changes to track: current_floor, destination, new elevators
        updated = False
        if len(before.elevators) > 6 and len(after.elevators) <= 6:
            updated = True
            self.sz.SetCols(3)
            self.sz.SetRows(2)
        elif len(before.elevators) != len(after.elevators) and len(after.elevators) > 6 and len(after.elevators) % 3 == 1:
            updated = True
            self.sz.SetCols(math.ceil(len(after.elevators) / 3))
            self.sz.SetRows(3)

        for ev in after.elevators:
            if ev.id not in self.texts:
                updated = True
                self._add_elevator(ev)
            else:
                fmt_text = f'{ev.current_floor}'
                if ev.destination is not None:
                    fmt_text += f' → {ev.destination}'

                if self.texts[ev.id].GetLabel() != fmt_text:
                    updated = True
                    self.texts[ev.id].SetLabel(fmt_text)

        if updated:
            self.window.WriteToLog("ElevatorsPanel Layout Updated")
            self.Layout()
            self.SetupScrolling(scroll_y=False)

    def InitUI(self):
        num_elevators = 0
        if num_elevators <= 6:
            rows = 2
            cols = 3
        else:
            rows = 3
            cols = math.ceil(num_elevators / 3)

        self.sz = wx.GridSizer(rows, cols, gap=wx.Size(5, 5))
 
        # _, height = self.sz.CalcMin()
        self.size = wx.Size(540, 380)
        self.SetSize(self.size)
        self.SetSizer(self.sz)




class DebugPanel(wx.Panel):
    def __init__(self, window):
        self.window = window
        # if self.window.positions['debug'] is None:
        #     raise RuntimeError('Elevator panel must be loaded first')

        self.size = wx.Size(540, self.window.effective_size.y - 400)
        super().__init__(id=wx.ID_ANY, parent=window, size=self.size, style=wx.TAB_TRAVERSAL | wx.BORDER_THEME, pos=(0, 400))
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
        elevator_sz.Add(wx.StaticText(panel, wx.ID_ANY, 'Add Elevator'), 1)
        ef_selection = wx.SpinCtrl(panel, value='Floor', initial=1, min=1, max=self.window.floors)
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
        pfi_selection = wx.SpinCtrl(panel, value='Start', initial=1, min=1, max=self.window.floors)
        pff_selection = wx.SpinCtrl(panel, value='Destination', initial=1, min=1, max=self.window.floors)
        passenger_sz.Add(pfi_selection, 1, wx.FIXED_MINSIZE)
        passenger_sz.Add(pff_selection, 1, wx.FIXED_MINSIZE)

        passenger_sz.AddSpacer(10)

        # # button
        passenger_sz.AddSpacer(10)
        add_passenger_btn = wx.Button(panel, ID.BUTTON_ADD_PASSENGER, 'Add')
        add_passenger_btn.Bind(wx.EVT_BUTTON, lambda e: self.window.AddPassenger(
            e, pfi_selection.GetValue(), pff_selection.GetValue())
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

        speed_selection = wx.SpinCtrlDouble(panel, initial=15, min=0.01, max=100, inc=0.01)
        speed_sz.Add(speed_selection, 1, wx.FIXED_MINSIZE)

        # # button
        speed_sz.AddSpacer(10)
        set_btn = wx.Button(panel, ID.BUTTON_ADD_PASSENGER, 'Set')
        set_btn.Bind(wx.EVT_BUTTON, lambda _: self.window.manager_thread.set_speed(
            speed_selection.GetValue())
        )
        speed_sz.Add(set_btn, 1, wx.FIXED_MINSIZE)

        sz.Add(speed_sz, 0, wx.FIXED_MINSIZE | wx.TOP)
        sz.AddSpacer(5)

        # floors
        floor_sz = wx.BoxSizer(wx.HORIZONTAL)
        floor_sz.Add(wx.StaticText(panel, wx.ID_ANY, 'Floors'), 1)
        floor_sz.AddSpacer(10)

        floor_selection = wx.SpinCtrl(panel, initial=10, min=1, max=100)
        floor_sz.Add(floor_selection, 1, wx.FIXED_MINSIZE)

        # # button
        floor_sz.AddSpacer(10)
        set_floor_btn = wx.Button(panel, ID.BUTTON_ADD_PASSENGER, 'Set')
        set_floor_btn.Bind(wx.EVT_BUTTON, lambda _: self.window.manager_thread.set_floors(
            floor_selection.GetValue())
        )
        floor_sz.Add(set_floor_btn, 1, wx.FIXED_MINSIZE)

        sz.Add(floor_sz, 0, wx.FIXED_MINSIZE | wx.TOP)
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
        sz.SetDimension(wx.Point(0, 0), self.size)
        self.nb.AddPage(panel, "Controls")

    def LoadLogPanel(self):
        panel = wx.Panel(self.nb, wx.ID_ANY)
        sz = wx.BoxSizer(wx.VERTICAL)

        self.window.log_tc = wx.TextCtrl(panel, wx.ID_ANY, '', style=wx.TE_MULTILINE | wx.TE_READONLY | wx.HSCROLL)
        self.window.WriteToLog('Log started')
        sz.Add(self.window.log_tc, 1, wx.EXPAND)

        sz.SetDimension(0, 0, 540, 400)
        self.nb.AddPage(panel, "Log")

class ElevatorStatusPanel(scrolled.ScrolledPanel):
    def __init__(self, window):
        self.window = window
        super().__init__(id=wx.ID_ANY, parent=window, size=wx.Size(150, self.window.effective_size.y), pos=wx.Point(560, 0), style=wx.TAB_TRAVERSAL | wx.BORDER_THEME)

        self.rows = []
        self.InitUI()

    def OnUpdateElevators(self, before, after):
        updated = False
        if before.floors < after.floors:
            for i in range(after.floors - before.floors):
                self._add_floor(i + before.floors)

            updated = True
        elif before.floors > after.floors:
            for i in range(before.floors - after.floors):
                for j in self.rows[-1]:
                    self.sz.Remove(j)
                    j.Destroy()
                self.rows.pop()
            updated = True
        if updated:
            self.window.WriteToLog("ElevatorStatusPanel Layout Updated")
            self.Layout()
            self.SetupScrolling(scroll_x=False)

    def _add_floor(self, num):
        label_font = wx.Font(self.window.font)
        label_font.SetPointSize(21)
        button_font = wx.Font(self.window.font)
        button_font.SetPointSize(18)

        text = wx.StaticText(self, wx.ID_ANY, str(num + 1))
        text.SetFont(label_font)
        self.sz.Add(text, 0, wx.FIXED_MINSIZE)
        self.sz.AddSpacer(30)

        up_text = wx.StaticText(self, wx.ID_ANY, Unicode.UP)
        up_text.SetFont(button_font)

        self.sz.Add(up_text, 0, wx.FIXED_MINSIZE)
        self.sz.AddSpacer(30)

        down_text = wx.StaticText(self, wx.ID_ANY, Unicode.DOWN)
        down_text.SetFont(button_font)

        self.rows.append((text, up_text, down_text))
        # down_text.SetForegroundColour((255,0,0)) # set text color

        self.sz.Add(down_text, 0, wx.FIXED_MINSIZE)

    def InitUI(self):
        self.sz = wx.FlexGridSizer(5)

        for i in range(self.window.manager_thread.manager.floors):
            self._add_floor(i)

        self.SetSizer(self.sz)
        self.sz.SetDimension(0, 0, 150, self.window.effective_size.y)
        self.SetupScrolling(scroll_x=False)

class StatsPanel(scrolled.ScrolledPanel):
    def __init__(self, window):
        # super().__init__(id=wx.ID_ANY, parent=window, style=wx.TAB_TRAVERSAL | wx.BORDER_THEME)
        self.window = window
        super().__init__(id=wx.ID_ANY, parent=window, size=wx.Size(350, self.window.effective_size.y), pos=wx.Point(730, 0), style=wx.TAB_TRAVERSAL | wx.BORDER_THEME)

        self.InitUI()
    
    def InitUI(self):
        sz = wx.BoxSizer(wx.VERTICAL)

        self.stats_tc = wx.TextCtrl(self, wx.ID_ANY, 'Stats (MIN/MAX/MEAN/MED)\n\nWait Time: 0/0/0/0\nTime in Lift: 0/0/0/0', style=wx.TE_MULTILINE | wx.TE_READONLY | wx.TE_BESTWRAP, size=wx.Size(350, 360))
        sz.Add(self.stats_tc)
        sz.AddSpacer(10)

        sz.Add(wx.StaticText(self, wx.ID_ANY, 'Notes'))
        sz.AddSpacer(3)
        _, height = sz.GetMinSize()
        sz.Add(wx.TextCtrl(self, wx.ID_ANY, '', style=wx.TE_MULTILINE | wx.TE_BESTWRAP, size=wx.Size(350, self.window.effective_size.y - height - 10)))
        sz.SetDimension(0, 0, 350, self.window.effective_size.y)
        self.SetSizer(sz)

def main():
    app = wx.App()
    control_panel = BaseWindow()
    control_panel.Show()

    current_elevators = ElevatorsPanel(window=control_panel)
    current_elevators.Show()

    debug_panel = DebugPanel(window=control_panel)
    debug_panel.Show()

    elevator_status_panel = ElevatorStatusPanel(window=control_panel)
    elevator_status_panel.Show()

    stats_panel = StatsPanel(window=control_panel)
    stats_panel.Show()

    app.MainLoop()


main()
