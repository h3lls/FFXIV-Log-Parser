#!/usr/bin/env python
# encoding: utf-8

import ConfigParser
import wx
from threading import Thread 
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

charactername = ""
doloop = 0


class MainFrame(wx.Frame):
    def __init__(self, parent, title):
        wx.Frame.__init__(self, parent, title=title, size=(400,310))
        
        self.sb = self.CreateStatusBar() # A Statusbar in the bottom of the window

        # Setting up the menu.
        filemenu= wx.Menu()

        # wx.ID_ABOUT and wx.ID_EXIT are standard IDs provided by wxWidgets.
        filemenu.Append(1, "&Start"," Start Processing Logs")
        filemenu.Append(wx.ID_ABOUT, "&About"," Information about this program")
        filemenu.AppendSeparator()
        filemenu.Append(wx.ID_EXIT,"E&xit"," Terminate the program")
        self.Bind(wx.EVT_MENU, self.OnStartCollecting, id=1)
        self.Bind(wx.EVT_MENU, self.OnExit, id=wx.ID_EXIT)
        self.Bind(wx.EVT_MENU, self.OnAbout, id=wx.ID_ABOUT)#menuItem)

        # Creating the menubar.
        menuBar = wx.MenuBar()
        menuBar.Append(filemenu,"&File") # Adding the "filemenu" to the MenuBar
        self.SetMenuBar(menuBar)  # Adding the MenuBar to the Frame content.
        
        panel = wx.Panel(self, -1)		
        logpath = ""
        charactername = hex(uuid.getnode())
        # read defaults
        try:
            config = ConfigParser.ConfigParser()
            config.read('logparser.cfg')
            logpath = config.get('Config', 'logpath')
            charactername = config.get('Config', 'charactername')
        except:
            logpath = ""
            pass
        if logpath == "":
            userdir = os.path.expanduser('~')
            logpath = os.path.join(userdir, "Documents\\My Games\\FINAL FANTASY XIV\\user\\") 
        self.st = wx.StaticText(panel, -1, 'Select Log Path', (5,3))
        self.control = wx.TextCtrl(panel, -1, logpath, (5,21), (345, 22))
        self.btnDialog = wx.Button(panel, 102, "...", (350,20), (28, 24))
        self.Bind(wx.EVT_BUTTON, self.OnLogSelect, id=102)
        self.st = wx.StaticText(panel, -1, 'Enter Your Character Name (default is unique id to hide your name)', (5,53))
        self.charname = wx.TextCtrl(panel, -1, charactername, (5,70), (370, 22))
        self.btnDialog = wx.Button(panel, 103, "Start", (150,100))
        self.Bind(wx.EVT_BUTTON, self.OnStartCollecting, id=103)
        lblLogWindow = wx.StaticText( panel, -1, "Activity Log", (5,120))
        self.logWindow = wx.TextCtrl(panel, -1, "", (5,136), (370, 80), style=wx.TE_MULTILINE)
        logLayout = wx.BoxSizer( wx.VERTICAL )
        logLayout.Add( lblLogWindow, 0, wx.EXPAND )
        logLayout.Add( self.logWindow, 1, wx.EXPAND )		
        redir=RedirectText(self.logWindow)
        sys.stdout=redir
        self.Show(True)

    def OnIdle( self, evt ):
        if self.process is not None:
            stream = self.process.GetInputStream()
            if stream.CanRead():
                text = stream.read()
                self.logWindow.AppendText( text ) 

    def OnLogSelect(self, e):
        dlg = wx.DirDialog(self, "Choose the Log Directory:", self.control.GetValue(), style=wx.DD_DEFAULT_STYLE | wx.DD_NEW_DIR_BUTTON)
        if dlg.ShowModal() == wx.ID_OK:
            self.control.SetValue(dlg.GetPath())
        dlg.Destroy()

    def OnAbout(self,e):
        # A message dialog box with an OK button. wx.OK is a standard ID in wxWidgets.
        dlg = wx.MessageDialog( self, "A log parser for Final Fantasy XIV.", "About FFXIV Log Parser", wx.OK)
        dlg.ShowModal() # Show it
        dlg.Destroy() # finally destroy it when finished.

    def OnStartCollecting(self, e):
        try:
            config = ConfigParser.ConfigParser()
            try:
                config.add_section('Config')
            except ConfigParser.DuplicateSectionError:
                pass
            config.set('Config', 'logpath', self.control.GetValue())
            config.set('Config', 'charactername', self.charname.GetValue())
            with open('logparser.cfg', 'wb') as configfile:
                config.write(configfile)
        except (Exception, e):
            print e
        self.guithread = GUIThread(self.control.GetValue(), self.charname.GetValue(), self.OnStatus) 
        self.guithread.start()

    def OnExit(self,e):
        try:
            self.guithread.exit()
        except (AttributeError):
            pass
        self.Close(True)  # Close the frame.

    def OnStatus(self, message):
        self.sb.PushStatusText(message, 0)

class RedirectText(object):
    def __init__(self,aWxTextCtrl):
        self.out=aWxTextCtrl

    def write(self,string):
        self.out.WriteText(string)

class GUIThread(Thread):
    def __init__(self, logpath, charactername, status): 
        self.stopped = 1
        self.logpath = logpath
        self.charactername = charactername
        self.status = status
        Thread.__init__(self) 

    def exit(self):
        self.stopped = 1

    def run(self):
        self.stopped = 0
        prev = []
        while not self.stopped:
            l = [(os.stat(i).st_mtime, i) for i in glob.glob(os.path.join(self.logpath, '*.log'))]
            l.sort()
            diff = set(l).difference( set(prev) )
            if len(diff) > 0:
                self.status("Found " + str(len(l)) + " new logs.")
                prev = l
                files = [i[1] for i in diff]
                readLogFile(files, 'battle', self.charactername)
            start = datetime.datetime.now()
            self.status("Waiting for new log data...")
            while (datetime.datetime.now() - start).seconds < 60:
                time.sleep(1)
                if self.stopped:
                    break

def main():
    global doloop
    args = sys.argv[1:]

    if len(args) < 1:
        doloop = 1
        app = wx.App()
        frame = MainFrame(None, "FFXIV Log Parser")
        app.MainLoop()
        return
    if args[0] == '?' or args[0] == 'h' or args[0] == '/?' or args[0] == '/h' or args[0] == '/help' or args[0] == 'help' or args[0] == '-h' or args[0] == '-help' or args[0] == '--help':
        print "\r\nUsage: CharacterName PathToLogFiles LogDataType RunForever[True/False] FilterByMonster[optional]"
        print "Example: python \"c:\\Users\\<youruser>\\Documents\\My Games\\Final Fantasy XIV\\user\\<yourcharid>\\log\\\" battle true\r\n"
        print "Available LogDataTypes:\nbattle - view battle logs.\nchat - all chat logs.\nlinkshell - linkshell chat logs.\nsay - say chat logs.\nparty - Party chat logs.\n"
        print "Examples of FilterByMonster:\n\"ice elemental\"\n\"fat dodo\"\n\"warf rat\"\n"
        return
    
    # assign args to nice names
    charactername = args[0]
    logpath = args[1]
    logdatatype = args[2]
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
            readLogFile(files, logdatatype, charactername, logmonsterfilter=logmonsterfilter)
        if not doloop:
            break
        time.sleep(60)

"""
20 = "ready (inswert combat skill)..." as well as loot obtain
42= all SP and EXP gain notices by you 
45= defeated message
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

defaultmonster = {"charactername":"", "datetime":"", "monster":"", "monstermiss":0, "othermonstermiss":0, "damage":[], "miss":0, "hitdamage":[], "otherdamage":[], "othermiss":0, "otherhitdamage":[], "skillpoints":0, "class":"", "exp":0}
defaultcrafting = {"charactername":"", "datetime":"", "item":"", "actions":[], "ingredients":[], "success":0, "skillpoints":0, "class":"", "exp":0}
uploaddata = []

def printCrafting(currentcrafting):
    #print currentcrafting
    #raw_input("")
    return

def printDamage(currentmonster):
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
        if currentmonster["miss"] > 0:
            hitpercent = int((float(currentmonster["miss"]) / float(len(currentmonster["damage"]))) * 100)
            hitpercent = (100 - hitpercent)
        print "Defeated %s as %s\nHit %%: %i%%\nTotal Avg Dmg: %i\nCrit Avg Dmg: %i\nReg Avg Dmg: %i\nTotal Hit Dmg Avg: %i\nCrit Hit Dmg Avg: %i\nHit Dmg Avg: %i\nTotal Dmg From Others: %i\nMisses By Others: %i\nExp: %i\nSkill Points: %i\nDate Time: %s\n" % (currentmonster["monster"], currentmonster["class"], hitpercent, totaldmgavg, criticaldmgavg, regulardmgavg, totalhitdmgavg, crithitdmgavg, hitdmgavg, othertotaldmg, currentmonster["othermiss"], currentmonster["exp"], currentmonster["skillpoints"], currentmonster["datetime"])
        uploaddata.append(currentmonster)



def readLogFile(paths, logdatatype, charactername, logmonsterfilter = None):
    exptotal = 0
    damagepermob = 0
    damageavgpermob = 0
    craftingcomplete = 0
    synthtype = ""
    progress = []
    quality = []
    durability = []
    defeated = False
    expset = False
    spset = False
    currentmonster = copy.deepcopy(defaultmonster)
    currentcrafting = copy.deepcopy(defaultcrafting)
    for logfilename in paths:
        logfiletime = os.stat(logfilename).st_mtime
        logfile = open(logfilename, 'r')
        logdata = logfile.read()
        logdata = logdata.split("00")
        for logitem in logdata[1:]:
            if logdatatype == "battle":
                #print logitem
                #if logitem.find("Welcome") != -1:
                #    raw_input("welcome")
                if logitem.startswith("20::"):
                    if logitem.find("engaged") != -1:
                        if craftingcomplete == 1:
                            printCrafting(currentcrafting)
                            currentcrafting = copy.deepcopy(defaultcrafting)
                            currentcrafting["datetime"] = time.strftime("%m/%d/%y %H:%M:%S",time.localtime(logfiletime))
                            craftingcomplete = 0
                        if logitem.find("You cannot change classes") != -1 or logitem.find("Levequest difficulty") != -1:
                            continue
                        if defeated and spset:
                            defeated = False
                            spset = False
                            printDamage(currentmonster)

                        currentmonster = copy.deepcopy(defaultmonster)
                        currentmonster["charactername"] = charactername
                        currentmonster["datetime"] = time.strftime("%m/%d/%y %H:%M:%S",time.localtime(logfiletime))
                        currentmonster["monster"] = logitem[logitem.find("The ") +4:logitem.find(" is")]
                        currentmonster["monster"] = currentmonster["monster"].split('\'')[0]
                    #elif logitem.find("your class to ") != -1:
                    #	currentmonster["class"] = logitem[logitem.find("class to ")+9:-1]
                    #	currentcrafting["class"] = logitem[logitem.find("class to ")+9:-1]
                    #	raw_input("ingredients")
                    elif logitem.find("You use") != -1:
                        if craftingcomplete == 1:
                            printCrafting(currentcrafting)
                            currentcrafting = copy.deepcopy(defaultcrafting)
                            currentcrafting["datetime"] = time.strftime("%m/%d/%y %H:%M:%S",time.localtime(logfiletime))
                            craftingcomplete = 0
                        if logitem.find("Standard Synthesis") != -1:
                            # store previous value if valid:
                            if synthtype != "":
                                currentcrafting["actions"].append([synthtype, progress, durability, quality])
                                progress = []
                                durability = []
                                quality = []
                            synthtype = "Standard"
                        elif logitem.find("Rapid Synthesis") != -1:
                            if synthtype != "":
                                currentcrafting["actions"].append([synthtype, progress, durability, quality])
                                progress = []
                                durability = []
                                quality = []
                            synthtype = "Rapid"
                        elif logitem.find("Bold Synthesis") != -1:
                            if synthtype != "":
                                currentcrafting["actions"].append([synthtype, progress, durability, quality])
                                progress = []
                                durability = []
                                quality = []
                            synthtype = "Bold"
                        else:
                            print logitem
                            # TODO: need to handle all special types or they will be ingredients, setup
                            # an array with all traits and abilities and compare.
                            if logitem.find("You use a") != -1:
                                ingcount = 1
                            elif logitem.find("Touch Up") != -1:
                                continue
                            else:
                                ingcount = int(logitem.split(" ")[2])
                            if logitem.find(" of ") != -1:
                                ingredient = logitem[logitem.find(" of ") +4:-1]
                            else:
                                ingredient = " ".join(logitem.split(" ")[3:])[:-1]
                            currentcrafting["ingredients"].append([ingredient, ingcount])
                    elif logitem.find("Progress") != -1:
                        # save progress as array of % and it was an increase or decrease
                        if logitem.find("increases") != -1:
                            progress = [logitem[logitem.find("by ") +3:-2], 1]
                        else:
                            progress = [logitem[logitem.find("by ") +3:-2], 0]
                    elif logitem.find("Durability") != -1:
                        if logitem.find("increases") != -1:
                            durability = [logitem[logitem.find("by ") +3:-1], 1]
                        else:
                            durability = [logitem[logitem.find("by ") +3:-1], 0]
                    elif logitem.find("Quality") != -1:
                        if logitem.find("increases") != -1:
                            quality = [logitem[logitem.find("by ") +3:-1], 1]
                        else:
                            quality = [logitem[logitem.find("by ") +3:-1], 0]
                    else:
                        pass
                        #print logitem
                elif logitem.startswith("42::") or logitem.startswith("43::"):
                    if logitem.startswith("42::"):
                        logitem = logitem.strip("42::")
                    elif logitem.startswith("43::"):
                        logitem = logitem.strip("43::")
                    pos = logitem.find("You gain")
                    if pos > -1:
                        points = ""
                        skill = ""
                        if logitem.find("experience") > -1:
                            points = logitem[9:logitem.find("experience") -1]
                            #exptotal += int(points)
                            currentmonster["exp"] = int(points)
                            currentcrafting["exp"] = int(points)
                            expset = True
                        elif logitem.find("skill") > -1:
                            logitemparts = logitem.split(" ")
                            currentmonster["skillpoints"] = int(logitemparts[2])
                            currentmonster["class"] = logitemparts[3]
                            currentcrafting["skillpoints"] = int(logitemparts[2])
                            currentcrafting["class"] = logitemparts[3]
                            spset = True
                elif logitem.startswith("45::") or  logitem.startswith("44::"):
                    if craftingcomplete == 1:
                        printCrafting(currentcrafting)
                        currentcrafting = copy.deepcopy(defaultcrafting)
                        currentcrafting["datetime"] = time.strftime("%m/%d/%y %H:%M:%S",time.localtime(logfiletime))
                        craftingcomplete = 0
                    if logitem.find("group") != -1:
                        continue
                    if logitem.find("defeat") != -1:
                        monster = logitem[logitem.find("The ") +4:logitem.find(" is defeat")].split('\'')[0]
                        if logmonsterfilter:
                            if monster != logmonsterfilter or monster != currentmonster["monster"]:
                                continue
                        defeated = True
                elif logitem.startswith("46::"):
                    print logitem
                    # Crafting success
                    if logitem.find("You create") != -1:
                        if logitem.find(" of ") != -1:
                            currentcrafting["item"] = logitem[logitem.find(" of ")+4:-1]
                        else:
                            currentcrafting["item"] = logitem[logitem.find(" a ")+3:-1]
                        currentcrafting["success"] = 1
                    # botched it
                    if logitem.find("botch") != -1:
                        currentcrafting["success"] = 0
                    craftingcomplete = 1
                elif logitem.startswith("50::"):
                    if logitem.find("your") != -1 or logitem.find("Your") != -1:
                        logitem = logitem.strip("50::")
                        if logitem.find("from the ") != -1:
                            monster = logitem[logitem.find("the ") +4:logitem.find(" from the")]
                        else:
                            monster = logitem[logitem.find("the ") +4:logitem.find(" for")]
                        if monster == currentmonster["monster"]:						
                            if logitem.find("Critical!") != -1:
                                critical = 1
                            else:
                                critical = 0
                            attacktype = logitem[logitem.find("Your ") +5:logitem.find(" hits")]
                            if logitem.find(" points") != -1:
                                damage = logitem[logitem.find("for ") +4:logitem.find(" points")]
                                currentmonster["damage"].append([damage, critical, attacktype])
                elif logitem.startswith("51::"):
                    if logitem.find("hits you") != -1:
                        logitem = logitem.strip("51::")
                        if logitem.find("points") == -1:
                            continue
                        monsterhit = logitem[logitem.find("The ") +4:logitem.find(" hits")]
                        monster = monsterhit.split('\'')[0]
                        attacktype = monsterhit[monsterhit.find("'s ")+3:]
                        if monster == currentmonster["monster"]:
                            hitdamage = logitem[logitem.find("for ") +4:logitem.find(" points")]
                            if logitem.find("Critical!") != -1:
                                critical = 1
                            else:
                                critical = 0
                            currentmonster["hitdamage"].append([hitdamage, critical, attacktype])
                elif logitem.startswith("52::"):
                    logitem = logitem.strip("52::")
                    if logitem.find("from the ") != -1:
                        monster = logitem[logitem.find("the ") +4:logitem.find(" from the")]
                    else:
                        monster = logitem[logitem.find("the ") +4:logitem.find(" for")]
                    if monster == currentmonster["monster"]:						
                        if logitem.find("Critical!") != -1:
                            critical = 1
                        else:
                            critical = 0
                        #print logitem
                        #raw_input("damage");
                        attacktype = logitem[logitem.find("'s ") +3:logitem.find(" hits")]
                        if logitem.find(" points") != -1:
                            damage = logitem[logitem.find("for ") +4:logitem.find(" points")]
                            currentmonster["otherdamage"].append([damage, critical, attacktype])
                elif logitem.startswith("53::"):
                    if logitem.find("hits ") != -1:
                        logitem = logitem.strip("53::")
                        if logitem.find("points") == -1:
                            continue
                        monsterhit = logitem[logitem.find("The ") +4:logitem.find(" hits")]
                        monster = monsterhit.split('\'')[0]
                        attacktype = monsterhit[monsterhit.find("'s ")+3:]
                        if monster == currentmonster["monster"]:
                            if logitem.find("Critical!") != -1:
                                critical = 1
                            else:
                                critical = 0
                            if logitem.find(" points") != -1:
                                hitdamage = logitem[logitem.find("for ") +4:logitem.find(" points")]
                                currentmonster["otherhitdamage"].append([hitdamage, critical, attacktype])
                        
                elif logitem.startswith("56::"):
                    monster = logitem[logitem.find("the ") +4:logitem.find(".")].split('\'')[0]
                    if monster == currentmonster["monster"]:
                        currentmonster["miss"] += 1
                elif logitem.startswith("58::"):
                    monster = logitem[logitem.find("the ") +4:logitem.find(".")].split('\'')[0]
                    if monster == currentmonster["monster"]:
                        currentmonster["othermiss"] += 1
                #elif logitem.startswith("59::"):
                #	monster = logitem[logitem.find("the ") +4:logitem.find(".")].split('\'')[0]
                #	if monster == currentmonster["monster"]:
                #		currentmonster["othermiss"] += 1
                # TODO: Do something with healing -- EVERYTHING BELOW THIS LINE NEEDS TO BE ADDED!
                elif logitem.startswith("5C::"):
                    if logitem.find("You absorb") != -1:
                        healing = logitem[logitem.find("absorb ") +7:logitem.find(" HP")]
                elif logitem.startswith("5D::"):
                    if logitem.find("You recover") != -1:
                        healing = logitem[logitem.find("recover ") +8:logitem.find(" HP")]
                elif logitem.startswith("5E::"):
                    if logitem.find("recovers") != -1:	
                        othershealing = logitem[logitem.find("recovers ") +9:logitem.find(" HP")]
                elif logitem.startswith("63::"):
                    if logitem.find("grants you") != -1:	
                        effect = logitem[logitem.find("effect of ") +10:-1]
                elif logitem.startswith("64::"):
                    if logitem.find("grants") != -1:
                        effect = logitem[logitem.find("effect of ") +10:-1]
                    if logitem.find("inflicts") != -1:
                        monsteraffliction = logitem[logitem.find("effect of ") +10:-1]
                elif logitem.startswith("69::"):
                    if logitem.find("inflicts you") != -1:
                        affliction = logitem[logitem.find("effect of ") +10:-1]
                elif logitem.startswith("6B::"):
                    if logitem.find("inflicts") != -1:
                        othersaffliction = logitem[logitem.find("effect of ") +10:-1]
                else:
                    pass
                    #print logitem
                    '''0020::You have received the required materials.
                    0047::Mie Miqolatte creates a trapper's tunic.
                    001B::Zilbelt Stanford bows courteously to Maisenta.
                    0020::You use Standard Synthesis. The attempt succeeds!
                    0020::Progress increases by 10%.
                    0020::Durability decreases by 4.
                    0020::Quality increases by 3.
                    0020::You use Standard Synthesis. The attempt succeeds!
                    0020::Progress increases by 17%.
                    0020::Quality increases by 5.
                    001B::Zilbelt Stanford bows courteously to Maisenta.
                    0020::You use Standard Synthesis. The attempt fails!
                    0020::Progress increases by 3%.
                    0020::Durability decreases by 13.0020::You use Standard Synthesis. The attempt succeeds!0020::Progress increases by 17%.0020::Durability decreases by 4.0020::Quality increases by 4.0020::You use Standard Synthesis. The attempt fails!0020::Progress increases by 8%.0020::Durability decreases by 10.0020::You use Standard Synthesis. The attempt fails!0020::Progress increases by 8%.0020::Durability decreases by 11.001B::Zilbelt Stanford bows courteously to Maisenta.0020::You use Standard Synthesis. The attempt succeeds!0020::Progress increases by 16%.0020::Durability decreases by 4.0020::Quality increases by 4.0020::You use Standard Synthesis. The attempt fails!0020::Progress increases by 5%.0020::Durability decreases by 11.0020::You use Standard Synthesis. The attempt fails!0020::Progress increases by 6%.0020::Durability decreases by 12.0020::The harnessed Earth element becomes unstable!0020::You use Standard Synthesis. 0020::Progress increases by 11%.
                    0020::Durability decreases by 9.0020::Quality increases by 2.0046::You create a silver wristlet.0020::The appraisal of your synthesized items increases by 4. (Total: 4)0020::â€œThe Band's Bandsâ€ synthesis successful. (1 of 4)0042::You gain 436 goldsmithing skill points.0042::You gain 1909 experience points.
                    '''
            if logdatatype == "chat":
                if logitem.startswith("04:") or logitem.startswith("01:") or logitem.startswith("0F:"):
                    logitemparts = logitem.split(":")
                    print "User: " + logitemparts[1]
                    print "Message: " + ":".join(logitemparts[2:])
            if logdatatype == "party":
                if logitem.startswith("04:"):
                    logitemparts = logitem.split(":")
                    print "User: " + logitemparts[1]
                    print "Message: " + ":".join(logitemparts[2:])
            if logdatatype == "say":
                if logitem.startswith("01:"):
                    logitemparts = logitem.split(":")
                    print "User: " + logitemparts[1]
                    print "Message: " + ":".join(logitemparts[2:])
            if logdatatype == "linkshell":
                if logitem.startswith("0F:"):
                    logitemparts = logitem.split(":")
                    print "User: " + logitemparts[1]
                    print "Message: " + ":".join(logitemparts[2:])

        logfile.close()
    uploadToDB()

def uploadToDB():
    global doloop
    if not doloop:
        response = raw_input("Do you wish to display raw data? [y/N]: ")
    else:
        response = "no"
    jsondata = json.dumps(uploaddata)
    if response.upper() == "Y" or response.upper() == "YES":
        print "JSON encoded for upload:"
        print jsondata
    if not doloop:
        response = raw_input("\nDo you wish to upload the data printed above? [Y/n]: ")
    else:
        response = "YES"
    if response == "" or response.upper() == "Y" or response.upper() == "YES":
        url = doUpload(jsondata)
        #if not doloop:
        print "\nTotal Global Battle Records: %s" % url["totalbattlerecords"]
        print "Records Sent (Duplicates ignored): %s" % url["recordsimported"]
        print "Records Uploaded To Website: %s" % url["updatedrecords"]
        if int(url["updatedrecords"]) > 0:
            print "\nYour data has been uploaded, you can view it at: \n\n%s\n" % url["url"] 
        else:
            print "\nNo new records. You can view your data at: \n\n%s\n" % url["url"] 
    else:
        print "Your data will not be sent."

def doUpload(jsondata):

    url = 'http://50.16.215.246/postlog.php'
    user_agent = 'Mozilla/4.0 (compatible; MSIE 5.5; Windows NT)'
    values = {'jsondata' : jsondata }
    headers = { 'User-Agent' : "H3lls Log Parser" }

    data = "jsondata=%s" % jsondata
    req = urllib2.Request(url, data, headers)
    response = urllib2.urlopen(req)
    jsonresults = response.read()
    print jsonresults
    #exit()
    return json.loads(jsonresults)

if __name__ == '__main__':
    main()



