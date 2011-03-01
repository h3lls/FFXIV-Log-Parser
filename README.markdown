# Log Parser Basics #

The logs that FFXIV produces have some issues that prevent deep statistics. A few notes on this:

There is no date/time for each log entry. Without this basic information it is not possible to gather information such as DPS.
There is no unique ID for each monster being attacked. This proves quite troublesome if you are attacking multiple monsters in the same group at the same time. This often shows up when fighting during Behest battles because each group has multiple of the same creature. This doesn't allow clean differentiation between one kill and the next. Because of this there will sometimes be missing or incomplete information. The log parser does what it can to extract the information about these but will often leave areas empty or missing.
The log format does not include damage due to damage over time. Because of this you will not see the total damage being done to you or the monster if a DOT is used.
The data gathered by the log viewer is reduced to just a small fraction of the overall log. An example output of a log entry being sent would be:

### Example Data ###

[{
"monster": "curious galago",
"othermiss": [["That Char", "Heavy Strike"], ["Some Other", "Light Shot"], 
"otherhitdamage": [["51", 0, "Bleat", "Some Other"]], 
"othermonstermiss": 0, 
"damage": [["219", 0, "Light Shot"], ["205", 0, "Light Shot"]], 
"datetime": "02/21/11 02:36:56", 
"skillpoints": 331, 
"exp": 551, 
"hitdamage": [["423", 0, "Head Butt"]], 
"monstermiss": 0, 
"miss": 0, 
"class": "archery", 
"otherdamage": [["202", 0, "Aura Pulse", "Some Other"], ["21", 1, "Light Slash", "That Char"]]
}]

Below we discuss what each of these are and how they are used.

* monster - Name of the monster being attacked.
* othermiss - Other characters in the party that have missed and the type of attack.
* otherhitdamage - Attacks on others in your party, damage, critical, type of attack, party member.
* damage - An array of damage delt by you, Amount of damage, critical, type of attack.
* datetime - This is the date/time the data was gathered not when it happened. Since the log doesn't contain this we use it mostly for reference.
* skillpoints - The total number of skill points gained from killing this monster.
* exp - The total number of experience points gained from killing this monster.
* hitdamage - Array of hits taken by you, damage taken, critical, type of attack by the monster.
* miss - the total number of times your character missed when attacking.
* class - the class your character was using when fighting this monster.
* otherdamage - An array of damage delt by others in the party, Amount of damage, critical, type of attack, party member.

The damage is sent as individual values so we can calculate the average for each type of hit(critical or not) 
and the overall. This is also true for the hitdamage which is used to calculate the average as well as totals 
for each fight. The miss number is used to determine the % accuracy of your hits based on the total number of 
hits you took.

# What Happens to my Data? #

The log data that is uploaded gets added to a database of all users. This is then used to display the 
information listed on the Character Battle Stats page. We do not show the actual user data that is 
being uploaded and it is not a requirement that you upload the data under your own character name. 
For consistency you should always use the same character name when uploading your data so we can prune 
and keep out duplicates.

With the addition of a password the party data is sent as well.  The names on the website will only be shown if
you log in using character name and password. Otherwise it will show greek gods and titans in place of the names.

# How the Script Works #

The script parses the logs one entry at a time and determines a code. This code tells you what type of data 
it is reading and then it parses the log text for the details such as damage, monster names and the like. 
The script has two modes. The windows mode is very simple and it will silently gather data in the background 
every minute and determine if there is anything new to upload. If it finds new data it will upload it and 
start from there.

You can also run it from the command line to have a more detailed view of what the log parser is doing. In 
this mode it will also let you see more information than the windowed version. You can parse out chat logs, 
battle information and filter on specific monsters. It will also ask if you want to upload the information. 
If you do not want to and just wish to view the data you can tell it that you do not want to upload and it 
will spit out the raw data to your screen.

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