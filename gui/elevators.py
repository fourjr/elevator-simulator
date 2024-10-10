import logging
import math

import wx
import wx.lib.scrolledpanel as scrolled

from utils import Unicode


class ElevatorsPanel(scrolled.ScrolledPanel):
    def __init__(self, window):
        self.window = window
        super().__init__(id=wx.ID_ANY, parent=window, style=wx.TAB_TRAVERSAL | wx.BORDER_THEME)
        self.texts = {}  # id : (floor_text, pax_text)
        self.InitUI()
        self.SetupScrolling(scroll_y=False)

    def _add_elevator(self, ev):
        elevator_box = wx.StaticBox(self, label=f'Elevator {ev.id}', pos=wx.Point(0, 0), size=wx.Size(130, 100))
        top_border, other_border = elevator_box.GetBordersForSizer()

        text_sizer = wx.BoxSizer(wx.VERTICAL)
        text_sizer.AddSpacer(top_border)

        fmt_text = f'{ev.current_floor}'
        if ev.destination is not None and ev.destination != ev.current_floor:
            fmt_text += f' {Unicode.ARROW} {ev.destination}'

        floor_text = wx.StaticText(elevator_box, wx.ID_ANY, fmt_text)

        font = wx.Font(self.window.font)
        font.SetPointSize(19)
        floor_text.SetFont(font)
        text_sizer.Add(floor_text, 1, wx.ALL | wx.CENTER)

        pax_text = wx.StaticText(elevator_box, wx.ID_ANY, f'{ev.load // 60} PAX')
        text_sizer.Add(pax_text, 1, wx.ALL | wx.CENTER, other_border + 10)

        elevator_box.SetSizer(text_sizer)
        self.texts[ev.id] = (floor_text, pax_text)

        self.sz.Add(elevator_box, 1, wx.ALL | wx.CENTRE, 10)

    def OnUpdateAlgorithm(self, before, after):
        # changes to track: current_floor, destination, new elevators
        updated = False
        if len(before.elevators) != len(after.elevators):
            if len(before.elevators) > 6 and len(after.elevators) <= 6:
                updated = True
                self.sz.SetCols(3)
                self.sz.SetRows(2)
            elif len(after.elevators) > 6 and math.ceil(len(before.elevators) / 3) != math.ceil(
                len(after.elevators) / 3
            ):
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
                if ev.destination is not None and ev.destination != ev.current_floor:
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
                    if elev.GetWindow().GetLabel() == f'Elevator {ev.id}':
                        break

                self.sz.Hide(index)
                self.sz.Remove(index)
                del self.texts[ev.id]
                updated = True

        if updated:
            self.window.WriteToLog(logging.DEBUG, 'ElevatorsPanel Layout Updated')
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
