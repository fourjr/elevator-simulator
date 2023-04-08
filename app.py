from collections import Counter, defaultdict
import copy
import math
from enum import IntEnum
import random
import statistics
from typing import List

import wx
import wx.lib.scrolledpanel as scrolled
import wx.lib.newevent as wxne
import wx.aui as aui

from elevators import ElevatorManagerThread
from managers import ElevatorManagerRandom, ElevatorManagerRolling

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
    ARROW = '\u2192'


class BaseWindow(BaseFrame):
    def __init__(self):
        super().__init__('flying things that move vertically', pos=wx.Point(0, 0), size=wx.Size(1080, 720))
        self.font = wx.Font(13, wx.DEFAULT, wx.NORMAL, wx.NORMAL, False, 'Segoue UI')
        self.log_tc = None
        self.speed = 1
        self.algo = None
        self.effective_size = wx.Size(1000, 640)


        self.manager_thread = ElevatorManagerThread(self, UpdateElevators)
        self.manager = copy.deepcopy(self.manager_thread.manager)  # TODO

        self.Bind(EVT_UPDATE_ELEVATORS, self.OnUpdateElevators)
        self.Bind(wx.EVT_CLOSE, self.OnClose)
        self.SetBackgroundColour('white')
        self.InitUI()

    def InitUI(self):
        menubar = wx.MenuBar()
        fileMenu = wx.Menu()
        fileMenu.Append(wx.MenuItem(fileMenu, ID.MENU_APP_EXIT, '&Quit\tCtrl+Q'))

        self.Bind(wx.EVT_MENU, self.OnQuit, id=ID.MENU_APP_EXIT)
        menubar.Append(fileMenu, '&File')

        self.SetMenuBar(menubar)
        self.SetFont(self.font)

    def OnUpdateElevators(self, e: wx.Event):
        for c in list(self.GetChildren()):
            if hasattr(c, 'OnUpdateElevators'):
                c.OnUpdateElevators(self.manager, e.manager)
        self.manager = copy.deepcopy(e.manager)  ## TODO

    def OnClose(self, _):
        self.Close()

    def OnQuit(self, e):
        self.Close()

    def Close(self):
        self.manager_thread.close()
        self.manager_thread.join()
        self.Destroy()

    def AddElevator(self, e, floor):
        self.manager_thread.add_elevator(floor)
        self.WriteToLog(f'Add elevator on floor {floor}')

    def Save(self, e):
        # TODO
        self.WriteToLog('Save')

    def WriteToLog(self, message):
        if self.log_tc is None:
            return
        self.log_tc.AppendText(f'{self.manager_thread.tick_count}: {message}\n')

    @property
    def active(self):
        return self.manager_thread.active

    @active.setter
    def active(self, value):
        self.manager_thread.active = value

    @property
    def floors(self):
        return self.manager_thread.manager.floors


class ElevatorsPanel(scrolled.ScrolledPanel):
    def __init__(self, window):
        self.window = window
        super().__init__(id=wx.ID_ANY, parent=window, style=wx.TAB_TRAVERSAL | wx.BORDER_THEME)
        self.texts = {}  # id : text
        self.InitUI()
        self.SetupScrolling(scroll_y=False)

    def _add_elevator(self, ev):
        elevator_box = wx.StaticBox(self, label=f"Elevator {ev.id}", pos=wx.Point(0, 0), size=wx.Size(130, 100))
        top_border, other_border = elevator_box.GetBordersForSizer()

        text_sizer = wx.BoxSizer(wx.VERTICAL)
        text_sizer.AddSpacer(top_border)

        fmt_text = f'{ev.current_floor}'
        if ev.destination is not None:
            fmt_text += f' {Unicode.ARROW} {ev.destination}'

        floor_text = wx.StaticText(elevator_box, wx.ID_ANY, fmt_text)

        font = wx.Font(self.window.font)
        font.SetPointSize(19)
        floor_text.SetFont(font)
        text_sizer.Add(floor_text, 1, wx.ALL | wx.CENTER)

        pax_text = wx.StaticText(elevator_box, wx.ID_ANY, f'{ev.load // 60} PAX')
        text_sizer.Add(pax_text, 1, wx.ALL | wx.CENTER, other_border+10)

        elevator_box.SetSizer(text_sizer)
        self.texts[ev.id] = (floor_text, pax_text)

        self.sz.Add(elevator_box, 1, wx.ALL | wx.CENTRE, 10)

    def OnUpdateElevators(self, before, after):
        # changes to track: current_floor, destination, new elevators
        # TODO: deletion of elevators
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
                    fmt_text += f' {Unicode.ARROW} {ev.destination}'

                if self.texts[ev.id][0].GetLabel() != fmt_text:
                    updated = True
                    self.texts[ev.id][0].SetLabel(fmt_text)

                fmt_pax = f'{ev.load // 60} PAX'
                if self.texts[ev.id][1].GetLabel() != fmt_pax:
                    updated = True
                    self.texts[ev.id][1].SetLabel(fmt_pax)


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
        self.floors_selections = []

        self.algorithms = {
            'Random': ElevatorManagerRandom,
            'Rolling': ElevatorManagerRolling,

        }
        self.InitUI()

    def OnUpdateElevators(self, before, after):
        # changes to track: current_floor, destination, new elevators
        updated = False

        if before.floors != after.floors:
            updated = True
            for i in self.floors_selections:
                i.SetRange(1, after.floors)

        if updated:
            self.window.WriteToLog("DebugPanel Layout Updated")
            self.Layout()

    def InitUI(self):
        self.LoadControlPanel()
        self.LoadControlPanel2()

        self.LoadNotesPanel()

        sz = wx.BoxSizer()
        sz.Add(self.nb, 1, wx.EXPAND)
        sz.SetDimension(0, 0, 540, 400)
        self.SetSizer(sz)

    def SetAlgorithm(self, e, algorithm):
        self.window.manager_thread.set_manager(self.algorithms[algorithm])
        self.window.WriteToLog(f'Set algorithm to {algorithm}')

    def AddPassenger(self, floor_i, floor_f):
        if floor_i == floor_f:
            self.WriteToLog(f'Passenger on floor {floor_i} to {floor_f} is not valid')
            return
        self.window.manager_thread.add_passenger(floor_i, floor_f)
        self.window.WriteToLog(f'Add passenger on floor {floor_i} to {floor_f}')

    def AddRandomPassengers(self, count):
        for _ in range(count):
            floor_i = random.randint(1, self.window.floors)
            floor_f = random.randint(1, self.window.floors)
            while floor_f == floor_i:
                floor_f = random.randint(1, self.window.floors)
            self.AddPassenger(floor_i, floor_f)

    def LoadControlPanel(self):
        panel = wx.Panel(self.nb, wx.ID_ANY)
        sz = wx.BoxSizer(wx.VERTICAL)
        sz.AddSpacer(10)

        # add elevator
        elevator_sz = wx.BoxSizer(wx.HORIZONTAL)
        elevator_sz.Add(wx.StaticText(panel, wx.ID_ANY, 'Add Elevator'), 1)
        ef_selection = wx.SpinCtrl(panel, value='Floor', initial=1, min=1, max=self.window.floors)
        elevator_sz.Add(ef_selection, 1, wx.FIXED_MINSIZE)

        self.floors_selections.append(ef_selection)
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
        passenger_sz.Add(wx.StaticText(panel, wx.ID_ANY, 'PAX'), 1)
        passenger_sz.AddSpacer(10)
        pfi_selection = wx.SpinCtrl(panel, value='Start', initial=1, min=1, max=self.window.floors)
        pff_selection = wx.SpinCtrl(panel, value='End', initial=1, min=1, max=self.window.floors)
        passenger_sz.Add(pfi_selection, 1, wx.FIXED_MINSIZE)
        passenger_sz.Add(pff_selection, 1, wx.FIXED_MINSIZE)

        self.floors_selections.extend([pfi_selection, pff_selection])

        passenger_sz.AddSpacer(10)

        # # button
        passenger_sz.AddSpacer(10)
        add_passenger_btn = wx.Button(panel, ID.BUTTON_ADD_PASSENGER, 'Add')
        add_passenger_btn.Bind(wx.EVT_BUTTON, lambda e: self.AddPassenger(
            pfi_selection.GetValue(), pff_selection.GetValue())
        )
        passenger_sz.Add(add_passenger_btn, 1, wx.FIXED_MINSIZE)
        passenger_sz.AddSpacer(10)

        # random
        random_passenger_count = wx.SpinCtrl(panel, value='Count', initial=1, min=1, max=100)
        passenger_sz.Add(random_passenger_count, 1, wx.FIXED_MINSIZE)
        random_passenger_btn = wx.Button(panel, ID.BUTTON_ADD_PASSENGER, 'Random')
        random_passenger_btn.Bind(wx.EVT_BUTTON, lambda e: self.AddRandomPassengers(
            random_passenger_count.GetValue()
        ))
        passenger_sz.Add(random_passenger_btn, 1, wx.FIXED_MINSIZE)


        sz.Add(passenger_sz, 0, wx.FIXED_MINSIZE | wx.TOP)
        sz.AddSpacer(5)

        # algorithm selection
        algo_sz = wx.BoxSizer(wx.HORIZONTAL)
        algo_sz.Add(wx.StaticText(panel, wx.ID_ANY, 'Algorithm'), 1)
        algo_sz.AddSpacer(10)

        algo_selection = wx.Choice(panel, choices=list(self.algorithms.keys()))
        algo_selection.SetSelection(0)
        algo_sz.Add(algo_selection, 1, wx.FIXED_MINSIZE)

        # # button
        algo_sz.AddSpacer(10)
        set_btn = wx.Button(panel, ID.BUTTON_ADD_PASSENGER, 'Set')
        set_btn.Bind(wx.EVT_BUTTON, lambda e: self.SetAlgorithm(
            e, algo_selection.GetString(algo_selection.GetCurrentSelection()))
        )
        algo_sz.Add(set_btn, 1, wx.FIXED_MINSIZE)

        sz.Add(algo_sz, 0, wx.FIXED_MINSIZE | wx.TOP)
        sz.AddSpacer(5)

        # speed
        speed_sz = wx.BoxSizer(wx.HORIZONTAL)
        speed_sz.Add(wx.StaticText(panel, wx.ID_ANY, 'Speed'), 1)
        speed_sz.AddSpacer(10)

        speed_selection = wx.SpinCtrlDouble(panel, initial=3, min=0.01, max=999, inc=0.01)
        speed_sz.Add(speed_selection, 1, wx.FIXED_MINSIZE)

        # # button

        def set_speed_callback(_):
            self.window.manager_thread.set_speed(speed_selection.GetValue())
            self.window.WriteToLog(f'Speed set to {speed_selection.GetValue()}')

        speed_sz.AddSpacer(10)
        set_btn = wx.Button(panel, wx.ID_ANY, 'Set')
        set_btn.Bind(wx.EVT_BUTTON, set_speed_callback)
        speed_sz.Add(set_btn, 1, wx.FIXED_MINSIZE)

        sz.Add(speed_sz, 0, wx.FIXED_MINSIZE | wx.TOP)
        sz.AddSpacer(5)

        # floors
        floor_sz = wx.BoxSizer(wx.HORIZONTAL)
        floor_sz.Add(wx.StaticText(panel, wx.ID_ANY, 'Floors'), 1)
        floor_sz.AddSpacer(10)

        floor_selection = wx.SpinCtrl(panel, initial=10, min=1, max=1000)
        floor_sz.Add(floor_selection, 1, wx.FIXED_MINSIZE)

        # # button
        floor_sz.AddSpacer(10)

        def set_floors_callback(_):
            self.window.manager_thread.set_floors(floor_selection.GetValue())
            self.window.WriteToLog(f"Setting floors to: {floor_selection.GetValue()}")

        set_floor_btn = wx.Button(panel, wx.ID_ANY, 'Set')
        set_floor_btn.Bind(wx.EVT_BUTTON, set_floors_callback)
        floor_sz.Add(set_floor_btn, 1, wx.FIXED_MINSIZE)

        sz.Add(floor_sz, 0, wx.FIXED_MINSIZE | wx.TOP)
        sz.AddSpacer(5)

        # control
        ctrl_sz = wx.BoxSizer(wx.HORIZONTAL)

        def toggle_play_callback(_):
            self.window.active = not self.window.active
            self.window.WriteToLog(f"Setting play state to: {self.window.active}")
            play_btn.SetLabel('Play' if not self.window.active else 'Pause')

        play_btn = wx.Button(panel, ID.BUTTON_ADD_PASSENGER, 'Play')
        play_btn.Bind(wx.EVT_BUTTON, toggle_play_callback)
        ctrl_sz.Add(play_btn, 1, wx.FIXED_MINSIZE)

        save_btn = wx.Button(panel, ID.BUTTON_ADD_PASSENGER, 'Save')
        save_btn.Bind(wx.EVT_BUTTON, self.window.Save)
        ctrl_sz.Add(save_btn, 1, wx.FIXED_MINSIZE)
        ctrl_sz.AddSpacer(10)

        def reset_callback(_):
            self.window.manager_thread.reset(self.algorithms[algo_selection.GetString(algo_selection.GetCurrentSelection())])
            self.window.WriteToLog(f"Reset")

        reset_btn = wx.Button(panel, ID.BUTTON_ADD_PASSENGER, 'Reset')
        reset_btn.Bind(wx.EVT_BUTTON, reset_callback)
        ctrl_sz.Add(reset_btn, 1, wx.FIXED_MINSIZE)
        ctrl_sz.AddSpacer(10)

        sz.Add(ctrl_sz, 0, wx.FIXED_MINSIZE | wx.TOP)

        # end
        sz.SetDimension(wx.Point(0, 0), self.size)
        self.nb.AddPage(panel, "Controls")

    def LoadControlPanel2(self):
        panel = wx.Panel(self.nb, wx.ID_ANY)
        sz = wx.BoxSizer(wx.VERTICAL)
        sz.AddSpacer(10)

        # max capacity
        cap_sz = wx.BoxSizer(wx.HORIZONTAL)
        cap_sz.Add(wx.StaticText(panel, wx.ID_ANY, 'Max Load'), 1)
        load_selection = wx.SpinCtrl(panel, initial=15, min=1, max=100)
        cap_sz.Add(load_selection, 1, wx.FIXED_MINSIZE)

        def set_cap_callback(_):
            self.window.manager_thread.set_max_load(load_selection.GetValue() * 60)
            self.window.WriteToLog(f"Setting max load to: {load_selection.GetValue()}")

        cap_sz.AddSpacer(10)
        set_btn = wx.Button(panel, wx.ID_ANY, 'Set')
        set_btn.Bind(wx.EVT_BUTTON, set_cap_callback)
        cap_sz.Add(set_btn, 1, wx.FIXED_MINSIZE)

        sz.Add(cap_sz, 0, wx.FIXED_MINSIZE | wx.TOP)

        # end
        sz.SetDimension(wx.Point(0, 0), self.size)
        self.nb.AddPage(panel, "Controls 2")

    def LoadNotesPanel(self):
        panel = wx.Panel(self.nb, wx.ID_ANY)
        sz = wx.BoxSizer(wx.VERTICAL)

        tc = wx.TextCtrl(panel, wx.ID_ANY, '', style=wx.TE_MULTILINE | wx.TE_BESTWRAP)
        sz.Add(tc, 1, wx.EXPAND)

        sz.SetDimension(0, 0, 540, 400)
        self.nb.AddPage(panel, "Notes")



class ElevatorStatusPanel(scrolled.ScrolledPanel):
    def __init__(self, window):
        self.window = window
        super().__init__(id=wx.ID_ANY, parent=window, size=wx.Size(180, self.window.effective_size.y), pos=wx.Point(550, 0), style=wx.TAB_TRAVERSAL | wx.BORDER_THEME)

        self.rows = []
        self.InitUI()

    def OnUpdateElevators(self, before, after):
        # Number of floors and loads
        updated = False
        if before.floors < after.floors:
            updated = True
            for i in range(after.floors - before.floors):
                self._add_floor(i + before.floors)


        elif before.floors > after.floors:
            updated = True
            count = self.sz.GetItemCount()
            to_remove = (before.floors - after.floors) * 5
            for i in range(to_remove):
                self.sz.Hide(count - to_remove)
                self.sz.Remove(count - to_remove)

                if i % 5 == 0:
                    self.rows.pop()

        if before.loads != after.loads:
            updated = True
            floors = [[0, 0] for _ in range(after.floors)]
            for load in after.loads:
                if load.elevator is None:
                    if load.initial_floor < load.destination_floor:
                        floors[load.initial_floor - 1][0] += load.weight
                    else:
                        floors[load.initial_floor - 1][1] += load.weight

            for n, (up, down) in enumerate(floors):
                if up == 0:
                    self.rows[n][0].SetForegroundColour(wx.Colour(0, 0, 0))
                else:
                    self.rows[n][0].SetForegroundColour(wx.Colour(0, 255, 0))
                if down == 0:
                    self.rows[n][1].SetForegroundColour(wx.Colour(0, 0, 0))
                else:
                    self.rows[n][1].SetForegroundColour(wx.Colour(0, 255, 0))
                self.rows[n][0].SetLabel(str(up // 60).zfill(2))
                self.rows[n][1].SetLabel(str(down // 60).zfill(2))

            updated = True

        if updated:
            self.window.WriteToLog("ElevatorStatusPanel Layout Updated")
            self.Layout()
            if before.floors != after.floors:
                self.SetupScrolling()

    def _add_floor(self, num):
        label_font = wx.Font(self.window.font)
        label_font.SetPointSize(21)
        button_font = wx.Font(self.window.font)
        button_font.SetPointSize(18)

        text = wx.StaticText(self, wx.ID_ANY, str(num + 1))
        text.SetFont(label_font)
        self.sz.Add(text, 0, wx.FIXED_MINSIZE)
        self.sz.AddSpacer(30)

        up_text = wx.StaticText(self, wx.ID_ANY, '00')
        up_text.SetFont(button_font)

        self.sz.Add(up_text, 0, wx.FIXED_MINSIZE)
        self.sz.AddSpacer(30)

        down_text = wx.StaticText(self, wx.ID_ANY, '00')
        down_text.SetFont(button_font)

        self.rows.append((up_text, down_text))

        self.sz.Add(down_text, 0, wx.FIXED_MINSIZE)

    def InitUI(self):
        self.sz = wx.FlexGridSizer(5)

        # header
        button_font = wx.Font(self.window.font)
        button_font.SetPointSize(18)

        self.sz.AddSpacer(30)
        self.sz.AddSpacer(30)

        up_text = wx.StaticText(self, wx.ID_ANY, Unicode.UP)
        up_text.SetFont(button_font)
        self.sz.Add(up_text, 0, wx.FIXED_MINSIZE)
        self.sz.AddSpacer(30)

        down_text = wx.StaticText(self, wx.ID_ANY, Unicode.DOWN)
        down_text.SetFont(button_font)
        self.sz.Add(down_text, 0, wx.FIXED_MINSIZE)

        # floors
        for i in range(self.window.manager_thread.manager.floors):
            self._add_floor(i)

        self.SetSizer(self.sz)
        self.sz.SetDimension(0, 0, 150, self.window.effective_size.y)
        self.SetupScrolling()


def generate_stats(values: List[int | float]):
    if len(values) == 0:
        values = [0]

    vals = (
        min(values),
        statistics.mean(values),
        statistics.median(values),
        max(values)
    )
    return f'{vals[0]:.2f}/{vals[1]:.2f}/{vals[2]:.2f}/{vals[3]:.2f}'

class StatsPanel(scrolled.ScrolledPanel):
    def __init__(self, window):
        # super().__init__(id=wx.ID_ANY, parent=window, style=wx.TAB_TRAVERSAL | wx.BORDER_THEME)
        self.window = window
        super().__init__(id=wx.ID_ANY, parent=window, size=wx.Size(350, 250), pos=wx.Point(730, 0), style=wx.TAB_TRAVERSAL | wx.BORDER_THEME)
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

    def OnUpdateElevators(self, before, after):
        updated = False
        if before.wait_times != after.wait_times or before.time_in_lift != after.time_in_lift:
            updated = True
            fmt_text = '(MIN/MEAN/MED/MAX)\n\n'
            fmt_text += f'Wait Time: {generate_stats(after.wait_times)}\n'
            fmt_text += f'Time in Lift: {generate_stats(after.time_in_lift)}' 
            self.stats_tc.SetValue(fmt_text)

        if before.loads != after.loads:
            updated = True
            # floor panel
            floor_fmt = ''
            floors = defaultdict(Counter)
            elevators = defaultdict(Counter)
            for load in after.loads:
                if load.elevator is not None:
                    elevators[load.elevator.id][load.destination_floor] += 1
                else:
                    floors[load.current_floor][load.destination_floor] += 1

            elevator_fmt = '\n'.join([f'{k} {Unicode.ARROW} {", ".join(f"{kk} (x{elevators[k][kk]})" for kk in sorted(elevators[k].keys()))}' for k in sorted(elevators.keys())])
            floor_fmt = '\n'.join([f'{k} {Unicode.ARROW} {", ".join(f"{kk} (x{floors[k][kk]})" for kk in sorted(floors[k].keys()))}' for k in sorted(floors.keys())])

            if self.elevator_tc.GetValue() != elevator_fmt:
                self.elevator_tc.SetValue(elevator_fmt)
            if self.floor_tc.GetValue() != floor_fmt:
                self.floor_tc.SetValue(floor_fmt)
        if updated:
            self.window.WriteToLog("StatsPanel Layout Updated")
            self.Layout()
            self.SetupScrolling()

    def LoadStatsPanel(self):
        panel = wx.Panel(self.nb, wx.ID_ANY)
        sz = wx.BoxSizer(wx.VERTICAL)

        self.stats_tc = wx.TextCtrl(panel, wx.ID_ANY, '(MIN/MAX/MEAN/MED)\n\nWait Time: 0/0/0/0\nTime in Lift: 0/0/0/0', style=wx.TE_MULTILINE | wx.TE_READONLY | wx.TE_BESTWRAP)
        sz.Add(self.stats_tc, 1, wx.EXPAND)

        sz.SetDimension(0, 0, 350, 250)

        self.nb.AddPage(panel, "Stats")

    def LoadFloorPanel(self):
        panel = wx.Panel(self.nb, wx.ID_ANY)
        sz = wx.BoxSizer(wx.VERTICAL)

        self.floor_tc = wx.TextCtrl(panel, wx.ID_ANY, '', style=wx.TE_MULTILINE | wx.TE_READONLY | wx.TE_BESTWRAP)
        sz.Add(self.floor_tc, 1, wx.EXPAND)

        sz.SetDimension(0, 0, 350, 250)

        self.nb.AddPage(panel, "Floors")

    def LoadElevatorPanel(self):
        panel = wx.Panel(self.nb, wx.ID_ANY)
        sz = wx.BoxSizer(wx.VERTICAL)

        self.elevator_tc = wx.TextCtrl(panel, wx.ID_ANY, '', style=wx.TE_MULTILINE | wx.TE_READONLY | wx.TE_BESTWRAP)
        sz.Add(self.elevator_tc, 1, wx.EXPAND)

        sz.SetDimension(0, 0, 350, 250)

        self.nb.AddPage(panel, "Elevators")

class LogPanel(wx.Panel):
    def __init__(self, window):
        # super().__init__(id=wx.ID_ANY, parent=window, style=wx.TAB_TRAVERSAL | wx.BORDER_THEME)
        self.window = window
        super().__init__(id=wx.ID_ANY, parent=window, size=wx.Size(350, 380), pos=wx.Point(730, 260), style=wx.TAB_TRAVERSAL | wx.BORDER_THEME)

        self.InitUI()

    def InitUI(self):
        sz = wx.BoxSizer(wx.VERTICAL)
        sz.Add(wx.StaticText(self, wx.ID_ANY, 'Log'))
        sz.AddSpacer(3)
        _, height = sz.GetMinSize()
        self.window.log_tc = wx.TextCtrl(self, wx.ID_ANY, '', style=wx.TE_MULTILINE | wx.TE_READONLY | wx.HSCROLL, size=wx.Size(350, 380 - height - 10))
        self.window.WriteToLog('Log started')
        sz.Add(self.window.log_tc, 1, wx.EXPAND)

        sz.SetDimension(0, 0, 350, 380)
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

    log_panel = LogPanel(window=control_panel)
    log_panel.Show()

    app.MainLoop()


main()
