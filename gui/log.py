from typing import List, Set

import wx

from constants import ID, LogLevel
from models import log_message


class LogPanel(wx.Panel):
    def __init__(self, window):
        # super().__init__(id=wx.ID_ANY, parent=window, style=wx.TAB_TRAVERSAL | wx.BORDER_THEME)
        self.window = window
        super().__init__(
            id=ID.PANEL_DEBUG_LOG,
            parent=window,
            size=wx.Size(350, 380),
            pos=wx.Point(730, 260),
            style=wx.TAB_TRAVERSAL | wx.BORDER_THEME,
        )

        self.log_messages: List[log_message.LogMessage] = []
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
        self.log_tc.SetValue(
            '\n'.join(f'[{i.level.name[0]}] {i.tick}: {i.message}' for i in filtered_log_messages) + '\n'
        )
        # scroll to bottom
        self.log_tc.SetScrollPos(wx.VERTICAL, self.log_tc.GetScrollRange(wx.VERTICAL))
        self.log_tc.SetInsertionPoint(-1)

    def InitUI(self):
        sz = wx.BoxSizer(wx.VERTICAL)
        sz.Add(wx.StaticText(self, wx.ID_ANY, 'Log'))
        sz.AddSpacer(3)
        _, height = sz.GetMinSize()
        self.log_tc = wx.TextCtrl(
            self,
            wx.ID_ANY,
            '',
            style=wx.TE_MULTILINE | wx.TE_READONLY | wx.HSCROLL,
            size=wx.Size(350, 380 - height - 100),
        )
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
