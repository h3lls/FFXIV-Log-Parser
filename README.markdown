# Log Parser Basics #

The logs that FFXIV produces have some issues that prevent deep statistics. A few notes on this:

There is no date/time for each log entry. Without this basic information it is not possible to gather information such as DPS.
There is no unique ID for each monster being attacked. This proves quite troublesome if you are attacking multiple monsters in the same group at the same time. This often shows up when fighting during Behest battles because each group has multiple of the same creature. This doesn't allow clean differentiation between one kill and the next. Because of this there will sometimes be missing or incomplete information. The log parser does what it can to extract the information about these but will often leave areas empty or missing.
The log format does not include damage due to damage over time. Because of this you will not see the total damage being done to you or the monster if a DOT is used.
The data gathered by the log viewer is reduced to just a small fraction of the overall log. An example output of a log entry being sent would be:

The website to browse your log data can be found at: http://www.ffxivbattle.com/

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

# Developers (fellow log parsers) #

## Reading Binary Headers ##

There are a number of things this log parser does that handles just about every type of entry that the logs
output. Changes in the 3.2 version of the log parser introduced parsing of the binary header data to get the 
offsets. This offers a dramatic improvement on the quality of the output since it always knows the length of
the lines being parsed.  The important part of this is the actual reading of the header:

<!-- HTML generated using hilite.me --><div style="background: #111111; overflow:auto;width:auto;color:white;background:black;border:solid gray;border-width:.1em .1em .1em .8em;padding:.2em .6em;"><pre style="margin: 0; line-height: 125%">    <span style="color: #ffffff">logfile</span> <span style="color: #ffffff">=</span> <span style="color: #ffffff">open(logfilename,</span> <span style="color: #0086d2">&#39;rb&#39;</span><span style="color: #ffffff">)</span>
    <span style="color: #008800; font-style: italic; background-color: #0f140f"># read in the length of this files records</span>
    <span style="color: #ffffff">headerparts</span> <span style="color: #ffffff">=</span> <span style="color: #ffffff">struct.unpack(</span><span style="color: #0086d2">&quot;2l&quot;</span><span style="color: #ffffff">,</span> <span style="color: #ffffff">logfile.read(</span><span style="color: #0086f7; font-weight: bold">8</span><span style="color: #ffffff">))</span>
    <span style="color: #ffffff">headerlen</span> <span style="color: #ffffff">=</span> <span style="color: #ffffff">headerparts[</span><span style="color: #0086f7; font-weight: bold">1</span><span style="color: #ffffff">]</span> <span style="color: #ffffff">-</span> <span style="color: #ffffff">headerparts[</span><span style="color: #0086f7; font-weight: bold">0</span><span style="color: #ffffff">]</span>
    <span style="color: #ffffff">header</span> <span style="color: #ffffff">=</span> <span style="color: #ffffff">struct.unpack(str(headerlen)+</span><span style="color: #0086d2">&quot;l&quot;</span><span style="color: #ffffff">,</span> <span style="color: #ffffff">logfile.read(headerlen*</span><span style="color: #0086f7; font-weight: bold">4</span><span style="color: #ffffff">))</span>
    <span style="color: #008800; font-style: italic; background-color: #0f140f"># header * 4 bytes for each and another 8 bytes for the header size</span>
    <span style="color: #ffffff">offset</span> <span style="color: #ffffff">=</span> <span style="color: #ffffff">headerlen*</span><span style="color: #0086f7; font-weight: bold">4</span><span style="color: #ffffff">+</span><span style="color: #0086f7; font-weight: bold">8</span>
    <span style="color: #fb660a; font-weight: bold">for</span> <span style="color: #ffffff">headerpos</span> <span style="color: #ffffff">in</span> <span style="color: #ffffff">range(len(header)):</span>
        <span style="color: #fb660a; font-weight: bold">if</span> <span style="color: #ffffff">headerpos</span> <span style="color: #ffffff">==</span> <span style="color: #0086f7; font-weight: bold">0</span><span style="color: #ffffff">:</span>
            <span style="color: #ffffff">startbyte</span> <span style="color: #ffffff">=</span> <span style="color: #ffffff">offset</span>
            <span style="color: #ffffff">endbyte</span> <span style="color: #ffffff">=</span> <span style="color: #ffffff">header[headerpos]</span>
        <span style="color: #fb660a; font-weight: bold">else</span><span style="color: #ffffff">:</span>
            <span style="color: #ffffff">startbyte</span> <span style="color: #ffffff">=</span> <span style="color: #ffffff">offset</span> <span style="color: #ffffff">+</span> <span style="color: #ffffff">header[headerpos-</span><span style="color: #0086f7; font-weight: bold">1</span><span style="color: #ffffff">]</span>
            <span style="color: #ffffff">endbyte</span> <span style="color: #ffffff">=</span> <span style="color: #ffffff">header[headerpos]</span> <span style="color: #ffffff">-</span> <span style="color: #ffffff">header[headerpos-</span><span style="color: #0086f7; font-weight: bold">1</span><span style="color: #ffffff">]</span>
        <span style="color: #ffffff">logfile.seek(startbyte)</span>
        <span style="color: #ffffff">logitem</span> <span style="color: #ffffff">=</span> <span style="color: #ffffff">logfile.read(endbyte)[</span><span style="color: #0086f7; font-weight: bold">2</span><span style="color: #ffffff">:]</span>
</pre></div>

Using the struct import makes this a quick process to read the headers and loop through each log entry.  Once
it has been read it passes it to all available language parsers to interprit since there isn't a specific language
defined when the app starts up it has to assume every line is in any possible language.  From here it hits the
function_map which takes the code and maps it to a function call. Several of the function calls are ignored but all
are defined so if someone wants to know what each type of log entry does this is a great starting point. Eventually
all of the log types will be handled but for the statistics I am gathering this is good enough for now.

## Auto-Translate ##

The auto-translate functionality attempts to convert the binary values in the logs for auto-translate into actual 
text values.  In english this is 99% complete but needs to be moved to a binary file to make for a smaller parser
and to improve the parsing times.  It still is quite fast even with the conversion of the binary values and checking
but could be much better. The goal is to eventually have a reference for every language and output auto-translate 
values but this is a labor intensive process.  To do the conversion I type in game the auto-tranlate value in chat
parse that log line along with the value displayed in chat.  Then I add the binary value starting with 0x022E along
with the actual text into an array.  It would be much better to be able to parse out the values from a resource
file in game but I haven't found where they store these translations so for now it is a manual process.
