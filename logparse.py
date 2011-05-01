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

version = 4.3
charactername = ""
doloop = 0
app = None

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
    def __init__(self, chatviewer):
        wx.Menu.__init__(self)
        self.chatviewer = chatviewer
        copy = self.Append(wx.ID_COPY, 'Copy' )        
        self.AppendSeparator()
        selectall = self.Append(wx.ID_SELECTALL, 'Select All' )
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

    title = "Chat Viewer"

    def __init__(self):
        wx.Frame.__init__(self, wx.GetApp().TopWindow, title=self.title, size=(500,400))
        self.currdates = []
        self.chat_types = {
            '01': self.WriteSay, # say
            '02': self.WriteShout, # shout
            '03': self.WriteTell, # sending tell
            '04': self.WriteParty, # party
            '05': self.WriteLinkshell, # linkshell
            '06': self.WriteLinkshell, # linkshell
            '07': self.WriteLinkshell, # linkshell
            '10': self.WriteSay, # say messages by others?
            '0D': self.WriteTell, # get tell
            '0F': self.WriteLinkshell, # linkshell
            '0E': self.WriteLinkshell, # linkshell
            '0F': self.WriteLinkshell, # linkshell
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
        static = wx.StaticText(panel, -1, 'Select a date/time to load the chat data.', (5,12), (210, 15))
        self.loadingMsg = wx.StaticText(panel, -1, '', (390,12), (30, 15))
        wx.StaticText(panel, -1, 'Search', (220,12), (35, 15))
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
        self.PopupMenu(LogWindowContext(self), pos)

    def DoSearch(self, event):
        self.loadingMsg.SetLabel("Searching...")
        self.logWindow.Clear()
        self.datelist.SetSelection(-1)
        searchval = self.searchbox.GetValue().lower()
        idx = 0.0
        ttllen = self.datelist.GetCount()
        for index in ReverseIterator(range(ttllen - 1)):
            idx = idx + 1
            self.loadingMsg.SetLabel("Searching... %i%%" % ((idx / ttllen) * 100.0))
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
        self.loadingMsg.SetLabel("Loading...")
        self.logWindow.Clear()
        #self.logWindow.Freeze()

        if datestring != "-- Last 20 Logs --":        
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
                self.loadingMsg.SetLabel("Loading... %i%%" % ((idx / ttllen) * 100.0))
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
            self.datelist.Append("-- Last 20 Logs --")
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
        self.logWindow.WriteText("%s whispers %s\r" % (charname, text))
        self.logWindow.EndTextColour()

    def WriteShout(self, charname, text):
        self.logWindow.BeginTextColour((140, 50, 50))
        self.logWindow.WriteText("%s shouts %s\r" % (charname, text))
        self.logWindow.EndTextColour()
        
    def WriteLinkshell(self, charname, text):
        self.logWindow.BeginTextColour((50, 140, 50))
        self.logWindow.BeginBold()
        self.logWindow.WriteText("<" + charname + "> ")
        self.logWindow.EndBold()
        self.logWindow.WriteText(text + "\r")
        self.logWindow.EndTextColour()

    def WriteSay(self, charname, text):
        self.logWindow.WriteText("%s says %s\r" % (charname, text))
        

    def OnClose(self, e):
        self.Destroy();

class MainFrame(wx.Frame):
    def SaveLanguageSetting(self, lang):
        global configfile

        config = ConfigParser.ConfigParser()
        try:
            config.add_section('Config')
        except ConfigParser.DuplicateSectionError:
            pass
        config.read(configfile)
        self.language = lang

        config.set('Config', 'language', lang)
        with open(configfile, 'wb') as openconfigfile:
            config.write(openconfigfile)

    def SetEnglish(self, event):
        self.SetTitle("FFXIV Log Parser")
        self.filemenu.SetLabel(1, "&Start")
        self.filemenu.SetHelpString(1, " Start Processing Logs")
        self.filemenu.SetLabel(4, "&Parse All Logs")
        self.filemenu.SetHelpString(4, " Start Processing All Logs")
        self.filemenu.SetLabel(wx.ID_ABOUT, "&About")
        self.filemenu.SetHelpString(wx.ID_ABOUT, " Information about this program")
        self.filemenu.SetLabel(2, "&Check for New Version")
        self.filemenu.SetHelpString(2, " Check for an update to the program")
        self.filemenu.SetLabel(wx.ID_EXIT, "E&xit")
        self.filemenu.SetHelpString(wx.ID_EXIT, " Terminate the program")
        self.menuBar.SetLabelTop(0, "&File")
        self.menuBar.SetLabelTop(1, "&Language")
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
        self.filemenu.SetLabel(4, u"再解析のログ")
        self.filemenu.SetHelpString(4, u" 再解析のログ")
        self.filemenu.SetLabel(wx.ID_ABOUT, u"について")
        self.filemenu.SetHelpString(wx.ID_ABOUT, u"このプログラムについての情報")
        self.filemenu.SetLabel(2, u"新しいバージョンの確認")
        self.filemenu.SetHelpString(2, u"プログラムの更新をチェックする")
        self.filemenu.SetLabel(wx.ID_EXIT, u"終了")
        self.filemenu.SetHelpString(wx.ID_EXIT, u"終了プログラム")
        self.menuBar.SetLabelTop(0, u"ファイル")
        self.menuBar.SetLabelTop(1, u"言語")
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
        self.chatviewer = ChatViewer()
        self.chatviewer.Show()
        
    def __init__(self, parent, title):
        global configfile
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
        self.filemenu.Append(4, "&Parse All Logs"," Start Processing All Logs")
        self.filemenu.Append(wx.ID_ABOUT, "&About"," Information about this program")
        self.filemenu.AppendSeparator()
        self.filemenu.Append(2, "&Check for New Version"," Check for an update to the program")
        self.filemenu.AppendSeparator()
        self.filemenu.Append(wx.ID_EXIT,"E&xit"," Terminate the program")
        self.Bind(wx.EVT_MENU, self.OnStartCollecting, id=1)
        self.Bind(wx.EVT_MENU, self.OnStartCollectingAll, id=4)
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
        except:
            pass

        sys.stdout=redir
        self.Show(True)

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
        self.filemenu.Enable(4, False)
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
            self.filemenu.Enable(4, True)
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
            guithread.updatevalues(self.control.GetValue(), self.charname.GetValue(), self.OnStatus, completecallback=self.threadcallback, password=password, chatviewer=self.chatviewer)
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

    def updatevalues(self, logpath, charactername, status, completecallback=None, password="", chatviewer=None):
        self.stopped = 0
        self.logpath = logpath
        self.charactername = charactername
        self.status = status
        self.completecallback = completecallback
        self.password = password
        self.chatviewer = chatviewer
        
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
                        files = [i[1] for i in l[len(l)-3:]]
                    readLogFile(files, self.charactername, isrunning=self.is_running, password=self.password, chatviewer=self.chatviewer)
                start = datetime.datetime.now()
                self.status("Waiting for new log data...")
                while (datetime.datetime.now() - start).seconds < 60:
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
        global doloop, guithread, configfile, lastlogparsed, app
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
        while 1==1:
            l = [(os.stat(i).st_mtime, i) for i in glob.glob(os.path.join(logpath, '*.log'))]
            l.sort()
            diff = set(l).difference( set(prev) )
            if len(diff) > 0:
                prev = l            
                files = [i[1] for i in sorted(diff)]
                try:
                    readLogFile(files, charactername, password=password, logmonsterfilter=logmonsterfilter)
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
        self.defaultcrafting = {"datetime":"", "item":"", "actions":[], "ingredients":[], "success":0, "skillpoints":0, "class":"", "exp":0}
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
            '10': self.parse_chatmessage, # say messages by others?
            '0D': self.parse_chatmessage, # get tell
            '0F': self.parse_chatmessage, # linkshell
            '0E': self.parse_chatmessage, # linkshell
            '0F': self.parse_chatmessage, # linkshell
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

    def getlanguage(self):
        return self.language

    def setLogFileTime(self, logfiletime):
        self.logfiletime = logfiletime

    def getlogparts(self, logitem):
        return logitem.split('::', 1)

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
        try:
            code, logvalue = self.getlogparts(logitem)
        except ValueError:            
            try:
                code, logvalue = self.getlogpartsalt(logitem)
            except ValueError as e:
                self.echo("Could not find code: %s, %s" % (logitem, e), 1)
                return
        
        try:
            self.function_map[code](code, logvalue)
        except KeyError as e:
            self.echo("Could not parse code: %s value: %s error: %s" % (code, logvalue, e), 1)

class english_parser(ffxiv_parser):
    
    #def savealllogs(self):
    #    if len(self.alllog) == 0:
    #        return
    #    if not os.path.exists('chatlogs'):
    #        os.mkdir('chatlogs')
    #    with open(os.path.join('chatlogs', '--Everything--.chat'), 'wb') as chatfile:
    #        pickle.dump(self.alllog, chatfile)
    #    self.alllog = []
        
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
        #self.alllog = []
        
        self.craftingcomplete = 0
        self.autotranslateheader = HexToByte('02 2E')
        #TODO: Move this to a bin file later to avoid the hextobyte and crap in the source.
        self.autotranslate = {        
            HexToByte('02 2E 03 01 66 03'):"(Please use the auto-translate function.)",
            HexToByte('02 2E 03 01 67 03'):"(Japanese)",
            HexToByte('02 2E 03 01 68 03'):"(English)",
            HexToByte('02 2E 03 01 69 03'):"(French)",
            HexToByte('02 2E 03 01 6A 03'):"(German)",
            HexToByte('02 2E 03 01 6B 03'):"(Can you speak Japanese?)",
            HexToByte('02 2E 03 01 6C 03'):"(Can you speak English?)",
            HexToByte('02 2E 03 01 6D 03'):"(Can you speak French?)",
            HexToByte('02 2E 03 01 6E 03'):"(Can you speak German?)",
            HexToByte('02 2E 03 01 6F 03'):"(I don't speak any English.)",
            HexToByte('02 2E 03 01 70 03'):"(I don't speak any Japanese.)",
            HexToByte('02 2E 03 01 71 03'):"(I don't speak any French.)",
            HexToByte('02 2E 03 01 72 03'):"(I don't speak any German.)",
            HexToByte('02 2E 03 01 73 03'):"(Please listen.)",
            HexToByte('02 2E 03 01 74 03'):"(Can you hear me?)",
            HexToByte('02 2E 03 01 75 03'):"(I can speak a little.)",
            HexToByte('02 2E 03 01 76 03'):"(I can understand a little.)",
            HexToByte('02 2E 03 01 77 03'):"(Please use simple words.)",
            HexToByte('02 2E 03 01 78 03'):"(Please do not abbreviate your words.)",
            HexToByte('02 2E 03 01 79 03'):"(I need some time to put together my answer.)",
            HexToByte('02 2E 03 02 CA 03'):"(Nice to meet you.)",
            HexToByte('02 2E 03 02 CB 03'):"(Good morning!)",
            HexToByte('02 2E 03 02 CC 03'):"(Hello!)",
            HexToByte('02 2E 03 02 CD 03'):"(Good evening!)",
            HexToByte('02 2E 03 02 CE 03'):"(Good night!)",
            HexToByte('02 2E 03 02 CF 03'):"(Goodbye.)",
            HexToByte('02 2E 04 02 F0 CF 03'):"(I had fun today!)",
            HexToByte('02 2E 04 02 F0 D0 03'):"(See you again!)",
            HexToByte('02 2E 04 02 F0 D1 03'):"(Let's play together again sometime!)",
            HexToByte('02 2E 04 02 F0 D2 03'):"(I'm back!)",
            HexToByte('02 2E 04 02 F0 D3 03'):"(Welcome back.)",
            HexToByte('02 2E 04 02 F0 D4 03'):"(Congratulations!)",
            HexToByte('02 2E 04 02 F0 D5 03'):"(Good job!)",
            HexToByte('02 2E 04 02 F0 D6 03'):"(Good luck!)",
            HexToByte('02 2E 04 02 F0 D7 03'):"(All right!)",
            HexToByte('02 2E 04 02 F0 D8 03'):"(Thank you.)",
            HexToByte('02 2E 04 02 F0 D9 03'):"(You're welcome.)",
            HexToByte('02 2E 04 02 F0 DA 03'):"(Take care.)",
            HexToByte('02 2E 04 02 F0 DB 03'):"(I'm sorry.)",
            HexToByte('02 2E 04 02 F0 DC 03'):"(Please forgive me.)",
            HexToByte('02 2E 04 02 F0 DD 03'):"(That's too bad.)",
            HexToByte('02 2E 04 02 F0 DE 03'):"(Excuse me...)",
            HexToByte('02 2E 05 03 F2 01 2D 03'):"(Who?)",
            HexToByte('02 2E 05 03 F2 01 2E 03'):"(Which?)",
            HexToByte('02 2E 05 03 F2 01 2F 03'):"(How?)",
            HexToByte('02 2E 05 03 F2 01 30 03'):"(What?)",
            HexToByte('02 2E 05 03 F2 01 31 03'):"(When?)",
            HexToByte('02 2E 05 03 F2 01 32 03'):"(How many?)",
            HexToByte('02 2E 05 03 F2 01 33 03'):"(Where?)",
            HexToByte('02 2E 05 03 F2 01 34 03'):"(Where shall we go?)",
            HexToByte('02 2E 05 03 F2 01 35 03'):"(Which guildleve shall we do?)",
            HexToByte('02 2E 05 03 F2 01 37 03'):"(Do you have it?)",
            HexToByte('02 2E 05 03 F2 01 38 03'):"(What weapons can you use?)",
            HexToByte('02 2E 05 03 F2 01 39 03'):"(What guildleves do you have?)",
            HexToByte('02 2E 05 03 F2 01 3B 03'):"(Can you do it?)",
            HexToByte('02 2E 05 03 F2 01 3C 03'):"(What other classes can you use?)",
            HexToByte('02 2E 05 03 F2 01 3D 03'):"(Do you have it set?)",
            HexToByte('02 2E 05 03 F2 01 3E 03'):"(What's the battle plan?)",
            HexToByte('02 2E 05 03 F2 01 3F 03'):"(What's the Battle Regimen order?)",
            HexToByte('02 2E 05 03 F2 01 40 03'):"(Can I add you to my friend list?)",
            HexToByte('02 2E 05 03 F2 01 41 03'):"(Shall we take a break?)",
            HexToByte('02 2E 05 03 F2 01 42 03'):"(Do you want me to repair it?)",
            HexToByte('02 2E 05 03 F2 01 43 03'):"(Do you need any help?)",
            HexToByte('02 2E 05 04 F2 01 91 03'):"(I don't understand.)",
            HexToByte('02 2E 05 04 F2 01 92 03'):"(No thanks.)",
            HexToByte('02 2E 05 04 F2 01 93 03'):"(Yes, please.)",
            HexToByte('02 2E 05 04 F2 01 94 03'):"(If you would be so kind.)",
            HexToByte('02 2E 05 04 F2 01 95 03'):"(Understood.)",
            HexToByte('02 2E 05 04 F2 01 96 03'):"(I'm sorry. I'm busy now.)",
            HexToByte('02 2E 05 04 F2 01 97 03'):"(I'm playing solo right now.)",
            HexToByte('02 2E 05 04 F2 01 98 03'):"(I don't know how ot answer that question.)",
            HexToByte('02 2E 05 04 F2 01 99 03'):"(I see.)",
            HexToByte('02 2E 05 04 F2 01 9A 03'):"(Thanks for the offer, but I'll have to pass.)",
            HexToByte('02 2E 05 04 F2 01 9B 03'):"(That's interesting.)",
            HexToByte('02 2E 05 04 F2 01 9C 03'):"(Um...)",
            HexToByte('02 2E 05 04 F2 01 9D 03'):"(Huh!?)",
            HexToByte('02 2E 05 04 F2 01 9E 03'):"(Really?)",
            HexToByte('02 2E 05 04 F2 01 9F 03'):"(Hmmm.)",
            HexToByte('02 2E 05 04 F2 01 A0 03'):"(I have to go soon.)",  
            HexToByte('02 2E 05 05 F2 01 F5 03'):"(Casting spell.)",
            HexToByte('02 2E 05 05 F2 01 F6 03'):"(Time for work!)",
            HexToByte('02 2E 05 05 F2 01 F7 03'):"(I have plans.)",
            HexToByte('02 2E 05 05 F2 01 F8 03'):"(I'm sleepy.)",
            HexToByte('02 2E 05 05 F2 01 F9 03'):"(I'm tired.)",
            HexToByte('02 2E 05 05 F2 01 FA 03'):"(Have stuff to do, gotta go!)",
            HexToByte('02 2E 05 05 F2 01 FB 03'):"(I don't feel well.)",
            HexToByte('02 2E 05 05 F2 01 FC 03'):"(I'm not up for it.)",
            HexToByte('02 2E 05 05 F2 01 FD 03'):"(I'm interested.)",
            HexToByte('02 2E 05 05 F2 01 FE 03'):"(Fighting right now!)",
            HexToByte('02 2E 05 05 F2 01 FF 03'):"(I want to make money.)",
            HexToByte('02 2E 04 05 F1 02 03'):"(I don't remember.)",
            HexToByte('02 2E 05 05 F2 02 01 03'):"(I don't know.)",
            HexToByte('02 2E 05 05 F2 02 02 03'):"(Just used it.)",
            HexToByte('02 2E 05 05 F2 02 03 03'):"(I want experience points.)",
            HexToByte('02 2E 05 05 F2 02 04 03'):"(I want skill points.)",
            HexToByte('02 2E 05 06 F2 02 59 03'):"(Can I have it?)",
            HexToByte('02 2E 05 06 F2 02 5A 03'):"(Can you do it for me?)",
            HexToByte('02 2E 05 06 F2 02 5B 03'):"(Lower the price?)",
            HexToByte('02 2E 05 06 F2 02 5C 03'):"(Buy?)",
            HexToByte('02 2E 05 06 F2 02 5D 03'):"(Sell?)",
            HexToByte('02 2E 05 06 F2 02 5E 03'):"(Trade?)",
            HexToByte('02 2E 05 06 F2 02 5F 03'):"(Do you need it?)",
            HexToByte('02 2E 05 06 F2 02 60 03'):"(Can you make it?)",
            HexToByte('02 2E 05 06 F2 02 61 03'):"(Do you have it?)",
            HexToByte('02 2E 05 06 F2 02 62 03'):"(Can you repair it?)",
            HexToByte('02 2E 05 06 F2 02 63 03'):"(What materials are needed?)",
            HexToByte('02 2E 05 06 F2 02 64 03'):"(No money!)",
            HexToByte('02 2E 05 06 F2 02 65 03'):"(I don't have anything to give you.)",
            HexToByte('02 2E 05 06 F2 02 66 03'):"(You can have this.)",
            HexToByte('02 2E 05 06 F2 02 67 03'):"(Please.)",
            HexToByte('02 2E 05 06 F2 02 68 03'):"(Reward:)",
            HexToByte('02 2E 05 06 F2 02 69 03'):"(Price:)", 
            HexToByte('02 2E 05 07 F2 02 BD 03'):"(Looking for members.)",
            HexToByte('02 2E 05 07 F2 02 BE 03'):"(Gather together.)",
            HexToByte('02 2E 05 07 F2 02 BF 03'):"(Team up?)",
            HexToByte('02 2E 05 07 F2 02 C0 03'):"(Are you alone?)",
            HexToByte('02 2E 05 07 F2 02 C1 03'):"(Any vacancies?)",
            HexToByte('02 2E 05 07 F2 02 C2 03'):"(Please invite me.)",
            HexToByte('02 2E 05 07 F2 02 C3 03'):"(Please let me join.)",
            HexToByte('02 2E 05 07 F2 02 C4 03'):"(Who is the leader?)",
            HexToByte('02 2E 05 07 F2 02 C5 03'):"(Just for a short time is fine.)",
            HexToByte('02 2E 05 07 F2 02 C6 03'):"(Our party's full.)",
            HexToByte('02 2E 05 07 F2 02 C7 03'):"(Please assist.)",
            HexToByte('02 2E 05 07 F2 02 C8 03'):"(Disbanding party.)",
            HexToByte('02 2E 05 07 F2 02 C9 03'):"(Taking a break.)",
            HexToByte('02 2E 05 07 F2 02 CA 03'):"(It's better if physical levels aren't too far apart.)",
            HexToByte('02 2E 05 07 F2 02 CB 03'):"(It's better if skill levels aren't too far apart.)",
            HexToByte('02 2E 05 08 F2 03 21 03'):"(Please follow.)",
            HexToByte('02 2E 05 08 F2 03 22 03'):"(I'll follow you.)",
            HexToByte('02 2E 05 08 F2 03 23 03'):"(Please check it.)",
            HexToByte('02 2E 05 08 F2 03 24 03'):"(Found it!)",
            HexToByte('02 2E 05 08 F2 03 25 03'):"(Full attack!)",
            HexToByte('02 2E 05 08 F2 03 26 03'):"(Pull back.)",
            HexToByte('02 2E 05 08 F2 03 27 03'):"(Watch out for enemies.)",
            HexToByte('02 2E 05 08 F2 03 28 03'):"(Defeat this one first!)",
            HexToByte('02 2E 05 08 F2 03 29 03'):"(Please don't attack.)",
            HexToByte('02 2E 05 08 F2 03 2A 03'):"(Please deactivate it.)",
            HexToByte('02 2E 05 08 F2 03 2B 03'):"(Heal!)",
            HexToByte('02 2E 05 08 F2 03 2C 03'):"(Run away!)",
            HexToByte('02 2E 05 08 F2 03 2D 03'):"(Help me out!)",
            HexToByte('02 2E 05 08 F2 03 2E 03'):"(Stop!)",
            HexToByte('02 2E 05 08 F2 03 2F 03'):"(Standing by.)",
            HexToByte('02 2E 05 08 F2 03 30 03'):"(None left.)",
            HexToByte('02 2E 05 08 F2 03 31 03'):"(Don't have it.)",
            HexToByte('02 2E 05 08 F2 03 32 03'):"(Please use it sparingly.)",
            HexToByte('02 2E 05 08 F2 03 33 03'):"(I'll use it sparingly.)",
            HexToByte('02 2E 05 08 F2 03 34 03'):"(I'm weakened.)",
            HexToByte('02 2E 05 08 F2 03 35 03'):"(My gear is in poor condition.)",
            HexToByte('02 2E 05 08 F2 03 36 03'):"(Ready!)",
            HexToByte('02 2E 05 08 F2 03 37 03'):"(Making a Battle Regimen.)",
            HexToByte('02 2E 05 08 F2 03 38 03'):"(Starting the Battle Regimen.)",
            HexToByte('02 2E 05 08 F2 03 39 03'):"(Please set enemy marks.)",
            HexToByte('02 2E 05 08 F2 03 3A 03'):"(Please set an ally mark.)",
            HexToByte('02 2E 05 08 F2 03 3B 03'):"(Please use it.)",
            HexToByte('02 2E 05 08 F2 03 3C 03'):"(Let's rest for a while.)",
            HexToByte('02 2E 05 08 F2 03 3D 03'):"(Front line job)",
            HexToByte('02 2E 05 08 F2 03 3E 03'):"(Support role job)",
            HexToByte('02 2E 05 08 F2 03 3F 03'):"(Back line job)",
            HexToByte('02 2E 05 08 F2 03 40 03'):"(Weakness)",
            HexToByte('02 2E 05 08 F2 03 41 03'):"(Warning)",
            HexToByte('02 2E 05 08 F2 03 42 03'):"(Recommend)",
            HexToByte('02 2E 05 08 F2 03 43 03'):"(Kill Order)",
            HexToByte('02 2E 05 09 F2 03 85 03'):"(Guildleve)",
            HexToByte('02 2E 05 09 F2 03 87 03'):"(Quest)",
            HexToByte('02 2E 05 09 F2 03 88 03'):"(Client)",
            HexToByte('02 2E 05 09 F2 03 89 03'):"(Instance)",
            HexToByte('02 2E 05 09 F2 03 8A 03'):"(Gil)",
            HexToByte('02 2E 05 09 F2 03 8B 03'):"(Skill)",
            HexToByte('02 2E 05 09 F2 03 8C 03'):"(Primary Skill)",
            HexToByte('02 2E 05 09 F2 03 8D 03'):"(Primary Skill Rank)",
            HexToByte('02 2E 05 09 F2 03 8E 03'):"(Physical Level)",
            HexToByte('02 2E 05 09 F2 03 8F 03'):"(Skill Point)",
            HexToByte('02 2E 05 09 F2 03 90 03'):"(Experience Points)",
            HexToByte('02 2E 05 09 F2 03 91 03'):"(Affinity)",
            HexToByte('02 2E 05 09 F2 03 92 03'):"(Attribute)",
            HexToByte('02 2E 05 09 F2 03 93 03'):"(Elemental Resistance)",
            HexToByte('02 2E 05 09 F2 03 94 03'):"(Fire)",
            HexToByte('02 2E 05 09 F2 03 95 03'):"(Ice)",
            HexToByte('02 2E 05 09 F2 03 96 03'):"(Wind)",
            HexToByte('02 2E 05 09 F2 03 97 03'):"(Earth)",
            HexToByte('02 2E 05 09 F2 03 98 03'):"(Lightning)",
            HexToByte('02 2E 05 09 F2 03 99 03'):"(Water)",
            HexToByte('02 2E 05 09 F2 03 9A 03'):"(Astral)",
            HexToByte('02 2E 05 09 F2 03 9B 03'):"(Umbral)",
            HexToByte('02 2E 05 09 F2 03 9C 03'):"(Guardian)",
            HexToByte('02 2E 05 09 F2 03 9D 03'):"(Nameday)",
            HexToByte('02 2E 05 09 F2 03 9E 03'):"(Race)",
            HexToByte('02 2E 05 09 F2 03 9F 03'):"(Clan)",
            HexToByte('02 2E 05 09 F2 03 A0 03'):"(Gender)",
            HexToByte('02 2E 05 09 F2 03 A1 03'):"(Title)",
            HexToByte('02 2E 05 09 F2 03 A2 03'):"(Quality)",
            HexToByte('02 2E 05 09 F2 03 A3 03'):"(☆☆☆)",
            HexToByte('02 2E 05 09 F2 03 A4 03'):"(☆☆)",
            HexToByte('02 2E 05 09 F2 03 A5 03'):"(☆)",
            HexToByte('02 2E 05 09 F2 03 A6 03'):"(Durability)",
            HexToByte('02 2E 05 09 F2 03 AC 03'):"(To Repair)",
            HexToByte('02 2E 05 09 F2 03 AD 03'):"(Status Effect)",
            HexToByte('02 2E 05 09 F2 03 AE 03'):"(Cast Time)",
            HexToByte('02 2E 05 09 F2 03 AF 03'):"(Recast Time)",
            HexToByte('02 2E 05 09 F2 03 B0 03'):"(KO'd)",
            HexToByte('02 2E 05 09 F2 03 B1 03'):"(Craft)",
            HexToByte('02 2E 05 09 F2 03 B2 03'):"(Gathering)",
            HexToByte('02 2E 05 09 F2 03 B3 03'):"(Negotiate)",
            HexToByte('02 2E 05 09 F2 03 B4 03'):"(Guild Mark)",
            HexToByte('02 2E 05 09 F2 03 B5 03'):"(Mark)",
            HexToByte('02 2E 05 09 F2 03 B6 03'):"(Linkshell)",
            HexToByte('02 2E 05 09 F2 03 B7 03'):"(Linkpearl)",
            HexToByte('02 2E 05 09 F2 03 B8 03'):"(Active Mode)",
            HexToByte('02 2E 05 09 F2 03 B9 03'):"(Passive Mode)",
            HexToByte('02 2E 05 09 F2 03 BA 03'):"(Action)",
            HexToByte('02 2E 05 09 F2 03 BB 03'):"(Magic)",
            HexToByte('02 2E 05 09 F2 03 BC 03'):"(Weaponskill)",
            HexToByte('02 2E 05 09 F2 03 BD 03'):"(Ability)",
            HexToByte('02 2E 05 09 F2 03 BE 03'):"(Trait)",
            HexToByte('02 2E 05 09 F2 03 BF 03'):"(Gathering Actions)",
            HexToByte('02 2E 05 09 F2 03 C0 03'):"(Synthesis Actions)",
            HexToByte('02 2E 05 09 F2 03 C1 03'):"(Engage)",
            HexToByte('02 2E 05 09 F2 03 C2 03'):"(Disengage)",
            HexToByte('02 2E 05 09 F2 03 C3 03'):"(Incapacitated)",
            HexToByte('02 2E 05 09 F2 03 C4 03'):"(Battle Regimen)",
            HexToByte('02 2E 05 09 F2 03 C5 03'):"(Enmity)",
            HexToByte('02 2E 05 09 F2 03 C6 03'):"(Loot)",
            HexToByte('02 2E 05 09 F2 03 C7 03'):"(Enemy Sign)",
            HexToByte('02 2E 05 09 F2 03 C8 03'):"(Ally Sign)",
            HexToByte('02 2E 05 09 F2 03 C9 03'):"(Target)",            
            HexToByte('02 2E 05 09 F2 03 CA 03'):"((Gear) Affinity)",
            HexToByte('02 2E 05 09 F2 03 CB 03'):"(Rare)",
            HexToByte('02 2E 05 09 F2 03 CC 03'):"(Unique)",
            HexToByte('02 2E 05 09 F2 03 CD 03'):"(Party)",
            HexToByte('02 2E 05 09 F2 03 CE 03'):"(Map)",
            HexToByte('02 2E 05 09 F2 03 CF 03'):"(Log out)",
            HexToByte('02 2E 05 09 F2 03 D0 03'):"(Indent)",
            HexToByte('02 2E 05 09 F2 03 D1 03'):"(Pattern)",
            HexToByte('02 2E 05 09 F2 03 D2 03'):"(Retainer)",
            HexToByte('02 2E 05 09 F2 03 D3 03'):"(Chocobo)",
            HexToByte('02 2E 05 09 F2 03 D4 03'):"(Aetheryte)",
            HexToByte('02 2E 05 09 F2 03 D5 03'):"(Aetherial Gate)",
            HexToByte('02 2E 05 09 F2 03 D6 03'):"(Aetherial Node)",
            HexToByte('02 2E 05 09 F2 03 D7 03'):"(Trade)",
            HexToByte('02 2E 05 09 F2 03 D8 03'):"(Bazaar)",
            HexToByte('02 2E 05 09 F2 03 D9 03'):"(Repair)",
            HexToByte('02 2E 05 09 F2 03 DA 03'):"(Auto-translation Dictionary)",
            HexToByte('02 2E 05 09 F2 03 DB 03'):"(Teleport)",            
            HexToByte('02 2E 05 09 F2 03 DC 03'):"(Warp)",
            HexToByte('02 2E 05 09 F2 03 DD 03'):"(Guild Shop)",
            HexToByte('02 2E 05 09 F2 03 DE 03'):"(Hyur)",
            HexToByte('02 2E 05 09 F2 03 DF 03'):"(Elezen)",
            HexToByte('02 2E 05 09 F2 03 E0 03'):"(Lalafell)",
            HexToByte('02 2E 05 09 F2 03 E1 03'):"(Miqo'te)",
            HexToByte('02 2E 05 09 F2 03 E2 03'):"(Roegadyn)",
            HexToByte('02 2E 05 09 F2 03 E3 03'):"(Midlander)",
            HexToByte('02 2E 05 09 F2 03 E4 03'):"(Highlander)",
            HexToByte('02 2E 05 09 F2 03 E5 03'):"(Wildwood)",
            HexToByte('02 2E 05 09 F2 03 E6 03'):"(Duskwight)",
            HexToByte('02 2E 05 09 F2 03 E7 03'):"(Plainsfolk)",
            HexToByte('02 2E 05 09 F2 03 E8 03'):"(Dunesfolk)",
            HexToByte('02 2E 05 09 F2 03 E9 03'):"(Seeker of the Sun)",
            HexToByte('02 2E 05 09 F2 03 EA 03'):"(Keeper of the Moon)",
            HexToByte('02 2E 05 09 F2 03 EB 03'):"(Sea Wolf)",
            HexToByte('02 2E 05 09 F2 03 EC 03'):"(Hellsguard)",
            HexToByte('02 2E 05 09 F2 03 ED 03'):"(Diciples of War)",
            HexToByte('02 2E 05 09 F2 03 EE 03'):"(Disciples of Magic)",
            HexToByte('02 2E 05 09 F2 03 EF 03'):"(Disciples of the Land)",
            HexToByte('02 2E 05 09 F2 03 F0 03'):"(Disciples of the Hand)",
            HexToByte('02 2E 05 0A F2 04 B1 03'):"(/?)",
            HexToByte('02 2E 05 0A F2 04 B2 03'):"(/action)",
            HexToByte('02 2E 05 0A F2 04 B3 03'):"(/angry)",
            HexToByte('02 2E 05 0A F2 04 B4 03'):"(/areaofeffect)",
            HexToByte('02 2E 05 0A F2 04 B5 03'):"(/automove)",
            HexToByte('02 2E 05 0A F2 04 B6 03'):"(/away)",
            HexToByte('02 2E 05 0A F2 04 B7 03'):"(/battlemode)",
            HexToByte('02 2E 05 0A F2 04 B8 03'):"(/battleregimen)",
            HexToByte('02 2E 05 0A F2 04 B9 03'):"(/beckon)",
            HexToByte('02 2E 05 0A F2 04 BA 03'):"(/blacklist)",
            HexToByte('02 2E 05 0A F2 04 BB 03'):"(/blush)",
            HexToByte('02 2E 05 0A F2 04 BC 03'):"(/bow)",
            HexToByte('02 2E 05 0A F2 04 BE 03'):"(/chatmode)",
            HexToByte('02 2E 05 0A F2 04 BF 03'):"(/check)",
            HexToByte('02 2E 05 0A F2 04 C0 03'):"(/cheer)",
            HexToByte('02 2E 05 0A F2 04 C1 03'):"(/chuckle)",
            HexToByte('02 2E 05 0A F2 04 C2 03'):"(/clap)",
            HexToByte('02 2E 05 0A F2 04 C3 03'):"(/clock)",
            HexToByte('02 2E 05 0A F2 04 C4 03'):"(/comfort)",
            HexToByte('02 2E 05 0A F2 04 C6 03'):"(/congratulate)",
            HexToByte('02 2E 05 0A F2 04 C7 03'):"(/cry)",
            HexToByte('02 2E 05 0A F2 04 C8 03'):"(/dance)",
            HexToByte('02 2E 05 0A F2 04 C9 03'):"(/decline)",
            HexToByte('02 2E 05 0A F2 04 CA 03'):"(/deny)",
            HexToByte('02 2E 05 0A F2 04 CD 03'):"(/display)",
            HexToByte('02 2E 05 0A F2 04 CB 03'):"(/doubt)",
            HexToByte('02 2E 05 0A F2 04 CC 03'):"(/doze)",
            HexToByte('02 2E 05 0A F2 04 CE 03'):"(/dusteffect)",
            HexToByte('02 2E 05 0A F2 04 CF 03'):"(/echo)",
            HexToByte('02 2E 05 0A F2 04 D0 03'):"(/emote)",
            HexToByte('02 2E 05 0A F2 04 D1 03'):"(/equip)",
            HexToByte('02 2E 05 0A F2 04 D2 03'):"(/equipaction)",
            HexToByte('02 2E 05 0A F2 04 D3 03'):"(/examineself)",
            HexToByte('02 2E 05 0A F2 04 D4 03'):"(/extendeddraw)",
            HexToByte('02 2E 05 0A F2 04 D6 03'):"(/friendlist)",
            HexToByte('02 2E 05 0A F2 04 D7 03'):"(/fume)",
            HexToByte('02 2E 05 0A F2 04 D8 03'):"(/furious)",
            HexToByte('02 2E 05 0A F2 04 D9 03'):"(/goodbye)",
            HexToByte('02 2E 05 0A F2 04 DB 03'):"(/item)",
            HexToByte('02 2E 05 0A F2 04 DC 03'):"(/join)",
            HexToByte('02 2E 05 0A F2 04 DD 03'):"(/joy)",
            HexToByte('02 2E 05 0A F2 04 DE 03'):"(/kneel)",
            HexToByte('02 2E 05 0A F2 04 DF 03'):"(/laugh)",
            HexToByte('02 2E 05 0A F2 04 E0 03'):"(/linkshell)",
            HexToByte('02 2E 05 0A F2 04 E2 03'):"(/lockon)",
            HexToByte('02 2E 05 0A F2 04 E3 03'):"(/logout)",
            HexToByte('02 2E 05 0A F2 04 E4 03'):"(/lookout)",
            HexToByte('02 2E 05 0A F2 04 E5 03'):"(/loot)",   
            HexToByte('02 2E 05 0A F2 04 E7 03'):"(/map)",
            HexToByte('02 2E 05 0A F2 04 E8 03'):"(/marking)",
            HexToByte('02 2E 05 0A F2 04 E9 03'):"(/me)",
            HexToByte('02 2E 05 0A F2 04 EA 03'):"(/meh)",
            HexToByte('02 2E 05 0A F2 04 EB 03'):"(/names)",
            HexToByte('02 2E 05 0A F2 04 EC 03'):"(/no)",
            HexToByte('02 2E 05 0A F2 04 EE 03'):"(/panic)",
            HexToByte('02 2E 05 0A F2 04 EF 03'):"(/party)",
            HexToByte('02 2E 05 0A F2 04 F0 03'):"(/partycmd)",
            HexToByte('02 2E 05 0A F2 04 F1 03'):"(/physics)",
            HexToByte('02 2E 05 0A F2 04 F3 03'):"(/point)",
            HexToByte('02 2E 05 0A F2 04 F4 03'):"(/poke)",
            HexToByte('02 2E 05 0A F2 04 F5 03'):"(/profanity)",
            HexToByte('02 2E 05 0A F2 04 F6 03'):"(/psych)",
            HexToByte('02 2E 05 0A F2 04 F7 03'):"(/rally)",
            HexToByte('02 2E 05 0A F2 04 F8 03'):"(/recast)",
            HexToByte('02 2E 05 0A F2 04 F9 03'):"(/salute)",
            HexToByte('02 2E 05 0A F2 04 FA 03'):"(/say)",
            HexToByte('02 2E 05 0A F2 04 FB 03'):"(/scrollingbattletext)",
            HexToByte('02 2E 05 0A F2 04 FD 03'):"(/shadow)",
            HexToByte('02 2E 05 0A F2 04 FE 03'):"(/shocked)",
            HexToByte('02 2E 05 0A F2 04 FF 03'):"(/shout)",
            HexToByte('02 2E 04 0A F1 05 03'):"(/shrug)",
            HexToByte('02 2E 05 0A F2 05 01 03'):"(/sit)",
            HexToByte('02 2E 05 0A F2 05 02 03'):"(/soothe)",
            HexToByte('02 2E 05 0A F2 05 03 03'):"(/stagger)",
            HexToByte('02 2E 05 0A F2 05 04 03'):"(/stretch)",
            HexToByte('02 2E 05 0A F2 05 05 03'):"(/sulk)",
            HexToByte('02 2E 05 0A F2 05 06 03'):"(/supportdesk)",
            HexToByte('02 2E 05 0A F2 05 07 03'):"(/surprised)",
            HexToByte('02 2E 05 0A F2 05 09 03'):"(/targetnpc)",
            HexToByte('02 2E 05 0A F2 05 0A 03'):"(/targetpc)",
            HexToByte('02 2E 05 0A F2 05 0B 03'):"(/tell)",
            HexToByte('02 2E 05 0A F2 05 15 03'):"(/textclear)",
            HexToByte('02 2E 05 0A F2 05 0C 03'):"(/think)",            
            HexToByte('02 2E 05 0A F2 05 0D 03'):"(/thumbsup)",
            HexToByte('02 2E 05 0A F2 05 0E 03'):"(/upset)",
            HexToByte('02 2E 05 0A F2 05 10 03'):"(/wait)",
            HexToByte('02 2E 05 0A F2 05 11 03'):"(/wave)",
            HexToByte('02 2E 05 0A F2 05 12 03'):"(/welcome)",
            HexToByte('02 2E 05 0A F2 05 14 03'):"(/yes)",
            HexToByte('02 2E 05 0B F2 05 DD 03'):"(North)",
            HexToByte('02 2E 05 0B F2 05 DE 03'):"(South)",
            HexToByte('02 2E 05 0B F2 05 DF 03'):"(East)",
            HexToByte('02 2E 05 0B F2 05 E0 03'):"(West)",
            HexToByte('02 2E 05 0B F2 05 E1 03'):"(Up)",
            HexToByte('02 2E 05 0B F2 05 E2 03'):"(Down)",
            HexToByte('02 2E 05 0B F2 05 E3 03'):"(Right)",
            HexToByte('02 2E 05 0B F2 05 E4 03'):"(Left)",
            HexToByte('02 2E 05 0B F2 05 E5 03'):"(Surface)",
            HexToByte('02 2E 05 0B F2 05 E6 03'):"(Rear)",
            HexToByte('02 2E 05 0B F2 05 E7 03'):"(Side)",
            HexToByte('02 2E 05 0B F2 05 E8 03'):"(Front)",
            HexToByte('02 2E 05 0B F2 05 E9 03'):"(Middle)",
            HexToByte('02 2E 05 0B F2 05 EA 03'):"(Flank)",
            HexToByte('02 2E 05 0B F2 05 EB 03'):"(Inside)",
            HexToByte('02 2E 05 0B F2 05 EC 03'):"(Outside)",
            HexToByte('02 2E 05 0B F2 05 ED 03'):"(This way)",
            HexToByte('02 2E 05 0B F2 05 EE 03'):"(Over there)",
            HexToByte('02 2E 05 0B F2 05 EF 03'):"(That way)",
            HexToByte('02 2E 05 0C F2 06 41 03'):"(Day before yesterday)",
            HexToByte('02 2E 05 0C F2 06 42 03'):"(Yesterday)",
            HexToByte('02 2E 05 0C F2 06 43 03'):"(Today)",
            HexToByte('02 2E 05 0C F2 06 44 03'):"(Tomorrow)",
            HexToByte('02 2E 05 0C F2 06 45 03'):"(Day after tomorrow)",
            HexToByte('02 2E 05 0C F2 06 46 03'):"(Last week)",
            HexToByte('02 2E 05 0C F2 06 47 03'):"(This week)",
            HexToByte('02 2E 05 0C F2 06 48 03'):"(Next week)",
            HexToByte('02 2E 05 0C F2 06 49 03'):"(a.m.)",
            HexToByte('02 2E 05 0C F2 06 4A 03'):"(p.m.)",
            HexToByte('02 2E 05 0C F2 06 4B 03'):"(Morning)",
            HexToByte('02 2E 05 0C F2 06 4C 03'):"(Afternoon)",
            HexToByte('02 2E 05 0C F2 06 4D 03'):"(Night)",
            HexToByte('02 2E 05 0C F2 06 4E 03'):"(Day of the week)",
            HexToByte('02 2E 05 0C F2 06 4F 03'):"(Sunday)",
            HexToByte('02 2E 05 0C F2 06 50 03'):"(Monday)",
            HexToByte('02 2E 05 0C F2 06 51 03'):"(Tuesday)",
            HexToByte('02 2E 05 0C F2 06 52 03'):"(Wednesday)",
            HexToByte('02 2E 05 0C F2 06 53 03'):"(Thursday)",
            HexToByte('02 2E 05 0C F2 06 54 03'):"(Friday)",
            HexToByte('02 2E 05 0C F2 06 55 03'):"(Saturday)",
            HexToByte('02 2E 05 0C F2 06 56 03'):"(Holiday)",
            HexToByte('02 2E 05 0C F2 06 57 03'):"(Break)",
            HexToByte('02 2E 05 0C F2 06 5A 03'):"(Second)",
            HexToByte('02 2E 05 0C F2 06 58 03'):"(Long time)",
            HexToByte('02 2E 05 0C F2 06 59 03'):"(Short time)",
            HexToByte('02 2E 05 0C F2 06 5B 03'):"(Minute)",
            HexToByte('02 2E 05 0C F2 06 5C 03'):"(Hour)",
            HexToByte('02 2E 05 0C F2 06 5D 03'):"(Time remaining)",
            HexToByte('02 2E 05 0C F2 06 5E 03'):"(January)",
            HexToByte('02 2E 05 0C F2 06 5F 03'):"(February)",
            HexToByte('02 2E 05 0C F2 06 60 03'):"(March (Month))",
            HexToByte('02 2E 05 0C F2 06 61 03'):"(April)",
            HexToByte('02 2E 05 0C F2 06 62 03'):"(May)",
            HexToByte('02 2E 05 0C F2 06 63 03'):"(June)",
            HexToByte('02 2E 05 0C F2 06 64 03'):"(July)",
            HexToByte('02 2E 05 0C F2 06 65 03'):"(August)",
            HexToByte('02 2E 05 0C F2 06 66 03'):"(September)",
            HexToByte('02 2E 05 0C F2 06 67 03'):"(October)",
            HexToByte('02 2E 05 0C F2 06 68 03'):"(November)",
            HexToByte('02 2E 05 0C F2 06 69 03'):"(December)",
            HexToByte('02 2E 05 0D F2 06 A5 03'):"(Connection Speed)",
            HexToByte('02 2E 05 0D F2 06 A6 03'):"(Blacklist)",
            HexToByte('02 2E 05 0D F2 06 A7 03'):"(Friend List)",
            HexToByte('02 2E 05 0D F2 06 A8 03'):"(Config)",
            HexToByte('02 2E 05 0D F2 06 A9 03'):"(Connection)",
            HexToByte('02 2E 05 0D F2 06 AA 03'):"(Screenshot)",
            HexToByte('02 2E 05 0D F2 06 AB 03'):"(Patch)",
            HexToByte('02 2E 05 0D F2 06 AC 03'):"(Version)",
            HexToByte('02 2E 05 0D F2 06 AD 03'):"(Connection Lost)",
            HexToByte('02 2E 05 0D F2 06 AE 03'):"(Lag)",
            HexToByte('02 2E 05 0D F2 06 AF 03'):"(Filter)",
            HexToByte('02 2E 05 0D F2 06 B0 03'):"(Client)",
            HexToByte('02 2E 05 0D F2 06 B1 03'):"(Backup)",
            HexToByte('02 2E 05 0D F2 06 B3 03'):"(Save)",
            HexToByte('02 2E 05 0D F2 06 B4 03'):"(TV)",
            HexToByte('02 2E 05 0D F2 06 B5 03'):"(Modem)",
            HexToByte('02 2E 05 0D F2 06 B6 03'):"(Monitor)",
            HexToByte('02 2E 05 0D F2 06 B7 03'):"(Log off)",
            HexToByte('02 2E 05 0D F2 06 B8 03'):"(Log on)",
            HexToByte('02 2E 05 0D F2 06 B9 03'):"(Hard Disk)",
            HexToByte('02 2E 05 0D F2 06 BA 03'):"(Server)",
            HexToByte('02 2E 05 0D F2 06 BB 03'):"(Macro)",
            HexToByte('02 2E 05 0E F2 07 09 03'):"(Online)",
            HexToByte('02 2E 05 0E F2 07 0A 03'):"(Away)",
            HexToByte('02 2E 05 0F F2 07 6D 03'):"(Numeric keypad)",
            HexToByte('02 2E 05 0F F2 07 6E 03'):"(Arrow keys)",
            HexToByte('02 2E 05 0F F2 07 6F 03'):"(Tab key)",
            HexToByte('02 2E 05 0F F2 07 70 03'):"(Enter key)",
            HexToByte('02 2E 05 0F F2 07 71 03'):"(End key)",
            HexToByte('02 2E 05 0F F2 07 72 03'):"(Num Lock key)",
            HexToByte('02 2E 05 0F F2 07 73 03'):"(Function keys)",
            HexToByte('02 2E 05 0F F2 07 74 03'):"(Spacebar)",
            HexToByte('02 2E 05 0F F2 07 75 03'):"(Backspace key)",
            HexToByte('02 2E 05 0F F2 07 76 03'):"(Halfwidth/Fullwidth key)",
            HexToByte('02 2E 05 0F F2 07 77 03'):"(Alt key)",
            HexToByte('02 2E 05 0F F2 07 78 03'):"(Insert key)",
            HexToByte('02 2E 05 0F F2 07 79 03'):"(Page Down key)",
            HexToByte('02 2E 05 0F F2 07 7A 03'):"(Home key)",
            HexToByte('02 2E 05 0F F2 07 7B 03'):"(Page Up key)",
            HexToByte('02 2E 05 0F F2 07 7C 03'):"(Caps Lock key)",
            HexToByte('02 2E 05 0F F2 07 7D 03'):"(Shift key)",
            HexToByte('02 2E 05 0F F2 07 7E 03'):"(Esc key)",
            HexToByte('02 2E 05 0F F2 07 7F 03'):"(Ctrl key)",
            HexToByte('02 2E 05 0F F2 07 80 03'):"(Delete key)",            
            HexToByte('02 2E 05 10 F2 07 D1 03'):"(notice)",
            HexToByte('02 2E 05 10 F2 07 D2 03'):"(place)",
            HexToByte('02 2E 05 10 F2 07 D3 03'):"(meat)",
            HexToByte('02 2E 05 10 F2 07 D4 03'):"(train)",
            HexToByte('02 2E 05 10 F2 07 D5 03'):"(last)",
            HexToByte('02 2E 05 10 F2 07 D7 03'):"(question)",
            HexToByte('02 2E 05 10 F2 07 D6 03'):"(death)",
            HexToByte('02 2E 05 10 F2 07 D8 03'):"(joy)",
            HexToByte('02 2E 05 10 F2 07 D9 03'):"(mistake)",
            HexToByte('02 2E 05 10 F2 07 DA 03'):"(purpose)",
            HexToByte('02 2E 05 10 F2 07 DB 03'):"(half)",
            HexToByte('02 2E 05 10 F2 07 DC 03'):"(date)",
            HexToByte('02 2E 05 10 F2 07 DD 03'):"(secret)",
            HexToByte('02 2E 05 10 F2 07 DE 03'):"(position)",
            HexToByte('02 2E 05 10 F2 07 DF 03'):"(lie)",
            HexToByte('02 2E 05 10 F2 07 E0 03'):"(excitement)",
            HexToByte('02 2E 05 10 F2 07 E1 03'):"(money)",
            HexToByte('02 2E 05 10 F2 07 E2 03'):"(fear)",
            HexToByte('02 2E 05 10 F2 07 E3 03'):"(friend)",
            HexToByte('02 2E 05 10 F2 07 E4 03'):"(entrance)",
            HexToByte('02 2E 05 10 F2 07 E5 03'):"(exit)",
            HexToByte('02 2E 05 10 F2 07 E6 03'):"(mine)",
            HexToByte('02 2E 05 10 F2 07 E7 03'):"(fun)",
            HexToByte('02 2E 05 10 F2 07 E8 03'):"(I)",
            HexToByte('02 2E 05 10 F2 07 E9 03'):"(you)",            
            HexToByte('02 2E 03 11 02 03'):"(Halone, the Fury)",
            HexToByte('02 2E 03 11 03 03'):"(Menphina, the Lover)",
            HexToByte('02 2E 03 11 04 03'):"(Thaliak, the Scholar)",
            HexToByte('02 2E 03 11 05 03'):"(Nymeia, the Spinner)",
            HexToByte('02 2E 03 11 06 03'):"(Llymlaen, the Navigator)",
            HexToByte('02 2E 03 11 07 03'):"(Oschon, the Wanderer)",
            HexToByte('02 2E 03 11 08 03'):"(Byregot, the Builder)",
            HexToByte('02 2E 03 11 09 03'):"(Rhalgr, the Destroyer)",
            HexToByte('02 2E 03 11 0A 03'):"(Azeyma, the Warden)",
            HexToByte('02 2E 03 11 0B 03'):"(Nald'thal, the Traders)",
            HexToByte('02 2E 03 11 0C 03'):"(Nophica, the Matron)",
            HexToByte('02 2E 03 11 0D 03'):"(Althyk, the Keeper)",
            HexToByte('02 2E 03 12 02 03'):"(Main hand)",
            HexToByte('02 2E 03 12 03 03'):"(Off Hand)",
            HexToByte('02 2E 03 12 06 03'):"(Throwing Weapon)",
            HexToByte('02 2E 03 12 07 03'):"(Pack)",
            HexToByte('02 2E 03 12 08 03'):"(Pouch)",
            HexToByte('02 2E 03 12 0A 03'):"(Head)",
            HexToByte('02 2E 03 12 0B 03'):"(Undershirt)",
            HexToByte('02 2E 03 12 0C 03'):"(Body)",
            HexToByte('02 2E 03 12 0D 03'):"(Undergarment)",
            HexToByte('02 2E 03 12 0E 03'):"(Legs)",
            HexToByte('02 2E 03 12 0F 03'):"(Hands)",
            HexToByte('02 2E 03 12 10 03'):"(Feet)",
            HexToByte('02 2E 03 12 11 03'):"(Waist)",
            HexToByte('02 2E 03 12 12 03'):"(Neck)",
            HexToByte('02 2E 03 12 13 03'):"(Right Ear)",
            HexToByte('02 2E 03 12 14 03'):"(Left Ear)",
            HexToByte('02 2E 03 12 15 03'):"(Right Wrist)",
            HexToByte('02 2E 03 12 16 03'):"(Left Wrist)",
            HexToByte('02 2E 03 12 17 03'):"(Right Index Finger)",
            HexToByte('02 2E 03 12 18 03'):"(Left Index Finger)",
            HexToByte('02 2E 03 12 19 03'):"(Right Ring Finger)",
            HexToByte('02 2E 03 12 20 03'):"(Left Right Finger)", # may be buggy
            HexToByte('02 2E 03 12'):"(Left Right Finger)", # may be buggy
            HexToByte('02 2E 03 13 03 03'):"(Hand-to-Hand)",
            HexToByte('02 2E 03 13 04 03'):"(Sword)",
            HexToByte('02 2E 03 13 05 03'):"(Axe)",
            HexToByte('02 2E 03 13 08 03'):"(Archery)",
            HexToByte('02 2E 03 13 09 03'):"(Polearm)",
            HexToByte('02 2E 03 13 0B 03'):"(Shield)",
            HexToByte('02 2E 03 13 17 03'):"(Thaumaturgy)",
            HexToByte('02 2E 03 13 18 03'):"(Conjury)",
            HexToByte('02 2E 03 13 1E 03'):"(Woodworking)",
            HexToByte('02 2E 03 13 1F 03'):"(Smithing)",
            HexToByte('02 2E 03 13 20 03'):"(Armorcraft)",
            HexToByte('02 2E 03 13 21 03'):"(Goldsmithing)",
            HexToByte('02 2E 03 13 22 03'):"(Leatherworking)",
            HexToByte('02 2E 03 13 23 03'):"(Clothcraft)",
            HexToByte('02 2E 03 13 24 03'):"(Alchemy)",
            HexToByte('02 2E 03 13 25 03'):"(Cooking)",
            HexToByte('02 2E 03 13 28 03'):"(Mining)",
            HexToByte('02 2E 03 13 29 03'):"(Botany)",
            HexToByte('02 2E 03 13 2A 03'):"(Fishing)",
            HexToByte('02 2E 03 14 03 03'):"(Pugilist)",
            HexToByte('02 2E 03 14 04 03'):"(Gladiator)",
            HexToByte('02 2E 03 14 05 03'):"(Marauder)",
            HexToByte('02 2E 03 14 08 03'):"(Archer)",
            HexToByte('02 2E 03 14 09 03'):"(Lancer)",
            HexToByte('02 2E 03 14 17 03'):"(Thaumaturge)",
            HexToByte('02 2E 03 14 18 03'):"(Conjurer)",
            HexToByte('02 2E 03 14 1E 03'):"(Carpenter)",
            HexToByte('02 2E 03 14 1F 03'):"(Blacksmith)",
            HexToByte('02 2E 03 14 20 03'):"(Armorer)",
            HexToByte('02 2E 03 14 21 03'):"(Goldsmith)",
            HexToByte('02 2E 03 14 22 03'):"(Leatherworker)",
            HexToByte('02 2E 03 14 23 03'):"(Weaver)",
            HexToByte('02 2E 03 14 24 03'):"(Alchemist)",
            HexToByte('02 2E 03 14 25 03'):"(Culinarian)",
            HexToByte('02 2E 03 14 28 03'):"(Miner)",
            HexToByte('02 2E 03 14 29 03'):"(Botanist)",
            HexToByte('02 2E 03 14 2A 03'):"(Fisher)",            
            }

    def monsterIsNM(self, monster):
        NMList = ['alux', 'bardi', 'barometz', 'bloodthirsty wolf', 'bomb baron', 'daddy longlegs', 'dodore', 'downy dunstan', 'elder mosshorn', 'escaped goobbue', 'frenzied aurelia', 'gluttonous gertrude', 'great buffalo', 'haughtpox bloatbelly', 'jackanapes', 'mosshorn billygoat', 'mosshorn nannygoat', 'nest commander', 'pyrausta', 'queen bolete', 'scurrying spriggan', 'sirocco', 'slippery sykes', 'uraeus']
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
            print "Completed Recipe for %s as %s\nTotal Progress: %i\nFinal Quality Added: %i\nFinal Durability Lost: %i\nIngredients Used: %s\nExp: %i\nSkill Points: %i\nDate Time: %s GMT\n" % (currentcrafting["item"], currentcrafting["class"], totalprogress, finalquality, finaldurability, itemsused, currentcrafting["exp"], currentcrafting["skillpoints"], currentcrafting["datetime"])
        else:
            print "Failed Recipe as %s\nTotal Progress: %i\nFinal Quality Added: %i\nFinal Durability Lost: %i\nIngredients Used: %s\nExp: %i\nSkill Points: %i\nDate Time: %s GMT\n" % (currentcrafting["class"], totalprogress, finalquality, finaldurability, itemsused, currentcrafting["exp"], currentcrafting["skillpoints"], currentcrafting["datetime"])
        self.craftingdata.append(currentcrafting)
        #raw_input("")
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
            print "Defeated %s as %s\nHit %%: %i%%\nTotal Damage: %i\nTotal Avg Dmg: %i\nCrit Avg Dmg: %i\nReg Avg Dmg: %i\nTotal Hit Dmg Avg: %i\nCrit Hit Dmg Avg: %i\nHit Dmg Avg: %i\nTotal Dmg From Others: %i\nHealing Avg: %i\nAbsorb Avg: %i\nExp: %i\nSkill Points: %i\nDate Time: %s GMT\n" % (currentmonster["monster"], currentmonster["class"], hitpercent, totaldamage, totaldmgavg, criticaldmgavg, regulardmgavg, totalhitdmgavg, crithitdmgavg, hitdmgavg, othertotaldmg, healingavg, absorbavg, currentmonster["exp"], currentmonster["skillpoints"], currentmonster["datetime"])
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
        if self.craftingcomplete == 1:
            #print logitem
            self.printCrafting(self.currentcrafting)
            self.currentcrafting = copy.deepcopy(self.defaultcrafting)
            self.currentcrafting["datetime"] = time.strftime("%m/%d/%y %H:%M:%S",time.gmtime(self.logfiletime))
            #print self.currentcrafting["datetime"]
            self.craftingcomplete = 0
        if logitem.find("You cannot change classes") != -1 or logitem.find("Levequest difficulty") != -1:
            return
        self.defeated = False
        self.spset = False
        self.expset = False
        self.currentmonster = copy.deepcopy(self.defaultmonster)

        self.currentmonster["datetime"] = time.strftime("%m/%d/%y %H:%M:%S",time.gmtime(self.logfiletime))
        self.currentmonster["monster"] = logitem[logitem.find("The ") +4:logitem.find(" is")]
        self.currentmonster["monster"] = self.currentmonster["monster"].split('\'')[0]
        
    def parse_gathering(self, code, logitem):
        self.echo("othergathering " + logitem, 1)

    def parse_othergathering(self, code, logitem):
        self.echo("othergathering " + logitem, 1)

    def parse_leve(self, code, logitem):
        self.echo("leve " + logitem, 1)

    def parse_chatmessage(self, code, logitem):
        #tabkey = '02 2E 05 0F F2 07 6F 03'
        self.echo("chatmessage " + code + logitem, 1)
        if (code == '1B') or (code == '19'):
            user = ' '.join(logitem.split(' ')[0:2]).strip()
            message = logitem.strip()
        else:
            logitemparts = logitem.split(":")
            user = logitemparts[0].strip()
            message = unicode(":".join(logitemparts[1:]).strip())
        try:
            if message.find(self.autotranslateheader) != -1:
                # found an auto translate
                '''
                if message.startswith("lang"):
                    msgparts = message.split(" ")
                    containsit = False
                    for text, value in self.autotranslate.items():
                        if message.find(text) != -1:
                            containsit = True
                            break
                    if not containsit:
                        #pass
                        self.echo(ByteToHex(message), 0)
                        self.echo("HexToByte('" + ByteToHex(msgparts[1]) + "'):" + "\"(" + " ".join(msgparts[2:]) + ")\",", 0)
                '''
                hasreplacement = False
                for text, value in self.autotranslate.items():
                    if message.find(unicode(text)) != -1:
                        hasreplacement = True
                        message = message.replace(text, value)
                if not hasreplacement:
                    # Save this up to the server so we can investigate later and add it.
                    pass
                #self.chatviewer.WriteLinkshell(user, message)
            chatdate = time.strftime("%d-%m-%y %H-%M-%S",time.gmtime(self.logfiletime))
            #if self.prevchatdate != chatdate:
            #    if self.prevchatdate != None:
            #        if not os.path.exists('chatlogs'):
            #            os.mkdir('chatlogs')
            #        with open(os.path.join('chatlogs', self.prevchatdate, '.chat'), 'wb') as chatfile:
            #            pickle.dump(self.chatlog, chatfile)
            #        self.chatlog = []
            self.prevchatdate = chatdate 
            self.chatlog.append((code, nullstrip(user), message))
            #self.alllog.append((code, nullstrip(user), message))
            '''
            '01': self.parse_chatmessage, # say
            '02': self.parse_chatmessage, # shout
            '03': self.parse_chatmessage, # sending tell
            '04': self.parse_chatmessage, # party
            '05': self.parse_chatmessage, # linkshell
            '06': self.parse_chatmessage, # linkshell
            '07': self.parse_chatmessage, # linkshell
            '10': self.parse_chatmessage, # say messages by others?
            '0D': self.parse_chatmessage, # get tell
            '0F': self.parse_chatmessage, # linkshell
            '0E': self.parse_chatmessage, # linkshell
            '0F': self.parse_chatmessage, # linkshell
            '19': self.parse_chatmessage, # other emote
            '1B': self.parse_chatmessage, # emote
            '''
            self.echo("Code: %s User: %s Message: %s" % (code, user, message), 1)
            #raw_input("tab")
        except:
            traceback.print_exc(file=sys.stdout)

    def parse_npcchat(self, code, logitem):
        self.echo("npc chat " + logitem, 1)

    def parse_invalidcommand(self, code, logitem):
        self.echo("invalid command " + logitem, 1)

    def parse_monstereffect(self, code, logitem):
        self.echo("other abilities " + logitem, 1)

    def parse_othereffect(self, code, logitem):
        if logitem.find("grants you") != -1:    
            effect = logitem[logitem.find("effect of ") +10:-1]
        self.echo("other abilities " + logitem, 1)

    def parse_partyabilities(self, code, logitem):
        if logitem.find("grants") != -1:
            effect = logitem[logitem.find("effect of ") +10:-1]
        if logitem.find("inflicts") != -1:
            monsteraffliction = logitem[logitem.find("effect of ") +10:-1]
        self.echo("other abilities " + logitem, 1)

    def parse_otherabilities(self, code, logitem):
        self.echo("other abilities " + logitem, 1)

    def parse_readyability(self, code, logitem):
        self.echo("ready ability " + logitem, 1)

    def parse_servermessage(self, code, logitem):
        self.echo("server message " + logitem, 1)

    def parse_invoke(self, code, logitem):
        self.echo("invoke " + logitem, 1)

    def parse_inflicts(self, code, logitem):
        if logitem.find("inflicts you") != -1:
            affliction = logitem[logitem.find("effect of ") +10:-1]
            return
        if logitem.find("inflicts") != -1:
            othersaffliction = logitem[logitem.find("effect of ") +10:-1]            
        self.echo("inflicts " + logitem, 1)

    def parse_effect(self, code, logitem):
        self.echo("effect " + logitem, 1)

    def parse_otherrecover(self, code, logitem):
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
        self.echo("monstermiss " + logitem, 1)

    def parse_othermiss(self, code, logitem):
        if logitem.find("KO'd target") != -1 or logitem.find("too far away") != -1 or logitem.find("guard fails.") != -1 or logitem.find("fails to take effect.") != -1:
            return
        if logitem.find("evades") != -1:
            monster = logitem[logitem.find("The ") + 4:logitem.find(" evades")]
            if monster == self.currentmonster["monster"]:
                misschar = logitem[logitem.find("evades") + 7:logitem.find("'s ")]
                attacktype = logitem[logitem.find("'s ") + 3:logitem.find(".")]
                self.currentmonster["othermiss"].append([misschar, attacktype])
        else:
            if logitem.find("from the") != -1:
                monster = logitem[logitem.find("the ") +4:logitem.find(" from the")].split('\'')[0]
            else:
                monster = logitem[logitem.find("the ") +4:logitem.find(".")].split('\'')[0]
            if monster == self.currentmonster["monster"]:
                misschar = logitem[: logitem.find("'s ")]
                attacktype = logitem[logitem.find("'s ") + 3:logitem.find(" misses")]
                self.currentmonster["othermiss"].append([misschar, attacktype])

        self.echo("othermiss " + logitem, 1)

    def parse_miss(self, code, logitem):
        monster = logitem[logitem.find("the ") +4:logitem.find(".")].split('\'')[0]
        if monster == self.currentmonster["monster"]:
            self.currentmonster["miss"] += 1
        self.echo("miss " + logitem, 1)

    def parse_otherhitdamage(self, code, logitem):
        if logitem.find("hits ") != -1:
            if logitem.find("points") == -1:
                return
            monsterhit = logitem[logitem.find("The ") +4:logitem.find(" hits")]
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
        if logitem.find("from the ") != -1:
            monster = logitem[logitem.find("the ") +4:logitem.find(" from the")]
        else:
            monster = logitem[logitem.find("the ") +4:logitem.find(" for")]
        if monster == self.currentmonster["monster"]:                        
            if logitem.find("Critical!") != -1:
                critical = 1
            else:
                critical = 0
            attackchar = ""
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
        if logitem.find("hits you") != -1:
            if logitem.find("points") == -1:
                return
            monsterhit = logitem[logitem.find("The ") +4:logitem.find(" hits")]
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
        if logitem.find("your") != -1 or logitem.find("Your") != -1:
            if logitem.find("from the ") != -1:
                monster = logitem[logitem.find("the ") +4:logitem.find(" from the")]
            else:
                monster = logitem[logitem.find("the ") +4:logitem.find(" for")]
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
        # Crafting success
        if logitem.find("You create") != -1:
            #print "Crafting Success: " + logitem
            if logitem.find(" of ") != -1:
                self.currentcrafting["item"] = logitem[logitem.find(" of ")+4:-1]
            else:
                self.currentcrafting["item"] = logitem[logitem.find(" a ")+3:-1]
            self.currentcrafting["success"] = 1
            self.craftingcomplete = 1
        # botched it
        if logitem.find("You botch") != -1:
            #print "Crafting Fail: " + logitem
            self.currentcrafting["success"] = 0
            self.craftingcomplete = 1
        
        self.echo("crafting success " + logitem, 1)

    def parse_defeated(self, code, logitem):
        if self.craftingcomplete == 1:
            #print "Defeated:" + logitem
            self.printCrafting(self.currentcrafting)
            self.currentcrafting = copy.deepcopy(self.defaultcrafting)
            self.currentcrafting["datetime"] = time.strftime("%m/%d/%y %H:%M:%S",time.gmtime(self.logfiletime))
            #print self.currentcrafting["datetime"]
            self.craftingcomplete = 0
        if logitem.find("group") != -1:
            return
        if logitem.find("defeats you") != -1:
            # You were killed...
            self.deathsdata["deaths"].append({"datetime":time.strftime("%m/%d/%y %H:%M:%S",time.gmtime(self.logfiletime)), "class":self.currentmonster["class"]})
            #self.characterdata["deaths"].append({"datetime":time.strftime("%m/%d/%y %H:%M:%S",time.gmtime(self.logfiletime)), "class":self.currentmonster["class"]})
            #0045::The fat dodo defeats you.
            return
        if logitem.find("defeat") != -1:
            monster = logitem[logitem.find("The ") +4:logitem.find(" is defeat")].split('\'')[0]
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

        self.echo("defeated " + logitem, 1)

    def parse_spexpgain(self, code, logitem):
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
    
    def __init__(self): 
        ffxiv_parser.__init__(self, "jp")
        self.craftingcomplete = 0
        self.autotranslateheader = HexToByte('02 2E')
        #TODO: Move this to a bin file later to avoid the hextobyte and crap in the source.
        self.autotranslate = {        
            HexToByte('02 2E 03 01 66 03'):"(Please use the auto-translate function.)",
            HexToByte('02 2E 03 01 67 03'):"(Japanese)",
            HexToByte('02 2E 03 01 68 03'):"(English)",
            HexToByte('02 2E 03 01 69 03'):"(French)",
            HexToByte('02 2E 03 01 6A 03'):"(German)",
            HexToByte('02 2E 03 01 6B 03'):"(Can you speak Japanese?)",
            HexToByte('02 2E 03 01 6C 03'):"(Can you speak English?)",
            HexToByte('02 2E 03 01 6D 03'):"(Can you speak French?)",
            HexToByte('02 2E 03 01 6E 03'):"(Can you speak German?)",
            HexToByte('02 2E 03 01 6F 03'):"(I don't speak any English.)",
            HexToByte('02 2E 03 01 70 03'):"(I don't speak any Japanese.)",
            HexToByte('02 2E 03 01 71 03'):"(I don't speak any French.)",
            HexToByte('02 2E 03 01 72 03'):"(I don't speak any German.)",
            HexToByte('02 2E 03 01 73 03'):"(Please listen.)",
            HexToByte('02 2E 03 01 74 03'):"(Can you hear me?)",
            HexToByte('02 2E 03 01 75 03'):"(I can speak a little.)",
            HexToByte('02 2E 03 01 76 03'):"(I can understand a little.)",
            HexToByte('02 2E 03 01 77 03'):"(Please use simple words.)",
            HexToByte('02 2E 03 01 78 03'):"(Please do not abbreviate your words.)",
            HexToByte('02 2E 03 01 79 03'):"(I need some time to put together my answer.)",
            HexToByte('02 2E 03 02 CA 03'):"(Nice to meet you.)",
            HexToByte('02 2E 03 02 CB 03'):"(Good morning!)",
            HexToByte('02 2E 03 02 CC 03'):"(Hello!)",
            HexToByte('02 2E 03 02 CD 03'):"(Good evening!)",
            HexToByte('02 2E 03 02 CE 03'):"(Good night!)",
            HexToByte('02 2E 03 02 CF 03'):"(Goodbye.)",
            HexToByte('02 2E 04 02 F0 CF 03'):"(I had fun today!)",
            HexToByte('02 2E 04 02 F0 D0 03'):"(See you again!)",
            HexToByte('02 2E 04 02 F0 D1 03'):"(Let's play together again sometime!)",
            HexToByte('02 2E 04 02 F0 D2 03'):"(I'm back!)",
            HexToByte('02 2E 04 02 F0 D3 03'):"(Welcome back.)",
            HexToByte('02 2E 04 02 F0 D4 03'):"(Congratulations!)",
            HexToByte('02 2E 04 02 F0 D5 03'):"(Good job!)",
            HexToByte('02 2E 04 02 F0 D6 03'):"(Good luck!)",
            HexToByte('02 2E 04 02 F0 D7 03'):"(All right!)",
            HexToByte('02 2E 04 02 F0 D8 03'):"(Thank you.)",
            HexToByte('02 2E 04 02 F0 D9 03'):"(You're welcome.)",
            HexToByte('02 2E 04 02 F0 DA 03'):"(Take care.)",
            HexToByte('02 2E 04 02 F0 DB 03'):"(I'm sorry.)",
            HexToByte('02 2E 04 02 F0 DC 03'):"(Please forgive me.)",
            HexToByte('02 2E 04 02 F0 DD 03'):"(That's too bad.)",
            HexToByte('02 2E 04 02 F0 DE 03'):"(Excuse me...)",
            HexToByte('02 2E 05 03 F2 01 2D 03'):"(Who?)",
            HexToByte('02 2E 05 03 F2 01 2E 03'):"(Which?)",
            HexToByte('02 2E 05 03 F2 01 2F 03'):"(How?)",
            HexToByte('02 2E 05 03 F2 01 30 03'):"(What?)",
            HexToByte('02 2E 05 03 F2 01 31 03'):"(When?)",
            HexToByte('02 2E 05 03 F2 01 32 03'):"(How many?)",
            HexToByte('02 2E 05 03 F2 01 33 03'):"(Where?)",
            HexToByte('02 2E 05 03 F2 01 34 03'):"(Where shall we go?)",
            HexToByte('02 2E 05 03 F2 01 35 03'):"(Which guildleve shall we do?)",
            HexToByte('02 2E 05 03 F2 01 37 03'):"(Do you have it?)",
            HexToByte('02 2E 05 03 F2 01 38 03'):"(What weapons can you use?)",
            HexToByte('02 2E 05 03 F2 01 39 03'):"(What guildleves do you have?)",
            HexToByte('02 2E 05 03 F2 01 3B 03'):"(Can you do it?)",
            HexToByte('02 2E 05 03 F2 01 3C 03'):"(What other classes can you use?)",
            HexToByte('02 2E 05 03 F2 01 3D 03'):"(Do you have it set?)",
            HexToByte('02 2E 05 03 F2 01 3E 03'):"(What's the battle plan?)",
            HexToByte('02 2E 05 03 F2 01 3F 03'):"(What's the Battle Regimen order?)",
            HexToByte('02 2E 05 03 F2 01 40 03'):"(Can I add you to my friend list?)",
            HexToByte('02 2E 05 03 F2 01 41 03'):"(Shall we take a break?)",
            HexToByte('02 2E 05 03 F2 01 42 03'):"(Do you want me to repair it?)",
            HexToByte('02 2E 05 03 F2 01 43 03'):"(Do you need any help?)",
            HexToByte('02 2E 05 04 F2 01 91 03'):"(I don't understand.)",
            HexToByte('02 2E 05 04 F2 01 92 03'):"(No thanks.)",
            HexToByte('02 2E 05 04 F2 01 93 03'):"(Yes, please.)",
            HexToByte('02 2E 05 04 F2 01 94 03'):"(If you would be so kind.)",
            HexToByte('02 2E 05 04 F2 01 95 03'):"(Understood.)",
            HexToByte('02 2E 05 04 F2 01 96 03'):"(I'm sorry. I'm busy now.)",
            HexToByte('02 2E 05 04 F2 01 97 03'):"(I'm playing solo right now.)",
            HexToByte('02 2E 05 04 F2 01 98 03'):"(I don't know how ot answer that question.)",
            HexToByte('02 2E 05 04 F2 01 99 03'):"(I see.)",
            HexToByte('02 2E 05 04 F2 01 9A 03'):"(Thanks for the offer, but I'll have to pass.)",
            HexToByte('02 2E 05 04 F2 01 9B 03'):"(That's interesting.)",
            HexToByte('02 2E 05 04 F2 01 9C 03'):"(Um...)",
            HexToByte('02 2E 05 04 F2 01 9D 03'):"(Huh!?)",
            HexToByte('02 2E 05 04 F2 01 9E 03'):"(Really?)",
            HexToByte('02 2E 05 04 F2 01 9F 03'):"(Hmmm.)",
            HexToByte('02 2E 05 04 F2 01 A0 03'):"(I have to go soon.)",  
            HexToByte('02 2E 05 05 F2 01 F5 03'):"(Casting spell.)",
            HexToByte('02 2E 05 05 F2 01 F6 03'):"(Time for work!)",
            HexToByte('02 2E 05 05 F2 01 F7 03'):"(I have plans.)",
            HexToByte('02 2E 05 05 F2 01 F8 03'):"(I'm sleepy.)",
            HexToByte('02 2E 05 05 F2 01 F9 03'):"(I'm tired.)",
            HexToByte('02 2E 05 05 F2 01 FA 03'):"(Have stuff to do, gotta go!)",
            HexToByte('02 2E 05 05 F2 01 FB 03'):"(I don't feel well.)",
            HexToByte('02 2E 05 05 F2 01 FC 03'):"(I'm not up for it.)",
            HexToByte('02 2E 05 05 F2 01 FD 03'):"(I'm interested.)",
            HexToByte('02 2E 05 05 F2 01 FE 03'):"(Fighting right now!)",
            HexToByte('02 2E 05 05 F2 01 FF 03'):"(I want to make money.)",
            HexToByte('02 2E 04 05 F1 02 03'):"(I don't remember.)",
            HexToByte('02 2E 05 05 F2 02 01 03'):"(I don't know.)",
            HexToByte('02 2E 05 05 F2 02 02 03'):"(Just used it.)",
            HexToByte('02 2E 05 05 F2 02 03 03'):"(I want experience points.)",
            HexToByte('02 2E 05 05 F2 02 04 03'):"(I want skill points.)",
            HexToByte('02 2E 05 06 F2 02 59 03'):"(Can I have it?)",
            HexToByte('02 2E 05 06 F2 02 5A 03'):"(Can you do it for me?)",
            HexToByte('02 2E 05 06 F2 02 5B 03'):"(Lower the price?)",
            HexToByte('02 2E 05 06 F2 02 5C 03'):"(Buy?)",
            HexToByte('02 2E 05 06 F2 02 5D 03'):"(Sell?)",
            HexToByte('02 2E 05 06 F2 02 5E 03'):"(Trade?)",
            HexToByte('02 2E 05 06 F2 02 5F 03'):"(Do you need it?)",
            HexToByte('02 2E 05 06 F2 02 60 03'):"(Can you make it?)",
            HexToByte('02 2E 05 06 F2 02 61 03'):"(Do you have it?)",
            HexToByte('02 2E 05 06 F2 02 62 03'):"(Can you repair it?)",
            HexToByte('02 2E 05 06 F2 02 63 03'):"(What materials are needed?)",
            HexToByte('02 2E 05 06 F2 02 64 03'):"(No money!)",
            HexToByte('02 2E 05 06 F2 02 65 03'):"(I don't have anything to give you.)",
            HexToByte('02 2E 05 06 F2 02 66 03'):"(You can have this.)",
            HexToByte('02 2E 05 06 F2 02 67 03'):"(Please.)",
            HexToByte('02 2E 05 06 F2 02 68 03'):"(Reward:)",
            HexToByte('02 2E 05 06 F2 02 69 03'):"(Price:)", 
            HexToByte('02 2E 05 07 F2 02 BD 03'):"(Looking for members.)",
            HexToByte('02 2E 05 07 F2 02 BE 03'):"(Gather together.)",
            HexToByte('02 2E 05 07 F2 02 BF 03'):"(Team up?)",
            HexToByte('02 2E 05 07 F2 02 C0 03'):"(Are you alone?)",
            HexToByte('02 2E 05 07 F2 02 C1 03'):"(Any vacancies?)",
            HexToByte('02 2E 05 07 F2 02 C2 03'):"(Please invite me.)",
            HexToByte('02 2E 05 07 F2 02 C3 03'):"(Please let me join.)",
            HexToByte('02 2E 05 07 F2 02 C4 03'):"(Who is the leader?)",
            HexToByte('02 2E 05 07 F2 02 C5 03'):"(Just for a short time is fine.)",
            HexToByte('02 2E 05 07 F2 02 C6 03'):"(Our party's full.)",
            HexToByte('02 2E 05 07 F2 02 C7 03'):"(Please assist.)",
            HexToByte('02 2E 05 07 F2 02 C8 03'):"(Disbanding party.)",
            HexToByte('02 2E 05 07 F2 02 C9 03'):"(Taking a break.)",
            HexToByte('02 2E 05 07 F2 02 CA 03'):"(It's better if physical levels aren't too far apart.)",
            HexToByte('02 2E 05 07 F2 02 CB 03'):"(It's better if skill levels aren't too far apart.)",
            HexToByte('02 2E 05 08 F2 03 21 03'):"(Please follow.)",
            HexToByte('02 2E 05 08 F2 03 22 03'):"(I'll follow you.)",
            HexToByte('02 2E 05 08 F2 03 23 03'):"(Please check it.)",
            HexToByte('02 2E 05 08 F2 03 24 03'):"(Found it!)",
            HexToByte('02 2E 05 08 F2 03 25 03'):"(Full attack!)",
            HexToByte('02 2E 05 08 F2 03 26 03'):"(Pull back.)",
            HexToByte('02 2E 05 08 F2 03 27 03'):"(Watch out for enemies.)",
            HexToByte('02 2E 05 08 F2 03 28 03'):"(Defeat this one first!)",
            HexToByte('02 2E 05 08 F2 03 29 03'):"(Please don't attack.)",
            HexToByte('02 2E 05 08 F2 03 2A 03'):"(Please deactivate it.)",
            HexToByte('02 2E 05 08 F2 03 2B 03'):"(Heal!)",
            HexToByte('02 2E 05 08 F2 03 2C 03'):"(Run away!)",
            HexToByte('02 2E 05 08 F2 03 2D 03'):"(Help me out!)",
            HexToByte('02 2E 05 08 F2 03 2E 03'):"(Stop!)",
            HexToByte('02 2E 05 08 F2 03 2F 03'):"(Standing by.)",
            HexToByte('02 2E 05 08 F2 03 30 03'):"(None left.)",
            HexToByte('02 2E 05 08 F2 03 31 03'):"(Don't have it.)",
            HexToByte('02 2E 05 08 F2 03 32 03'):"(Please use it sparingly.)",
            HexToByte('02 2E 05 08 F2 03 33 03'):"(I'll use it sparingly.)",
            HexToByte('02 2E 05 08 F2 03 34 03'):"(I'm weakened.)",
            HexToByte('02 2E 05 08 F2 03 35 03'):"(My gear is in poor condition.)",
            HexToByte('02 2E 05 08 F2 03 36 03'):"(Ready!)",
            HexToByte('02 2E 05 08 F2 03 37 03'):"(Making a Battle Regimen.)",
            HexToByte('02 2E 05 08 F2 03 38 03'):"(Starting the Battle Regimen.)",
            HexToByte('02 2E 05 08 F2 03 39 03'):"(Please set enemy marks.)",
            HexToByte('02 2E 05 08 F2 03 3A 03'):"(Please set an ally mark.)",
            HexToByte('02 2E 05 08 F2 03 3B 03'):"(Please use it.)",
            HexToByte('02 2E 05 08 F2 03 3C 03'):"(Let's rest for a while.)",
            HexToByte('02 2E 05 08 F2 03 3D 03'):"(Front line job)",
            HexToByte('02 2E 05 08 F2 03 3E 03'):"(Support role job)",
            HexToByte('02 2E 05 08 F2 03 3F 03'):"(Back line job)",
            HexToByte('02 2E 05 08 F2 03 40 03'):"(Weakness)",
            HexToByte('02 2E 05 08 F2 03 41 03'):"(Warning)",
            HexToByte('02 2E 05 08 F2 03 42 03'):"(Recommend)",
            HexToByte('02 2E 05 08 F2 03 43 03'):"(Kill Order)",
            HexToByte('02 2E 05 09 F2 03 85 03'):"(Guildleve)",
            HexToByte('02 2E 05 09 F2 03 87 03'):"(Quest)",
            HexToByte('02 2E 05 09 F2 03 88 03'):"(Client)",
            HexToByte('02 2E 05 09 F2 03 89 03'):"(Instance)",
            HexToByte('02 2E 05 09 F2 03 8A 03'):"(Gil)",
            HexToByte('02 2E 05 09 F2 03 8B 03'):"(Skill)",
            HexToByte('02 2E 05 09 F2 03 8C 03'):"(Primary Skill)",
            HexToByte('02 2E 05 09 F2 03 8D 03'):"(Primary Skill Rank)",
            HexToByte('02 2E 05 09 F2 03 8E 03'):"(Physical Level)",
            HexToByte('02 2E 05 09 F2 03 8F 03'):"(Skill Point)",
            HexToByte('02 2E 05 09 F2 03 90 03'):"(Experience Points)",
            HexToByte('02 2E 05 09 F2 03 91 03'):"(Affinity)",
            HexToByte('02 2E 05 09 F2 03 92 03'):"(Attribute)",
            HexToByte('02 2E 05 09 F2 03 93 03'):"(Elemental Resistance)",
            HexToByte('02 2E 05 09 F2 03 94 03'):"(Fire)",
            HexToByte('02 2E 05 09 F2 03 95 03'):"(Ice)",
            HexToByte('02 2E 05 09 F2 03 96 03'):"(Wind)",
            HexToByte('02 2E 05 09 F2 03 97 03'):"(Earth)",
            HexToByte('02 2E 05 09 F2 03 98 03'):"(Lightning)",
            HexToByte('02 2E 05 09 F2 03 99 03'):"(Water)",
            HexToByte('02 2E 05 09 F2 03 9A 03'):"(Astral)",
            HexToByte('02 2E 05 09 F2 03 9B 03'):"(Umbral)",
            HexToByte('02 2E 05 09 F2 03 9C 03'):"(Guardian)",
            HexToByte('02 2E 05 09 F2 03 9D 03'):"(Nameday)",
            HexToByte('02 2E 05 09 F2 03 9E 03'):"(Race)",
            HexToByte('02 2E 05 09 F2 03 9F 03'):"(Clan)",
            HexToByte('02 2E 05 09 F2 03 A0 03'):"(Gender)",
            HexToByte('02 2E 05 09 F2 03 A1 03'):"(Title)",
            HexToByte('02 2E 05 09 F2 03 A2 03'):"(Quality)",
            HexToByte('02 2E 05 09 F2 03 A3 03'):"(☆☆☆)",
            HexToByte('02 2E 05 09 F2 03 A4 03'):"(☆☆)",
            HexToByte('02 2E 05 09 F2 03 A5 03'):"(☆)",
            HexToByte('02 2E 05 09 F2 03 A6 03'):"(Durability)",
            HexToByte('02 2E 05 09 F2 03 AC 03'):"(To Repair)",
            HexToByte('02 2E 05 09 F2 03 AD 03'):"(Status Effect)",
            HexToByte('02 2E 05 09 F2 03 AE 03'):"(Cast Time)",
            HexToByte('02 2E 05 09 F2 03 AF 03'):"(Recast Time)",
            HexToByte('02 2E 05 09 F2 03 B0 03'):"(KO'd)",
            HexToByte('02 2E 05 09 F2 03 B1 03'):"(Craft)",
            HexToByte('02 2E 05 09 F2 03 B2 03'):"(Gathering)",
            HexToByte('02 2E 05 09 F2 03 B3 03'):"(Negotiate)",
            HexToByte('02 2E 05 09 F2 03 B4 03'):"(Guild Mark)",
            HexToByte('02 2E 05 09 F2 03 B5 03'):"(Mark)",
            HexToByte('02 2E 05 09 F2 03 B6 03'):"(Linkshell)",
            HexToByte('02 2E 05 09 F2 03 B7 03'):"(Linkpearl)",
            HexToByte('02 2E 05 09 F2 03 B8 03'):"(Active Mode)",
            HexToByte('02 2E 05 09 F2 03 B9 03'):"(Passive Mode)",
            HexToByte('02 2E 05 09 F2 03 BA 03'):"(Action)",
            HexToByte('02 2E 05 09 F2 03 BB 03'):"(Magic)",
            HexToByte('02 2E 05 09 F2 03 BC 03'):"(Weaponskill)",
            HexToByte('02 2E 05 09 F2 03 BD 03'):"(Ability)",
            HexToByte('02 2E 05 09 F2 03 BE 03'):"(Trait)",
            HexToByte('02 2E 05 09 F2 03 BF 03'):"(Gathering Actions)",
            HexToByte('02 2E 05 09 F2 03 C0 03'):"(Synthesis Actions)",
            HexToByte('02 2E 05 09 F2 03 C1 03'):"(Engage)",
            HexToByte('02 2E 05 09 F2 03 C2 03'):"(Disengage)",
            HexToByte('02 2E 05 09 F2 03 C3 03'):"(Incapacitated)",
            HexToByte('02 2E 05 09 F2 03 C4 03'):"(Battle Regimen)",
            HexToByte('02 2E 05 09 F2 03 C5 03'):"(Enmity)",
            HexToByte('02 2E 05 09 F2 03 C6 03'):"(Loot)",
            HexToByte('02 2E 05 09 F2 03 C7 03'):"(Enemy Sign)",
            HexToByte('02 2E 05 09 F2 03 C8 03'):"(Ally Sign)",
            HexToByte('02 2E 05 09 F2 03 C9 03'):"(Target)",            
            HexToByte('02 2E 05 09 F2 03 CA 03'):"((Gear) Affinity)",
            HexToByte('02 2E 05 09 F2 03 CB 03'):"(Rare)",
            HexToByte('02 2E 05 09 F2 03 CC 03'):"(Unique)",
            HexToByte('02 2E 05 09 F2 03 CD 03'):"(Party)",
            HexToByte('02 2E 05 09 F2 03 CE 03'):"(Map)",
            HexToByte('02 2E 05 09 F2 03 CF 03'):"(Log out)",
            HexToByte('02 2E 05 09 F2 03 D0 03'):"(Indent)",
            HexToByte('02 2E 05 09 F2 03 D1 03'):"(Pattern)",
            HexToByte('02 2E 05 09 F2 03 D2 03'):"(Retainer)",
            HexToByte('02 2E 05 09 F2 03 D3 03'):"(Chocobo)",
            HexToByte('02 2E 05 09 F2 03 D4 03'):"(Aetheryte)",
            HexToByte('02 2E 05 09 F2 03 D5 03'):"(Aetherial Gate)",
            HexToByte('02 2E 05 09 F2 03 D6 03'):"(Aetherial Node)",
            HexToByte('02 2E 05 09 F2 03 D7 03'):"(Trade)",
            HexToByte('02 2E 05 09 F2 03 D8 03'):"(Bazaar)",
            HexToByte('02 2E 05 09 F2 03 D9 03'):"(Repair)",
            HexToByte('02 2E 05 09 F2 03 DA 03'):"(Auto-translation Dictionary)",
            HexToByte('02 2E 05 09 F2 03 DB 03'):"(Teleport)",            
            HexToByte('02 2E 05 09 F2 03 DC 03'):"(Warp)",
            HexToByte('02 2E 05 09 F2 03 DD 03'):"(Guild Shop)",
            HexToByte('02 2E 05 09 F2 03 DE 03'):"(Hyur)",
            HexToByte('02 2E 05 09 F2 03 DF 03'):"(Elezen)",
            HexToByte('02 2E 05 09 F2 03 E0 03'):"(Lalafell)",
            HexToByte('02 2E 05 09 F2 03 E1 03'):"(Miqo'te)",
            HexToByte('02 2E 05 09 F2 03 E2 03'):"(Roegadyn)",
            HexToByte('02 2E 05 09 F2 03 E3 03'):"(Midlander)",
            HexToByte('02 2E 05 09 F2 03 E4 03'):"(Highlander)",
            HexToByte('02 2E 05 09 F2 03 E5 03'):"(Wildwood)",
            HexToByte('02 2E 05 09 F2 03 E6 03'):"(Duskwight)",
            HexToByte('02 2E 05 09 F2 03 E7 03'):"(Plainsfolk)",
            HexToByte('02 2E 05 09 F2 03 E8 03'):"(Dunesfolk)",
            HexToByte('02 2E 05 09 F2 03 E9 03'):"(Seeker of the Sun)",
            HexToByte('02 2E 05 09 F2 03 EA 03'):"(Keeper of the Moon)",
            HexToByte('02 2E 05 09 F2 03 EB 03'):"(Sea Wolf)",
            HexToByte('02 2E 05 09 F2 03 EC 03'):"(Hellsguard)",
            HexToByte('02 2E 05 09 F2 03 ED 03'):"(Diciples of War)",
            HexToByte('02 2E 05 09 F2 03 EE 03'):"(Disciples of Magic)",
            HexToByte('02 2E 05 09 F2 03 EF 03'):"(Disciples of the Land)",
            HexToByte('02 2E 05 09 F2 03 F0 03'):"(Disciples of the Hand)",
            HexToByte('02 2E 05 0A F2 04 B1 03'):"(/?)",
            HexToByte('02 2E 05 0A F2 04 B2 03'):"(/action)",
            HexToByte('02 2E 05 0A F2 04 B3 03'):"(/angry)",
            HexToByte('02 2E 05 0A F2 04 B4 03'):"(/areaofeffect)",
            HexToByte('02 2E 05 0A F2 04 B5 03'):"(/automove)",
            HexToByte('02 2E 05 0A F2 04 B6 03'):"(/away)",
            HexToByte('02 2E 05 0A F2 04 B7 03'):"(/battlemode)",
            HexToByte('02 2E 05 0A F2 04 B8 03'):"(/battleregimen)",
            HexToByte('02 2E 05 0A F2 04 B9 03'):"(/beckon)",
            HexToByte('02 2E 05 0A F2 04 BA 03'):"(/blacklist)",
            HexToByte('02 2E 05 0A F2 04 BB 03'):"(/blush)",
            HexToByte('02 2E 05 0A F2 04 BC 03'):"(/bow)",
            HexToByte('02 2E 05 0A F2 04 BE 03'):"(/chatmode)",
            HexToByte('02 2E 05 0A F2 04 BF 03'):"(/check)",
            HexToByte('02 2E 05 0A F2 04 C0 03'):"(/cheer)",
            HexToByte('02 2E 05 0A F2 04 C1 03'):"(/chuckle)",
            HexToByte('02 2E 05 0A F2 04 C2 03'):"(/clap)",
            HexToByte('02 2E 05 0A F2 04 C3 03'):"(/clock)",
            HexToByte('02 2E 05 0A F2 04 C4 03'):"(/comfort)",
            HexToByte('02 2E 05 0A F2 04 C6 03'):"(/congratulate)",
            HexToByte('02 2E 05 0A F2 04 C7 03'):"(/cry)",
            HexToByte('02 2E 05 0A F2 04 C8 03'):"(/dance)",
            HexToByte('02 2E 05 0A F2 04 C9 03'):"(/decline)",
            HexToByte('02 2E 05 0A F2 04 CA 03'):"(/deny)",
            HexToByte('02 2E 05 0A F2 04 CD 03'):"(/display)",
            HexToByte('02 2E 05 0A F2 04 CB 03'):"(/doubt)",
            HexToByte('02 2E 05 0A F2 04 CC 03'):"(/doze)",
            HexToByte('02 2E 05 0A F2 04 CE 03'):"(/dusteffect)",
            HexToByte('02 2E 05 0A F2 04 CF 03'):"(/echo)",
            HexToByte('02 2E 05 0A F2 04 D0 03'):"(/emote)",
            HexToByte('02 2E 05 0A F2 04 D1 03'):"(/equip)",
            HexToByte('02 2E 05 0A F2 04 D2 03'):"(/equipaction)",
            HexToByte('02 2E 05 0A F2 04 D3 03'):"(/examineself)",
            HexToByte('02 2E 05 0A F2 04 D4 03'):"(/extendeddraw)",
            HexToByte('02 2E 05 0A F2 04 D6 03'):"(/friendlist)",
            HexToByte('02 2E 05 0A F2 04 D7 03'):"(/fume)",
            HexToByte('02 2E 05 0A F2 04 D8 03'):"(/furious)",
            HexToByte('02 2E 05 0A F2 04 D9 03'):"(/goodbye)",
            HexToByte('02 2E 05 0A F2 04 DB 03'):"(/item)",
            HexToByte('02 2E 05 0A F2 04 DC 03'):"(/join)",
            HexToByte('02 2E 05 0A F2 04 DD 03'):"(/joy)",
            HexToByte('02 2E 05 0A F2 04 DE 03'):"(/kneel)",
            HexToByte('02 2E 05 0A F2 04 DF 03'):"(/laugh)",
            HexToByte('02 2E 05 0A F2 04 E0 03'):"(/linkshell)",
            HexToByte('02 2E 05 0A F2 04 E2 03'):"(/lockon)",
            HexToByte('02 2E 05 0A F2 04 E3 03'):"(/logout)",
            HexToByte('02 2E 05 0A F2 04 E4 03'):"(/lookout)",
            HexToByte('02 2E 05 0A F2 04 E5 03'):"(/loot)",   
            HexToByte('02 2E 05 0A F2 04 E7 03'):"(/map)",
            HexToByte('02 2E 05 0A F2 04 E8 03'):"(/marking)",
            HexToByte('02 2E 05 0A F2 04 E9 03'):"(/me)",
            HexToByte('02 2E 05 0A F2 04 EA 03'):"(/meh)",
            HexToByte('02 2E 05 0A F2 04 EB 03'):"(/names)",
            HexToByte('02 2E 05 0A F2 04 EC 03'):"(/no)",
            HexToByte('02 2E 05 0A F2 04 EE 03'):"(/panic)",
            HexToByte('02 2E 05 0A F2 04 EF 03'):"(/party)",
            HexToByte('02 2E 05 0A F2 04 F0 03'):"(/partycmd)",
            HexToByte('02 2E 05 0A F2 04 F1 03'):"(/physics)",
            HexToByte('02 2E 05 0A F2 04 F3 03'):"(/point)",
            HexToByte('02 2E 05 0A F2 04 F4 03'):"(/poke)",
            HexToByte('02 2E 05 0A F2 04 F5 03'):"(/profanity)",
            HexToByte('02 2E 05 0A F2 04 F6 03'):"(/psych)",
            HexToByte('02 2E 05 0A F2 04 F7 03'):"(/rally)",
            HexToByte('02 2E 05 0A F2 04 F8 03'):"(/recast)",
            HexToByte('02 2E 05 0A F2 04 F9 03'):"(/salute)",
            HexToByte('02 2E 05 0A F2 04 FA 03'):"(/say)",
            HexToByte('02 2E 05 0A F2 04 FB 03'):"(/scrollingbattletext)",
            HexToByte('02 2E 05 0A F2 04 FD 03'):"(/shadow)",
            HexToByte('02 2E 05 0A F2 04 FE 03'):"(/shocked)",
            HexToByte('02 2E 05 0A F2 04 FF 03'):"(/shout)",
            HexToByte('02 2E 04 0A F1 05 03'):"(/shrug)",
            HexToByte('02 2E 05 0A F2 05 01 03'):"(/sit)",
            HexToByte('02 2E 05 0A F2 05 02 03'):"(/soothe)",
            HexToByte('02 2E 05 0A F2 05 03 03'):"(/stagger)",
            HexToByte('02 2E 05 0A F2 05 04 03'):"(/stretch)",
            HexToByte('02 2E 05 0A F2 05 05 03'):"(/sulk)",
            HexToByte('02 2E 05 0A F2 05 06 03'):"(/supportdesk)",
            HexToByte('02 2E 05 0A F2 05 07 03'):"(/surprised)",
            HexToByte('02 2E 05 0A F2 05 09 03'):"(/targetnpc)",
            HexToByte('02 2E 05 0A F2 05 0A 03'):"(/targetpc)",
            HexToByte('02 2E 05 0A F2 05 0B 03'):"(/tell)",
            HexToByte('02 2E 05 0A F2 05 15 03'):"(/textclear)",
            HexToByte('02 2E 05 0A F2 05 0C 03'):"(/think)",            
            HexToByte('02 2E 05 0A F2 05 0D 03'):"(/thumbsup)",
            HexToByte('02 2E 05 0A F2 05 0E 03'):"(/upset)",
            HexToByte('02 2E 05 0A F2 05 10 03'):"(/wait)",
            HexToByte('02 2E 05 0A F2 05 11 03'):"(/wave)",
            HexToByte('02 2E 05 0A F2 05 12 03'):"(/welcome)",
            HexToByte('02 2E 05 0A F2 05 14 03'):"(/yes)",
            HexToByte('02 2E 05 0B F2 05 DD 03'):"(North)",
            HexToByte('02 2E 05 0B F2 05 DE 03'):"(South)",
            HexToByte('02 2E 05 0B F2 05 DF 03'):"(East)",
            HexToByte('02 2E 05 0B F2 05 E0 03'):"(West)",
            HexToByte('02 2E 05 0B F2 05 E1 03'):"(Up)",
            HexToByte('02 2E 05 0B F2 05 E2 03'):"(Down)",
            HexToByte('02 2E 05 0B F2 05 E3 03'):"(Right)",
            HexToByte('02 2E 05 0B F2 05 E4 03'):"(Left)",
            HexToByte('02 2E 05 0B F2 05 E5 03'):"(Surface)",
            HexToByte('02 2E 05 0B F2 05 E6 03'):"(Rear)",
            HexToByte('02 2E 05 0B F2 05 E7 03'):"(Side)",
            HexToByte('02 2E 05 0B F2 05 E8 03'):"(Front)",
            HexToByte('02 2E 05 0B F2 05 E9 03'):"(Middle)",
            HexToByte('02 2E 05 0B F2 05 EA 03'):"(Flank)",
            HexToByte('02 2E 05 0B F2 05 EB 03'):"(Inside)",
            HexToByte('02 2E 05 0B F2 05 EC 03'):"(Outside)",
            HexToByte('02 2E 05 0B F2 05 ED 03'):"(This way)",
            HexToByte('02 2E 05 0B F2 05 EE 03'):"(Over there)",
            HexToByte('02 2E 05 0B F2 05 EF 03'):"(That way)",
            HexToByte('02 2E 05 0C F2 06 41 03'):"(Day before yesterday)",
            HexToByte('02 2E 05 0C F2 06 42 03'):"(Yesterday)",
            HexToByte('02 2E 05 0C F2 06 43 03'):"(Today)",
            HexToByte('02 2E 05 0C F2 06 44 03'):"(Tomorrow)",
            HexToByte('02 2E 05 0C F2 06 45 03'):"(Day after tomorrow)",
            HexToByte('02 2E 05 0C F2 06 46 03'):"(Last week)",
            HexToByte('02 2E 05 0C F2 06 47 03'):"(This week)",
            HexToByte('02 2E 05 0C F2 06 48 03'):"(Next week)",
            HexToByte('02 2E 05 0C F2 06 49 03'):"(a.m.)",
            HexToByte('02 2E 05 0C F2 06 4A 03'):"(p.m.)",
            HexToByte('02 2E 05 0C F2 06 4B 03'):"(Morning)",
            HexToByte('02 2E 05 0C F2 06 4C 03'):"(Afternoon)",
            HexToByte('02 2E 05 0C F2 06 4D 03'):"(Night)",
            HexToByte('02 2E 05 0C F2 06 4E 03'):"(Day of the week)",
            HexToByte('02 2E 05 0C F2 06 4F 03'):"(Sunday)",
            HexToByte('02 2E 05 0C F2 06 50 03'):"(Monday)",
            HexToByte('02 2E 05 0C F2 06 51 03'):"(Tuesday)",
            HexToByte('02 2E 05 0C F2 06 52 03'):"(Wednesday)",
            HexToByte('02 2E 05 0C F2 06 53 03'):"(Thursday)",
            HexToByte('02 2E 05 0C F2 06 54 03'):"(Friday)",
            HexToByte('02 2E 05 0C F2 06 55 03'):"(Saturday)",
            HexToByte('02 2E 05 0C F2 06 56 03'):"(Holiday)",
            HexToByte('02 2E 05 0C F2 06 57 03'):"(Break)",
            HexToByte('02 2E 05 0C F2 06 5A 03'):"(Second)",
            HexToByte('02 2E 05 0C F2 06 58 03'):"(Long time)",
            HexToByte('02 2E 05 0C F2 06 59 03'):"(Short time)",
            HexToByte('02 2E 05 0C F2 06 5B 03'):"(Minute)",
            HexToByte('02 2E 05 0C F2 06 5C 03'):"(Hour)",
            HexToByte('02 2E 05 0C F2 06 5D 03'):"(Time remaining)",
            HexToByte('02 2E 05 0C F2 06 5E 03'):"(January)",
            HexToByte('02 2E 05 0C F2 06 5F 03'):"(February)",
            HexToByte('02 2E 05 0C F2 06 60 03'):"(March (Month))",
            HexToByte('02 2E 05 0C F2 06 61 03'):"(April)",
            HexToByte('02 2E 05 0C F2 06 62 03'):"(May)",
            HexToByte('02 2E 05 0C F2 06 63 03'):"(June)",
            HexToByte('02 2E 05 0C F2 06 64 03'):"(July)",
            HexToByte('02 2E 05 0C F2 06 65 03'):"(August)",
            HexToByte('02 2E 05 0C F2 06 66 03'):"(September)",
            HexToByte('02 2E 05 0C F2 06 67 03'):"(October)",
            HexToByte('02 2E 05 0C F2 06 68 03'):"(November)",
            HexToByte('02 2E 05 0C F2 06 69 03'):"(December)",
            HexToByte('02 2E 05 0D F2 06 A5 03'):"(Connection Speed)",
            HexToByte('02 2E 05 0D F2 06 A6 03'):"(Blacklist)",
            HexToByte('02 2E 05 0D F2 06 A7 03'):"(Friend List)",
            HexToByte('02 2E 05 0D F2 06 A8 03'):"(Config)",
            HexToByte('02 2E 05 0D F2 06 A9 03'):"(Connection)",
            HexToByte('02 2E 05 0D F2 06 AA 03'):"(Screenshot)",
            HexToByte('02 2E 05 0D F2 06 AB 03'):"(Patch)",
            HexToByte('02 2E 05 0D F2 06 AC 03'):"(Version)",
            HexToByte('02 2E 05 0D F2 06 AD 03'):"(Connection Lost)",
            HexToByte('02 2E 05 0D F2 06 AE 03'):"(Lag)",
            HexToByte('02 2E 05 0D F2 06 AF 03'):"(Filter)",
            HexToByte('02 2E 05 0D F2 06 B0 03'):"(Client)",
            HexToByte('02 2E 05 0D F2 06 B1 03'):"(Backup)",
            HexToByte('02 2E 05 0D F2 06 B3 03'):"(Save)",
            HexToByte('02 2E 05 0D F2 06 B4 03'):"(TV)",
            HexToByte('02 2E 05 0D F2 06 B5 03'):"(Modem)",
            HexToByte('02 2E 05 0D F2 06 B6 03'):"(Monitor)",
            HexToByte('02 2E 05 0D F2 06 B7 03'):"(Log off)",
            HexToByte('02 2E 05 0D F2 06 B8 03'):"(Log on)",
            HexToByte('02 2E 05 0D F2 06 B9 03'):"(Hard Disk)",
            HexToByte('02 2E 05 0D F2 06 BA 03'):"(Server)",
            HexToByte('02 2E 05 0D F2 06 BB 03'):"(Macro)",
            HexToByte('02 2E 05 0E F2 07 09 03'):"(Online)",
            HexToByte('02 2E 05 0E F2 07 0A 03'):"(Away)",
            HexToByte('02 2E 05 0F F2 07 6D 03'):"(Numeric keypad)",
            HexToByte('02 2E 05 0F F2 07 6E 03'):"(Arrow keys)",
            HexToByte('02 2E 05 0F F2 07 6F 03'):"(Tab key)",
            HexToByte('02 2E 05 0F F2 07 70 03'):"(Enter key)",
            HexToByte('02 2E 05 0F F2 07 71 03'):"(End key)",
            HexToByte('02 2E 05 0F F2 07 72 03'):"(Num Lock key)",
            HexToByte('02 2E 05 0F F2 07 73 03'):"(Function keys)",
            HexToByte('02 2E 05 0F F2 07 74 03'):"(Spacebar)",
            HexToByte('02 2E 05 0F F2 07 75 03'):"(Backspace key)",
            HexToByte('02 2E 05 0F F2 07 76 03'):"(Halfwidth/Fullwidth key)",
            HexToByte('02 2E 05 0F F2 07 77 03'):"(Alt key)",
            HexToByte('02 2E 05 0F F2 07 78 03'):"(Insert key)",
            HexToByte('02 2E 05 0F F2 07 79 03'):"(Page Down key)",
            HexToByte('02 2E 05 0F F2 07 7A 03'):"(Home key)",
            HexToByte('02 2E 05 0F F2 07 7B 03'):"(Page Up key)",
            HexToByte('02 2E 05 0F F2 07 7C 03'):"(Caps Lock key)",
            HexToByte('02 2E 05 0F F2 07 7D 03'):"(Shift key)",
            HexToByte('02 2E 05 0F F2 07 7E 03'):"(Esc key)",
            HexToByte('02 2E 05 0F F2 07 7F 03'):"(Ctrl key)",
            HexToByte('02 2E 05 0F F2 07 80 03'):"(Delete key)",            
            HexToByte('02 2E 05 10 F2 07 D1 03'):"(notice)",
            HexToByte('02 2E 05 10 F2 07 D2 03'):"(place)",
            HexToByte('02 2E 05 10 F2 07 D3 03'):"(meat)",
            HexToByte('02 2E 05 10 F2 07 D4 03'):"(train)",
            HexToByte('02 2E 05 10 F2 07 D5 03'):"(last)",
            HexToByte('02 2E 05 10 F2 07 D7 03'):"(question)",
            HexToByte('02 2E 05 10 F2 07 D6 03'):"(death)",
            HexToByte('02 2E 05 10 F2 07 D8 03'):"(joy)",
            HexToByte('02 2E 05 10 F2 07 D9 03'):"(mistake)",
            HexToByte('02 2E 05 10 F2 07 DA 03'):"(purpose)",
            HexToByte('02 2E 05 10 F2 07 DB 03'):"(half)",
            HexToByte('02 2E 05 10 F2 07 DC 03'):"(date)",
            HexToByte('02 2E 05 10 F2 07 DD 03'):"(secret)",
            HexToByte('02 2E 05 10 F2 07 DE 03'):"(position)",
            HexToByte('02 2E 05 10 F2 07 DF 03'):"(lie)",
            HexToByte('02 2E 05 10 F2 07 E0 03'):"(excitement)",
            HexToByte('02 2E 05 10 F2 07 E1 03'):"(money)",
            HexToByte('02 2E 05 10 F2 07 E2 03'):"(fear)",
            HexToByte('02 2E 05 10 F2 07 E3 03'):"(friend)",
            HexToByte('02 2E 05 10 F2 07 E4 03'):"(entrance)",
            HexToByte('02 2E 05 10 F2 07 E5 03'):"(exit)",
            HexToByte('02 2E 05 10 F2 07 E6 03'):"(mine)",
            HexToByte('02 2E 05 10 F2 07 E7 03'):"(fun)",
            HexToByte('02 2E 05 10 F2 07 E8 03'):"(I)",
            HexToByte('02 2E 05 10 F2 07 E9 03'):"(you)",            
            HexToByte('02 2E 03 11 02 03'):"(Halone, the Fury)",
            HexToByte('02 2E 03 11 03 03'):"(Menphina, the Lover)",
            HexToByte('02 2E 03 11 04 03'):"(Thaliak, the Scholar)",
            HexToByte('02 2E 03 11 05 03'):"(Nymeia, the Spinner)",
            HexToByte('02 2E 03 11 06 03'):"(Llymlaen, the Navigator)",
            HexToByte('02 2E 03 11 07 03'):"(Oschon, the Wanderer)",
            HexToByte('02 2E 03 11 08 03'):"(Byregot, the Builder)",
            HexToByte('02 2E 03 11 09 03'):"(Rhalgr, the Destroyer)",
            HexToByte('02 2E 03 11 0A 03'):"(Azeyma, the Warden)",
            HexToByte('02 2E 03 11 0B 03'):"(Nald'thal, the Traders)",
            HexToByte('02 2E 03 11 0C 03'):"(Nophica, the Matron)",
            HexToByte('02 2E 03 11 0D 03'):"(Althyk, the Keeper)",
            HexToByte('02 2E 03 12 02 03'):"(Main hand)",
            HexToByte('02 2E 03 12 03 03'):"(Off Hand)",
            HexToByte('02 2E 03 12 06 03'):"(Throwing Weapon)",
            HexToByte('02 2E 03 12 07 03'):"(Pack)",
            HexToByte('02 2E 03 12 08 03'):"(Pouch)",
            HexToByte('02 2E 03 12 0A 03'):"(Head)",
            HexToByte('02 2E 03 12 0B 03'):"(Undershirt)",
            HexToByte('02 2E 03 12 0C 03'):"(Body)",
            HexToByte('02 2E 03 12 0D 03'):"(Undergarment)",
            HexToByte('02 2E 03 12 0E 03'):"(Legs)",
            HexToByte('02 2E 03 12 0F 03'):"(Hands)",
            HexToByte('02 2E 03 12 10 03'):"(Feet)",
            HexToByte('02 2E 03 12 11 03'):"(Waist)",
            HexToByte('02 2E 03 12 12 03'):"(Neck)",
            HexToByte('02 2E 03 12 13 03'):"(Right Ear)",
            HexToByte('02 2E 03 12 14 03'):"(Left Ear)",
            HexToByte('02 2E 03 12 15 03'):"(Right Wrist)",
            HexToByte('02 2E 03 12 16 03'):"(Left Wrist)",
            HexToByte('02 2E 03 12 17 03'):"(Right Index Finger)",
            HexToByte('02 2E 03 12 18 03'):"(Left Index Finger)",
            HexToByte('02 2E 03 12 19 03'):"(Right Ring Finger)",
            HexToByte('02 2E 03 12 20 03'):"(Left Right Finger)", # may be buggy
            HexToByte('02 2E 03 12'):"(Left Right Finger)", # may be buggy
            HexToByte('02 2E 03 13 03 03'):"(Hand-to-Hand)",
            HexToByte('02 2E 03 13 04 03'):"(Sword)",
            HexToByte('02 2E 03 13 05 03'):"(Axe)",
            HexToByte('02 2E 03 13 08 03'):"(Archery)",
            HexToByte('02 2E 03 13 09 03'):"(Polearm)",
            HexToByte('02 2E 03 13 0B 03'):"(Shield)",
            HexToByte('02 2E 03 13 17 03'):"(Thaumaturgy)",
            HexToByte('02 2E 03 13 18 03'):"(Conjury)",
            HexToByte('02 2E 03 13 1E 03'):"(Woodworking)",
            HexToByte('02 2E 03 13 1F 03'):"(Smithing)",
            HexToByte('02 2E 03 13 20 03'):"(Armorcraft)",
            HexToByte('02 2E 03 13 21 03'):"(Goldsmithing)",
            HexToByte('02 2E 03 13 22 03'):"(Leatherworking)",
            HexToByte('02 2E 03 13 23 03'):"(Clothcraft)",
            HexToByte('02 2E 03 13 24 03'):"(Alchemy)",
            HexToByte('02 2E 03 13 25 03'):"(Cooking)",
            HexToByte('02 2E 03 13 28 03'):"(Mining)",
            HexToByte('02 2E 03 13 29 03'):"(Botany)",
            HexToByte('02 2E 03 13 2A 03'):"(Fishing)",
            HexToByte('02 2E 03 14 03 03'):"(Pugilist)",
            HexToByte('02 2E 03 14 04 03'):"(Gladiator)",
            HexToByte('02 2E 03 14 05 03'):"(Marauder)",
            HexToByte('02 2E 03 14 08 03'):"(Archer)",
            HexToByte('02 2E 03 14 09 03'):"(Lancer)",
            HexToByte('02 2E 03 14 17 03'):"(Thaumaturge)",
            HexToByte('02 2E 03 14 18 03'):"(Conjurer)",
            HexToByte('02 2E 03 14 1E 03'):"(Carpenter)",
            HexToByte('02 2E 03 14 1F 03'):"(Blacksmith)",
            HexToByte('02 2E 03 14 20 03'):"(Armorer)",
            HexToByte('02 2E 03 14 21 03'):"(Goldsmith)",
            HexToByte('02 2E 03 14 22 03'):"(Leatherworker)",
            HexToByte('02 2E 03 14 23 03'):"(Weaver)",
            HexToByte('02 2E 03 14 24 03'):"(Alchemist)",
            HexToByte('02 2E 03 14 25 03'):"(Culinarian)",
            HexToByte('02 2E 03 14 28 03'):"(Miner)",
            HexToByte('02 2E 03 14 29 03'):"(Botanist)",
            HexToByte('02 2E 03 14 2A 03'):"(Fisher)",            
            }

    def printCrafting(self, currentcrafting):
        #self.craftingdata
        #print currentcrafting
        #raw_input("")
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
            print u"敗北 %s ⇒ %s\nヒット %%: %i%%\n合計平均ダメージ: %i\nクリティカルの平均ダメージ: %i\nレギュラーの平均被害: %i\n合計ダメージ平均を撮影ヒット: %i\nクリティカルヒットのダメージの平均: %i\nダメージ平均ヒット: %i\nその他から合計ダメージ: %i\n平均ヒーリング: %i\n吸収平均: %i\n経験値: %i\n修錬値: %i\n日付時刻: %s GMT\n" % (currentmonster["monster"], currentmonster["class"], hitpercent, totaldmgavg, criticaldmgavg, regulardmgavg, totalhitdmgavg, crithitdmgavg, hitdmgavg, othertotaldmg, healingavg, absorbavg, currentmonster["exp"], currentmonster["skillpoints"], currentmonster["datetime"])
            self.monsterdata.append(currentmonster)
            #if len(monsterdata) > 20:
            #    uploadToDB()

    def useitem(self, logitem):
        if self.craftingcomplete == 1:
            self.printCrafting(self.currentcrafting)
            self.currentcrafting = copy.deepcopy(self.defaultcrafting)
            self.currentcrafting["datetime"] = time.strftime("%m/%d/%y %H:%M:%S",time.gmtime(self.logfiletime))
            self.craftingcomplete = 0
        if logitem.find("Standard Synthesis") != -1:
            # store previous value if valid:
            if self.synthtype != "":
                self.currentcrafting["actions"].append([self.synthtype, self.progress, self.durability, self.quality])
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
            self.printCrafting(self.currentcrafting)
            self.currentcrafting = copy.deepcopy(self.defaultcrafting)
            self.currentcrafting["datetime"] = time.strftime("%m/%d/%y %H:%M:%S",time.gmtime(self.logfiletime))
            self.craftingcomplete = 0
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
        # no plural form
        #self.currentmonster["monster"] = self.currentmonster["monster"].split('\'')[0]
        
    def parse_gathering(self, code, logitem):
        self.echo("othergathering " + logitem, 1)

    def parse_othergathering(self, code, logitem):
        self.echo("othergathering " + logitem, 1)

    def parse_leve(self, code, logitem):
        self.echo("leve " + logitem, 1)

    def parse_chatmessage(self, code, logitem):
        #tabkey = '02 2E 05 0F F2 07 6F 03'
        self.echo("chatmessage " + code + logitem, 1)
        if (code == '1B') or (code == '19'):
            user = ' '.join(logitem.split(' ')[0:2])
            message = unicode(logitem)
        else:
            logitemparts = logitem.split(":")
            user = logitemparts[0].strip()
            message = unicode(":".join(logitemparts[1:]).strip())
        try:
            if message.find(self.autotranslateheader) != -1:
                # found an auto translate
                '''
                if message.startswith("lang"):
                    msgparts = message.split(" ")
                    containsit = False
                    for text, value in self.autotranslate.items():
                        if message.find(text) != -1:
                            containsit = True
                            break
                    if not containsit:
                        #pass
                        self.echo(ByteToHex(message), 0)
                        self.echo("HexToByte('" + ByteToHex(msgparts[1]) + "'):" + "\"(" + " ".join(msgparts[2:]) + ")\",", 0)
                '''
                hasreplacement = False
                for text, value in self.autotranslate.items():
                    if message.find(text) != -1:
                        hasreplacement = True
                        message = message.replace(text, value)
                if not hasreplacement:
                    # Save this up to the server so we can investigate later and add it.
                    pass
                self.echo("Message: " + message, 1)
            #raw_input("tab")
        except:
            traceback.print_exc(file=sys.stdout)

    def parse_npcchat(self, code, logitem):
        self.echo("npc chat " + logitem, 1)

    def parse_invalidcommand(self, code, logitem):
        self.echo("invalid command " + logitem, 1)

    def parse_monstereffect(self, code, logitem):
        self.echo("other abilities " + logitem, 1)

    def parse_othereffect(self, code, logitem):
        if logitem.find("grants you") != -1:    
            effect = logitem[logitem.find("effect of ") +10:-1]
        self.echo("other abilities " + logitem, 1)

    def parse_partyabilities(self, code, logitem):
        if logitem.find("grants") != -1:
            effect = logitem[logitem.find("effect of ") +10:-1]
        if logitem.find("inflicts") != -1:
            monsteraffliction = logitem[logitem.find("effect of ") +10:-1]
        self.echo("other abilities " + logitem, 1)

    def parse_otherabilities(self, code, logitem):
        self.echo("other abilities " + logitem, 1)

    def parse_readyability(self, code, logitem):
        self.echo("ready ability " + logitem, 1)

    def parse_servermessage(self, code, logitem):
        self.echo("server message " + logitem, 1)

    def parse_invoke(self, code, logitem):
        self.echo("invoke " + logitem, 1)

    def parse_inflicts(self, code, logitem):
        if logitem.find("inflicts you") != -1:
            affliction = logitem[logitem.find("effect of ") +10:-1]
            return
        if logitem.find("inflicts") != -1:
            othersaffliction = logitem[logitem.find("effect of ") +10:-1]            
        self.echo("inflicts " + logitem, 1)

    def parse_effect(self, code, logitem):
        self.echo("effect " + logitem, 1)

    def parse_otherrecover(self, code, logitem):
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
        self.echo("monstermiss " + logitem, 1)

    def parse_othermiss(self, code, logitem):
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
        monster = logitem[logitem.find(u"は") +1:logitem.find(u"に")]
        if monster == self.currentmonster["monster"]:
            self.currentmonster["miss"] += 1
            return
        self.echo("miss " + logitem, 1)

    def parse_otherhitdamage(self, code, logitem):
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
        #if logitem.find("your") != -1 or logitem.find("Your") != -1:
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
        #print logitem
        # Crafting success
        if logitem.find("You create") != -1:
            if logitem.find(" of ") != -1:
                self.currentcrafting["item"] = logitem[logitem.find(" of ")+4:-1]
            else:
                self.currentcrafting["item"] = logitem[logitem.find(" a ")+3:-1]
            self.currentcrafting["success"] = 1
        # botched it
        if logitem.find("botch") != -1:
            self.currentcrafting["success"] = 0
        self.craftingcomplete = 1
        
        self.echo("crafting success " + logitem, 1)

    def parse_defeated(self, code, logitem):
        if self.craftingcomplete == 1:
            self.printCrafting(self.currentcrafting)
            self.currentcrafting = copy.deepcopy(self.defaultcrafting)
            self.currentcrafting["datetime"] = time.strftime("%m/%d/%y %H:%M:%S",time.gmtime(self.logfiletime))
            self.craftingcomplete = 0
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
            return

        self.echo("defeated " + logitem, 1)

    def parse_spexpgain(self, code, logitem):
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

        if self.defeated and self.spset and self.expset:
            self.defeated = False
            self.spset = False
            self.expset = False
            self.printDamage(self.currentmonster)

        self.echo("spexpgain " + logitem, 1)

    def parse_genericmessage(self, code, logitem):
        if logitem.find(u"を占有した") != -1:
            self.engaged(logitem)
        elif logitem.find("You use") != -1:
            self.useitem(logitem)
        elif logitem.find("Progress") != -1:
            # save progress as array of % and it was an increase or decrease
            if logitem.find("increases") != -1:
                self.progress = [logitem[logitem.find("by ") +3:-2], 1]
            else:
                self.progress = [logitem[logitem.find("by ") +3:-2], 0]
        elif logitem.find("Durability") != -1:
            if logitem.find("increases") != -1:
                self.durability = [logitem[logitem.find("by ") +3:-1], 1]
            else:
                self.durability = [logitem[logitem.find("by ") +3:-1], 0]
        elif logitem.find("Quality") != -1:
            if logitem.find("increases") != -1:
                self.quality = [logitem[logitem.find("by ") +3:-1], 1]
            else:
                self.quality = [logitem[logitem.find("by ") +3:-1], 0]
        else:
            pass
            #print "generic"
            #print logitem
       
            
        self.echo("generic " + logitem, 1)


def readLogFile(paths, charactername, logmonsterfilter = None, isrunning=None, password="", chatviewer=None):
    global configfile, lastlogparsed
    config = ConfigParser.ConfigParser()
    config.read(configfile)
    try:
        config.add_section('Config')
    except ConfigParser.DuplicateSectionError:
        pass
    en_parser = english_parser()
    jp_parser = japanese_parser()
    en_parser.characterdata["charactername"] = charactername
    jp_parser.characterdata["charactername"] = charactername
    logfile = None
    logsparsed = 0
    for logfilename in paths:
        try:
            logfiletime = os.stat(logfilename).st_mtime
            if not os.path.exists('newinstall'):
                if logfiletime < lastlogparsed - 5000:
                    continue
            logsparsed = logsparsed + 1
            en_parser.setLogFileTime(logfiletime)
            jp_parser.setLogFileTime(logfiletime)
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
            
                try:
                    en_parser.parse_line(unicode(logitem, 'utf-8', errors='replace'))
                except UnicodeDecodeError:
                    pass
                except:
                    traceback.print_exc(file=sys.stdout)
                try:
                    jp_parser.parse_line(unicode(logitem, 'utf-8', errors='replace'))
                except UnicodeDecodeError:
                    pass
                except:
                    traceback.print_exc(file=sys.stdout)
                if isrunning:
                    if not isrunning():
                        return                
                continue
            en_parser.close()
            if chatviewer:
                chatviewer.RefreshDisplay()

        finally:            
            if logfile:
                logfile.close()
        lastlogparsed = logfiletime
        config.set('Config', 'lastlogparsed', lastlogparsed)
        with open(configfile, 'wb') as openconfigfile:
            config.write(openconfigfile)
    if os.path.exists('newinstall'):
        os.remove('newinstall')
    #en_parser.savealllogs()
    # uncomment for debugging to disable uploads
    #return
    if logsparsed > 0:
        uploadToDB2(password, [en_parser, jp_parser])
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
    
def uploadToDB2(password="", parsers=[]):
    for parser in parsers:
        header = {"version":version,"language":parser.getlanguage(),"password":password, "character":parser.characterdata}        
        uploadDeaths(header, parser.deathsdata)
        uploadCrafting(header, parser.craftingdata)
        uploadBattles(header, parser.monsterdata)
        
        # Clear records for next run
        parser.monsterdata = []
        parser.craftingdata = []
        parser.gatheringdata = []
        parser.characterdata["deaths"] = []
        #numcrafting = uploadCrafting(header["crafting"] = parser.craftingdata)
        '''
        if parser.getlanguage() == "jp":
            print u"\n合計グローバルバトルレコード: %d" % totalbattlerecords
            print u"合計新キャラクター死亡: %d" % deaths
            print u"レコード送信（無視される重複）: %d" % recordsimported
            print u"ウェブサイトにアップロードされたレコード: %d" % updatedrecords
            if int(updatedrecords) > 0:
                print u"\nあなたのデータはあなたがそれを見ることができる、アップロードされています： \n\n%s" % url["url"] 
            else:
                print u"\nいいえ、新しいレコード。あなたはあなたのデータを表示することができます： \n\n%s\n" % url["url"] 
        elif parser.getlanguage() == "en":
            print "\nTotal Global Battle Records: %d" % totalbattlerecords
            print "Total New Character Deaths: %d" % deaths
            print "Records Sent (Duplicates ignored): %d" % recordsimported
            print "Records Uploaded To Website: %d" % updatedrecords
            if int(updatedrecords) > 0:
                print "\nYour data has been uploaded, you can view it at: \n\n%s" % url["url"] 
            else:
                print "\nNo new records. You can view your data at: \n\n%s\n" % url["url"] 
        '''
def uploadToDB(password="", parsers=[]):
    global doloop
    for parser in parsers:
        tmpdata = {"version": version, "language": parser.getlanguage(), "password": password, "character": parser.characterdata, "battle": parser.monsterdata, "crafting":parser.craftingdata, "gathering":parser.gatheringdata}
        jsondata = json.dumps(tmpdata)
        if not doloop:
            response = raw_input("Do you wish to display raw data? [y/N]: ")
        else:
            response = "no"
        if response.upper() == "Y" or response.upper() == "YES":
            if parser.getlanguage() == "en":
                print "JSON encoded for upload:"
            elif parser.getlanguage() == "jp":
                print u"JSONは、アップロード用にエンコードされた:"
            print jsondata
        if not doloop:
            if parser.getlanguage() == "en":
                response = raw_input("\nDo you wish to upload the data printed above? [Y/n]: ")
            else:
                response = raw_input(u"\n上記の印刷データをアップロードしますか？ [Y/n]: ")
        else:
            response = "YES"
        if response == "" or response.upper() == "Y" or response.upper() == "YES":
            if len(parser.monsterdata) > 0:
                end = 100
                totalbattlerecords = 0
                deaths = 0
                recordsimported = 0
                updatedrecords = 0
                url = None
                for start in range(0, len(parser.monsterdata), 100):
                    if end > len(parser.monsterdata):
                        end = len(parser.monsterdata)
                    tmpdata = {"version": version, "language": parser.getlanguage(), "password": password, "character": parser.characterdata, "battle": parser.monsterdata[start:end]}
                    if parser.getlanguage() == "en":
                        print "Uploading log data. Records %d to %d." % (start, end)
                    else:
                        print "アップロードのログデータ。レコード%d〜%d。" % (start, end)
                    jsondata = json.dumps(tmpdata)
                    url = doUpload(jsondata)
                    if url == None:
                        return
                    end = end+100
                    try:
                        totalbattlerecords = int(url["totalbattlerecords"])
                        deaths = deaths + int(url["deaths"])
                        recordsimported = recordsimported + int(url["recordsimported"])
                        updatedrecords = updatedrecords + int(url["updatedrecords"])
                    except:
                        if parser.getlanguage() == "en":
                            print "Did not understand the response from the server."
                        else:
                            print u"サーバーからの応答を理解できませんでした。"
                #for start in range(0, len(parser.craftingdata), 100):
                #    tmpdata = {"version":version, "language":parser.getlanguage(), "password": password, "character": parser.characterdata, "crafting":parser.craftingdata, "gathering":parser.gatheringdata                    
                if parser.getlanguage() == "jp":
                    print u"\n合計グローバルバトルレコード: %d" % totalbattlerecords
                    print u"合計新キャラクター死亡: %d" % deaths
                    print u"レコード送信（無視される重複）: %d" % recordsimported
                    print u"ウェブサイトにアップロードされたレコード: %d" % updatedrecords
                    if int(updatedrecords) > 0:
                        print u"\nあなたのデータはあなたがそれを見ることができる、アップロードされています： \n\n%s" % url["url"] 
                    else:
                        print u"\nいいえ、新しいレコード。あなたはあなたのデータを表示することができます： \n\n%s\n" % url["url"] 
                elif parser.getlanguage() == "en":
                    print "\nTotal Global Battle Records: %d" % totalbattlerecords
                    print "Total New Character Deaths: %d" % deaths
                    print "Records Sent (Duplicates ignored): %d" % recordsimported
                    print "Records Uploaded To Website: %d" % updatedrecords
                    if int(updatedrecords) > 0:
                        print "\nYour data has been uploaded, you can view it at: \n\n%s" % url["url"] 
                    else:
                        print "\nNo new records. You can view your data at: \n\n%s\n" % url["url"]                 
        else:
            if parser.getlanguage() == "jp":
                print "Your data will not be sent."
            elif parser.getlanguage() == "jp":
                print u"あなたのデータは送信されません。."

        parser.monsterdata = []
        parser.craftingdata = []
        parser.gatheringdata = []
        parser.characterdata["deaths"] = []

def doUpload(jsondata, url):
    try:
        #url = 'http://ffxivbattle.com/postlog-test.php'
        user_agent = 'Mozilla/4.0 (compatible; MSIE 5.5; Windows NT)'
        values = {'jsondata' : jsondata }
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



