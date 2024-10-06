import os
import random

import wx
import wx.aui as aui

from constants import ID, LogLevel
from errors import BadArgument
from utils import save_algorithm


class ControlPanel(wx.Panel):
    def __init__(self, window):
        self.window = window
        # if self.window.positions['debug'] is None:
        #     raise RuntimeError('Elevator panel must be loaded first')

        self.size = wx.Size(540, self.window.effective_size.y - 400)
        super().__init__(
            id=wx.ID_ANY,
            parent=window,
            size=self.size,
            style=wx.TAB_TRAVERSAL | wx.BORDER_THEME,
            pos=(0, 400),
        )
        self.nb = aui.AuiNotebook(self, style=wx.aui.AUI_NB_TOP)
        self.floors_selections = []

        self.InitUI()

    def OnUpdateAlgorithm(self, before, after):
        # changes to track: current_floor, destination, new elevators, active
        updated = False

        if before.floors != after.floors:
            updated = True
            for element_id in (
                ID.SELECT_ELEVATOR_ADD,
                ID.SELECT_PASSENGER_INITIAL,
                ID.SELECT_PASSENGER_DESTINATION,
            ):
                element = self.FindWindowById(element_id)
                element.SetRange(1, after.floors)

        if before.elevators != after.elevators:
            updated = True
            for element_id in (ID.SELECT_ELEVATOR_REMOVE,):
                element = self.FindWindowById(element_id)
                element.SetItems([str(e.id) for e in after.elevators])

        if before.active != after.active:
            updated = True
            element = self.FindWindowById(ID.BUTTON_CONTROL_PLAY)
            element.SetLabel('Play' if not after.active else 'Pause')

        if updated:
            self.window.WriteToLog(LogLevel.TRACE, 'DebugPanel Layout Updated')
            self.Layout()

    def InitUI(self):
        self.LoadControlPanel()
        self.LoadControlPanel2()

        self.LoadNotesPanel()

        sz = wx.BoxSizer()
        sz.Add(self.nb, 1, wx.EXPAND)
        sz.SetDimension(0, 0, 540, 400)
        self.SetSizer(sz)

    def add_elevator(self, floor):
        self.window.manager.add_elevator(floor)
        self.window.WriteToLog(LogLevel.INFO, f'Added elevator on floor {floor}')

    def remove_elevator(self, elevator_id):
        try:
            elevator_id = int(elevator_id)
        except ValueError:
            self.window.WriteToLog(LogLevel.ERROR, f'Invalid elevator id {elevator_id}')
            return

        try:
            self.window.manager.remove_elevator(elevator_id)
        except BadArgument as e:
            self.window.WriteToLog(LogLevel.ERROR, str(e))
            return

        self.window.WriteToLog(LogLevel.INFO, f'Removed elevator {elevator_id}')

    def add_passenger(self, floor_i, floor_f):
        if floor_i == floor_f:
            self.window.WriteToLog(
                LogLevel.ERROR,
                f'Passenger on floor {floor_i} to {floor_f} is not valid',
            )
            return
        self.window.WriteToLog(LogLevel.INFO, f'Add passenger on floor {floor_i} to {floor_f}')
        return self.window.manager.add_passenger(floor_i, floor_f)

    def _add_random_passengers(self, count):
        for _ in range(count):
            floor_i, floor_f = random.sample(range(1, self.window.floors + 1), 2)
            self.add_passenger(floor_i, floor_f)

    def set_algorithm(self, algorithm_name):
        if algorithm_name not in self.window.algorithms:
            self.window.WriteToLog(LogLevel.ERROR, f'Algorithm {algorithm_name} not found')
            return

        self.window.manager.set_algorithm(self.window.algorithms[algorithm_name])
        self.window.current_algorithm = self.window.algorithms[algorithm_name]
        self.window.WriteToLog(LogLevel.INFO, f'Set algorithm to {algorithm_name}')

    def set_speed(self, speed):
        self.window.manager.set_speed(speed)
        self.window.WriteToLog(LogLevel.INFO, f'Speed set to {speed}')

    def set_floors(self, floor_count):
        self.window.manager.set_floors(floor_count)
        self.window.WriteToLog(LogLevel.INFO, f'Setting floors to: {floor_count}')

    def toggle_play(self):
        self.window.manager.toggle_active()
        new_state = not self.window.manager.algorithm.active
        self.window.WriteToLog(LogLevel.INFO, f'Setting play state to: {new_state}')
        # self.FindWindowById(ID.BUTTON_CONTROL_PLAY).SetLabel('Play' if not self.window.active else 'Pause')

    def import_simulation_fs(self):
        default_dir = os.getcwd()
        if os.path.isdir(os.path.join(default_dir, 'exports')):
            default_dir = os.path.join(default_dir, 'exports')

        dlg = wx.FileDialog(
            self,
            message='Choose a file',
            defaultDir=default_dir,
            defaultFile='',
            wildcard='*.esi',
            style=wx.FD_OPEN | wx.FD_CHANGE_DIR | wx.FD_FILE_MUST_EXIST | wx.FD_PREVIEW,
        )
        if dlg.ShowModal() == wx.ID_OK:
            # This returns a Python list of files that were selected.
            paths = dlg.GetPaths()
            fp = paths[0]

            self.window._import_simulation(fp)
            _, fn = os.path.split(fp)

            self.window.WriteToLog(LogLevel.INFO, f'Imported {fn}')

        dlg.Destroy()

    def export_simulation(self):
        fn = save_algorithm(self.window.manager.algorithm)
        self.window.WriteToLog(LogLevel.INFO, f'Exported as {fn}')

    def reset_simulation(self):
        self.window.manager.reset(self.window.current_algorithm)
        self.window.WriteToLog(LogLevel.INFO, 'Reset')

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
        add_elevator_btn.Bind(wx.EVT_BUTTON, lambda _: self.add_elevator(ef_add_selection.GetValue()))
        elevator_sz.Add(add_elevator_btn, 0, wx.FIXED_MINSIZE)

        elevator_sz.AddSpacer(15)
        ef_remove_selection = wx.ComboBox(
            panel,
            id=ID.SELECT_ELEVATOR_REMOVE,
            choices=[x.id for x in self.window.manager.algorithm.elevators],
        )
        elevator_sz.Add(ef_remove_selection, 1, wx.FIXED_MINSIZE)

        add_elevator_btn = wx.Button(panel, wx.ID_ANY, 'Remove')
        add_elevator_btn.Bind(
            wx.EVT_BUTTON,
            lambda _: self.remove_elevator(ef_remove_selection.GetValue()),
        )
        elevator_sz.Add(add_elevator_btn, 0, wx.FIXED_MINSIZE)

        sz.Add(elevator_sz, 0, wx.FIXED_MINSIZE | wx.TOP)
        sz.AddSpacer(5)

        # passenger adding
        passenger_sz = wx.BoxSizer(wx.HORIZONTAL)
        passenger_sz.Add(wx.StaticText(panel, wx.ID_ANY, 'PAX'), 0)
        passenger_sz.AddSpacer(10)
        pfi_selection = wx.SpinCtrl(
            panel,
            id=ID.SELECT_PASSENGER_INITIAL,
            value='Start',
            initial=1,
            min=1,
            max=self.window.floors,
        )
        pff_selection = wx.SpinCtrl(
            panel,
            id=ID.SELECT_PASSENGER_DESTINATION,
            value='End',
            initial=1,
            min=1,
            max=self.window.floors,
        )
        passenger_sz.Add(pfi_selection, 1, wx.FIXED_MINSIZE)
        passenger_sz.Add(pff_selection, 1, wx.FIXED_MINSIZE)

        add_passenger_btn = wx.Button(panel, wx.ID_ANY, 'Add')
        add_passenger_btn.Bind(
            wx.EVT_BUTTON,
            lambda _: self.add_passenger(pfi_selection.GetValue(), pff_selection.GetValue()),
        )
        passenger_sz.Add(add_passenger_btn, 0, wx.FIXED_MINSIZE)
        passenger_sz.AddSpacer(20)

        # -> random
        random_passenger_count = wx.SpinCtrl(panel, value='Count', initial=1, min=1)
        passenger_sz.Add(random_passenger_count, 1, wx.FIXED_MINSIZE)
        random_passenger_btn = wx.Button(panel, wx.ID_ANY, 'Random')
        random_passenger_btn.Bind(
            wx.EVT_BUTTON,
            lambda _: self._add_random_passengers(random_passenger_count.GetValue()),
        )
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
            lambda _: self.set_algorithm(algo_selection.GetString(algo_selection.GetCurrentSelection())),
        )

        sz.Add(algo_sz, 0, wx.FIXED_MINSIZE | wx.TOP)
        sz.AddSpacer(5)

        # speed
        speed_sz = wx.BoxSizer(wx.HORIZONTAL)
        speed_sz.Add(wx.StaticText(panel, wx.ID_ANY, 'Speed'), 0)
        speed_sz.AddSpacer(10)

        speed_selection = wx.SpinCtrlDouble(panel, initial=3, min=0.01, inc=0.01)
        speed_sz.Add(speed_selection, 1, wx.FIXED_MINSIZE)

        speed_selection.Bind(wx.EVT_SPINCTRLDOUBLE, lambda _: self.set_speed(speed_selection.GetValue()))

        sz.Add(speed_sz, 0, wx.FIXED_MINSIZE | wx.TOP)
        sz.AddSpacer(5)

        # floors
        floor_sz = wx.BoxSizer(wx.HORIZONTAL)
        floor_sz.Add(wx.StaticText(panel, wx.ID_ANY, 'Floors'), 0)
        floor_sz.AddSpacer(10)

        floor_selection = wx.SpinCtrl(panel, initial=10, min=1, max=1000)
        floor_sz.Add(floor_selection, 1, wx.FIXED_MINSIZE)

        floor_sz.AddSpacer(10)

        floor_selection.Bind(wx.EVT_SPINCTRL, lambda _: self.set_floors(floor_selection.GetValue()))

        sz.Add(floor_sz, 0, wx.FIXED_MINSIZE | wx.TOP)
        sz.AddSpacer(5)

        # control
        ctrl_sz = wx.BoxSizer(wx.HORIZONTAL)

        play_btn = wx.Button(panel, ID.BUTTON_CONTROL_PLAY, 'Play')
        play_btn.Bind(wx.EVT_BUTTON, lambda _: self.toggle_play())
        ctrl_sz.Add(play_btn, 1, wx.FIXED_MINSIZE)
        ctrl_sz.AddSpacer(10)

        import_btn = wx.Button(panel, wx.ID_ANY, 'Import')
        import_btn.Bind(wx.EVT_BUTTON, lambda _: self.import_simulation_fs())
        ctrl_sz.Add(import_btn, 1, wx.FIXED_MINSIZE)

        save_btn = wx.Button(panel, wx.ID_ANY, 'Export')
        save_btn.Bind(wx.EVT_BUTTON, lambda _: self.export_simulation())
        ctrl_sz.Add(save_btn, 1, wx.FIXED_MINSIZE)
        ctrl_sz.AddSpacer(10)

        reset_btn = wx.Button(panel, wx.ID_ANY, 'Reset')
        reset_btn.Bind(wx.EVT_BUTTON, lambda _: self.reset_simulation())
        ctrl_sz.Add(reset_btn, 1, wx.FIXED_MINSIZE)
        ctrl_sz.AddSpacer(10)

        sz.Add(ctrl_sz, 0, wx.FIXED_MINSIZE | wx.TOP)

        # end
        sz.SetDimension(wx.Point(0, 0), self.size)
        self.nb.AddPage(panel, 'Controls')

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
            self.window.manager.set_max_load(load_selection.GetValue() * 60)
            self.window.WriteToLog(LogLevel.INFO, f'Setting max load to: {load_selection.GetValue()}')

        load_selection.Bind(wx.EVT_SPINCTRL, set_load_callback)

        sz.Add(load_sz, 0, wx.FIXED_MINSIZE | wx.TOP)

        # end
        sz.SetDimension(wx.Point(0, 0), self.size)
        self.nb.AddPage(panel, 'Controls 2')

    def LoadNotesPanel(self):
        panel = wx.Panel(self.nb, wx.ID_ANY)
        sz = wx.BoxSizer(wx.VERTICAL)

        tc = wx.TextCtrl(
            panel,
            wx.ID_ANY,
            '',
            style=wx.TE_MULTILINE | wx.TE_BESTWRAP,
            size=(self.size.x, self.size.y - 20),
        )
        sz.Add(tc, 1, wx.EXPAND)

        sz.SetDimension(wx.Point(0, 0), self.size)
        self.nb.AddPage(panel, 'Notes')
