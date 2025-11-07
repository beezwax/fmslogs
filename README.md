# fmslogs
Display and configure FileMaker Server logs

Consolidates access to various logs with no dependencies other than the core Python libraries. Goal is to be cross-platform, supporting all three server environments: macOS, Ubuntu, and Windows

Some things that it does that using just tail, head, or Get-Content don't:
- displays headers for columns
- uses tab stops that give consistent column values
- quicker access since you don't have to type full log path
- limit messages those only after a given timestamp or duration
- lists size and modification dates for all logs

## WORK IN PROGRESS

Currently Not Working:
- `-b` or `--begin`: start at first message on or after time or time interval
- `-m` or `--merge`: combine output of two or more logs based on timestamp
- `-s` or `--set`: set log options
- `-t` or `--tail`: follow log
- `--truncate`: truncate longer lines instead of wrapping them
 
---

```
usage: fmslogs [-f FILTER] [-h [HEAD ...]] [--help] [-l] [-L] [-m] [-r RANGE] [-S SET] [-s] [-t] [--truncate] [-v] [LOG1] [LOG2]
               [{access,admin,clientstats,dapi,events,fac,fmodatadebug,fmsadmindebug,fmsasedebug,fmscwpc,fmscwpcli,fmsdebug,fmsgetpasskeyebug,fmshdebug,fmshelper,fmslogdebug,fmwipd,install,loadschedules,odata,scriptevent,stats,stderr,stdout,topcall,trimlog,wpe,wpedebug,interval,clientstats,fmsdebug,logsize,topcall}]
               
View FileMaker Server logs and set logging options

positional arguments:
  {access,admin,clientstats,dapi,events,fac,fmodatadebug,fmsadmindebug,fmsasedebug,fmscwpc,fmscwpcli,fmsdebug,fmsgetpasskeyebug,fmshdebug,fmshelper,fmslogdebug,fmwipd,install,loadschedules,odata,scriptevent,stats,stderr,stdout,topcall,trimlog,wpe,wpedebug,interval,clientstats,fmsdebug,logsize,topcall}

options:
  -b, --begin BEGIN     start at first message on or after time or time interval in BEGIN
  -f, --filter FILTER   only return lines matching regex expression FILTER
  -h, --head            display the start of the specified log files instead of its tail
  --help                display command details
  -H, --headers-off     turn off headers for all logs
  -l, --list            list all log files, including size, date created & modified, sorted by modification time
  -L, --lognames        list log names supported by command
  -m, --merge           combine output of two or more logs
  -r, --range RANGE     range or number of lines to print
  -S, --set SET         change log configuration option
  -s, --succinct        strip less useful details from log output
  -t, --tail            wait for any new messages after printing current end of log
  --truncate            cut off any output if beyond width of screen
  -v, --version         version info
```

---

