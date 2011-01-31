# Log Parser Basics #

The logs that FFXIV produces have some issues that prevent deep statistics. A few notes on this:

There is no date/time for each log entry. Without this basic information it is not possible to gather information such as DPS.
There is no unique ID for each monster being attacked. This proves quite troublesome if you are attacking multiple monsters in the same group at the same time. This often shows up when fighting during Behest battles because each group has multiple of the same creature. This doesn't allow clean differentiation between one kill and the next. Because of this there will sometimes be missing or incomplete information. The log parser does what it can to extract the information about these but will often leave areas empty or missing.
The log format does not include damage due to damage over time. Because of this you will not see the total damage being done to you or the monster if a DOT is used.
The data gathered by the log viewer is reduced to just a small fraction of the overall log. An example output of a log entry being sent would be:

### Example Data ###

[{"monster": "brine bogy", 
"charactername": "Joe User", 
"damage": [["25", 0], ["27", 0]], 
"datetime": "12/23/10 22:40:33", 
"skillpoints": 192, 
"exp": 479, 
"hitdamage": [["29", 0], ["29", 0]], 
"miss": 1, 
"class": "hand-to-hand"}]

Below we discuss what each of these are and how they are used.

* monster - Name of the monster being attacked.
* charactername - Your character name you provided when you started the log parser.
* damage - An array of each hit and if it was a critical hit. If it is critical it will show a 1.
* datetime - This is the date/time the data was gathered not when it happened. Since the log doesn't contain this we use it mostly for reference.
* skillpoints - The total number of skill points gained from killing this monster.
* exp - The total number of experience points gained from killing this monster.
* hitdamage - The amount of damage your character took while fighting this monster. If it is a critical it will show a 1.
* miss - the total number of times your character missed when attacking.
* class - the class your character was using when fighting this monster.

The damage is sent as individual values so we can calculate the average for each type of hit(critical or not) and the overall. This is also true for the hitdamage which is used to calculate the average as well as totals for each fight. The miss number is used to determine the % accuracy of your hits based on the total number of hits you took.

# What Happens to my Data? #

The log data that is uploaded gets added to a database of all users. This is then used to display the information listed on the Character Battle Stats page. We do not show the actual user data that is being uploaded and it is not a requirement that you upload the data under your own character name. For consistency you should always use the same character name when uploading your data so we can prune and keep out duplicates.

# How the Script Works #

The script parses the logs one entry at a time and determines a code. This code tells you what type of data it is reading and then it parses the log text for the details such as damage, monster names and the like. The script has two modes. The windows mode is very simple and it will silently gather data in the background every minute and determine if there is anything new to upload. If it finds new data it will upload it and start from there.

You can also run it from the command line to have a more detailed view of what the log parser is doing. In this mode it will also let you see more information than the windowed version. You can parse out chat logs, battle information and filter on specific monsters. It will also ask if you want to upload the information. If you do not want to and just wish to view the data you can tell it that you do not want to upload and it will spit out the raw data to your screen.

### Command Line Parameters ###

Usage:
CharacterName PathToLogFiles LogDataType RunForever[True/False] FilterByMonster[optional]
Example: 
python logparse.py "c:\Users\\Documents\My Games\Final Fantasy XIV\user\\log\" battle false
Available LogDataTypes:
battle - view battle logs.
chat - all chat logs.
linkshell - linkshell chat logs.
say - say chat logs.
party - Party chat logs.

Examples of FilterByMonster: "ice elemental" "fat dodo" "warf rat"
if you are running the executable version an example would be:
logparse.exe "c:\Users\\Documents\My Games\Final Fantasy XIV\user\\log\" battle false