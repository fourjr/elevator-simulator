import logging
import wx
import wx.lib.scrolledpanel as scrolled

from utils import Unicode


class ElevatorStatusPanel(scrolled.ScrolledPanel):
    def __init__(self, window):
        self.window = window
        super().__init__(
            id=wx.ID_ANY,
            parent=window,
            size=wx.Size(180, self.window.effective_size.y),
            pos=wx.Point(550, 0),
            style=wx.TAB_TRAVERSAL | wx.BORDER_THEME,
        )

        self.rows = []
        self.InitUI()

    def OnUpdateAlgorithm(self, before, after):
        # Number of floors and loads
        updated = False
        if before.floors < after.floors:
            updated = True
            for i in range(after.floors - before.floors):
                self._add_floor(i + before.floors)

        elif before.floors > after.floors:
            updated = True
            count = self.sz.GetItemCount()
            to_remove = (before.floors - after.floors) * 3
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
            self.window.WriteToLog(logging.DEBUG, 'ElevatorStatusPanel Layout Updated')
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
        for i in range(self.window.manager.algorithm.floors):
            self._add_floor(i)

        self.SetSizer(self.sz)
        self.sz.SetDimension(0, 0, 150, self.window.effective_size.y)
        self.SetupScrolling()
