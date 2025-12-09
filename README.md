# fmslogs
## Display and configure FileMaker Server logs


Some things that it does that using just tail, head, or Get-Content don't:
- displays headers for columns, even if not showing first row
- uses custom tab stops for each log for consistent column alignments
- quick access to print or open in editor (don't have to type full log path or cd to correct directory)
- limit messages to those only after a given timestamp or duration
- lists size and modification dates for all logs
- optionally truncate lines to avoid line wrap

Design Goals:
- no dependencies other than the core Python libraries, and requiring just one file to be copied onto server
- support all three server environments: macOS, Ubuntu, and Windows
- consolidates access to various logs

---

## CURRENT ISSUES

Current functionality with major issues:
- `-b` or `--begin`: only working with durations (eg, 'd' or '1d' for 1 day)
- `-m` or `--merge`: not working
- `-S` or `--set`: not working
- `-s` or `--succinct`: not working
- `--ssh`: not working
- `-t` or `--tail`: does not print current log segment before starting to follow
- not including nginx/apache/IIS logs
 
---

```
usage: fmslogs [-b BEGIN] [-e EDIT] [-f FILTER] [-h] [-H] [--help] [-l] [-L] [-m] [-n NUMBER] [-p PASSWORD] [-S SET] [-s] [--ssh SSH] [-t] [--tail TAIL] [--truncate] [-u USER] [-N] [-v] [logs ...]
               [{access,admin,clientstats,dapi,events,fac,fmodatadebug,fmsadmindebug,fmsasedebug,fmscwpc,fmscwpcli,fmsdebug,fmsgetpasskeyebug,fmshdebug,fmshelper,fmslogdebug,fmwipd,install,loadschedules,odata,scriptevent,stats,stderr,stdout,topcall,trimlog,wpe,wpedebug,interval,clientstats,fmsdebug,logsize,topcall}]
               
View FileMaker Server logs and set logging options

positional arguments:
  {access,admin,clientstats,dapi,events,fac,fmodatadebug,fmsadmindebug,fmsasedebug,fmscwpc,fmscwpcli,fmsdebug,fmsgetpasskeyebug,fmshdebug,fmshelper,fmslogdebug,fmwipd,install,loadschedules,odata,scriptevent,stats,stderr,stdout,topcall,trimlog,wpe,wpedebug,interval,clientstats,fmsdebug,logsize,topcall}

options:
  -b, --begin BEGIN     start at first message on or after time or time interval in BEGIN
  -e, --edit            open the log in a text editor; first try $EDITOR, then GUI editor (macOS), then nano
  -f, --filter FILTER   only return lines matching regex expression FILTER
  -h, --head            display the start of the specified log files instead of its tail
  --help                display command details
  -H, --headers-off     turn off headers for all logs
  -l, --list            list all log files, including size, date created & modified, sorted by modification time
  -L, --lognames        list log names supported by command
  -n, --number RANGE    quantity of lines to print
  -N, --network         Network usage info
  -S, --set SET         change log configuration option
  -s, --succinct        strip less useful details from log output (partially implemented)
  --ssh SSH             use the connection string to fetch logs from remote server
  -t, --tail            wait for any new messages after printing current end of log
  --truncate            cut off any output if beyond width of screen
  -V, --version         version info
```

---

### -b, --begin
Start printing logs on or after the given duration. Durations are an optional number followed by:
- 's': seconds from now
- 'm': minutes from now
- 'h': hours from now
- 'd': days since midnight today (e.g., '2d' would be from midnight yesterday)

### -e, --edit
Opens a log file in an editor. If the standard shell environment variable $EDITOR is set for the user, the file will be opened using that command.

Next, attempt to open using a GUI editor. On macOS, first check that there is a user logged in to the desktop, and if so, open the log file using TextEdit. For Windows, it will open the file using Notepad.

Finally, on Ubuntu and macOS, it will attempt to open the log using the Terminal based nano text editor.

### -f, --filter
Only display messages matching the given regular expression (regex). Filtering will happen before any -r/--range limits are applied or simplification if using --succinct.

The version of regex expressions used is similar to Perl's regex (often called PCRE), but is specific to Python.

### -h, --head
Display the start of the specified log files instead of its end (tail).

### -H, --headers-off
Disable the printing of any log column headers the command may use, and don't skip any column headers present in the log files.

Normally, unless tailing a log or printing a log that does not have any fixed columns, the command includes its own column header as the first line for each log.

### -l, --list
List all log names, and for those where a log file is found, list their creation and modification timestamps and their size.

### -L, --lognames
List all log names known by the command for the current platform, followed by their full paths.

### -n, --number
Number of log message lines or screens to print. For screens, add 's' as a suffix, e.g. '-n 2s' for two screens. Since some messages may not fit current screen size
you may want to use the --truncate option to have an exact fit.

### -N, --network
List ports in use by FileMaker's processes.

### -s, --succinct
Shorten the output of log lines where possible. This includes things like redundant time zones and host names, and shortening some values (eg, Warning becomes Warn).

### -t, --tail
Print messages as they are added to log files until user cancels with Ctrl-C.

Use the form `--tail=<seconds>` to set how many seconds to wait between checks for new data.

### --truncate
Remove any output from the end of the line that would cause a line wrap for the current screen width.

### -V, --version
Print version and contact information for fmslogs command.