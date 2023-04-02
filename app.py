import wx
import wx.lib.scrolledpanel as scrolled
from enum import IntEnum


app = wx.App()


class BaseFrame(wx.Frame):
    def __init__(self, title, *, size=wx.DefaultSize, pos=wx.DefaultPosition, parent=None):
        super().__init__(parent, title=title, size=size, pos=pos)


class ID(IntEnum):
    APP_EXIT = 1
    ELEVATORS_PANEL = 2


class ControlPanel(BaseFrame):
    def __init__(self):
        super().__init__('Control Panel', pos=wx.Point(0, 0), size=wx.Size(1080, 720))
        self.font = wx.Font(13, wx.DEFAULT, wx.NORMAL, wx.NORMAL, False, 'Segoue UI')
        self.InitUI()

    def InitUI(self):
        menubar = wx.MenuBar()
        fileMenu = wx.Menu()
        fileMenu.Append(wx.MenuItem(fileMenu, ID.APP_EXIT, '&Quit\tCtrl+Q'))

        self.Bind(wx.EVT_MENU, self.OnQuit, id=ID.APP_EXIT)
        menubar.Append(fileMenu, '&File')

        self.SetMenuBar(menubar)
        self.SetFont(self.font)

    def OnQuit(self, e):
        self.Close()


class ElevatorsPanel(scrolled.ScrolledPanel):
    def __init__(self, parent):
        self.parent = parent
        self.size = wx.Size(540, 240)
        super().__init__(id=wx.ID_ANY, parent=parent, size=self.size, style=wx.TAB_TRAVERSAL | wx.BORDER_THEME)
        self.InitUI()

    def InitUI(self):
        main_box = wx.StaticBox(self, label="Elevators", pos=wx.Point(0, 0))
        sz = wx.StaticBoxSizer(main_box, wx.HORIZONTAL)

        elevators = [(2, 3), (5, 1), (7, 4), (9, 2), (7, 1)]  # current_pos, going_to
        # num_elevators = len(elevators)
        # if num_elevators <= 6:
        #     rows = 2
        #     cols = 3
        # else:
        #     rows = 3
        #     cols = math.ceil(num_elevators / 3)

        # sz = wx.GridSizer(rows, cols, gap=wx.Size(5, 5))
        for n, (curr, going) in enumerate(elevators):
            elevator_box = wx.StaticBox(main_box, label="Elevator " + str(n + 1), pos=wx.Point(0, 0), size=wx.Size(115, 100))
            top_border, other_border = elevator_box.GetBordersForSizer()

            text_sizer = wx.BoxSizer(wx.VERTICAL)
            text_sizer.AddSpacer(top_border)

            text = wx.StaticText(elevator_box, wx.ID_ANY, f'{curr} → {going}')
            font = wx.Font(self.parent.font)
            font.SetPointSize(22)
            text.SetFont(font)
            text_sizer.Add(text, 1, wx.ALL | wx.CENTER, other_border+10)
            elevator_box.SetSizer(text_sizer)

            sz.Add(elevator_box, 1, wx.ALL | wx.CENTRE, 10)
 
        sz.SetDimension(wx.Point(0, 0), self.size)
        self.SetSizer(sz)
        self.SetupScrolling(scroll_y=False)

    # def OnPaint(self, e): -
    #     dc = wx.PaintDC(self) 
    #     brush = wx.Brush("white")  
    #     dc.SetBackground(brush)
    #     dc.Clear() 


def main():
    control_panel = ControlPanel()
    control_panel.Show()

    current_elevators = ElevatorsPanel(parent=control_panel)
    current_elevators.Show()
    app.MainLoop()


main()
