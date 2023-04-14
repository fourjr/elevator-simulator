import copy
import glob
import gzip
import importlib
import math
import os
import pickle
import random
from collections import Counter, defaultdict
from datetime import datetime
from typing import List, Set

import wx
import wx.lib.scrolledpanel as scrolled
import wx.lib.newevent as wxne
import wx.aui as aui

from elevators import ElevatorManagerThread
from enums import ID
from errors import BadArgument, InvalidManager
from models import ElevatorManager, LogLevel, LogMessage
from utils import Constants, Unicode, generate_stats


(UpdateElevators, EVT_UPDATE_ELEVATORS) = wxne.NewEvent()


class BaseWindow(wx.Frame):
    def __init__(self):
        super().__init__(None, title='flying things that move vertically', pos=wx.Point(0, 0), size=wx.Size(1080, 720))
        self.font = wx.Font(13, wx.DEFAULT, wx.NORMAL, wx.NORMAL, False, 'Segoue UI')
        self.log_tc = None
        self.speed = 1
        self.algo = None
        self.effective_size = wx.Size(1000, 640)

        self._load_algorithms()
        self.current_algorithm = self.algorithms[Constants.DEFAULT_ALGORITHM]

        self.manager_thread = ElevatorManagerThread(self, UpdateElevators, self.current_algorithm)
        self.manager = copy.deepcopy(self.manager_thread.manager)

        self.Bind(EVT_UPDATE_ELEVATORS, self.OnUpdateElevators)
        self.Bind(wx.EVT_CLOSE, self.Close)
        self.SetBackgroundColour('white')
        self.InitMenuBar()

    def _load_algorithms(self):
        self.algorithms = {}
        for i in glob.iglob('managers/*.py'):
            module = importlib.import_module(i.replace(os.path.sep, '.')[:-3])
            if not hasattr(module, '__manager__'):
                raise InvalidManager(f'Manager in {module} is not defined')
            if not hasattr(module, '__name__'):
                raise InvalidManager(f'Name in {module} is not defined')

            manager = module.__manager__
            if not issubclass(manager, ElevatorManager):
                raise InvalidManager(f'Manager in {module} is not a subclass of ElevatorManager')

            manager.name = module.__name__
            self.algorithms[manager.name] = manager

    def _import_simulation(self, fn):
        # TODO
        dt = datetime.now().isoformat()
        skip_bytes = len(f'fourjr/elevator-simulator {dt} fourjr/elevator-simulator'.encode('utf8'))
        with open(fn, 'rb') as f:
            self.manager_thread.manager = pickle.loads(gzip.decompress(f.read(skip_bytes)[:-skip_bytes]))

    def InitMenuBar(self):
        menubar = wx.MenuBar()
        fileMenu = wx.Menu()
        fileMenu.Append(wx.MenuItem(fileMenu, ID.MENU_APP_EXIT, '&Quit\tCtrl+Q'))

        self.Bind(wx.EVT_MENU, self.Close, id=ID.MENU_APP_EXIT)
        menubar.Append(fileMenu, '&File')

        self.SetMenuBar(menubar)
        self.SetFont(self.font)

    def OnUpdateElevators(self, e: wx.Event):
        for c in list(self.GetChildren()):
            if hasattr(c, 'OnUpdateElevators'):
                c.OnUpdateElevators(self.manager, e.manager)
        self.manager = copy.deepcopy(e.manager)

    def Close(self, *_):
        self.manager_thread.close()
        self.manager_thread.join()
        self.Destroy()

    def WriteToLog(self, level: LogLevel, message):
        self.FindWindowById(ID.PANEL_DEBUG_LOG).OnLogUpdate(LogMessage(level, message, self.manager_thread.current_tick))

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
        self.texts = {}  # id : (floor_text, pax_text)
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
        updated = False
        if len(before.elevators) > 6 and len(after.elevators) <= 6:
            updated = True
            self.sz.SetCols(3)
            self.sz.SetRows(2)
        elif len(before.elevators) != len(after.elevators) and len(after.elevators) > 6 and len(after.elevators) % 3 == 1:
            updated = True
            self.sz.SetCols(math.ceil(len(after.elevators) / 3))
            self.sz.SetRows(3)

        # elevator added
        for ev in after.elevators:
            if ev.id not in self.texts:  # equivalent to ev not in before.elevators
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

        # elevator removed
        for ev in before.elevators:
            if ev not in after.elevators:
                for index, elev in enumerate(self.sz.GetChildren()):
                    if elev.GetWindow().GetLabel() == f"Elevator {ev.id}":
                        break

                self.sz.Hide(index)
                self.sz.Remove(index)
                del self.texts[ev.id]
                updated = True

        if updated:
            self.window.WriteToLog(LogLevel.TRACE, "ElevatorsPanel Layout Updated")
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

        self.InitUI()

    def OnUpdateElevators(self, before, after):
        # changes to track: current_floor, destination, new elevators
        updated = False

        if before.floors != after.floors:
            updated = True
            for element_id in (
                ID.SELECT_ELEVATOR_ADD, ID.SELECT_PASSENGER_INITIAL, ID.SELECT_PASSENGER_DESTINATION
            ):
                element = self.FindWindowById(element_id)
                element.SetRange(1, after.floors)

        if before.elevators != after.elevators:
            updated = True
            for element_id in (ID.SELECT_ELEVATOR_REMOVE,):
                element = self.FindWindowById(element_id)
                element.SetItems([str(e.id) for e in after.elevators])

        if updated:
            self.window.WriteToLog(LogLevel.TRACE, "DebugPanel Layout Updated")
            self.Layout()

    def InitUI(self):
        self.LoadControlPanel()
        self.LoadControlPanel2()

        self.LoadNotesPanel()

        sz = wx.BoxSizer()
        sz.Add(self.nb, 1, wx.EXPAND)
        sz.SetDimension(0, 0, 540, 400)
        self.SetSizer(sz)

    def _add_elevator(self, floor):
        self.window.manager_thread.add_elevator(floor)
        self.window.WriteToLog(LogLevel.INFO, f'Added elevator on floor {floor}')

    def _remove_elevator(self, elevator_id):
        try:
            elevator_id = int(elevator_id)
        except ValueError:
            self.window.WriteToLog(LogLevel.ERROR, f'Invalid elevator id {elevator_id}')
            return

        try:
            self.window.manager_thread.remove_elevator(elevator_id)
        except BadArgument as e:
            self.window.WriteToLog(LogLevel.ERROR, str(e))
            return

        self.window.WriteToLog(LogLevel.INFO, f'Removed elevator {elevator_id}')

    def _add_passenger(self, floor_i, floor_f):
        if floor_i == floor_f:
            self.window.WriteToLog(LogLevel.ERROR, f'Passenger on floor {floor_i} to {floor_f} is not valid')
            return
        self.window.WriteToLog(LogLevel.INFO, f'Add passenger on floor {floor_i} to {floor_f}')
        return self.window.manager_thread.add_passenger(floor_i, floor_f)

    def _add_random_passengers(self, count):
        for _ in range(count):
            floor_i, floor_f = random.sample(range(1, self.window.floors + 1), 2)
            self._add_passenger(floor_i, floor_f)

    def _set_algorithm(self, algorithm):
        if algorithm not in self.window.algorithms:
            self.window.WriteToLog(LogLevel.ERROR, f'Algorithm {algorithm} not found')
            return

        self.window.manager_thread.set_manager(self.window.algorithms[algorithm])
        self.window.current_algorithm = self.window.algorithms[algorithm]
        self.window.WriteToLog(LogLevel.INFO, f'Set algorithm to {algorithm}')

    def _set_speed(self, speed):
        self.window.manager_thread.set_speed(speed)
        self.window.WriteToLog(LogLevel.INFO, f'Speed set to {speed}')

    def _set_floors(self, floor):
        self.window.manager_thread.set_floors(floor)
        self.window.WriteToLog(LogLevel.INFO, f"Setting floors to: {floor}")

    def _toggle_play(self, play_btn):
        self.window.active = not self.window.active
        self.window.WriteToLog(LogLevel.INFO, f"Setting play state to: {self.window.active}")
        play_btn.SetLabel('Play' if not self.window.active else 'Pause')

    def _export_simulation(self):
        dt = datetime.now().isoformat(sep=' ', timespec='seconds').replace(':', '-').replace(' ', '_')
        fn = f'{self.window.current_algorithm.name}_{dt}.esi'
        if not os.path.isdir('exports'):
            os.mkdir('exports')

        with open(f'exports/{fn}', 'wb') as f:
            f.write(
                f'fourjr/elevator-simulator {dt} fourjr/elevator-simulator'.encode('utf8') +
                gzip.compress(pickle.dumps(self.window.manager_thread.manager)) +
                f'\00\00fourjr/elevator-simulator {dt} fourjr/elevator-simulator'.encode('utf8')
            )

        self.window.WriteToLog(LogLevel.INFO, f'Exported as {fn}')

    def _reset_simulation(self):
        self.window.manager_thread.reset(self.window.current_algorithm)
        self.window.WriteToLog(LogLevel.INFO, f"Reset")

    def LoadControlPanel(self):
        panel = wx.Panel(self.nb, wx.ID_ANY)
        sz = wx.BoxSizer(wx.VERTICAL)
        sz.AddSpacer(10)

        # add elevator
        elevator_sz = wx.BoxSizer(wx.HORIZONTAL)
        elevator_sz.Add(wx.StaticText(panel, wx.ID_ANY, 'Elevators'), 0)

        elevator_sz.AddSpacer(15)
        ef_add_selection = wx.SpinCtrl(panel, id=ID.SELECT_ELEVATOR_ADD, initial=1, min=1, max=self.window.floors)
        elevator_sz.Add(ef_add_selection, 1, wx.FIXED_MINSIZE)
        self.floors_selections.append(ef_add_selection)

        add_elevator_btn = wx.Button(panel, wx.ID_ANY, 'Add')
        add_elevator_btn.Bind(
            wx.EVT_BUTTON,
            lambda _: self._add_elevator(ef_add_selection.GetValue())
        )
        elevator_sz.Add(add_elevator_btn, 0, wx.FIXED_MINSIZE)

        elevator_sz.AddSpacer(15)
        ef_remove_selection = wx.ComboBox(panel, id=ID.SELECT_ELEVATOR_REMOVE, choices=[x.id for x in self.window.manager_thread.manager.elevators])
        elevator_sz.Add(ef_remove_selection, 1, wx.FIXED_MINSIZE)

        add_elevator_btn = wx.Button(panel, wx.ID_ANY, 'Remove')
        add_elevator_btn.Bind(
            wx.EVT_BUTTON,
            lambda _: self._remove_elevator(ef_remove_selection.GetValue())
        )
        elevator_sz.Add(add_elevator_btn, 0, wx.FIXED_MINSIZE)

        sz.Add(elevator_sz, 0, wx.FIXED_MINSIZE | wx.TOP)
        sz.AddSpacer(5)

        # passenger adding
        passenger_sz = wx.BoxSizer(wx.HORIZONTAL)
        passenger_sz.Add(wx.StaticText(panel, wx.ID_ANY, 'PAX'), 0)
        passenger_sz.AddSpacer(10)
        pfi_selection = wx.SpinCtrl(panel, id=ID.SELECT_PASSENGER_INITIAL, value='Start', initial=1, min=1, max=self.window.floors)
        pff_selection = wx.SpinCtrl(panel, id=ID.SELECT_PASSENGER_DESTINATION, value='End', initial=1, min=1, max=self.window.floors)
        passenger_sz.Add(pfi_selection, 1, wx.FIXED_MINSIZE)
        passenger_sz.Add(pff_selection, 1, wx.FIXED_MINSIZE)

        add_passenger_btn = wx.Button(panel, wx.ID_ANY, 'Add')
        add_passenger_btn.Bind(
            wx.EVT_BUTTON,
            lambda _: self._add_passenger(pfi_selection.GetValue(), pff_selection.GetValue())
        )
        passenger_sz.Add(add_passenger_btn, 0, wx.FIXED_MINSIZE)
        passenger_sz.AddSpacer(20)

        # -> random
        random_passenger_count = wx.SpinCtrl(panel, value='Count', initial=1, min=1)
        passenger_sz.Add(random_passenger_count, 1, wx.FIXED_MINSIZE)
        random_passenger_btn = wx.Button(panel, wx.ID_ANY, 'Random')
        random_passenger_btn.Bind(
            wx.EVT_BUTTON,
            lambda _: self._add_random_passengers(random_passenger_count.GetValue()
        ))
        passenger_sz.Add(random_passenger_btn, 1, wx.FIXED_MINSIZE)


        sz.Add(passenger_sz, 0, wx.FIXED_MINSIZE | wx.TOP)
        sz.AddSpacer(5)

        # algorithm selection
        algo_sz = wx.BoxSizer(wx.HORIZONTAL)
        algo_sz.Add(wx.StaticText(panel, wx.ID_ANY, 'Algorithm'), 0)
        algo_sz.AddSpacer(10)

        algo_selection = wx.Choice(panel, choices=list(self.window.algorithms.keys()))
        algo_selection.SetSelection(0)
        algo_sz.Add(algo_selection, 1, wx.FIXED_MINSIZE)

        algo_selection.Bind(
            wx.EVT_CHOICE,
            lambda _: self._set_algorithm(algo_selection.GetString(algo_selection.GetCurrentSelection()))
        )

        sz.Add(algo_sz, 0, wx.FIXED_MINSIZE | wx.TOP)
        sz.AddSpacer(5)

        # speed
        speed_sz = wx.BoxSizer(wx.HORIZONTAL)
        speed_sz.Add(wx.StaticText(panel, wx.ID_ANY, 'Speed'), 0)
        speed_sz.AddSpacer(10)

        speed_selection = wx.SpinCtrlDouble(panel, initial=3, min=0.01, inc=0.01)
        speed_sz.Add(speed_selection, 1, wx.FIXED_MINSIZE)

        speed_selection.Bind(
            wx.EVT_SPINCTRLDOUBLE,
            lambda _: self._set_speed(speed_selection.GetValue())
        )

        sz.Add(speed_sz, 0, wx.FIXED_MINSIZE | wx.TOP)
        sz.AddSpacer(5)

        # floors
        floor_sz = wx.BoxSizer(wx.HORIZONTAL)
        floor_sz.Add(wx.StaticText(panel, wx.ID_ANY, 'Floors'), 0)
        floor_sz.AddSpacer(10)

        floor_selection = wx.SpinCtrl(panel, initial=10, min=1, max=1000)
        floor_sz.Add(floor_selection, 1, wx.FIXED_MINSIZE)

        floor_sz.AddSpacer(10)

        floor_selection.Bind(
            wx.EVT_SPINCTRL,
            lambda _: self._set_floors(floor_selection.GetValue())
        )

        sz.Add(floor_sz, 0, wx.FIXED_MINSIZE | wx.TOP)
        sz.AddSpacer(5)

        # control
        ctrl_sz = wx.BoxSizer(wx.HORIZONTAL)

        play_btn = wx.Button(panel, wx.ID_ANY, 'Play')
        play_btn.Bind(
            wx.EVT_BUTTON,
            lambda _: self._toggle_play(play_btn)
        )
        ctrl_sz.Add(play_btn, 1, wx.FIXED_MINSIZE)

        save_btn = wx.Button(panel, wx.ID_ANY, 'Export')
        save_btn.Bind(
            wx.EVT_BUTTON,
            lambda _: self._export_simulation()
        )
        ctrl_sz.Add(save_btn, 1, wx.FIXED_MINSIZE)
        ctrl_sz.AddSpacer(10)

        reset_btn = wx.Button(panel, wx.ID_ANY, 'Reset')
        reset_btn.Bind(
            wx.EVT_BUTTON,
            lambda _: self._reset_simulation()
        )
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
        load_sz = wx.BoxSizer(wx.HORIZONTAL)
        load_sz.Add(wx.StaticText(panel, wx.ID_ANY, 'Max Load'), 1)
        load_selection = wx.SpinCtrl(panel, initial=15, min=1)
        load_sz.Add(load_selection, 1, wx.FIXED_MINSIZE)

        def set_load_callback(_):
            self.window.manager_thread.set_max_load(load_selection.GetValue() * 60)
            self.window.WriteToLog(LogLevel.INFO, f"Setting max load to: {load_selection.GetValue()}")

        load_selection.Bind(wx.EVT_SPINCTRL, set_load_callback)

        sz.Add(load_sz, 0, wx.FIXED_MINSIZE | wx.TOP)

        # end
        sz.SetDimension(wx.Point(0, 0), self.size)
        self.nb.AddPage(panel, "Controls 2")

    def LoadNotesPanel(self):
        panel = wx.Panel(self.nb, wx.ID_ANY)
        sz = wx.BoxSizer(wx.VERTICAL)

        tc = wx.TextCtrl(panel, wx.ID_ANY, '', style=wx.TE_MULTILINE | wx.TE_BESTWRAP, size=(self.size.x, self.size.y - 20))
        sz.Add(tc, 1, wx.EXPAND)

        sz.SetDimension(wx.Point(0, 0), self.size)
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
                    self.rows[n][1].SetForegroundColour(wx.Colour(255, 0, 0))
                self.rows[n][0].SetLabel(str(up // 60).zfill(2))
                self.rows[n][1].SetLabel(str(down // 60).zfill(2))

            updated = True

        if updated:
            self.window.WriteToLog(LogLevel.TRACE, "ElevatorStatusPanel Layout Updated")
            self.Layout()
            if before.floors != after.floors:
                self.SetupScrolling()

    def _add_floor(self, num):
        label_font = wx.Font(self.window.font)
        label_font.SetPointSize(21)
        button_font = wx.Font(self.window.font)
        button_font.SetPointSize(18)

        text = wx.StaticText(self, wx.ID_ANY, str(num + 1))
        text.SetFont(button_font)
        self.sz.Add(text, 0, wx.FIXED_MINSIZE | wx.CENTER)

        up_text = wx.StaticText(self, wx.ID_ANY, '00')
        up_text.SetFont(button_font)

        self.sz.Add(up_text, 0, wx.FIXED_MINSIZE)

        down_text = wx.StaticText(self, wx.ID_ANY, '00')
        down_text.SetFont(button_font)

        self.rows.append((up_text, down_text))

        self.sz.Add(down_text, 0, wx.FIXED_MINSIZE)

    def InitUI(self):
        self.sz = wx.FlexGridSizer(3, 1, 3)

        # header
        button_font = wx.Font(self.window.font)
        button_font.SetPointSize(18)

        self.sz.AddSpacer(30)

        up_text = wx.StaticText(self, wx.ID_ANY, Unicode.UP)
        up_text.SetFont(button_font)
        self.sz.Add(up_text, 0, wx.FIXED_MINSIZE)

        down_text = wx.StaticText(self, wx.ID_ANY, Unicode.DOWN)
        down_text.SetFont(button_font)
        self.sz.Add(down_text, 0, wx.FIXED_MINSIZE)

        # floors
        for i in range(self.window.manager_thread.manager.floors):
            self._add_floor(i)

        self.SetSizer(self.sz)
        self.sz.SetDimension(0, 0, 150, self.window.effective_size.y)
        self.SetupScrolling()


class StatsPanel(scrolled.ScrolledPanel):
    def __init__(self, window):
        super().__init__(id=wx.ID_ANY, parent=window, size=wx.Size(350, 250), pos=wx.Point(730, 0), style=wx.TAB_TRAVERSAL | wx.BORDER_THEME)
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

    def update_stats(self, manager):
        fmt_text = f'Tick: {manager.thread.current_tick}\nAlgorithm: {manager.name}\n\n(MIN/MEAN/MED/MAX)\n\n'
        fmt_text += f'Wait Time: {generate_stats(manager.wait_times)}\n'
        fmt_text += f'Time in Lift: {generate_stats(manager.time_in_lift)}\n'
        fmt_text += f'Occupancy: {generate_stats(manager.occupancy)}'
        self.stats_tc.SetValue(fmt_text)

    def OnUpdateElevators(self, before, after):
        self.update_stats(after)

        if before.loads != after.loads:
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

        self.window.WriteToLog(LogLevel.TRACE, "StatsPanel Layout Updated")
        self.Layout()
        self.SetupScrolling()

    def LoadStatsPanel(self):
        panel = wx.Panel(self.nb, wx.ID_ANY)
        sz = wx.BoxSizer(wx.VERTICAL)

        self.stats_tc = wx.TextCtrl(panel, wx.ID_ANY, '', style=wx.TE_MULTILINE | wx.TE_READONLY | wx.TE_BESTWRAP)
        self.update_stats(self.window.manager_thread.manager)
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
        super().__init__(id=ID.PANEL_DEBUG_LOG, parent=window, size=wx.Size(350, 380), pos=wx.Point(730, 260), style=wx.TAB_TRAVERSAL | wx.BORDER_THEME)

        self.log_messages: List[LogMessage] = []
        self.log_levels: Set[LogLevel] = set(LogLevel)
        self.log_levels.remove(LogLevel.TRACE)
        self.log_levels.remove(LogLevel.DEBUG)
        self.InitUI()
        self.window.WriteToLog(LogLevel.INFO, 'Log started')

    def OnLogUpdate(self, message):
        self.log_messages.append(message)
        if message.level in self.log_levels:
            self.log_tc.AppendText(f'[{message.level.name[0]}] {message.tick}: {message.message}\n')

    def OnLogLevelChanged(self, e):
        cb = e.GetEventObject()
        if e.IsChecked():
            self.log_levels.add(LogLevel[cb.GetLabel()])
        else:
            self.log_levels.remove(LogLevel[cb.GetLabel()])

        filtered_log_messages = filter(lambda x: x.level in self.log_levels, self.log_messages)
        self.log_tc.SetValue('\n'.join(f'[{i.level.name[0]}] {i.tick}: {i.message}' for i in filtered_log_messages) + '\n')
        # scroll to bottom
        self.log_tc.SetScrollPos(
            wx.VERTICAL,
            self.log_tc.GetScrollRange(wx.VERTICAL)
        )
        self.log_tc.SetInsertionPoint(-1)

    def InitUI(self):
        sz = wx.BoxSizer(wx.VERTICAL)
        sz.Add(wx.StaticText(self, wx.ID_ANY, 'Log'))
        sz.AddSpacer(3)
        _, height = sz.GetMinSize()
        self.log_tc = wx.TextCtrl(self, wx.ID_ANY, '', style=wx.TE_MULTILINE | wx.TE_READONLY | wx.HSCROLL, size=wx.Size(350, 380 - height - 100))
        sz.Add(self.log_tc, 1, wx.EXPAND)

        checkbox_sz = wx.FlexGridSizer(3, 1, 1)

        for i in LogLevel:
            cb = wx.CheckBox(self, wx.ID_ANY, i.name)
            if i in self.log_levels:
                cb.SetValue(True)
            checkbox_sz.Add(cb)

            self.Bind(wx.EVT_CHECKBOX, self.OnLogLevelChanged, cb)

        sz.Add(checkbox_sz, 0, wx.EXPAND)

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
