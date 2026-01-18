# fmslog
## Display FileMaker Server logs & resource usage

Some things that it does that using just tail, head, or Get-Content don't:
- displays headers for columns, even if not showing first row
- improved formatting, including consistent column alignments
- quickly display or open logs in editor (don't have to type full log path)
- limit messages to those only after a given timestamp or duration
- lists path, size, and modification dates for all logs
- optionally truncate lines to avoid line wrap
- network ports in use
- sizes of database directories
- connectivity tests for 10 different FMS endpoints
- list versions of FMS components (NodeJS, Tomcat, etc.)

Design Goals:
- very simple installation
- support all three server environments: macOS, Ubuntu, and Windows
- consolidates access to various logs
- no waiting for logs to import

---

## REFERENCES & RELATED

* FMS Help - Event log: https://help.claris.com/en/server-help/content/monitor-event-log.html
* FMS Help - Monitoring FileMaker Server: https://help.claris.com/en/server-help/content/monitor-server.html
* General Web Publishing Settings for Server: https://support.claris.com/s/answerview?anum=000023506
* Log Viewer for Claris FileMaker: https://luminfire.com/our-solutions/claris-filemaker-log-viewer/
* Ports used by FileMaker Server: https://help.claris.com/en/server-installation-configuration-guide/content/ports-used-by-server.html
* Top Call statistics logging: https://support.claris.com/s/answerview?anum=000025776
* Tracking activity in log files in FileMaker Server: https://support.claris.com/s/article/Tracking-activity-in-log-files-in-FileMaker-Server-1503692942153

---

## CURRENT ISSUES

Current functionality with major issues:
- `-b` or `--begin`: only working with durations (eg, 'd' or '1d' for 1 day)
- `-B` or `--backups`: may list backup sets twice if target dir is used more than once but using different path
- `-C` or `--check-connectivity`: VPN connection may confuse tests
- `-m` or `--merge`: not implemented
- `-S` or `--set`: not working except for `enable/disable debuglogging`
- `-s` or `--succinct`: partially implemented
- `--ssh`: not implemented
- `-t` or `--tail`: does not print current log segment before starting to follow/tail
- nginx/apache/IIS: log parsing not fully implemented

---

## INSTALLATION

### macOS

Copy the latest version of the `fmslog` file to a directory in user's command PATH:

* macOS: `sudo curl -o /usr/local/bin/fmslog https://raw.githubusercontent.com/beezwax/fmslog/refs/heads/main/fmslog && sudo chmod +x /usr/local/bin/fmslog`
* Ubuntu: `sudo curl -o /usr/bin/fmslog https://raw.githubusercontent.com/beezwax/fmslog/refs/heads/main/fmslog && sudo chmod +x /usr/bin/fmslog`

Requires Python 3.9 or newer.

---

## OPTIONS & PARAMETERS

```
usage: fmslog [-b BEGIN] [-e EDIT] [-f FILTER] [-h] [-H] [--help] [-l] [-L] [-m] [-n NUMBER] [-p PASSWORD] [-S SET] [-s] [--ssh SSH] [-t] [--tail TAIL] [--truncate] [-u USER] [-N] [-v] [logs ...]
              [logname]
               
View FileMaker Server logs and set logging options

positional arguments (log name):
  {access,admin,clientstats,dapi,event,fac,fmodatadebug,fmsadmindebug,fmsasedebug,fmscwpc,fmscwpcli,fmsdebug,fmsgetpasskeyebug,fmshdebug,fmshelper,fmslogdebug,fmwipd,httpaccess,httpdctlerr,httpdctlout,httperror,httpsslaccess,httpsslerror,install,httpaccess,loadschedules,odata,scriptevent,stats,stderr,stdout,topcall,trimlog,wpe,wpedebug,interval,clientstats,fmsdebug,logsize,topcall}

options:
  -B, --backups             list scheduled backup sets present
  -b, --begin BEGIN         start at first message on or after time or time interval in BEGIN
  -C, --check-connectivity	test connectivity to FMS components
  -D, --data                list directories being used for databases, external container data, documents, and temp files
  -e, --edit                open the log in a text editor; first try $EDITOR, then GUI editor (macOS), then nano
  -f, --filter FILTER       only return lines matching regex expression FILTER
  --go						go (cd) to the directory of the named log
  -h, --head                display the start of the specified log files instead of its tail
  --help                    display command details
  -H, --headers-off         turn off headers for all logs
  -l, --list                list all log files, including size, date created & modified, sorted by modification time
  -n, --number RANGE        quantity of lines to print
  -N, --network             network usage info
  -p, --process-info		metrics for FMS processes
  -S, --set SET             change log configuration options
  -s, --succinct            strip less useful details from log output (partially implemented)
  -t, --tail                wait for any new messages after printing current end of log
  --truncate                cut off any output if beyond width of screen
  -V, --version             version info for fmslog and FMS components
```

---

### -B, --backups

List the paths and their sizes for any backup sets. Target paths are determined by scanning FMS' preferences file.

Disk usage calculations may overstate actual usage, since backup sets can use shared (hard linked) copies of the same data
if there were no changes between the backup sets and the backups were created with the same backup schedule.

On macOS, it is possible to have multiple target folders that FMS' will still resolve to the same location. Typically this is because
the boot drive had been renamed at some point.

### -b, --begin
Start printing logs on or after the given duration. Durations are an optional number followed by:
- 's': seconds from now
- 'm': minutes from now
- 'h': hours from now
- 'd': days since midnight today (e.g., '2d' would be from midnight yesterday)

### -C, --check-connectivity
Verify connectivity to various server components, and display SSL TLS version and hostnames. Where possible, both internal and external interfaces are checked, since
external connections are routed via a reverse proxy through the web server (Apache, IIS, NGINX). Also see the related -N/--network option.

### -D, --data
Using values based on the last relevant message in the Event log, display the current database directories being used and their sizes, splitting out any
optional external container directories.

### -e, --edit
Opens a log file in an editor. If the standard shell environment variable $EDITOR is set for the user, the file will be opened using that command.

Next, attempt to open using a GUI editor. On macOS, first check that there is a user logged in to the desktop, and if so, open the log file using TextEdit. For Windows, it will open the file using Notepad.

Finally, on Ubuntu and macOS, it will attempt to open the log using the Terminal based nano text editor.

### -f, --filter
For any subsequent logs, only display messages matching the given regular expression (regex).

Filtering will happen before any -n/--number limits are applied, or simplification if using --succinct.

The version of regex expressions used is similar to Perl's regex (often called PCRE), but is specific to Python.

### -h, --head
Display the start of the specified log files instead of its end (tail).

### -H, --headers-off
Disable the printing of any log column headers the command may use, and don't skip any column headers present in the log files.

Normally, unless tailing a log or printing a log that does not have any fixed columns, the command includes its own column header as the first line for each log.

### -l, --list
List all log names and paths for the current platform. For logs that are present, list their creation and modification timestamps and their size.

### -n, --number
Number of log message lines or screens to print. For screens, add 's' as a suffix, e.g. '-n 2s' for two screens. Since some messages may not fit current screen size
you may want to use the --truncate option to have an exact fit.

### -N, --network
List ports in use by FileMaker's processes.

### -p, --process-info
Display metrics for all processes running under the fmserver user. Metrics include process ID, CPU & memory usage, and process start time.

### -s, --succinct
Shorten the output of log lines where possible. This includes things like redundant time zones and host names, and shortening some values (eg, Warning becomes Warn).

### -S, --set VERB NOUN
Change FMS configuration options. It takes two parameters, a noun and a verb. Currently, verbs are `enable` or `disable`.
The only supported noun is `debuglogging` to enable the detailed FMS logs such as fmsDebug.log. When enabled, this will
significantly slow down some server operations and the log files can get large quickly.

### -t, --tail
Print messages as they are added to log files until user cancels with Ctrl-C.

Use the form `--tail=<seconds>` to set how many seconds to wait between checks for new data.

### --truncate
Remove any output from the end of the line that would cause a line wrap for the current screen width.

### -V, --version
Print version of fmslog command and FileMaker Server components.

---

![alt](display_logs.png?raw=true "Display Logs")

![alt](connectivity_check.png?raw=true "Connectivity Test")