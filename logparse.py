#!/usr/bin/env python
# encoding: utf-8
# -*- coding: utf-8 -*-

'''

Copyright (C) 2010-2011 FFXIVBattle.com
All rights reserved.

Permission is hereby granted, free of charge, to any person obtaining a copy of this software and 
associated documentation files (the "Log Parser"), to deal in the Software without restriction, 
including without limitation the rights to use, copy, modify, merge, publish, distribute, sublicense, 
and/or sell copies of the Software, and to permit persons to whom the Software is furnished to do 
so, subject to the following conditions:

1. Redistributions of source code must retain the above copyright notice, this list of conditions, 
and the following disclaimer.

2. Redistributions in binary form must reproduce the above copyright notice, this list of conditions 
and the following disclaimer in the documentation and/or other materials provided with the distribution, 
and in the same place and form as other copyright, license and disclaimer information.

3. The end-user documentation included with the redistribution, if any, must include the following acknowledgment: 

"This product includes software developed by FFXIVBattle.com (http://www.ffxivbattle.com/) and its contributors", 

in the same place and form as other third-party acknowledgments. Alternately, this acknowledgment may appear in 
the software itself, in the same form and location as other such third-party acknowledgments.

4. Except as contained in this notice, the name of FFXIVBattle.com shall not be used in advertising or otherwise 
to promote the sale, use or other dealings in this Software without prior written authorization from FFXIVBattle.com.

THIS SOFTWARE IS PROVIDED ``AS IS'' AND ANY EXPRESSED OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, 
THE IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE ARE DISCLAIMED. IN NO EVENT 
SHALL FFXIVBATTLE.COM OR ITS CONTRIBUTORS BE LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, 
OR CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES; LOSS 
OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER 
IN CONTRACT, STRICT LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE 
USE OF THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.

'''

import traceback

import hashlib
import ConfigParser
import wx
import wx.richtext
from threading import Thread 
import pickle
import datetime
import gzip
import sys
import os
import glob
import copy
import time
import json
import urllib
import urllib2
import uuid
import shutil
import array
import struct

from subprocess import Popen
import wx.lib.agw.hyperlink as hl

# for installations that already have a config move the file to the config directory
try:
    if os.path.exists('logparser.cfg'):
        if os.path.exists('config/'):
            shutil.move('logparser.cfg', 'config/logparser.cfg')
except:
    pass

# check to see if the config subdir exists and if the root logparser.cfg does
# not exist.  This is so when there is a problem moving the existing config it
# won't skip it.
if os.path.exists('config/') and not os.path.exists('logparser.cfg'):
    configfile = 'config/logparser.cfg'
else:
    configfile = 'logparser.cfg'

version = 4.7
charactername = ""
doloop = 0
app = None
autotranslatearray = None
currentlanguage = 'en'

# Store the last log parsed
lastlogparsed = 0

guithread = None

def nullstrip(s):
    # Return a string truncated at the first null character.
    try:
        s = s[:s.index('\x00')]
    except ValueError:  # No nulls were found, which is okay.
        pass
    return s

class PasswordDialog(wx.Dialog):
    def __init__(self, parent, id, title, defaultPassword, language):
        wx.Dialog.__init__(self, parent, id, title, size=(285, 160))

        if language == 'en':
            wx.StaticText(self, -1, 'Enter Character Password (NOT your ffxiv password)\r\n* This is so only you can submit records for your character. If you don\'t have a password type in a new one to set it.', (5,3), (280, 60))
            self.password = wx.TextCtrl(self, -1, defaultPassword, (5,65), (260, 22), style=wx.TE_PASSWORD)
            self.checkbox = wx.CheckBox(self, -1, "Save Password", (5,95), (110, 22))
            
            wx.Button(self,  wx.ID_OK, 'Ok', (115, 95), (70, 30))
            wx.Button(self,  wx.ID_CANCEL, 'Cancel', (195, 95), (70, 30))
        else:
            wx.StaticText(self, -1, u'文字パスワード（はなく、あなたのFF14パスワード）を入力してください\r\n* このためだけでなく、あなたの文字の記録を提出することができますです。あなたはそれを設定するための新しいいずれかのパスワードタイプを持っていない場合。', (5,3), (280, 60))
            self.password = wx.TextCtrl(self, -1, defaultPassword, (5,65), (260, 22), style=wx.TE_PASSWORD)
            self.checkbox = wx.CheckBox(self, -1, u"パスワードを保存", (5,95), (110, 22))
            
            wx.Button(self,  wx.ID_OK, u'はい', (115, 95), (70, 30))
            wx.Button(self,  wx.ID_CANCEL, u'キャンセル', (195, 95), (70, 30))

    def SetChecked(self, value):
        self.checkbox.SetValue(value)

    def SetValue(self, value):
        self.password.SetValue(value)

    def GetChecked(self):
        return self.checkbox.GetValue()

    def GetValue(self):
        return self.password.GetValue()

class ChangeCharacterNameDialog(wx.Dialog):
    def __init__(self, parent, id, title, language):
        wx.Dialog.__init__(self, parent, id, title, size=(320, 200))
        if language == 'en':
            wx.StaticText(self, -1, 'Enter new character name:', (5,3), (305, 15))
        else:
            wx.StaticText(self, -1, u'新キャラクターの名前を入力してください：', (5,3), (305, 15))
            
        self.newcharactername = wx.TextCtrl(self, -1, "", (5,20), (300, 22))
        if language == 'en':
            wx.StaticText(self, -1, 'Enter current password:', (5,47), (300, 15))
        else:
            wx.StaticText(self, -1, u'現在のパスワードを入力してください：', (5,47), (300, 15))
        self.password = wx.TextCtrl(self, -1, "", (5,65), (300, 22), style=wx.TE_PASSWORD)
        if language == 'en':
            wx.StaticText(self, -1, 'This may take up to 1 hour to appear on the website.\nChanging your character name can only be performed once an hour so choose wisely.', (5,90), (305, 40))
        else:
            wx.StaticText(self, -1, u'これは、ウェブサイト上で表示されるように1時間かかることがあります。\n時間はとても賢明な選択一度文字の名前を変更するだけで行うことができます。', (5,90), (305, 40))

        if language == 'en':
            wx.Button(self,  wx.ID_OK, 'Ok', (158, 135), (70, 30))
            wx.Button(self,  wx.ID_CANCEL, 'Cancel', (235, 135), (70, 30))
        else:
            wx.Button(self,  wx.ID_OK, u'はい', (158, 135), (70, 30))
            wx.Button(self,  wx.ID_CANCEL, u'キャンセル', (235, 135), (70, 30))

    def GetNewCharacterName(self):
        return self.newcharactername.GetValue()

    def GetPassword(self):
        return self.password.GetValue()

class ReverseIterator:
    def __init__(self, sequence):
        self.sequence = sequence
    def __iter__(self):
        length = len(self.sequence)
        i = length
        while i > 0:
            i = i - 1
            yield self.sequence[i]

class LogWindowContext(wx.Menu):
    def __init__(self, chatviewer, language):
        wx.Menu.__init__(self)
        self.chatviewer = chatviewer
        if language == 'en':
            copy = self.Append(wx.ID_COPY, 'Copy' )        
        else:
            copy = self.Append(wx.ID_COPY, u'コピー' )        
        self.AppendSeparator()
        if language == 'en':
            selectall = self.Append(wx.ID_SELECTALL, 'Select All' )
        else:
            selectall = self.Append(wx.ID_SELECTALL, u'すべて選択' )        
        copy.Enable(True)
        selectall.Enable(True)
        
        self.Bind(wx.EVT_MENU, self.ExecEvent)

    def ExecEvent(self, event):
        if event.GetId() == wx.ID_COPY:
            clipdata = wx.TextDataObject()
            clipdata.SetText(self.chatviewer.logWindow.GetStringSelection())
            wx.TheClipboard.Open()
            wx.TheClipboard.SetData(clipdata)
            wx.TheClipboard.Close()
        elif event.GetId() == wx.ID_SELECTALL:
            self.chatviewer.logWindow.SelectAll()

class ChatViewer(wx.Frame):

    def __init__(self, language):
        if language == 'en':
            wx.Frame.__init__(self, wx.GetApp().TopWindow, title='Chat Viewer', size=(500,400))
        else:
            wx.Frame.__init__(self, wx.GetApp().TopWindow, title=u'チャットビューア', size=(500,400))
        self.language = language
        # this is cleanup from an earlier version.  It will be removed after a few versions go by.
        if os.path.exists(os.path.join('chatlogs', '--Everything--.chat')):
            os.remove(os.path.join('chatlogs', '--Everything--.chat'))
        self.currdates = []
        self.chat_types = {
            '01': self.WriteSay, # say
            '02': self.WriteShout, # shout
            '03': self.WriteTell, # sending tell
            '04': self.WriteParty, # party
            '05': self.WriteLinkshell, # linkshell
            '06': self.WriteLinkshell, # linkshell
            '07': self.WriteLinkshell, # linkshell
            '08': self.WriteLinkshell, # linkshell
            '09': self.WriteLinkshell, # linkshell
            '0A': self.WriteLinkshell, # linkshell
            '0B': self.WriteLinkshell, # linkshell
            '0C': self.WriteLinkshell, # linkshell
            '0D': self.WriteTell, # get tell
            '0F': self.WriteLinkshell, # linkshell
            '0E': self.WriteLinkshell, # linkshell
            '0F': self.WriteLinkshell, # linkshell
            '10': self.WriteLinkshell, # linkshell
            '11': self.WriteLinkshell, # linkshell
            '12': self.WriteLinkshell, # linkshell
            '13': self.WriteLinkshell, # linkshell
            '14': self.WriteLinkshell, # linkshell
            '15': self.WriteLinkshell, # linkshell
            '19': self.WriteEmote, # other emote
            '1B': self.WriteEmote # emote
            }

        self.SetBackgroundColour((240,240,240))
        try:
            self.SetIcon(wx.Icon("icon.ico", wx.BITMAP_TYPE_ICO))
        except Exception as e:
            print e
        self.Bind(wx.EVT_CLOSE, self.OnClose)
        self.sb = self.CreateStatusBar() # A Statusbar in the bottom of the window
        panel = wx.Panel(self, -1)
        if self.language == 'en':
            static = wx.StaticText(panel, -1, 'Select a date/time to load the chat data.', (5,12), (210, 15))
            wx.StaticText(panel, -1, 'Search', (220,12), (35, 15))
        else:
            static = wx.StaticText(panel, -1, u'選択して日付と時刻は、チャットデータをロードする.', (5,12), (210, 15))
            wx.StaticText(panel, -1, u'検索', (220,12), (35, 15))
        self.loadingMsg = wx.StaticText(panel, -1, '', (390,12), (30, 15))
        self.searchbox = wx.TextCtrl(panel, -1, pos=(260, 9), size=(120, 19), style=wx.TE_PROCESS_ENTER)
        self.searchbox.Bind(wx.EVT_TEXT_ENTER, self.DoSearch)
        self.datelist = wx.ListBox(panel, -1, pos=(0, 40), size=(140, 300))
        self.Bind(wx.EVT_LISTBOX, self.OnDateSelected, self.datelist)
        self.logWindow = wx.richtext.RichTextCtrl(panel, -1, pos=(132,40), size=(250, 300), style=wx.TE_READONLY | wx.EXPAND | wx.TE_MULTILINE)
        self.logWindow.Bind(wx.EVT_RIGHT_DOWN, self.CustomMenu)
        self.logWindow.SetBackgroundColour((243, 246, 237))
        self.LoadDates()
        self.Bind(wx.EVT_SIZE, self.OnSize)

    def CustomMenu(self, event):
        pos = (event.GetPosition()[0]+self.logWindow.GetPosition()[0], event.GetPosition()[1]+self.logWindow.GetPosition()[1])
        self.PopupMenu(LogWindowContext(self), pos, self.language)

    def DoSearch(self, event):
        if self.language == 'en':
            self.loadingMsg.SetLabel("Searching...")
        else:
            self.loadingMsg.SetLabel(u"検索...")
        self.logWindow.Clear()
        self.datelist.SetSelection(-1)
        searchval = self.searchbox.GetValue().lower()
        idx = 0.0
        ttllen = self.datelist.GetCount()
        for index in ReverseIterator(range(ttllen - 1)):
            idx = idx + 1
            if self.language == 'en':
                self.loadingMsg.SetLabel("Searching... %i%%" % ((idx / ttllen) * 100.0))
            else:
                self.loadingMsg.SetLabel(u"検索... %i%%" % ((idx / ttllen) * 100.0))
            app.Yield()
            filename = os.path.join('chatlogs', self.datelist.GetString(index + 1) + '.chat')
            filesize = os.path.getsize(filename)
            with open(filename, 'rb') as f:
                chatdata = pickle.load(f)
                for chatitem in chatdata:
                    if (chatitem[1].lower().find(searchval) > -1) or (chatitem[2].lower().find(searchval) > -1):
                        self.WriteDataToDisplay(chatitem, singlevalue=True)
        self.loadingMsg.SetLabel("")

    def WriteDataToDisplay(self, chatdata, singlevalue=False):
        self.logWindow.BeginSuppressUndo()
        if singlevalue:
            try:
                try:
                    self.chat_types[chatdata[0]](chatdata[1], chatdata[2])
                    self.logWindow.ShowPosition(self.logWindow.GetLastPosition())
                except KeyError as e:
                    self.WriteSay(chatdata[1], chatdata[2])
            except:
                pass        
        else:
            for chatitem in chatdata:
                try:
                    try:
                        self.chat_types[chatitem[0]](chatitem[1], chatitem[2])
                        self.logWindow.ShowPosition(self.logWindow.GetLastPosition())
                    except KeyError as e:
                        self.WriteSay(chatitem[1], chatitem[2])
                except:
                    pass
        self.logWindow.EndSuppressUndo()

    def RefreshDisplay(self):
        #self.LoadDates()
        #self.DoDateLoad(self.datelist.GetString(self.datelist.GetSelection()))
        pass

    def OnDateSelected(self, event):
        self.DoDateLoad(event.GetString())
        
    def DoDateLoad(self, datestring):
        global app
        if self.language == 'en':
            self.loadingMsg.SetLabel("Loading...")
        else:
            self.loadingMsg.SetLabel(u"ロード...")
        self.logWindow.Clear()
        #self.logWindow.Freeze()

        if datestring != "-- Last 20 Logs --" and datestring != u'-- 20最後にログ --':
            filename = os.path.join('chatlogs', datestring + '.chat')
            filesize = os.path.getsize(filename)
            with open(filename, 'rb') as f:
                chatdata = pickle.load(f)
                self.WriteDataToDisplay(chatdata)
        else:
            idx = 0.0
            ttllen = self.datelist.GetCount()
            if ttllen > 20:
                ttllen = 20
            for index in ReverseIterator(range(ttllen - 1)):
                idx = idx + 1
                if self.language == 'en':
                    self.loadingMsg.SetLabel("Loading... %i%%" % ((idx / ttllen) * 100.0))
                else:
                    self.loadingMsg.SetLabel(u"ロード... %i%%" % ((idx / ttllen) * 100.0))
                app.Yield()
                filename = os.path.join('chatlogs', self.datelist.GetString(index + 1) + '.chat')
                filesize = os.path.getsize(filename)
                with open(filename, 'rb') as f:
                    chatdata = pickle.load(f)
                    self.WriteDataToDisplay(chatdata)

        #self.logWindow.Thaw()
        self.loadingMsg.SetLabel("")
        
    def OnSize(self, event):
        event.Skip()        
        size = event.GetSize()
        self.logWindow.SetSize((size[0] - 150, size[1] - 102))
        self.datelist.SetSize((130, size[1] - 102))
        
    def LoadDates(self):
        # This loads all date files into the listbox.
        chatdates = [(os.stat(i).st_mtime, i) for i in glob.glob(os.path.join('chatlogs', '*.chat'))]
        chatdates.sort(reverse=True)
        if len(self.currdates) == 0:
            if self.language == 'en':
                self.datelist.Append("-- Last 20 Logs --")
            else:
                self.datelist.Append(u"-- 20最後にログ --")
            for date in chatdates:
                filename = os.path.basename(os.path.splitext(date[1])[0])
                self.currdates.append(filename)
                self.datelist.Append(filename)
        else:
            diff = set(chatdates).difference( set(self.currdates) )
            for date in diff:
                filename = os.path.basename(os.path.splitext(date[1])[0])
                self.currdates.append(filename)
                self.datelist.Append(filename)


    def WriteEmote(self, charname, text):
        self.logWindow.BeginTextColour((80, 50, 50))
        self.logWindow.WriteText("%s\r" % (text))
        self.logWindow.EndTextColour()

    def WriteParty(self, charname, text):
        self.logWindow.BeginTextColour((70, 70, 170))
        self.logWindow.WriteText("<%s> %s\r" % (charname, text))
        self.logWindow.EndTextColour()

    def WriteTell(self, charname, text):
        self.logWindow.BeginTextColour((190, 70, 70))
        if self.language == 'en':
            self.logWindow.WriteText("%s whispers %s\r" % (charname, text))
        else:
            self.logWindow.WriteText(u"%s >> %s\r" % (charname, text))
        self.logWindow.EndTextColour()

    def WriteShout(self, charname, text):
        self.logWindow.BeginTextColour((140, 50, 50))
        if self.language == 'en':
            self.logWindow.WriteText("%s shouts %s\r" % (charname, text))
        else:
            self.logWindow.WriteText(u"%s コメント %s\r" % (charname, text))
        self.logWindow.EndTextColour()
        
    def WriteLinkshell(self, charname, text):
        self.logWindow.BeginTextColour((50, 140, 50))
        self.logWindow.BeginBold()
        self.logWindow.WriteText("<" + charname + "> ")
        self.logWindow.EndBold()
        self.logWindow.WriteText(text + "\r")
        self.logWindow.EndTextColour()

    def WriteSay(self, charname, text):
        if self.language == 'en':
            self.logWindow.WriteText("%s says %s\r" % (charname, text))
        else:
            self.logWindow.WriteText(u"%s 言う %s\r" % (charname, text))
        

    def OnClose(self, e):
        self.Destroy();

class MainFrame(wx.Frame):
    def SaveLanguageSetting(self, lang):
        global configfile, currentlanguage
        config = ConfigParser.ConfigParser()
        try:
            config.add_section('Config')
        except ConfigParser.DuplicateSectionError:
            pass
        config.read(configfile)
        self.language = lang
        currentlanguage = lang

        config.set('Config', 'language', lang)
        with open(configfile, 'wb') as openconfigfile:
            config.write(openconfigfile)

    def SetEnglish(self, event):
        self.SetTitle("FFXIV Log Parser")
        self.filemenu.SetLabel(1, "&Start")
        self.filemenu.SetHelpString(1, " Start Processing Logs")
        #self.filemenu.SetLabel(4, "&Parse All Logs")
        #self.filemenu.SetHelpString(4, " Start Processing All Logs")
        self.filemenu.SetLabel(wx.ID_ABOUT, "&About")
        self.filemenu.SetHelpString(wx.ID_ABOUT, " Information about this program")
        self.filemenu.SetLabel(2, "&Check for New Version")
        self.filemenu.SetHelpString(2, " Check for an update to the program")
        self.filemenu.SetLabel(wx.ID_EXIT, "E&xit")
        self.filemenu.SetHelpString(wx.ID_EXIT, " Terminate the program")
        self.chatmenu.SetLabel(13, 'Chat &Viewer')
        self.chatmenu.SetHelpString(13, "Opens the chat viewer window.")

        self.menuBar.SetLabelTop(0, "&File")
        self.menuBar.SetLabelTop(1, "&Language")
        self.menuBar.SetLabelTop(2, "&Chat")
        self.st.SetLabel("Select Log Path")
        self.st2.SetLabel("Enter Your Character Name (default is unique id to hide your name)")
        if self.btnCharChange:
            self.btnCharChange.SetLabel("Change")
        self.btnStart.SetLabel("Start")
        self.lblLogWindow.SetLabel("Activity Log")
        self.charlink.SetLabel("test")
        self.charlink.SetLabel("FFXIVBattle.com Character Page")
        self.charlink.SetURL("http://ffxivbattle.com/character.php?charactername=%s&lang=en" % (self.charname.GetValue()))
        self.SaveLanguageSetting('en')

    def SetJapanese(self, event):
        self.SetTitle(u"FFXIVのログパーサー")
        self.filemenu.SetLabel(1, u"開始")
        self.filemenu.SetHelpString(1, u"スタート処理のログ")
        #self.filemenu.SetLabel(4, u"再解析のログ")
        #self.filemenu.SetHelpString(4, u" 再解析のログ")
        self.filemenu.SetLabel(wx.ID_ABOUT, u"について")
        self.filemenu.SetHelpString(wx.ID_ABOUT, u"このプログラムについての情報")
        self.filemenu.SetLabel(2, u"新しいバージョンの確認")
        self.filemenu.SetHelpString(2, u"プログラムの更新をチェックする")
        self.filemenu.SetLabel(wx.ID_EXIT, u"終了")
        self.filemenu.SetHelpString(wx.ID_EXIT, u"終了プログラム")
        self.chatmenu.SetLabel(13, u'チャットビューア')
        self.chatmenu.SetHelpString(13, u"が表示されますビューアチャットウィンドウ。")

        self.menuBar.SetLabelTop(0, u"ファイル")
        self.menuBar.SetLabelTop(1, u"言語")
        self.menuBar.SetLabelTop(2, u"チャット")
        self.st.SetLabel(u"選択してログのパス")
        self.st2.SetLabel(u"文字型の名前 （デフォルトでは、名前を非表示にする一意のIDです）")
        if self.btnCharChange:
            self.btnCharChange.SetLabel(u"変更")
        self.btnStart.SetLabel(u"開始")
        self.lblLogWindow.SetLabel(u"アクティビティログ")
        self.charlink.SetLabel(u"FFXIVBattle.com文字ページ")
        self.charlink.SetURL("http://ffxivbattle.com/character.php?charactername=%s&lang=jp" % (self.charname.GetValue()))
        self.SaveLanguageSetting('jp')

    def OpenChatViewer(self, event):
        self.chatviewer = ChatViewer(self.language)
        self.chatviewer.Show()
        
    def __init__(self, parent, title):
        global configfile, autotranslatearray, currentlanguage
        wx.Frame.__init__(self, parent, title=title, size=(400,314))
        try:
            self.SetIcon(wx.Icon("icon.ico", wx.BITMAP_TYPE_ICO))
        except Exception as e:
            print e
        self.Bind(wx.EVT_CLOSE, self.OnClose)
        self.sb = self.CreateStatusBar() # A Statusbar in the bottom of the window
        self.salt = None
        # Setting up the menu.
        self.filemenu= wx.Menu()

        # wx.ID_ABOUT and wx.ID_EXIT are standard IDs provided by wxWidgets.
        self.filemenu.Append(1, "&Start"," Start Processing Logs")
        #self.filemenu.Append(4, "&Parse All Logs"," Start Processing All Logs")
        self.filemenu.Append(wx.ID_ABOUT, "&About"," Information about this program")
        self.filemenu.AppendSeparator()
        self.filemenu.Append(2, "&Check for New Version"," Check for an update to the program")
        self.filemenu.AppendSeparator()
        self.filemenu.Append(wx.ID_EXIT,"E&xit"," Terminate the program")
        self.Bind(wx.EVT_MENU, self.OnStartCollectingAll, id=1)
        #self.Bind(wx.EVT_MENU, self.OnStartCollectingAll, id=4)
        self.Bind(wx.EVT_MENU, self.OnCheckVersion, id=2)
        self.Bind(wx.EVT_MENU, self.OnExit, id=wx.ID_EXIT)
        self.Bind(wx.EVT_MENU, self.OnAbout, id=wx.ID_ABOUT)#menuItem)

        # Setup language menu
        self.languagemenu= wx.Menu()
        self.englishMenu = self.languagemenu.Append(11, "&English","Set application to english display", kind=wx.ITEM_RADIO)
        self.japaneseMenu = self.languagemenu.Append(12, u"日本語", u"日本語表示", kind=wx.ITEM_RADIO)
        self.Bind(wx.EVT_MENU, self.SetEnglish, id=11)
        self.Bind(wx.EVT_MENU, self.SetJapanese, id=12)

        # Setup chat menu
        self.chatmenu= wx.Menu()
        self.chatviewerMenu = self.chatmenu.Append(13, "Chat &Viewer","Opens the chat viewer window")
        self.Bind(wx.EVT_MENU, self.OpenChatViewer, id=13)

        # Creating the menubar.
        self.menuBar = wx.MenuBar()
        self.menuBar.Append(self.filemenu,"&File") # Adding the "filemenu" to the MenuBar
        self.menuBar.Append(self.languagemenu,"&Language") # Adding the "filemenu" to the MenuBar
        self.menuBar.Append(self.chatmenu,"&Chat") # Adding the "filemenu" to the MenuBar
        self.SetMenuBar(self.menuBar)  # Adding the MenuBar to the Frame content.

        panel = wx.Panel(self, -1)
        logpath = ""
        charactername = hex(uuid.getnode())
        charinconfig = False
        # read defaults
        config = ConfigParser.ConfigParser()
        try:
            config.read(configfile)
            logpath = config.get('Config', 'logpath')
            charactername = config.get('Config', 'charactername')
            charinconfig = True
        except:
            logpath = ""
            pass
        if logpath == "":
            userdir = os.path.expanduser('~')
            logpath = os.path.join(userdir, "Documents\\My Games\\FINAL FANTASY XIV\\user\\") 
            userdirs = os.listdir(logpath)
            newestdate = None
            try:
                for dir in userdirs:
                    l = [(os.stat(i).st_mtime, i) for i in glob.glob(os.path.join(logpath, dir, 'log', '*.log'))]
                    l.sort()
                    if len(l) > 0:
                        if newestdate != None:
                            if l[0][0] > newestdate:
                                newestdate = l[0][0];
                                logpath = os.path.join(logpath, dir, 'log')
                        else:
                            newestdate = l[0][0];
                            logpath = os.path.join(logpath, dir, 'log')
            except:
                logpath = os.path.join(userdir, "Documents\\My Games\\FINAL FANTASY XIV\\user\\")
        self.st = wx.StaticText(panel, -1, 'Select Log Path', (5,3))
        self.control = wx.TextCtrl(panel, -1, logpath, (5,21), (345, 22))
        self.btnDialog = wx.Button(panel, 102, "...", (350,20), (28, 24))
        self.Bind(wx.EVT_BUTTON, self.OnLogSelect, id=102)
        if charinconfig:
            self.st2 = wx.StaticText(panel, -1, 'Enter Your Character Name (default is unique id to hide your name)', (5,53))
            self.charname = wx.TextCtrl(panel, -1, charactername, (5,70), (310, 22))
            self.charname.Disable()
            self.btnCharChange = wx.Button(panel, 150, "Change", (320,69), (55, 24))
            self.Bind(wx.EVT_BUTTON, self.OnChangeCharacter, id=150)
        else:
            self.btnCharChange = None
            self.st2 = wx.StaticText(panel, -1, 'Enter Your Character Name (default is unique id to hide your name)', (5,53))
            self.charname = wx.TextCtrl(panel, -1, charactername, (5,70), (370, 22))
            
        self.btnStart = wx.Button(panel, 103, "Start", (150,100))
        self.Bind(wx.EVT_BUTTON, self.OnStartCollecting, id=103)

        self.Bind(wx.EVT_SIZE, self.OnSize)
        
        self.lblLogWindow = wx.StaticText( panel, -1, "Activity Log", (5,120))
        self.logWindow = wx.TextCtrl(panel, -1, "", (5,136), (370, 80), style=wx.TE_MULTILINE)
        self.logLayout = wx.BoxSizer( wx.HORIZONTAL )
        self.logLayout.Add( self.lblLogWindow, 0, wx.EXPAND )
        self.logLayout.Add( self.logWindow, 1, wx.EXPAND | wx.BOTTOM | wx.RIGHT )

        redir=RedirectText(self.logWindow)
        self.charlink = hl.HyperLinkCtrl(panel, -1, "FFXIVBattle.com Character Page", (5,216), (22, 80))
        self.charlink.SetURL("http://ffxivbattle.com/character.php?charactername=" + charactername)
        self.language = 'en'
        try:
            configlang = config.get('Config', 'language')
            if configlang == 'jp':
                self.languagemenu.Check(12, True)
                self.SetJapanese(None)
                self.language = 'jp'
                currentlanguage = 'jp'
        except:
            pass

        sys.stdout=redir
        self.Show(True)
        '''
        if os.path.exists('autotranslate.gz'):
            print "Opening autotranslate file..."
            f = gzip.open('autotranslate.gz', 'rb')
            autotranslatearray = json.loads(f.read())
            f.close()
            print "Autotranslate loaded."        
        '''

    def OnChangeCharacter(self, event):
        global configfile
        if self.language == 'en':
            changecharnamedlg = ChangeCharacterNameDialog(self, -1, "Enter New Character Name", self.language)
        else:
            changecharnamedlg = ChangeCharacterNameDialog(self, -1, u"新キャラクター名を入力してください", self.language)
            
        if changecharnamedlg.ShowModal() == wx.ID_OK:
            if not self.salt:
                # extract salt from the dir
                dirparts = self.control.GetValue().split("\\")
                # set the salt to the users directory name for the character.  Not 100% but good enough to salt with.
                self.salt = ""
                if dirparts[len(dirparts)-1] == "":
                    self.salt = dirparts[len(dirparts) - 3]
                else:
                    self.salt = dirparts[len(dirparts) - 2]
            hash = hashlib.md5( self.salt + changecharnamedlg.GetPassword() ).hexdigest()
            results = self.ChangeCharacterName(self.charname.GetValue(), changecharnamedlg.GetNewCharacterName(), hash)
            if results:
                if results["code"] < 0:
                    if self.language == 'en':
                        dlg = wx.MessageDialog( self, results["text"], "Error Changing Character Name", wx.OK)
                    else:
                        dlg = wx.MessageDialog( self, results["text"], u"文字の名前の変更中にエラー", wx.OK)
                    dlg.ShowModal() # Show it
                    dlg.Destroy() # finally destroy it when finished.
                else:
                    self.charname.SetValue(changecharnamedlg.GetNewCharacterName())
                    config = ConfigParser.ConfigParser()
                    try:
                        config.add_section('Config')
                    except ConfigParser.DuplicateSectionError:
                        pass
                    config.read(configfile)

                    config.set('Config', 'charactername', self.charname.GetValue())
                    with open(configfile, 'wb') as openconfigfile:
                        config.write(openconfigfile)


                    if self.language == 'en':
                        dlg = wx.MessageDialog( self, results["text"], "Success", wx.OK)
                    else:
                        dlg = wx.MessageDialog( self, results["text"], u"成功", wx.OK)                        
                    dlg.ShowModal() # Show it
                    dlg.Destroy() # finally destroy it when finished.
            else:
                    if self.language == 'en':
                        dlg = wx.MessageDialog( self, "Did not understand server response.", "Try Again Later", wx.OK)
                    else:
                        dlg = wx.MessageDialog( self, u"サーバの応答を解釈しませんでした。", u"てみてください後でもう一度", wx.OK)
                    dlg.ShowModal() # Show it
                    dlg.Destroy() # finally destroy it when finished.
        else:
            if self.language == 'en':
                print "Character name change cancelled."
            else:
                print u"キャラクター名の変更がキャンセルされました。"

    def ChangeCharacterName(self, charactername, newcharactername, hashed_password):
        # call out to verify the password
        response = None
        try:
            encodedname = urllib.urlencode({"oldcharname": charactername.encode("utf-8")})
            newencodedname = urllib.urlencode({"newcharname": newcharactername.encode("utf-8")})
            response = urllib2.urlopen('http://ffxivbattle.com/updatecharactername.php?%s&%s&password=%s' % (encodedname, newencodedname, hashed_password))
            responsetext = response.read()
            #print responsetext
            return json.loads(responsetext)
        except Exception as e:
            # The result was garbage so skip it.
            print type(e)
            print e
            print "Did not understand the response from the server for the character name change."
            return False

    def OnSize(self, event):
        event.Skip()        
        size = event.GetSize()
        self.logWindow.SetSize((size[0] - 30, size[1] - 240))
        self.charlink.SetPosition((5, size[1] - 100))

    def CheckPassword(self, charactername, salt, hashed_password):
        # call out to verify the password
        response = None
        try:
            encodedname = urllib.urlencode({"charactername": charactername.encode("utf-8")})
            response = urllib2.urlopen('http://ffxivbattle.com/passwordcheck.php?%s&salt=%s&password=%s' % (encodedname, salt, hashed_password))
            return json.loads(response.read())["result"] == True
        except Exception, e:
            # The result was garbage so skip it.
            print e
            print "Did not understand the response from the server for the password check."
            return False
        
    def GetPassword(self, config, salt):
        pass_stored = ""
        try:
            if self.language == 'en':
                passwordentry = PasswordDialog(self, -1, "Enter password", pass_stored, self.language)
            else:
                passwordentry = PasswordDialog(self, -1, u"パスワードを入力してください", pass_stored, self.language)
            try:
                pass_stored = config.get('Config', 'password')
                passwordentry.SetChecked(True)
                passwordentry.SetValue(pass_stored)
            except ConfigParser.NoOptionError:
                pass
            if passwordentry.ShowModal() == wx.ID_OK:
                if pass_stored != "":
                    if pass_stored != passwordentry.GetValue():
                        password = passwordentry.GetValue()
                        if password != "":
                            hash = hashlib.md5( salt + password ).hexdigest()
                            return hash, passwordentry.GetChecked()                        
                    else:
                        return pass_stored, passwordentry.GetChecked()
                else:
                    password = passwordentry.GetValue()
                    if password != "":
                        hash = hashlib.md5( salt + password ).hexdigest()
                        return hash, passwordentry.GetChecked()                        
                    else:
                        return "", False
            else:
                return "", passwordentry.GetChecked()
        finally:
            passwordentry.Destroy()
        
    def OnIdle( self, evt ):
        if self.process is not None:
            stream = self.process.GetInputStream()
            if stream.CanRead():
                text = stream.read()
                self.logWindow.AppendText( text ) 

    def OnLogSelect(self, e):
        if self.japaneseMenu.IsChecked():
            dlg = wx.DirDialog(self, u"ログディレクトリを選択してください：", self.control.GetValue(), style=wx.DD_DEFAULT_STYLE | wx.DD_NEW_DIR_BUTTON)
        else:
            dlg = wx.DirDialog(self, "Choose the Log Directory:", self.control.GetValue(), style=wx.DD_DEFAULT_STYLE | wx.DD_NEW_DIR_BUTTON)
        if dlg.ShowModal() == wx.ID_OK:
            self.control.SetValue(dlg.GetPath())
        dlg.Destroy()

    def OnAbout(self,e):
        global version
        
        license = '''Copyright (C) 2010-2011 FFXIVBattle.com All rights reserved.
Permission is hereby granted, free of charge, to any person obtaining a copy of this software and associated documentation files (the "Log Parser"), to deal in the Software without restriction, including without limitation the rights to use, copy, modify, merge, publish, distribute, sublicense, and/or sell copies of the Software, and to permit persons to whom the Software is furnished to do so, subject to the following conditions:

1. Redistributions of source code must retain the above copyright notice, this list of conditions, and the following disclaimer.

2. Redistributions in binary form must reproduce the above copyright notice, this list of conditions and the following disclaimer in the documentation and/or other materials provided with the distribution, and in the same place and form as other copyright, license and disclaimer information.

3. The end-user documentation included with the redistribution, if any, must include the following acknowledgment: "This product includes software developed by FFXIVBattle.com (http://www.ffxivbattle.com/) and its contributors", in the same place and form as other third-party acknowledgments. Alternately, this acknowledgment may appear in the software itself, in the same form and location as other such third-party acknowledgments.

4. Except as contained in this notice, the name of FFXIVBattle.com shall not be used in advertising or otherwise to promote the sale, use or other dealings in this Software without prior written authorization from FFXIVBattle.com.

THIS SOFTWARE IS PROVIDED ``AS IS'' AND ANY EXPRESSED OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE ARE DISCLAIMED. IN NO EVENT SHALL FFXIVBATTLE.COM OR ITS CONTRIBUTORS BE LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE OF THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.
                        '''
        info = wx.AboutDialogInfo()
        info.SetName('FFXIV Log Parser')
        info.SetVersion(str(version))
        if self.japaneseMenu.IsChecked():
            info.SetDescription(u"ファイナルファンタジーXIVのログパーサー。")
            info.AddTranslator(u'H3lls (ffxivbattle@gmail.com) ご了承ください、私は翻訳の間違いをしたなら、私に知らせてください。')
        else:
            info.SetDescription("A log parser for Final Fantasy XIV.")
            info.AddTranslator('H3lls (ffxivbattle@gmail.com) PLEASE let me know if I have made any mistakes in translation.')
        info.SetIcon(wx.Icon('icon.ico',wx.BITMAP_TYPE_ICO))
        info.SetCopyright('(C) 2011 ffxivbattle.com')
        info.SetWebSite('http://www.ffxivbattle.com')
        info.SetLicence(license)
        info.AddDeveloper('H3lls (ffxivbattle@gmail.com)')

        wx.AboutBox(info)

    def OnCheckVersion(self, e):
        if self.japaneseMenu.IsChecked():
            lang = "JP"
        else:
            lang = "EN"
        if versioncheck(status=1, language=lang):
            Popen("setup.exe", shell=False) # start reloader
            self.OnExit(None)
            return

    def OnStartCollectingAll(self, e):
        global lastlogparsed
        lastlogparsed = 0
        self.OnStartCollecting(e)
        
    def OnStartCollecting(self, e):
        global guithread, configfile
        self.filemenu.Enable(1, False)
        #self.filemenu.Enable(4, False)
        self.btnStart.Disable()
        #try:
        config = ConfigParser.ConfigParser()
        try:
            config.add_section('Config')
        except ConfigParser.DuplicateSectionError:
            pass
        config.read(configfile)

        # extract salt from the dir
        dirparts = self.control.GetValue().split("\\")
        # set the salt to the users directory name for the character.  Not 100% but good enough to salt with.
        self.salt = ""
        if dirparts[len(dirparts)-1] == "":
            self.salt = dirparts[len(dirparts) - 3]
        else:
            self.salt = dirparts[len(dirparts) - 2]
        password, savepass = self.GetPassword(config, self.salt)
        if self.CheckPassword(self.charname.GetValue(), self.salt, password):
            if savepass:
                config.set('Config', 'password', password)
            else:
                try:
                    config.remove_option('Config', 'password')
                except ConfigParser.NoSectionError:
                    pass
        else:
            if self.language == 'en':
                dlg = wx.MessageDialog( self, "The password provided does not match.", "Invalid Password", wx.OK)
            else:
                dlg = wx.MessageDialog( self, u"提供されたパスワードが一致しません。", u"無効なパスワード", wx.OK)
            dlg.ShowModal() # Show it
            dlg.Destroy() # finally destroy it when finished.
            self.filemenu.Enable(1, True)
            #self.filemenu.Enable(4, True)
            self.btnStart.Enable()
            return
                
        config.set('Config', 'logpath', self.control.GetValue())
        config.set('Config', 'charactername', self.charname.GetValue())
        with open(configfile, 'wb') as openconfigfile:
            config.write(openconfigfile)
        #except (Exception, e):
        #    print e
        try:
            self.charlink.SetURL("http://ffxivbattle.com/character.php?charactername=" + self.charname.GetValue())
            guithread.updatevalues(self.control.GetValue(), self.charname.GetValue(), self.OnStatus, completecallback=self.threadcallback, password=password)
            guithread.daemon = False
            guithread.start()
        except:
            pass

    def threadcallback(self):
        if self:
            if self.filemenu:
                self.filemenu.Enable(1, True)
            if self.btnStart:
                self.btnStart.Enable()
        
    def OnClose(self, e):
        self.Destroy();

    def OnExit(self,e):
        self.Close(True)  # Close the frame.

    def OnStatus(self, message):
        try:
            self.sb.PushStatusText(message, 0)
        except:
            pass

class RedirectText(object):
    def __init__(self,aWxTextCtrl):
        self.out=aWxTextCtrl

    def write(self,string):
        try:
            self.out.AppendText(string)
        except:
            pass

class GUIThread(Thread):
    def __init__(self, logpath, charactername, status): 
        self.stopped = 1
        self.logpath = logpath
        self.charactername = charactername
        self.status = status
        self.exitready = 0
        Thread.__init__(self) 

    def updatevalues(self, logpath, charactername, status, completecallback=None, password=""):
        self.stopped = 0
        self.logpath = logpath
        self.charactername = charactername
        self.status = status
        self.completecallback = completecallback
        self.password = password
        
    def exit(self):
        self.stopped = 1

    def exitcomplete(self):
        return self.exitready

    def is_running(self):
        if self.stopped:
            return 0
        else:
            return 1

    def run(self):
        try:
            en_parser = english_parser()
            jp_parser = japanese_parser()
            en_parser.characterdata["charactername"] = self.charactername
            jp_parser.characterdata["charactername"] = self.charactername
            parsers = [en_parser, jp_parser]
            self.exitready = 0
            self.stopped = 0
            prev = []
            while not self.stopped:
                l = [(os.stat(i).st_mtime, i) for i in glob.glob(os.path.join(self.logpath, '*.log'))]
                l.sort()
                diff = set(l).difference( set(prev) )
                if len(diff) > 0:
                    self.status("Found " + str(len(l)) + " new logs.")
                    prev = l
                    if len(diff) == len(l):
                        files = [i[1] for i in l]
                    else:
                        files = [i[1] for i in l[len(l)-len(diff):]]
                    readLogFile(files, self.charactername, isrunning=self.is_running, password=self.password, parsers=parsers)
                start = datetime.datetime.now()
                self.status("Waiting for new log data...")
                while (datetime.datetime.now() - start).seconds < 5:
                    time.sleep(1)
                    if self.stopped:
                        return
        finally:
            self.exitready = 1
            self.stopped = 1
            if self.completecallback:
                self.completecallback()

def main():
    #try:    
        global doloop, guithread, configfile, lastlogparsed, app, autotranslatearray
        args = sys.argv[1:]

        config = ConfigParser.ConfigParser()
        try:
            config.read(configfile)
            lastlogparsed = float(config.get('Config', 'lastlogparsed'))
        except:
            pass

        if len(args) < 1:
            try:
                guithread = GUIThread(None, None, None) 
                doloop = 1
                app = wx.App()
                configlang = 'en'
                try:
                    configlang = config.get('Config', 'language')
                except:
                    pass
                if versioncheck(language=configlang):
                    Popen("setup.exe", shell=False) # start reloader
                    return
                frame = MainFrame(None, "FFXIV Log Parser")
                if os.path.exists('autotranslate.gz'):
                    print "Opening autotranslate file..."
                    app.Yield()
                    f = gzip.open('autotranslate.gz', 'rb')
                    autotranslatearray = json.loads(f.read())
                    f.close()
                    print "Autotranslate loaded."        
                app.MainLoop()
                
                try:
                    if guithread:
                        guithread.exit()
                except (AttributeError):
                    pass
                alivecount = 0
                while 1:
                    if guithread:
                        if guithread.isAlive():
                            time.sleep(1)
                            alivecount == alivecount + 1
                            if alivecount > 20:
                                # Exit anyways the thread is misbehaving
                                break
                        else:
                            break
                    else:
                        break
                return
            except Exception as e:
                print e
                return
        if args[0] == '?' or args[0] == 'h' or args[0] == '/?' or args[0] == '/h' or args[0] == '/help' or args[0] == 'help' or args[0] == '-h' or args[0] == '-help' or args[0] == '--help' or len(args) < 4:
            print "\r\nUsage: CharacterName password PathToLogFiles RunForever[True/False] FilterByMonster[optional]"
            print "Example: python logparse.py mychar mypass \"c:\\Users\\<youruser>\\Documents\\My Games\\Final Fantasy XIV\\user\\<yourcharid>\\log\\\" true\r\n"
            print "Examples of FilterByMonster:\n\"ice elemental\"\n\"fat dodo\"\n\"warf rat\"\n"
            return
        
        # assign args to nice names
        charactername = args[0]
        password = args[1]
        logpath = args[2]
        logmonsterfilter = None
        if args[3].lower() == "true":
            doloop = 1
        if len(args) > 4:
            logmonsterfilter = args[4]
        prev = []
        
        en_parser = english_parser()
        jp_parser = japanese_parser()
        en_parser.characterdata["charactername"] = charactername
        jp_parser.characterdata["charactername"] = charactername
        parsers = [en_parser, jp_parser]
        while 1==1:
            l = [(os.stat(i).st_mtime, i) for i in glob.glob(os.path.join(logpath, '*.log'))]
            l.sort()
            diff = set(l).difference( set(prev) )
            if len(diff) > 0:
                prev = l            
                files = [i[1] for i in sorted(diff)]
                try:
                    readLogFile(files, charactername, password=password, logmonsterfilter=logmonsterfilter, parsers=parsers)
                except:
                    traceback.print_exc()
                    
            if not doloop:
                break
            time.sleep(60)
    #except ConfigParser.NoSectionError, e:
    #    print "Program Exception:"
    #    print e
"""
20 = "ready (inswert combat skill)..." as well as loot obtain
42= all SP and EXP gain notices by you 
45= monster defeated message or you defeated
-46 = crafting success / failure
50=all my attacks that land 
51= all auto-attacks that mobs land on me, even crits / side attacks 
-52= Hits from left by party member
-53= mob hits some party member
54 = monster readying special ability 
55= all friendly AND hostile attacks on/by npc's near me 
56 = all my misses Vs monsters as well as their evades vs me 
57= all misses vs me 
-58= Party member misses
-59= party member evades mob attack
005c= so far it shows everytime i drain health with lancer speed surge 
-5E= used cure someone else on someone else

61= players other than me casting heals on themselves/PC's  as well as HP absorb messages 
67 = appears to be buffs/debuffs on players that have just been removed 
69= status effects just being inflicted upon me via monsters 
-6C= mob no longer stunned
6D = status affects being inflicted on monsters near you AND players 
"""

def HexToByte( hexStr ):
    bytes = []
  
    hexStr = ''.join( hexStr.split(" ") )
  
    for i in range(0, len(hexStr), 2):
        bytes.append( chr( int (hexStr[i:i+2], 16 ) ) )
  
    return unicode(''.join( bytes), 'utf-8', errors='ignore')

  
def ByteToHex( byteStr ):
    return ''.join( [ "%02X " % ord( x ) for x in byteStr ] ).strip()

'''
defaultmonster = {"datetime":"", "monster":"", "monstermiss":0, "othermonstermiss":0, "damage":[], "miss":0, "hitdamage":[], "otherdamage":[], "othermiss":[], "otherhitdamage":[], "skillpoints":0, "class":"", "exp":0}
defaultcrafting = {"datetime":"", "item":"", "actions":[], "ingredients":[], "success":0, "skillpoints":0, "class":"", "exp":0}
characterdata = {"charactername":"", "deaths":[]}
monsterdata = []
craftingdata = []
gatheringdata = []
#uploaddata = []
'''

debuglevel = 0
class ffxiv_parser:
    def __init__(self, language): 
        self.language = language
        self.defaultmonster = {"datetime":"", "monster":"", "monstermiss":0, "othermonstermiss":0, "damage":[], "miss":0, "hitdamage":[], "otherdamage":[], "othermiss":[], "spells":[], "healing":[], "otherhealing":[], "otherhitdamage":[], "skillpoints":0, "class":"", "exp":0}
        self.defaultcrafting = {"datetime":"", "item":"", "quantity":0,"actions":[], "ingredients":[], "success":0, "skillpoints":0, "class":"", "exp":0}
        self.characterdata = {"charactername":""}
        self.deathsdata = {"charactername":"", "deaths":[]}
        self.monsterdata = []
        self.craftingdata = []
        self.gatheringdata = []
        self.currentmonster = copy.deepcopy(self.defaultmonster)
        self.currentcrafting = copy.deepcopy(self.defaultcrafting)
        self.exptotal = 0
        self.damagepermob = 0
        self.damageavgpermob = 0
        self.craftingcomplete = 0
        self.synthtype = ""
        self.progress = []
        self.quality = []
        self.durability = []
        self.defeated = False
        self.expset = False
        self.spset = False

        self.function_map = {
            '01': self.parse_chatmessage, # say
            '02': self.parse_chatmessage, # shout
            '03': self.parse_chatmessage, # sending tell
            '04': self.parse_chatmessage, # party
            '05': self.parse_chatmessage, # linkshell
            '06': self.parse_chatmessage, # linkshell
            '07': self.parse_chatmessage, # linkshell
            '08': self.parse_chatmessage, # linkshell
            '09': self.parse_chatmessage, # linkshell
            '0A': self.parse_chatmessage, # linkshell
            '0B': self.parse_chatmessage, # linkshell
            '0C': self.parse_chatmessage, # linkshell
            '0D': self.parse_chatmessage, # get tell
            '0F': self.parse_chatmessage, # linkshell
            '0E': self.parse_chatmessage, # linkshell
            '0F': self.parse_chatmessage, # linkshell
            '10': self.parse_chatmessage, # linkshell
            '11': self.parse_chatmessage, # linkshell
            '12': self.parse_chatmessage, # linkshell
            '13': self.parse_chatmessage, # linkshell
            '14': self.parse_chatmessage, # linkshell
            '15': self.parse_chatmessage, # linkshell
            '19': self.parse_chatmessage, # other emote
            '1B': self.parse_chatmessage, # emote
            '1D': self.parse_servermessage,
            '20': self.parse_genericmessage, 
            '21': self.parse_invalidcommand,
            '23': self.parse_leve,
            '25': self.parse_npcchat, # battlewarden msg
            '26': self.parse_npcchat, # say text
            '27': self.parse_npcchat, # npc linkshell 
            '28': self.parse_invoke, #invoke diety
            '42': self.parse_spexpgain,
            '43': self.parse_spexpgain,
            '44': self.parse_defeated,
            '45': self.parse_defeated,
            '46': self.parse_craftingsuccess,
            '47': self.parse_craftingsuccess,
            '48': self.parse_gathering,
            '49': self.parse_othergathering,
            '50': self.parse_damagedealt,
            '51': self.parse_hitdamage,
            '52': self.parse_otherdamage,
            '53': self.parse_otherhitdamage,
            '54': self.parse_readyability,
            '55': self.parse_otherdamage,
            '56': self.parse_miss,
            '57': self.parse_monstermiss,
            '58': self.parse_othermiss,
            '59': self.parse_othermiss,
            '5A': self.parse_monstermiss,
            '5B': self.parse_othermiss,
            '5C': self.parse_selfcast, #self casting
            '5D': self.parse_otherrecover, # party casting?
            '5E': self.parse_otherrecover, # other casting?
            '5F': self.parse_otherrecover, # recover mp from monster
            '60': self.parse_monstereffect, # monster starts casting
            '61': self.parse_otherrecover,
            '62': self.parse_effect,
            '63': self.parse_othereffect,
            '64': self.parse_partyabilities,
            '65': self.parse_othereffect,
            '66': self.parse_monstereffect,
            '67': self.parse_othereffect,
            '68': self.parse_inflicts,
            '69': self.parse_inflicts,
            '6B': self.parse_inflicts,
            '6A': self.parse_othereffect,
            '6C': self.parse_effect,
            '6D': self.parse_monstereffect # wears off
            }

    def lookup(self, d, groupid, id, lang):
        langlookup = ['ja', 'en', 'de', 'fr']
        for row in d:
            if row['groupid'] == groupid:
                for k in row['values']:
                    if k['id'] == id:
                        return k['translations'][[x for x, y in enumerate(langlookup) if y == lang][0]]

    def GetGroupAndIndex(self, bytes ):
        #bytes = bytearray()
      
        #hexStr = ''.join( hexStr.split(" ") )
      
        #for i in range(0, len(hexStr), 2):
        #    bytes.append( chr( int (hexStr[i:i+2], 16 ) ) )
        indexlen = bytes[2]
        indexval = bytes[3:3+indexlen]
        groupid = indexval[0]
        # get value without group id or terminator 0x03
        
        if (indexlen < 4):
            index = indexval[1:-1]
        elif (indexlen < 5):
            index = indexval[2:-1]
        else:
            index = indexval[2:-1]
            index.reverse()
            
        while len(index) < 4:
            index.append(0x00)
        #print ByteToHex2(index)
        index = struct.unpack_from('i', buffer(index))[0]
        if (indexlen < 4):
            index = index - 1

        # return tuple with groupid and index
        return groupid, index

    def getlanguage(self):
        return self.language

    def setLogFileTime(self, logfiletime):
        self.logfiletime = logfiletime

    def getlogparts(self, logitem):
        code = logitem[0:2]
        if logitem[2:4] == b'::':
            logvalue = logitem[4:]
        else:
            logvalue = logitem[3:]
        return str(code), logvalue #, 'ascii', errors='ignore'), logvalue #.decode('utf-8'), logvalue

    def getlogpartsalt(self, logitem):
        if (logitem.find(':') != -1):
            code = logitem[:logitem.find(':')]
            # trim the first char since it is likely a 0 that was written strangely
            # if its longer than 3 then its likely a crlf on a log border so
            # let it fall out
            # *** NOTE: Since going to the binary read version this should never happen.
            if len(code) > 2:
                code = code[1:]
            logvalue = logitem[logitem.find(':') + 1:]
        else:
            raise ValueError
        return code, logvalue
    
    def contains(self, findterm, text):
        if text.find(findterm) != -1:
            return False
        else:
            return True
            
    def between(self, text, starttext, endtext):
        return text[text.find(starttext) +len(starttext):text.find(endtext)]
    
    def echo(self, text, messagetype=0):
        global debuglevel
        if messagetype < debuglevel:
            try:
                print text#.encode('utf-8')
            except:
                pass

    def parse_line(self, logitem):
        #print ''.join( [ "%02X " % x for x in logitem ] ).strip()
        code, logvalue = self.getlogparts(logitem)
        #print code
        #print self.function_map[code]
        try:
            self.function_map[code](code, logvalue)
            #print logvalue.decode('utf-8')
        except: # Exception as e:
            traceback.print_exc(file=sys.stdout)            
            self.echo("Could not parse code: %s value: %s" % (code, ByteToHex(logvalue.decode('utf-8'))), -1)

class english_parser(ffxiv_parser):
    
    def close(self):
        if len(self.chatlog) == 0:
            return
        if self.prevchatdate != None:
            if not os.path.exists('chatlogs'):
                os.mkdir('chatlogs')
            with open(os.path.join('chatlogs', self.prevchatdate + '.chat'), 'wb') as chatfile:
                pickle.dump(self.chatlog, chatfile)
            self.chatlog = []

    def __init__(self): 
        ffxiv_parser.__init__(self, "en")
        self.prevchatdate = None
        self.chatlog = []
        
        self.craftingcomplete = 0
        self.autotranslateheader = b'\x02\x2E'

    def monsterIsNM(self, monster):
        NMList = ['alux', 'bardi', 'barometz', 'bloodthirsty wolf', 'bomb baron', 'daddy longlegs', 'dodore', 'downy dunstan', 'elder mosshorn', 'escaped goobbue', 'frenzied aurelia', 'gluttonous gertrude', 'great buffalo', 'haughtpox bloatbelly', 'jackanapes', 'mosshorn billygoat', 'mosshorn nannygoat', 'nest commander', 'pyrausta', 'queen bolete', 'scurrying spriggan', 'sirocco', 'slippery sykes', 'uraeus']
        #print "%s %r" % (monster.lower(), monster.lower() in NMList)
        return monster.lower() in NMList
            
    def printCrafting(self, currentcrafting):        
        #print currentcrafting
        self.currentcrafting["datetime"] = time.strftime("%m/%d/%y %H:%M:%S",time.gmtime(self.logfiletime))
        totalprogress = 0
        finalquality = 0
        finaldurability = 0
        for action in currentcrafting["actions"]:
            if len(action[1]) > 0:
                totalprogress = totalprogress + action[1][0]
            if len(action[2]) > 0:
                finaldurability = finaldurability + action[2][0]
            if len(action[3]) > 0:
                finalquality = finalquality + action[3][0]
        itemsused = ""
        if len(currentcrafting["ingredients"]) == 0:
            itemsused = "Local levequests do not use ingredients."
        else:
            inglist = []
            first = True
            for item in currentcrafting["ingredients"]:
                if first:
                    itemsused = str(item[1]) + " x " + item[0]
                    first = False
                else:
                    itemsused = itemsused + ", " + str(item[1]) + " x " + item[0]
        if currentcrafting["success"]:
            print "Completed Recipe for %s as %s\nQuantity: %i\nTotal Progress: %i\nFinal Quality Added: %i\nFinal Durability Lost: %i\nIngredients Used: %s\nExp: %i\nSkill Points: %i\nDate Time: %s GMT\n" % (currentcrafting["item"], currentcrafting["class"], currentcrafting["quantity"], totalprogress, finalquality, finaldurability, itemsused, currentcrafting["exp"], currentcrafting["skillpoints"], currentcrafting["datetime"])
        else:
            print "Failed Recipe as %s\nTotal Progress: %i\nFinal Quality Added: %i\nFinal Durability Lost: %i\nIngredients Used: %s\nExp: %i\nSkill Points: %i\nDate Time: %s GMT\n" % (currentcrafting["class"], totalprogress, finalquality, finaldurability, itemsused, currentcrafting["exp"], currentcrafting["skillpoints"], currentcrafting["datetime"])
        self.craftingdata.append(currentcrafting)
        #raw_input("")
        return

    def printDamage(self, currentmonster):
        #print currentmonster
        if len(currentmonster["damage"]) > 0:
            hitpercent = 100
            critpercent = 0
            criticalavg = 0
            criticalavgcount = 0
            regularavg = 0
            regularavgcount = 0
            criticaldmgavg = 0
            regulardmgavg = 0
            totaldmgavg = 0
            hitdmgavg = 0
            hitdmgavgcount = 0
            crithitdmgavg = 0
            crithitdmgavgcount = 0
            totalhitdmgavg = 0
            othertotaldmg = 0
            healingavg = 0
            healingavgcount = 0
            absorbavg = 0
            absorbavgcount = 0
            totaldamage = 0
            for otherdamage in currentmonster["otherdamage"]:
                if otherdamage[0] == '':
                    continue
                othertotaldmg += int(otherdamage[0])
            for hitdamage in currentmonster["hitdamage"]:
                if hitdamage[0] == '':
                    continue
                if hitdamage[1] == True:
                    crithitdmgavg = crithitdmgavg + int(hitdamage[0])
                    crithitdmgavgcount = crithitdmgavgcount + 1
                else:
                    hitdmgavg = hitdmgavg + int(hitdamage[0])
                    hitdmgavgcount = hitdmgavgcount + 1

            for healing in currentmonster["healing"]:
                if healing[1] == 'heal':
                    healingavg = healingavg + int(healing[2])
                    healingavgcount = healingavgcount + 1
                if healing[1] == 'absorb':
                    absorbavg = absorbavg + int(healing[2])
                    absorbavgcount = absorbavgcount + 1

            for damage in currentmonster["damage"]:
                if damage[0] == '':
                    continue
                totaldamage = totaldamage + int(damage[0])
                if damage[1] == True:
                    criticalavg = criticalavg + int(damage[0])
                    criticalavgcount = criticalavgcount + 1
                else:
                    regularavg = regularavg + int(damage[0])
                    regularavgcount = regularavgcount + 1
            if crithitdmgavg != 0:
                crithitdmgavg = crithitdmgavg / crithitdmgavgcount
            if criticalavgcount > 0:
                critpercent = int((float(criticalavgcount) / float(len(currentmonster["damage"]))) * 100)
            if hitdmgavg != 0:
                hitdmgavg = hitdmgavg / hitdmgavgcount
            if crithitdmgavg + hitdmgavg != 0:
                totalhitdmgavg = (crithitdmgavg + hitdmgavg) / (crithitdmgavgcount + hitdmgavgcount)
            if criticalavg != 0:
                criticaldmgavg = criticalavg / criticalavgcount
            if regularavg != 0:
                regulardmgavg = regularavg / regularavgcount
            if criticalavg + regularavg != 0:
                totaldmgavg = (criticalavg + regularavg) / (criticalavgcount + regularavgcount)
            if healingavg != 0:
                healingavg = healingavg / healingavgcount
            if absorbavg != 0:
                absorbavg = absorbavg / absorbavgcount
            if currentmonster["miss"] > 0:
                hitpercent = int((float(currentmonster["miss"]) / float(len(currentmonster["damage"]))) * 100)
                hitpercent = (100 - hitpercent)
            print "Defeated %s as %s\nAccuracy: %i%%\nTotal Damage: %i\nTotal Avg Dmg: %i\nCrit Hit %%: %i\nCrit Avg Dmg: %i%%\nReg Avg Dmg: %i\nTotal Hit Dmg Avg: %i\nCrit Hit Dmg Avg: %i\nHit Dmg Avg: %i\nTotal Dmg From Others: %i\nHealing Avg: %i\nAbsorb Avg: %i\nExp: %i\nSkill Points: %i\nDate Time: %s GMT\n" % (currentmonster["monster"], currentmonster["class"], hitpercent, totaldamage, totaldmgavg, critpercent, criticaldmgavg, regulardmgavg, totalhitdmgavg, crithitdmgavg, hitdmgavg, othertotaldmg, healingavg, absorbavg, currentmonster["exp"], currentmonster["skillpoints"], currentmonster["datetime"])
            self.monsterdata.append(currentmonster)
            self.defeated = False
            self.spset = False
            self.expset = False
            self.currentmonster = copy.deepcopy(self.defaultmonster)

    def useitem(self, logitem):
        #print "Use Item: " + logitem
        if self.craftingcomplete == 1:
            self.printCrafting(self.currentcrafting)
            self.currentcrafting = copy.deepcopy(self.defaultcrafting)
            self.currentcrafting["datetime"] = time.strftime("%m/%d/%y %H:%M:%S",time.gmtime(self.logfiletime))
            #print self.currentcrafting["datetime"]
            self.craftingcomplete = 0

        if logitem.find("Standard Synthesis") != -1:
            # store previous value if valid:
            if self.synthtype != "":
                self.currentcrafting["actions"].append([self.synthtype, self.progress, self.durability, self.quality])
                #print self.currentcrafting["actions"]
                self.progress = []
                self.durability = []
                self.quality = []
            self.synthtype = "Standard"
        elif logitem.find("Rapid Synthesis") != -1:
            if self.synthtype != "":
                self.currentcrafting["actions"].append([self.synthtype, self.progress, self.durability, self.quality])
                self.progress = []
                self.durability = []
                self.quality = []
            self.synthtype = "Rapid"
        elif logitem.find("Bold Synthesis") != -1:
            if self.synthtype != "":
                self.currentcrafting["actions"].append([self.synthtype, self.progress, self.durability, self.quality])
                self.progress = []
                self.durability = []
                self.quality = []
            self.synthtype = "Bold"
        else:
            #print logitem
            # TODO: need to handle all special types or they will be ingredients, setup
            # an array with all traits and abilities and compare.
            if logitem.find("You use a") != -1:
                ingcount = 1
            elif logitem.find("Touch Up") != -1:
                return
            elif logitem.find("Preserve") != -1:
                return
            elif logitem.find("Blinding Speed") != -1:
                return
            else:
                try:
                    ingcount = int(logitem.split(" ")[2])
                except ValueError:
                    # this is a special so skip it for now...
                    return
            if logitem.find(" of ") != -1:
                ingredient = logitem[logitem.find(" of ") +4:-1]
            else:
                ingredient = " ".join(logitem.split(" ")[3:])[:-1]
            self.currentcrafting["ingredients"].append([ingredient, ingcount])
            
    def engaged(self, logitem):
        self.echo("engaged " + logitem, 1)
        if self.craftingcomplete == 1:
            if self.synthtype != "":
                self.currentcrafting["actions"].append([self.synthtype, self.progress, self.durability, self.quality])
            self.printCrafting(self.currentcrafting)
            self.currentcrafting = copy.deepcopy(self.defaultcrafting)
            self.currentcrafting["datetime"] = time.strftime("%m/%d/%y %H:%M:%S",time.gmtime(self.logfiletime))
            self.craftingcomplete = 0
            self.synthtype = ""
        if logitem.find("You cannot change classes") != -1 or logitem.find("Levequest difficulty") != -1:
            return
        self.defeated = False
        self.spset = False
        self.expset = False
        self.currentmonster = copy.deepcopy(self.defaultmonster)

        self.currentmonster["datetime"] = time.strftime("%m/%d/%y %H:%M:%S",time.gmtime(self.logfiletime))
        self.currentmonster["monster"] = logitem[logitem.find("The ") +4:logitem.find(" is")]
        self.currentmonster["monster"] = self.currentmonster["monster"].split('\'')[0]
        if logitem.find("is engaged.") != -1 and logitem.find("The ") == -1:
            self.currentmonster["monster"] = logitem[:logitem.find(" is")]
        if logitem.find("group") != -1:
            # This is a group start, we need to check to see if it is a NM fight.
            tmpmonster = logitem[:logitem.find("group")].split('\'')[0]
            if self.monsterIsNM(tmpmonster):
                self.currentmonster["monster"] = tmpmonster
        
    def parse_gathering(self, code, logitem):
        logitem = logitem.decode('utf-8')
        self.echo("othergathering " + logitem, 1)

    def parse_othergathering(self, code, logitem):
        logitem = logitem.decode('utf-8')
        self.echo("othergathering " + logitem, 1)

    def parse_leve(self, code, logitem):
        logitem = logitem.decode('utf-8')
        self.echo("leve " + logitem, 1)

    def parse_chatmessage(self, code, logitem):
        global autotranslatearray, currentlanguage
        if currentlanguage != 'en':
            #print "Current Lanuage in EN: " + currentlanguage
            return
        loopcnt = 0
        while logitem.find(self.autotranslateheader) != -1:
            loopcnt +=1;
            if loopcnt > 100:
                break
            # has autotranslate value
            transstart = int(logitem.find(self.autotranslateheader))
            translen = logitem[transstart + 2]
            transbytes = logitem[transstart:transstart + translen + 3]
            groupid, index = self.GetGroupAndIndex(transbytes)
            result = '(%s)' % (self.lookup(autotranslatearray, str(groupid), str(index), 'en'))
            logitem = logitem[:logitem.find(transbytes)] + bytearray(result, 'utf-8') + logitem[logitem.find(transbytes) + len(transbytes):]

        logitem = logitem.decode('utf-8')
        #self.echo("chatmessage " + code + logitem, 1)

        if (code == '1B') or (code == '19'):
            user = ' '.join(logitem.split(' ')[0:2]).strip()
            message = logitem.strip()
        else:
            logitemparts = logitem.split(":")
            user = logitemparts[0].strip()
            message = unicode(":".join(logitemparts[1:]).strip())
        
        try:            
            chatdate = time.strftime("%d-%m-%y %H-%M-%S",time.gmtime(self.logfiletime))
            self.prevchatdate = chatdate 
            self.chatlog.append((code, nullstrip(user), message))
            self.echo("Code: %s User: %s Message: %s" % (code, user, message), 1)
        except:
            traceback.print_exc(file=sys.stdout)

    def parse_npcchat(self, code, logitem):
        logitem = logitem.decode('utf-8')
        self.echo("npc chat " + logitem, 1)

    def parse_invalidcommand(self, code, logitem):
        try:
            logitem = logitem.decode('utf-8')
            self.echo("invalid command " + logitem, 1)
        except:
            pass

    def parse_monstereffect(self, code, logitem):
        logitem = logitem.decode('utf-8')
        self.echo("other abilities " + logitem, 1)

    def parse_othereffect(self, code, logitem):
        logitem = logitem.decode('utf-8')
        if logitem.find("grants you") != -1:    
            effect = logitem[logitem.find("effect of ") +10:-1]
        self.echo("other abilities " + logitem, 1)

    def parse_partyabilities(self, code, logitem):
        logitem = logitem.decode('utf-8')
        if logitem.find("grants") != -1:
            effect = logitem[logitem.find("effect of ") +10:-1]
        if logitem.find("inflicts") != -1:
            monsteraffliction = logitem[logitem.find("effect of ") +10:-1]
        self.echo("other abilities " + logitem, 1)

    def parse_otherabilities(self, code, logitem):
        logitem = logitem.decode('utf-8')
        self.echo("other abilities " + logitem, 1)

    def parse_readyability(self, code, logitem):
        logitem = logitem.decode('utf-8')
        self.echo("ready ability " + logitem, 1)

    def parse_servermessage(self, code, logitem):
        logitem = logitem.decode('utf-8')
        self.echo("server message " + logitem, 1)

    def parse_invoke(self, code, logitem):
        logitem = logitem.decode('utf-8')
        self.echo("invoke " + logitem, 1)

    def parse_inflicts(self, code, logitem):
        logitem = logitem.decode('utf-8')
        if logitem.find("inflicts you") != -1:
            affliction = logitem[logitem.find("effect of ") +10:-1]
            return
        if logitem.find("inflicts") != -1:
            othersaffliction = logitem[logitem.find("effect of ") +10:-1]            
        self.echo("inflicts " + logitem, 1)

    def parse_effect(self, code, logitem):
        logitem = logitem.decode('utf-8')
        self.echo("effect " + logitem, 1)

    def parse_otherrecover(self, code, logitem):
        logitem = logitem.decode('utf-8')
        if logitem.find(" MP") != -1:
            return
        if logitem.find("You recover") != -1:
            usepos = logitem.find(" uses ")
            caster = logitem[:usepos]
            spell = logitem[usepos + 6: logitem.find(". ")]
            target = self.characterdata["charactername"]
            healamount = logitem[logitem.find("recover ") +8:logitem.find(" HP")]
            if int(healamount) == 0:
                return
            self.currentmonster["otherhealing"].append([caster, target, spell, healamount])
            #print self.currentmonster["otherhealing"]
        if logitem.find("recovers") != -1:
            usepos = logitem.find(" uses ")
            onpos = logitem.find(" on ")
            caster = logitem[:usepos]
            spell = logitem[usepos + 6: onpos]
            target = logitem[onpos + 4:logitem.find(". ")]
            healamount = logitem[logitem.find("recovers ") +9:logitem.find(" HP")]
            if int(healamount) == 0:
                return
            self.currentmonster["otherhealing"].append([caster, target, spell, healamount])
        self.echo("otherrecover %s %s" % (code, logitem), 1)

    def parse_selfcast(self, code, logitem):
        logitem = logitem.decode('utf-8')
        if logitem.find(" MP") != -1:
            return
        if logitem.find("You absorb") != -1:
            monster = logitem[logitem.find("from the ") + 9:logitem.find(".")]
            if monster == self.currentmonster["monster"]:
                type = "absorb"
                healing = logitem[logitem.find("absorb ") +7:logitem.find(" HP")]
                if int(healing) == 0:
                    return
                self.currentmonster["healing"].append([self.characterdata["charactername"], type, healing])
                #print self.currentmonster["healing"]
                return
        if logitem.find("You recover") != -1:
            type = "heal"
            healing = logitem[logitem.find("recover ") +8:logitem.find(" HP")]
            if int(healing) == 0:
                return
            self.currentmonster["healing"].append([self.characterdata["charactername"], type, healing])
            #print self.currentmonster["healing"]
            return
        if logitem.find("recovers") != -1:
            type = "heal"
            healing = logitem[logitem.find("recovers ") +9:logitem.find(" HP")]
            if int(healing) == 0:
                return
            target = logitem[logitem.find(". ") + 2:logitem.find(" recovers")]
            self.currentmonster["healing"].append([target, type, healing])
            #print self.currentmonster["healing"]
            return
        self.echo("recover %s %s" % (code, logitem), 1)

    def parse_monstermiss(self, code, logitem):
        logitem = logitem.decode('utf-8')
        self.echo("monstermiss " + logitem, 1)

    def parse_othermiss(self, code, logitem):
        logitem = logitem.decode('utf-8')
        if logitem.find("KO'd target") != -1 or logitem.find("too far away") != -1 or logitem.find("guard fails.") != -1 or logitem.find("fails to take effect.") != -1:
            return
        if logitem.find("evades") != -1:
            if logitem.find(self.currentmonster["monster"] + " evades") != -1:
                monster = logitem[:logitem.find(" evades")]
            else:
                monster = logitem[logitem.find("The ") + 4:logitem.find(" evades")]
            if monster == self.currentmonster["monster"]:
                misschar = logitem[logitem.find("evades ") + 7:logitem.find("'s ")]
                attacktype = logitem[logitem.find("'s ") + 3:logitem.find(".")]
                self.currentmonster["othermiss"].append([misschar, attacktype])
        else:
            if logitem.find("from the") != -1:
                if logitem.find(self.currentmonster["monster"] + " from the") != -1:
                    monster = logitem[logitem.find("misses ") +7:logitem.find(" from the")].split('\'')[0]
                else:
                    monster = logitem[logitem.find("the ") +4:logitem.find(" from the")].split('\'')[0]
            else:
                if logitem.find("misses the") != -1:
                    monster = logitem[logitem.find("the ") +4:logitem.find(".")].split('\'')[0]
                else:
                    monster = logitem[logitem.find("misses ") +7:logitem.find(".")]
            if monster == self.currentmonster["monster"]:
                misschar = logitem[: logitem.find("'s ")]
                attacktype = logitem[logitem.find("'s ") + 3:logitem.find(" misses")]
                self.currentmonster["othermiss"].append([misschar, attacktype])
        # NM monster miss: Uraeus's Body Slam fails.
        if logitem.find("fails.") != -1:
            monster = logitem[:logitem.find('\'')]
            if monster == self.currentmonster["monster"]:
                self.currentmonster["othermonstermiss"] += 1
        self.echo("othermiss " + logitem, 1)

    def parse_miss(self, code, logitem):
        logitem = logitem.decode('utf-8')
        if logitem.find("evades") != -1:
            if logitem.find("The ") != -1:
                monster = logitem[logitem.find("The ") +4:logitem.find(" evades")]
            else:
                monster = logitem[:logitem.find(" evades")]
        else:
            if logitem.find("from the") != -1:
                if logitem.find("misses the") != -1:
                    monster = logitem[logitem.find("the ") +4:logitem.find(" from the")].split('\'')[0]
                else:
                    monster = logitem[logitem.find("misses ") +7:logitem.find(" from the")].split('\'')[0]
            else:
                if logitem.find("misses the") != -1:
                    monster = logitem[logitem.find("the ") +4:logitem.find(".")].split('\'')[0]
                else:
                    monster = logitem[logitem.find("misses ") +7:logitem.find(".")].split('\'')[0]
        
        if monster == self.currentmonster["monster"]:
            self.currentmonster["miss"] += 1
        if logitem.find("fails.") != -1:
            monster = logitem[:logitem.find('\'')]
            if monster == self.currentmonster["monster"]:
                self.currentmonster["monstermiss"] += 1
        self.echo("miss " + logitem, 1)

    def parse_otherhitdamage(self, code, logitem):
        logitem = logitem.decode('utf-8')
        if logitem.find("hits ") != -1:
            if logitem.find("points") == -1:
                return
            if logitem.find("The") != -1:
                monsterhit = logitem[logitem.find("The ") +4:logitem.find(" hits")]
                monster = monsterhit.split('\'')[0]
                attacktype = monsterhit[monsterhit.find("'s ")+3:]
            else:
                monsterhit = logitem[:logitem.find(" hits")]
                monster = monsterhit.split('\'')[0]
                attacktype = monsterhit[monsterhit.find("'s ")+3:]
            if monster == self.currentmonster["monster"]:
                if logitem.find("Critical!") != -1:
                    critical = 1
                else:
                    critical = 0
                if logitem.find(" points") != -1:
                    if logitem.find("from the") != -1:
                        hitchar = logitem[logitem.find("hits ") + 5:logitem.find(" from")]
                    else:
                        hitchar = logitem[logitem.find("hits ") + 5:logitem.find(" for")]
                    hitdamage = logitem[logitem.find("for ") +4:logitem.find(" points")]
                    self.currentmonster["otherhitdamage"].append([hitdamage, critical, attacktype, hitchar])
        self.echo("otherhitdamage " + logitem, 1)

    def parse_otherdamage(self, code, logitem):
        logitem = logitem.decode('utf-8')
        if logitem.find("hits the") != -1:
            if logitem.find("from the ") != -1:
                monster = logitem[logitem.find("the ") +4:logitem.find(" from the")]
            else:
                monster = logitem[logitem.find("the ") +4:logitem.find(" for")]
        else:
            if logitem.find("from the ") != -1:
                monster = logitem[logitem.find("hits ") +5:logitem.find(" from the")]
            else:
                monster = logitem[logitem.find("hits ") +5:logitem.find(" for")]
        if monster == self.currentmonster["monster"]:                        
            if logitem.find("Critical!") != -1:
                critical = 1
            else:
                critical = 0
            attackchar = ""
            if logitem.find("Counter!") != -1:
                # "Counter! Par Shadowmaster hits the great buffalo for 419 points of damage"
                attackchar = logitem[logitem.find("! ")+2:logitem.find(" hits")]
                attacktype = "Counter"
            else:
                if critical:
                    attackchar = logitem[10: logitem.find("'s ")]
                else:
                    attackchar = logitem[: logitem.find("'s ")]
                attacktype = logitem[logitem.find("'s ") +3:logitem.find(" hits")]
            if logitem.find(" points") != -1:
                damage = logitem[logitem.find("for ") +4:logitem.find(" points")]
                self.currentmonster["otherdamage"].append([damage, critical, attacktype, attackchar])
        self.echo("otherdamage " + logitem, 1)

    def parse_hitdamage(self, code, logitem):
        logitem = logitem.decode('utf-8')
        if logitem.find("hits you") != -1:
            if logitem.find("points") == -1:
                return
            if logitem.find("The ") != -1:
                monsterhit = logitem[logitem.find("The ") +4:logitem.find(" hits")]
            else:
                monsterhit = logitem[:logitem.find(" hits")]
            monster = monsterhit.split('\'')[0]
            attacktype = monsterhit[monsterhit.find("'s ")+3:]
            if monster == self.currentmonster["monster"]:
                hitdamage = logitem[logitem.find("for ") +4:logitem.find(" points")]
                if logitem.find("Critical!") != -1:
                    critical = 1
                else:
                    critical = 0
                self.currentmonster["hitdamage"].append([hitdamage, critical, attacktype])
        self.echo("hitdamage " + logitem, 1)

    def parse_damagedealt(self, code, logitem):
        logitem = logitem.decode('utf-8')
        if logitem.find("your") != -1 or logitem.find("Your") != -1:
            if logitem.find("hits the") != -1:
                if logitem.find("from the ") != -1:
                    monster = logitem[logitem.find("the ") +4:logitem.find(" from the")]
                else:
                    monster = logitem[logitem.find("the ") +4:logitem.find(" for")]
            else:
                if logitem.find("from the ") != -1:
                    monster = logitem[logitem.find("hits ") +5:logitem.find(" from the")]
                else:
                    monster = logitem[logitem.find("hits ") +5:logitem.find(" for")]
            if monster == self.currentmonster["monster"]:                        
                if logitem.find("Critical!") != -1:
                    critical = 1
                else:
                    critical = 0
                attacktype = logitem[logitem.find("Your ") +5:logitem.find(" hits")]
                if logitem.find(" points") != -1:
                    damage = logitem[logitem.find("for ") +4:logitem.find(" points")]
                    self.currentmonster["damage"].append([damage, critical, attacktype])
        self.echo("damagedealt " + logitem, 1)

    def parse_craftingsuccess(self, code, logitem):
        logitem = logitem.decode('utf-8')
        # Crafting success
        if logitem.find("You create") != -1:
            self.currentcrafting["quantity"] = 1
            if logitem.find(" of ") != -1:
                self.currentcrafting["item"] = logitem[logitem.find(" of ")+4:-1]
            elif logitem.find(" a ") != -1:
                self.currentcrafting["item"] = logitem[logitem.find(" a ")+3:-1]
            else:
                itemparts = logitem.split(' ')
                idx = 0
                for item in itemparts:            
                    idx += 1;
                    try:
                        if item == 'an':
                            break
                        self.currentcrafting["quantity"] = int(item)
                        break
                    except:
                        continue
                self.currentcrafting["item"] = ' '.join(itemparts[idx:])
            if self.currentcrafting["item"].endswith("."):
                self.currentcrafting["item"] = self.currentcrafting["item"][:-1]
            self.currentcrafting["success"] = 1
            self.craftingcomplete = 1
        # botched it
        if logitem.find("You botch") != -1:
            #print "Crafting Fail: " + logitem
            self.currentcrafting["quantity"] = 0
            self.currentcrafting["success"] = 0
            self.craftingcomplete = 1
        
        self.echo("crafting success " + logitem, 1)

    def parse_defeated(self, code, logitem):
        logitem = logitem.decode('utf-8')
        self.echo("defeated " + logitem, 1)
        #print self.currentmonster
        if self.craftingcomplete == 1:
            #print "Defeated:" + logitem
            if self.synthtype != "":
                self.currentcrafting["actions"].append([self.synthtype, self.progress, self.durability, self.quality])
            self.printCrafting(self.currentcrafting)
            self.currentcrafting = copy.deepcopy(self.defaultcrafting)
            self.currentcrafting["datetime"] = time.strftime("%m/%d/%y %H:%M:%S",time.gmtime(self.logfiletime))
            #print self.currentcrafting["datetime"]
            self.craftingcomplete = 0
            self.synthtype = ""
        if logitem.find("group") != -1:
            return
        if logitem.find("defeats you") != -1:
            # You were killed...
            self.deathsdata["deaths"].append({"datetime":time.strftime("%m/%d/%y %H:%M:%S",time.gmtime(self.logfiletime)), "class":self.currentmonster["class"]})
            #self.characterdata["deaths"].append({"datetime":time.strftime("%m/%d/%y %H:%M:%S",time.gmtime(self.logfiletime)), "class":self.currentmonster["class"]})
            #0045::The fat dodo defeats you.
            return
        if logitem.find("You defeat the") != -1:
            monster = logitem[logitem.find("defeat the ") +11:logitem.find(".")]
            if monster != self.currentmonster["monster"]:
                return
            self.defeated = True
        if logitem.find("defeats") != -1:
            monster = logitem[logitem.find("defeats ") +8:logitem.find(".")]
            if monster != self.currentmonster["monster"]:
                return
            self.defeated = True

        if logitem.find("The ") == -1 and logitem.find("is defeated") != -1:
            monster = logitem[:logitem.find(" is defeated")]
            if monster != self.currentmonster["monster"]:
                return
            self.defeated = True
        elif logitem.find("defeated") != -1:
            monster = logitem[logitem.find("The ") +4:logitem.find(" is defeated")].split('\'')[0]
            if monster != self.currentmonster["monster"]:
                return
            self.defeated = True
        if self.monsterIsNM(self.currentmonster["monster"]) and self.defeated:
            self.currentmonster["skillpoints"] = 0
            self.currentmonster["exp"] = 0
            self.defeated = False
            self.spset = False
            self.expset = False
            self.printDamage(self.currentmonster)


    def parse_spexpgain(self, code, logitem):
        logitem = logitem.decode('utf-8')
        pos = logitem.find("You gain")
        if pos > -1:
            points = ""
            skill = ""
            if logitem.find("experience") != -1:
                points = logitem[9:logitem.find("experience") -1]
                #exptotal += int(points)
                self.currentmonster["exp"] = int(points)
                self.currentcrafting["exp"] = int(points)
                self.expset = True
            elif logitem.find("skill") != -1:
                logitemparts = logitem.split(" ")
                self.currentmonster["skillpoints"] = int(logitemparts[2])
                self.currentmonster["class"] = logitemparts[3]
                self.currentcrafting["skillpoints"] = int(logitemparts[2])
                self.currentcrafting["class"] = logitemparts[3]
                self.spset = True
        if self.craftingcomplete and self.spset:
            self.parse_defeated("", "")
            self.defeated = False
            self.spset = False
            self.expset = False
            
        if self.defeated and self.spset and self.expset:
            self.defeated = False
            self.spset = False
            self.expset = False
            self.printDamage(self.currentmonster)

        #if and self.spset and self.defeated:
        #    self.engaged(logitem)
        self.echo("spexpgain " + logitem, 1)

    def throwaway(self, logitem):
        item = logitem[logitem.find("away the ") + 9:logitem.find(".")]
        #self.lostitems.append({"datetime":time.strftime("%m/%d/%y %H:%M:%S",time.gmtime(self.logfiletime)), "item":item})
        
    def parse_genericmessage(self, code, logitem):
        try:
            logitem = logitem.decode('utf-8')
        except:
            # specific to: 54 68 65 20 64 61 72 6B 77 69 6E 67 20 64 65 76 69 6C 65 74 20 69 73 20 6D 61 72 6B 65 64 20 77 69 74 68 20 02 12 04 F2 01 29 03 2E
            #print ''.join( [ "%02X " % x for x in logitem ] ).strip()
            return
        if logitem.find("You throw away") != -1:
            self.throwaway(logitem)
        if logitem.find("is defeated") != -1:
            self.parse_defeated(code, logitem)
        if logitem.find("engaged") != -1:
            self.engaged(logitem)
        elif logitem.find("You use") != -1:
            self.useitem(logitem)
        elif logitem.find("Progress") != -1:
            #print logitem
            # save progress as array of % and it was an increase or decrease
            if logitem.find("increases") != -1:
                self.progress = [int(logitem[logitem.find("by ") +3:-2]), 1]
            else:
                self.progress = [int(logitem[logitem.find("by ") +3:-2]), 0]
        elif logitem.find("Durability") != -1:
            if logitem.find("increases") != -1:
                self.durability = [int(logitem[logitem.find("by ") +3:-1]), 1]
            else:
                self.durability = [int(logitem[logitem.find("by ") +3:-1]), 0]
        elif logitem.find("Quality") != -1:
            if logitem.find("increases") != -1:
                self.quality = [int(logitem[logitem.find("by ") +3:-1]), 1]
            else:
                self.quality = [int(logitem[logitem.find("by ") +3:-1]), 0]
        else:
            pass        
            
        self.echo("generic " + logitem, 1)

class japanese_parser(ffxiv_parser):

    def close(self):
        if len(self.chatlog) == 0:
            return
        if self.prevchatdate != None:
            if not os.path.exists('chatlogs'):
                os.mkdir('chatlogs')
            with open(os.path.join('chatlogs', self.prevchatdate + '.chat'), 'wb') as chatfile:
                pickle.dump(self.chatlog, chatfile)
            self.chatlog = []
    
    def __init__(self):
        ffxiv_parser.__init__(self, "jp")
        self.prevchatdate = None
        self.chatlog = []
        
        self.craftingcomplete = 0
        self.autotranslateheader = b'\x02\x2E'

    def monsterIsNM(self, monster):
        NMList = [u'アルシュ', u'アンノウンソルジャー', u'ウラエウス', u'エルダーモスホーン', u'オールドシックスアームズ', u'カクタージャック', u'クィーンボリート', u'グゥーブー', u'グルタナスガーティ', u'グレートバッファロー', u'シロッコ', u'ジャッカネイプス', u'スピットファイア', u'スリプリーサイクス', u'ダウニーダンスタン', u'ダディーロングレッグ', u'ドドレ', u'ネストコマンダー', u'バルディ', u'バロメッツ', u'パイア', u'ピュラウスタ', u'フレンジード・オーレリア', u'ブラッディウルフ', u'プリンスオブペスト', u'ボムバロン', u'モスホーン・ナニー', u'モスホーン・ビリー', u'太っ腹のホットポックス', u'弾指のココルン']
        return monster.lower() in NMList

    def printCrafting(self, currentcrafting):
        #print currentcrafting
        self.currentcrafting["datetime"] = time.strftime("%m/%d/%y %H:%M:%S",time.gmtime(self.logfiletime))
        totalprogress = 0
        finalquality = 0
        finaldurability = 0
        for action in currentcrafting["actions"]:
            if len(action[1]) > 0:
                totalprogress = totalprogress + action[1][0]
            if len(action[2]) > 0:
                finaldurability = finaldurability + action[2][0]
            if len(action[3]) > 0:
                finalquality = finalquality + action[3][0]
        itemsused = ""
        if len(currentcrafting["ingredients"]) == 0:
            itemsused = u'リーヴは食材を使用しないでください。'
        else:
            inglist = []
            first = True
            for item in currentcrafting["ingredients"]:
                if first:
                    itemsused = str(item[1]) + " x " + item[0]
                    first = False
                else:
                    itemsused = itemsused + ", " + str(item[1]) + " x " + item[0]
        if currentcrafting["success"]:
            print u"%sの完成レシピとして%s\n全体の進行状況: %i\n最終的な品質が追加されました: %i\n最終的な耐久性が失わ: %i\n材料使用: %s\n経験値: %i\n修錬値: %i\n日付時刻: %s GMT\n" % (currentcrafting["item"], currentcrafting["class"], totalprogress, finalquality, finaldurability, itemsused, currentcrafting["exp"], currentcrafting["skillpoints"], currentcrafting["datetime"])
        else:
            print u"%sとして失敗したレシピ\n全体の進行状況: %i\n最終的な品質が追加されました: %i\n最終的な耐久性が失わ: %i\n材料使用: %s\n経験値: %i\n修錬値: %i\n日付時刻: %s GMT\n" % (currentcrafting["class"], totalprogress, finalquality, finaldurability, itemsused, currentcrafting["exp"], currentcrafting["skillpoints"], currentcrafting["datetime"])
        self.craftingdata.append(currentcrafting)
        return

    def printDamage(self, currentmonster):
        if len(currentmonster["damage"]) > 0:
            hitpercent = 100
            criticalavg = 0
            criticalavgcount = 0
            regularavg = 0
            regularavgcount = 0
            criticaldmgavg = 0
            regulardmgavg = 0
            totaldmgavg = 0
            hitdmgavg = 0
            hitdmgavgcount = 0
            crithitdmgavg = 0
            crithitdmgavgcount = 0
            totalhitdmgavg = 0
            othertotaldmg = 0
            healingavg = 0
            healingavgcount = 0
            absorbavg = 0
            absorbavgcount = 0
            totaldamage = 0
            for otherdamage in currentmonster["otherdamage"]:
                if otherdamage[0] == '':
                    continue
                othertotaldmg += int(otherdamage[0])
            for hitdamage in currentmonster["hitdamage"]:
                if hitdamage[0] == '':
                    continue
                if hitdamage[1] == True:
                    crithitdmgavg = crithitdmgavg + int(hitdamage[0])
                    crithitdmgavgcount = crithitdmgavgcount + 1
                else:
                    hitdmgavg = hitdmgavg + int(hitdamage[0])
                    hitdmgavgcount = hitdmgavgcount + 1

            for healing in currentmonster["healing"]:
                if healing[1] == 'heal':
                    healingavg = healingavg + int(healing[2])
                    healingavgcount = healingavgcount + 1
                if healing[1] == 'absorb':
                    absorbavg = absorbavg + int(healing[2])
                    absorbavgcount = absorbavgcount + 1

            for damage in currentmonster["damage"]:
                if damage[0] == '':
                    continue
                totaldamage = totaldamage + int(damage[0])
                if damage[1] == True:
                    criticalavg = criticalavg + int(damage[0])
                    criticalavgcount = criticalavgcount + 1
                else:
                    regularavg = regularavg + int(damage[0])
                    regularavgcount = regularavgcount + 1
            if crithitdmgavg != 0:
                crithitdmgavg = crithitdmgavg / crithitdmgavgcount
            if hitdmgavg != 0:
                hitdmgavg = hitdmgavg / hitdmgavgcount
            if crithitdmgavg + hitdmgavg != 0:
                totalhitdmgavg = (crithitdmgavg + hitdmgavg) / (crithitdmgavgcount + hitdmgavgcount)
            if criticalavg != 0:
                criticaldmgavg = criticalavg / criticalavgcount
            if regularavg != 0:
                regulardmgavg = regularavg / regularavgcount
            if criticalavg + regularavg != 0:
                totaldmgavg = (criticalavg + regularavg) / (criticalavgcount + regularavgcount)
            if healingavg != 0:
                healingavg = healingavg / healingavgcount
            if absorbavg != 0:
                absorbavg = absorbavg / absorbavgcount
            if currentmonster["miss"] > 0:
                hitpercent = int((float(currentmonster["miss"]) / float(len(currentmonster["damage"]))) * 100)
                hitpercent = (100 - hitpercent)
            print u"敗北 %s ⇒ %s\nヒット %%: %i%%\n被害総額: %i\n合計平均ダメージ: %i\nクリティカルの平均ダメージ: %i\nレギュラーの平均被害: %i\n合計ダメージ平均を撮影ヒット: %i\nクリティカルヒットのダメージの平均: %i\nダメージ平均ヒット: %i\nその他から合計ダメージ: %i\n平均ヒーリング: %i\n吸収平均: %i\n経験値: %i\n修錬値: %i\n日付時刻: %s GMT\n" % (currentmonster["monster"], currentmonster["class"], hitpercent, totaldamage, totaldmgavg, criticaldmgavg, regulardmgavg, totalhitdmgavg, crithitdmgavg, hitdmgavg, othertotaldmg, healingavg, absorbavg, currentmonster["exp"], currentmonster["skillpoints"], currentmonster["datetime"])
            self.monsterdata.append(currentmonster)
            self.defeated = False
            self.spset = False
            self.expset = False
            self.currentmonster = copy.deepcopy(self.defaultmonster)

    def useitem(self, logitem):
        #print "useitem" + logitem
        if logitem.find(u"は作業") != -1:
            # store previous value if valid:
            if self.synthtype != "":
                self.currentcrafting["actions"].append([self.synthtype, self.progress, self.durability, self.quality])
                self.progress = []
                self.durability = []
                self.quality = []
            self.synthtype = "Standard"
        elif logitem.find(u"突貫") != -1:
            if self.synthtype != "":
                self.currentcrafting["actions"].append([self.synthtype, self.progress, self.durability, self.quality])
                self.progress = []
                self.durability = []
                self.quality = []
            self.synthtype = "Rapid"
        elif logitem.find(u"入魂") != -1:
            if self.synthtype != "":
                self.currentcrafting["actions"].append([self.synthtype, self.progress, self.durability, self.quality])
                self.progress = []
                self.durability = []
                self.quality = []
            self.synthtype = "Bold"
        else:
            # TODO: Need to handle ingredients in Japanese.
            if logitem.find("You use a") != -1:
                ingcount = 1
            elif logitem.find("Touch Up") != -1:
                return
            elif logitem.find("Preserve") != -1:
                return
            elif logitem.find("Blinding Speed") != -1:
                return
            else:
                try:
                    ingcount = int(logitem.split(" ")[2])
                except ValueError:
                    # this is a special so skip it for now...
                    return
            if logitem.find(" of ") != -1:
                ingredient = logitem[logitem.find(" of ") +4:-1]
            else:
                ingredient = " ".join(logitem.split(" ")[3:])[:-1]
            self.currentcrafting["ingredients"].append([ingredient, ingcount])
    
    def engaged(self, logitem):
        if self.craftingcomplete == 1:
            if self.synthtype != "":
                self.currentcrafting["actions"].append([self.synthtype, self.progress, self.durability, self.quality])
            self.printCrafting(self.currentcrafting)
            self.currentcrafting = copy.deepcopy(self.defaultcrafting)
            self.currentcrafting["datetime"] = time.strftime("%m/%d/%y %H:%M:%S",time.gmtime(self.logfiletime))
            self.craftingcomplete = 0
            self.synthtype = ""
        # TODO: Find the equivelant in japanese
        if logitem.find("You cannot change classes") != -1 or logitem.find("Levequest difficulty") != -1:
            return
        self.defeated = False
        self.spset = False
        self.expset = False
        self.currentmonster = copy.deepcopy(self.defaultmonster)
        
        self.currentmonster["datetime"] = time.strftime("%m/%d/%y %H:%M:%S",time.gmtime(self.logfiletime))
        if logitem.find(u"の一群を占有した") != -1:
            # this is a party engage
            self.currentmonster["monster"] = logitem[:logitem.find(u"の一群を占有した")]
        else:
            self.currentmonster["monster"] = logitem[:logitem.find(u"を占有した")]
        
    def parse_gathering(self, code, logitem):
        logitem = logitem.decode('utf-8')
        self.echo("othergathering " + logitem, 1)

    def parse_othergathering(self, code, logitem):
        logitem = logitem.decode('utf-8')
        self.echo("othergathering " + logitem, 1)

    def parse_leve(self, code, logitem):
        logitem = logitem.decode('utf-8')
        self.echo("leve " + logitem, 1)

    def parse_chatmessage(self, code, logitem):
        #print "here" + code + logitem
        global autotranslatearray, currentlanguage
        if currentlanguage != 'jp':
            #print "Current Lanuage in JP: " + currentlanguage
            return
        #print "starting chat msg"
        loopcnt = 0
        while logitem.find(self.autotranslateheader) != -1:
            loopcnt +=1;
            if loopcnt > 100:
                break
            # has autotranslate value
            transstart = int(logitem.find(self.autotranslateheader))
            translen = logitem[transstart + 2]
            transbytes = logitem[transstart:transstart + translen + 3]
            groupid, index = self.GetGroupAndIndex(transbytes)
            result = '(%s)' % (self.lookup(autotranslatearray, str(groupid), str(index), 'ja'))
            logitem = logitem[:logitem.find(transbytes)] + bytearray(result, 'utf-8') + logitem[logitem.find(transbytes) + len(transbytes):]

        logitem = logitem.decode('utf-8')
        #self.echo("chatmessage " + code + logitem, 1)

        if (code == '1B') or (code == '19'):
            user = ' '.join(logitem.split(' ')[0:2]).strip()
            message = logitem.strip()
        else:
            logitemparts = logitem.split(":")
            user = logitemparts[0].strip()
            message = unicode(":".join(logitemparts[1:]).strip())
        
        try:            
            chatdate = time.strftime("%d-%m-%y %H-%M-%S",time.gmtime(self.logfiletime))
            self.prevchatdate = chatdate 
            self.chatlog.append((code, nullstrip(user), message))
            self.echo("Code: %s User: %s Message: %s" % (code, user, message), 1)
        except:
            traceback.print_exc(file=sys.stdout)

    def parse_npcchat(self, code, logitem):
        logitem = logitem.decode('utf-8')
        self.echo("npc chat " + logitem, 1)

    def parse_invalidcommand(self, code, logitem):
        try:
            logitem = logitem.decode('utf-8')
            self.echo("invalid command " + logitem, 1)
        except:
            pass

    def parse_monstereffect(self, code, logitem):
        logitem = logitem.decode('utf-8')
        self.echo("other abilities " + logitem, 1)

    def parse_othereffect(self, code, logitem):
        logitem = logitem.decode('utf-8')
        if logitem.find("grants you") != -1:    
            effect = logitem[logitem.find("effect of ") +10:-1]
        self.echo("other abilities " + logitem, 1)

    def parse_partyabilities(self, code, logitem):
        logitem = logitem.decode('utf-8')
        if logitem.find("grants") != -1:
            effect = logitem[logitem.find("effect of ") +10:-1]
        if logitem.find("inflicts") != -1:
            monsteraffliction = logitem[logitem.find("effect of ") +10:-1]
        self.echo("other abilities " + logitem, 1)

    def parse_otherabilities(self, code, logitem):
        logitem = logitem.decode('utf-8')
        self.echo("other abilities " + logitem, 1)

    def parse_readyability(self, code, logitem):
        logitem = logitem.decode('utf-8')
        self.echo("ready ability " + logitem, 1)

    def parse_servermessage(self, code, logitem):
        logitem = logitem.decode('utf-8')
        self.echo("server message " + logitem, 1)

    def parse_invoke(self, code, logitem):
        logitem = logitem.decode('utf-8')
        self.echo("invoke " + logitem, 1)

    def parse_inflicts(self, code, logitem):
        logitem = logitem.decode('utf-8')
        if logitem.find("inflicts you") != -1:
            affliction = logitem[logitem.find("effect of ") +10:-1]
            return
        if logitem.find("inflicts") != -1:
            othersaffliction = logitem[logitem.find("effect of ") +10:-1]            
        self.echo("inflicts " + logitem, 1)

    def parse_effect(self, code, logitem):
        logitem = logitem.decode('utf-8')
        self.echo("effect " + logitem, 1)

    def parse_otherrecover(self, code, logitem):
        logitem = logitem.decode('utf-8')
        self.echo("otherrecover %s %s" % (code, logitem), 1)
        if logitem.find("MP") != -1:
            return
        if logitem.find(u"回復した") != -1:
            caster = logitem[:logitem.find(u"は")]
            spell = logitem[logitem.find(u"「")+1: logitem.find(u"」")]
            target = logitem[logitem.find(u"⇒　") + 2:logitem.find(u"はＨＰ")]
            healamount = logitem[logitem.find(u"ＨＰを") +3:logitem.find(u"回復した")]
            if int(healamount) == 0:
                return
            self.currentmonster["otherhealing"].append([caster, target, spell, healamount])

    def parse_selfcast(self, code, logitem):
        logitem = logitem.decode('utf-8')
        self.echo("recover %s %s" % (code, logitem), 1)
        if logitem.find("MP") != -1:
            return
        if logitem.find(u"吸収した") != -1:
            monster = logitem[logitem.find(u"は") + 1:logitem.find(u"の")]
            if monster == self.currentmonster["monster"]:
                type = "absorb"
                healing = logitem[logitem.find(u"ＨＰを") +3:logitem.find(u"吸収した")]
                if int(healing) == 0:
                    return
                self.currentmonster["healing"].append([self.characterdata["charactername"], type, healing])
                return
        if logitem.find(u"回復した") != -1:
            type = "heal"
            healing = logitem[logitem.find(u"ＨＰを") +3:logitem.find(u"回復した")]
            if int(healing) == 0:
                return
            caster = logitem[:logitem.find(u"は")]
            target = logitem[logitem.find(u"は") + 1:logitem.find(u"に")]
            if caster == target:
                self.currentmonster["healing"].append([self.characterdata["charactername"], type, healing])
            else:
                self.currentmonster["healing"].append([target, type, healing])
            return

    def parse_monstermiss(self, code, logitem):
        logitem = logitem.decode('utf-8')
        self.echo("monstermiss " + logitem, 1)

    def parse_othermiss(self, code, logitem):
        logitem = logitem.decode('utf-8')
        if logitem.find(u"行動不能状態") != -1 or logitem.find(u"目標が遠すぎます。") != -1 or logitem.find("guard fails.") != -1 or logitem.find(u"効果がなかった") != -1:
            return 
        if logitem.find(u"攻撃を外してしまった") != -1:
            attacker = logitem[:logitem.find(u"は")]
            defender = logitem[logitem.find(u"は") +1:logitem.find(u"に")]
            
            if defender == self.currentmonster["monster"]:
                misschar = logitem[:logitem.find(u"は")]
                attacktype = logitem[logitem.find(u"「") +1:logitem.find(u"」")]
                self.currentmonster["othermiss"].append([misschar, attacktype])
                return
            elif attacker == self.currentmonster["monster"]:
                self.parse_monstermiss(code, logitem)
                return

        self.echo("othermiss " + logitem, 1)

    def parse_miss(self, code, logitem):
        logitem = logitem.decode('utf-8')
        monster = logitem[logitem.find(u"は") +1:logitem.find(u"に")]
        if monster == self.currentmonster["monster"]:
            self.currentmonster["miss"] += 1
            return
        self.echo("miss " + logitem, 1)

    def parse_otherhitdamage(self, code, logitem):
        logitem = logitem.decode('utf-8')
        attacker = logitem[:logitem.find(u"は")]
        defender = logitem[logitem.find(u"は") +1:logitem.find(u"に")]
        attacktype = logitem[logitem.find(u"「") +1:logitem.find(u"」")]

        if defender == self.currentmonster["monster"] and attacktype == u"攻撃":
            # The monster did damage to itself, jumping djigga im looking at you...
            return
            
        if attacker == self.currentmonster["monster"]:
            if logitem.find(u"クリティカル！") != -1:
                critical = 1
            else:
                critical = 0
            if logitem.find(u"ダメージを与えた") != -1:
                if critical:
                    hitdamage = int(logitem[logitem.find(u"クリティカル！　") +9:logitem.find(u"ダメージを与えた")])
                else:
                    hitdamage = int(logitem[logitem.find(u"⇒　") +2:logitem.find(u"ダメージを与えた")])
                self.currentmonster["otherhitdamage"].append([hitdamage, critical, attacktype, defender])
                return
        self.echo("otherhitdamage " + logitem, 1)

    def parse_otherdamage(self, code, logitem):
        logitem = logitem.decode('utf-8')
        # this one is tricky, the only way to tell if it is damage or a hit is to look at the
        # order of the names and compare to see if it is the monster. Pain in the butt because
        # they both come in from code 55... There are also quite a few variants that do not exist
        # in the english version of the logs.
        if logitem.find(u"に命中した") != -1:
            # this is useless because it just shows the value (may be nice for other effects or something later.
            return
        attacker = logitem[:logitem.find(u"は")]
        defender = logitem[logitem.find(u"は") +1:logitem.find(u"に")]
        attacktype = logitem[logitem.find(u"「") +1:logitem.find(u"」")]
        # this is a hit, not damage redirect to the right method.
        if attacker == self.currentmonster["monster"] or attacktype == u"攻撃":
            self.parse_otherhitdamage(code, logitem)
            return
        if logitem.find(u"クリティカル！") != -1:
            critical = 1
        else:
            critical = 0
        # Spell Resistance
        if logitem.find(u"魔法に抵抗し") != -1:
            try:
                damage = int(logitem[logitem.find(u"ダメージは") + 6:logitem.find(u"に半減された")])
            except ValueError:
                return
            self.currentmonster["otherdamage"].append([damage, critical, attacktype, attacker])
            return
        if logitem.find(u"に軽減された") != -1:
            try:
                damage = int(logitem[logitem.find(u"ダメージは") + 6:logitem.find(u"に軽減された")])
            except ValueError:
                return
            self.currentmonster["otherdamage"].append([damage, critical, attacktype, attacker])
            return
        if logitem.find(u"のＭＰ") != -1:
            # no use for MP drain right now.  later when i do healing it will be good.
            return
        if logitem.find(u"ダメージを与えた") != -1:
            try:
                if critical:
                    damage = int(logitem[logitem.find(u"クリティカル！　") +9:logitem.find(u"ダメージを与えた")])
                else:
                    # leg hit
                    if logitem.find(u"の脚部") != -1:
                        damage = int(logitem[logitem.find(u"の脚部に") +5:logitem.find(u"のダメージを与えた")])
                    else:
                        damage = int(logitem[logitem.find(u"⇒　") +2:logitem.find(u"ダメージを与えた")])
                self.currentmonster["otherdamage"].append([damage, critical, attacktype, attacker])
                return
            except ValueError:
                return
            
        self.echo("otherdamage code %s: %s " % (code, logitem), 1)

    def parse_hitdamage(self, code, logitem):
        logitem = logitem.decode('utf-8')
        if logitem.find(u"ダメージを与えた。") != -1:
            if logitem.find(u"⇒　") == -1:
                return
            #monsterhit = logitem[logitem.find(u"⇒　") +2:logitem.find(" hits")]
            monster = logitem.split(u"は")[0]
            attacktype = logitem[logitem.find(u"「")+1:logitem.find(u"」")]
            if monster == self.currentmonster["monster"]:
                if logitem.find(u"クリティカル！") != -1:
                    critical = 1
                else:
                    critical = 0
                if critical:
                    hitdamage = logitem[logitem.find(u"クリティカル！　") +9:logitem.find(u"ダメージを与えた。")]
                else:
                    hitdamage = logitem[logitem.find(u"⇒　") +2:logitem.find(u"ダメージを与えた。")]
                self.currentmonster["hitdamage"].append([int(hitdamage), critical, attacktype])
                return
        self.echo("hitdamage " + logitem, 1)

    def parse_damagedealt(self, code, logitem):
        logitem = logitem.decode('utf-8')
        # we can ignore From the left / right / back because of the formatting
        # may want to record that later but not really needed for any useful stats
        monster = logitem[logitem.find(u"は") +1:logitem.find(u"に")]
        if monster == self.currentmonster["monster"]:                        
            if logitem.find(u"クリティカル！") != -1:
                critical = 1
            else:
                critical = 0
            attacktype = logitem[logitem.find(u"「") +1:logitem.find(u"」")]
            if critical:
                damage = logitem[logitem.find(u"クリティカル！　") +9:logitem.find(u"ダメージを与えた。")]
            else:
                damage = logitem[logitem.find(u"⇒　") +2:logitem.find(u"ダメージを与えた。")]
            try:
                self.currentmonster["damage"].append([int(damage), critical, attacktype])
            except:
                if logitem.find(u"打ち消した") != -1:
                    return
            return
        self.echo("damagedealt " + logitem, 1)

    def parse_craftingsuccess(self, code, logitem):
        logitem = logitem.decode('utf-8')
        # Crafting success
        if logitem.find(u"完成させた") != -1:
            #print "Crafting Success: " + logitem
            self.currentcrafting["item"] = logitem[logitem.find(u'「')+1:logitem.find(u'」')]
            # TODO: Get created count with -> ×
            self.currentcrafting["success"] = 1
            self.craftingcomplete = 1
        # botched it
        if logitem.find(u"製作に失敗した") != -1:
            self.currentcrafting["success"] = 0
            self.craftingcomplete = 1
        
        self.echo("crafting success " + logitem, 1)

    def parse_defeated(self, code, logitem):
        logitem = logitem.decode('utf-8')
        self.echo("defeated " + logitem, 1)
        if self.craftingcomplete == 1:
            if self.synthtype != "":
                self.currentcrafting["actions"].append([self.synthtype, self.progress, self.durability, self.quality])
            self.printCrafting(self.currentcrafting)
            self.currentcrafting = copy.deepcopy(self.defaultcrafting)
            self.currentcrafting["datetime"] = time.strftime("%m/%d/%y %H:%M:%S",time.gmtime(self.logfiletime))
            self.craftingcomplete = 0
            self.synthtype = ""
        if logitem.find(u"一群") != -1:
            return
        #if logitem.find("defeats you") != -1:
        #    # You were killed...
        #    self.deathsdata["deaths"].append({"datetime":time.strftime("%m/%d/%y %H:%M:%S",time.gmtime(self.logfiletime)), "class":self.currentmonster["class"]})
        #    #self.characterdata["deaths"].append({"datetime":time.strftime("%m/%d/%y %H:%M:%S",time.gmtime(self.logfiletime)), "class":self.currentmonster["class"]})
        #    #0045::The fat dodo defeats you.
        #    return
        if logitem.find(u"を倒した。") != -1:
            monster = logitem[:logitem.find(u"を倒した。")]
            if monster != self.currentmonster["monster"]:
                return
            self.defeated = True
        if self.monsterIsNM(self.currentmonster["monster"]) and self.defeated:
            self.currentmonster["skillpoints"] = 0
            self.currentmonster["exp"] = 0
            self.defeated = False
            self.spset = False
            self.expset = False
            self.printDamage(self.currentmonster)

    def parse_spexpgain(self, code, logitem):
        logitem = logitem.decode('utf-8')
        if logitem.find(u"の経験値") != -1:
            points = logitem[logitem.find(u"は")+1:logitem.find(u"の経験値")]
            self.currentmonster["exp"] = int(points)
            self.currentcrafting["exp"] = int(points)
            self.expset = True

        elif logitem.find(u"修錬") != -1:
            sp = logitem[logitem.find(u"値") + 1:logitem.find(u"を得")]
            self.currentmonster["skillpoints"] = int(sp)
            self.currentmonster["class"] = logitem[logitem.find(u"「") + 1:logitem.find(u"」")]
            self.currentcrafting["skillpoints"] = int(sp)
            self.currentcrafting["class"] = logitem[logitem.find(u"「") + 1:logitem.find(u"」")]
            self.spset = True
        
        if self.spset and self.craftingcomplete:
            self.parse_defeated("", "")
            self.defeated = False
            self.spset = False
            self.expset = False

        if self.defeated and self.spset and self.expset:
            self.defeated = False
            self.spset = False
            self.expset = False
            self.printDamage(self.currentmonster)

        self.echo("spexpgain " + logitem, 1)
        
    def throwaway(self, logitem):
        item = logitem[logitem.find("away the ") + 9:logitem.find(".")]
        #self.lostitems.append({"datetime":time.strftime("%m/%d/%y %H:%M:%S",time.gmtime(self.logfiletime)), "item":item})

    def parse_genericmessage(self, code, logitem):
        try:
            logitem = logitem.decode('utf-8')
        except:
            # specific to: 54 68 65 20 64 61 72 6B 77 69 6E 67 20 64 65 76 69 6C 65 74 20 69 73 20 6D 61 72 6B 65 64 20 77 69 74 68 20 02 12 04 F2 01 29 03 2E
            return
        if logitem.find("You throw away") != -1:
            self.throwaway(logitem)
        elif logitem.find(u"を占有した") != -1:
            self.engaged(logitem)
        elif logitem.find(u"開始した") != -1:
            self.useitem(logitem)
        elif logitem.find(u"作業進捗") != -1:
            # save progress as array of % and it was an increase or decrease
            self.progress = [int(logitem[logitem.find(u"作業進捗 ") +5:logitem.find(u"％")]), 1]
        elif logitem.find(u"素材耐用") != -1:
            # TODO: Figure out if there is ever an increase rather than 減少した
            if logitem.find(u"上昇した") != -1:
                self.durability = [int(logitem[logitem.find(u"が ") +2:logitem.find(u"上昇した")]), 1]
            else:
                self.durability = [int(logitem[logitem.find(u"が ") +2:logitem.find(u"減少した")]), 0]
        elif logitem.find(u"目標品質") != -1:
            if logitem.find(u"上昇した") != -1:
                self.quality = [int(logitem[logitem.find(u"が ") +2:logitem.find(u"上昇した")]), 1]
            else:
                #print logitem
                #⇒　目標品質度が 11低下した……
                self.quality = [int(logitem[logitem.find(u"が ") +2:logitem.find(u"低下した")]), 0]
        else:
            pass
            
        self.echo("generic " + logitem, 1)

def readLogFile(paths, charactername, logmonsterfilter = None, isrunning=None, password="", parsers=[]):
    global configfile, lastlogparsed
    config = ConfigParser.ConfigParser()
    config.read(configfile)
    try:
        config.add_section('Config')
    except ConfigParser.DuplicateSectionError:
        pass
    logfile = None
    logsparsed = 0
    for logfilename in paths:
        try:
            # have to read ALL of the files in case something was missed due to a restart when a read was in the middle.
            # can't guess where a fight may start since NM fights are VERY VERY long 2000+ hits.
            logfiletime = os.stat(logfilename).st_mtime
            logsparsed = logsparsed + 1
            for parser in parsers:
                parser.setLogFileTime(logfiletime)
            logfile = open(logfilename, 'rb')
            # read in the length of this files records
            headerparts = struct.unpack("2l", logfile.read(8))
            headerlen = headerparts[1] - headerparts[0]
            header = struct.unpack(str(headerlen)+"l", logfile.read(headerlen*4))
            # header * 4 bytes for each and another 8 bytes for the header size
            offset = headerlen*4+8
            for headerpos in range(len(header)):
                if headerpos == 0:
                    startbyte = offset
                    endbyte = header[headerpos]
                else:
                    startbyte = offset + header[headerpos-1]
                    endbyte = header[headerpos] - header[headerpos-1]
                logfile.seek(startbyte)
                logitem = logfile.read(endbyte)[2:]
                for parser in parsers:
                    try:
                        parser.parse_line(bytearray(logitem))
                    except UnicodeDecodeError:
                        pass
                    except:
                        traceback.print_exc(file=sys.stdout)
                if isrunning:
                    if not isrunning():
                        return
                continue
            for parser in parsers:
                parser.close()

        finally:            
            if logfile:
                logfile.close()
        lastlogparsed = logfiletime
        config.set('Config', 'lastlogparsed', lastlogparsed)
        with open(configfile, 'wb') as openconfigfile:
            config.write(openconfigfile)
    if os.path.exists('newinstall'):
        os.remove('newinstall')
    # uncomment for debugging to disable uploads
    #return
    if logsparsed > 0:
        uploadToDB(password, parsers)
    else:
        print "No new log data to parse.  Don't you have some leves to do?"

def uploadDeaths(header, deathdata):
    if len(deathdata["deaths"]) > 0:
        #print deathdata
        #return
        if header["language"] == "en":
            print "Uploading deaths data."
        else:
            print "アップロードの死亡データ。"
        header["deaths"] = deathdata
        jsondata = json.dumps(header)
        #print jsondata
        url = doUpload(jsondata, 'http://ffxivbattle.com/postdeaths.php')
        if url == None:
            return
        if header["language"] == "en":
            print "Total New Character Deaths: %d\n" % int(url["deaths"])
        else:
            print u"合計新キャラクター死亡: %d" % int(url["deaths"])

def uploadBattles(header, battledata):
    if len(battledata) > 0:
        end = 100
        totalbattlerecords = 0
        recordsimported = 0
        updatedrecords = 0
        url = None
        for start in range(0, len(battledata), 100):
            if end > len(battledata):
                end = len(battledata)
            tmpbattledata = header
            tmpbattledata["battle"] = battledata[start:end]
            if header["language"] == "en":
                print "Uploading battle data. Records %d to %d." % (start, end)
            else:
                print "アップロードの戦闘データ。レコード%d〜%d。" % (start, end)
            jsondata = json.dumps(tmpbattledata)
            url = doUpload(jsondata, 'http://ffxivbattle.com/postbattles.php')
            if url == None:
                return
            end = end+100
            try:
                totalbattlerecords = int(url["totalbattlerecords"])
                recordsimported = recordsimported + int(url["recordsimported"])
                updatedrecords = updatedrecords + int(url["updatedrecords"])
            except:
                if parser.getlanguage() == "en":
                    print "Did not understand the response from the server."
                else:
                    print u"サーバーからの応答を理解できませんでした。"
        if header["language"] == "en":
            print "\nTotal Global Battle Records: %d" % totalbattlerecords
            print "Records Sent (Duplicates ignored): %d" % recordsimported
            print "Records Uploaded To Website: %d" % updatedrecords
            if int(updatedrecords) > 0:
                print "\nYour data has been uploaded, you can view it at: \n\n%s" % url["url"] 
            else:
                print "\nNo new records. You can view your data at: \n\n%s\n" % url["url"] 
        else:
            print u"\n合計グローバルバトルレコード: %d" % totalbattlerecords
            print u"レコード送信（無視される重複）: %d" % recordsimported
            print u"ウェブサイトにアップロードされたレコード: %d" % updatedrecords
            if int(updatedrecords) > 0:
                print u"\nあなたのデータはあなたがそれを見ることができる、アップロードされています： \n\n%s" % url["url"] 
            else:
                print u"\nいいえ、新しいレコード。あなたはあなたのデータを表示することができます： \n\n%s\n" % url["url"] 
    
def uploadCrafting(header, craftingdata):
    if len(craftingdata) > 0:
        #print craftingdata
        #return
        end = 100
        craftingcount = 0
        url = None
        for start in range(0, len(craftingdata), 100):
            if end > len(craftingdata):
                end = len(craftingdata)
            tmpcraftingdata = header
            tmpcraftingdata["crafting"] = craftingdata[start:end]
            if header["language"] == "en":
                print "Uploading crafting data. Records %d to %d." % (start, end)
            else:
                print "アップロードは、データを意図的に作成。レコード%d〜%d。" % (start, end)
            jsondata = json.dumps(tmpcraftingdata)
            url = doUpload(jsondata, 'http://ffxivbattle.com/postcrafting.php')
            if url == None:
                return
            end = end+100
            try:
                craftingcount = int(url["craftingcount"])
            except:
                if parser.getlanguage() == "en":
                    print "Did not understand the response from the server."
                else:
                    print u"サーバーからの応答を理解できませんでした。"
        if header["language"] == "en":
            print "Crafting Records Uploaded To Website: %d\n" % craftingcount
        else:
            print u"ウェブサイトにアップロード記録クラフト: %d\n" % craftingcount
    
def uploadToDB(password="", parsers=[]):
    for parser in parsers:
        header = {"version":version,"language":parser.getlanguage(),"password":password, "character":parser.characterdata}        
        uploadDeaths(header, parser.deathsdata)
        uploadCrafting(header, parser.craftingdata)
        uploadBattles(header, parser.monsterdata)
        
        # Clear records for next run
        parser.monsterdata = []
        parser.craftingdata = []
        parser.gatheringdata = []
        parser.deathsdata["deaths"] = []

def doUpload(jsondata, url):
    try:
        #url = 'http://ffxivbattle.com/postlog-test.php'
        user_agent = 'Mozilla/4.0 (compatible; MSIE 5.5; Windows NT)'
        values = {'jsondata' : jsondata }
        #print values
        headers = { 'User-Agent' : "H3lls Log Parser v %s" % (str(version)),
            'Content-Type': 'text/plain; charset=utf-8' }
        req = urllib2.Request(url, jsondata, headers)
        response = urllib2.urlopen(req)
        jsonresults = response.read()
        try:
            return json.loads(jsonresults)
        except:
            print "There was an issue uploading to the server see below:"
            print jsonresults
            return None
    except Exception as e:
        print "There was a problem uploading your data."
        print e

def doAppUpdate():
    try:
        response = urllib2.urlopen('http://ffxivbattle.com/setup.exe');
        file_size = int(response.info().getheader('Content-Length').strip())
        dialog = wx.ProgressDialog ( 'Progress', 'Downloading New Installer Version.', maximum = file_size, style = wx.PD_CAN_ABORT | wx.PD_AUTO_HIDE | wx.PD_ELAPSED_TIME | wx.PD_REMAINING_TIME )
        chunk_size = 8192
        bytes_so_far = 0
        setupfile = 'setup.exe'
        f = open(setupfile, 'wb')
        while 1:
            chunk = response.read(chunk_size)
            f.write(chunk)
            bytes_so_far += len(chunk)
            (keep_going, skip) = dialog.Update ( bytes_so_far )
            if not keep_going:
                dialog.Destroy()
                f.close()
                os.remove(setupfile)
                return 0
            if not chunk:
                break
        f.close()
        return 1
    except Exception, e:
        return 0

def versioncheck(status=0, language="en"):
    response = None
    try:
        response = urllib2.urlopen('http://ffxivbattle.com/logparserversion-2.php');
    except:
        # There was a problem reading the version page skip it.
        if language=="jp":
            print u"リモートのバージョン番号を読み取ることができません。"
        else:
            print "Unable to read the remote version number."
        return 0
    try:
        versiondata = json.loads(response.read())
        if versiondata["version"] > version:
            if language=="jp":
                verdialog = wx.MessageDialog(None, u'新しいバージョンでは、ダウンロードし、インストールすることをご希望の利用可能ですか？\r\n変更: \r\n%s' % (versiondata["changetext"]), u'バージョン %d 対応' % (versiondata["version"]), 
                    wx.YES_NO | wx.NO_DEFAULT | wx.ICON_QUESTION)
            else:
                verdialog = wx.MessageDialog(None, 'A new version is available would you like to download and install it?\r\nChanges: \r\n%s' % (versiondata["changetext"]), 'Version %d Available' % (versiondata["version"]), 
                    wx.YES_NO | wx.NO_DEFAULT | wx.ICON_QUESTION)
            if verdialog.ShowModal() == wx.ID_YES:
                return doAppUpdate()
        elif status:
            if language=="jp":
                okdlg = wx.MessageDialog(None, u'現在、最新のバージョンを実行している。', u'最新バージョン', wx.OK)
            else:
                okdlg = wx.MessageDialog(None, 'You are currently running the latest version.', 'Latest Version', wx.OK)
            okdlg.ShowModal()
    except ValueError, e:
        # The result was garbage so skip it.
        traceback.print_exc()
        if language=="jp":
            print u"リモートのバージョン番号を理解していないか。"
        else:
            print "Did not understand the remote version number."
        return 0
    return 0

if __name__ == '__main__':
    try:
        main()
    except Exception, e:
        print e



