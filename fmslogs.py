# -*- Mode:Python; indent-tabs-mode:nil; tab-width:4; encoding:utf-8 -*-

"""
fmslogs.py

Display FileMaker Server logs and change logging options.

Created by Simon Brown on 10/15/2025.
"""

import argparse, curses, os, pathlib, platform, sys, time
from collections import OrderedDict

"""
non-standard install location?
'top' or iostat option
Show column headers if relevant
have merged logs


fmslogs [show|tail] all|access|dapi|events|fmsdebug|odata|topcall|wpe [-l|--last] [-h|head] [-t|tail]

fmslogs dapi # tail of log (but not following), printing as many lines as rows on screen
fmslogs -h access events
fmslogs -h -n 100 access events
fmslogs -s topcall 1 # enable TopCall.log

"""

FILTER_REGEX = ''
SCREENCOLS, SCREENROWS = os.get_terminal_size()
MAX_READ_LEN = 1048576*10
#LOG_CHOICES = ['access', 'admin', 'clientstats', 'dapi', 'events', 'install', 'odata', 'scriptevent', 'stats', 'stderr', 'stderrserverscripting', 'stdout', 'syslog', 'stats', 'topcall', 'wpe']

# Default deployment paths (Windows paths will have forward slashes converted)
DEF_BASE_PATHS = {
    'Darwin': '/Library/FileMaker Server',
    'Linux': '/opt/FileMaker/FileMaker Server',
    'Windows': 'C:/Programs/FileMaker/FileMaker Server'
}

# This may get overridden by user option,
BASE_PATH = DEF_BASE_PATHS [platform.system()]

LOG_HEADERS = {
    'access': 'TIMESTAMP                        LEVEL         CODE    MESSAGE',
    'admin': 'TIMESTAMP                   {LEVEL} {COMP} {ADDRESS}   {ENDPOINT}    {TYPE}    {CODE}  MESSAGE',
    'clientstats': 'Timestamp    Network Bytes In    Network Bytes Out    Remote Calls    Remote Calls In Progress    Elapsed Time    Wait Time    I/O Time    Client name',
    'events': 'TIMESTAMP                ZONE    LEVEL         CODE    HOSTNAME                       MESSAGE',
    'fmdapi': 'TIMESTAMP    ERROR    LEVEL    IP_ADDRESS    USER    HTTP    MESSAGE    USAGE'
    'fmodata': 'TIMESTAMP                        CODE    LEVEL   ADDRESS             OP     ENDPOINT       SIZE',
    'fmshelper': 'TIMESTAMP                ZONE MESSAGE'
    'loadschedules': 'MESSAGE',
    'scriptevent': 'TIMESTAMP                ZONE    CODE MESSAGE',
    'stats': 'TIMESTAMP                ZONE NET KB/s In    NET KB/s OUT    DISK KB/s READ    DISDK KB/s WRITE    CACHE HIT %    CACHE UNSAVED %    PRO CLIENTS    OPEN DBS    XDBC CLIENTS    WEBD CLIENTS    CWP CLIENTS    REMOTE CALLS/s    IN PROGRESS    ELAPSED TIME    WAIT TIME    I/O TIME    GO CLIENTS',
    'stderrserverscripting': 'MESSAGE',
}

LOG_PATHS_STANDARD = {
    'access': 'Logs/Access.log',
    'admin': 'Admin/FAC/logs/fac.log',
    'clientstats': 'Logs/ClientStats.log',
    'dapi': 'Logs/fmdapi.log',
    'events': 'Logs/Event.log',
    'fac': 'Admin/FAC/logs/fac.log',
    'fmsadmindebug': 'Database Server/bin/fmsadminDebug.log',
    'fmsasedebug': 'Database Server/bin/fmsaseDebug.log',
    'fmscwpc': 'Database Server/bin/fmscwpc',
    'fmscwpcli': 'Database Server/bin/fmscwpcli.log',
    'fmslogdebug': 'Database Server/bin/fmslogDebug.log',
    'fmsdebug': 'Database Server/bin/fmsDebug',
    'fmwipd': 'Database Server/bin/fmwipd.log',
    'fmsgetpasskeyebug': 'Database Server/bin/fmsgetpasskeyDebug.log',
    'fmshdebug': 'Database Server/bin/fmshDebug.log',
    'fmshelper': 'Logs/fmshelper.log',
    'fmslogdebug': 'Database Server/bin/fmslogDebug.log',
    'fmodatadebug': 'Database Server/bin/fmodataDebug.log',
    'fmsgetpasskeyebug': 'Database Server/bin/fmsgetpasskeyDebug.log',
    'loadschedules': 'Logs/LoadSchedules.log',
    'install': 'Logs/install.log',
    'odata': 'Logs/fmodata.log',
    'scriptevent': 'Logs/scriptEvent.log',
    'stats': 'Logs/Stats.log',
    'topcall': 'Logs/TopCallStats.log',
    'trimlog': 'Database Server/bin/trimlog.log',
    'wpe': 'Logs/wpe0.log',
    'wpedebug': 'Logs/wpe_debug.log'
}

LOG_PATHS_LINUX = {
    'stderrserverscripting': 'Logs/StdErrServerScripting.log',
    'stdoutserverscripting': 'Logs/StdOutServerScripting.log',
#    'syslog': '/var/log/syslog'
}
LOG_PATHS_LINUX.update (LOG_PATHS_STANDARD)

LOG_PATHS_DARWIN = {
    'stderr': 'Logs/stderr',
    'stdout': 'Logs/stdout',
#    'syslog': '/var/log/system.log'
}

LOG_PATHS_DARWIN.update (LOG_PATHS_STANDARD)

LOG_PATHS_WINDOWS = LOG_PATHS_STANDARD

LOG_PATHS_ALL = {
    'Darwin': LOG_PATHS_DARWIN,
    'Linux': LOG_PATHS_LINUX,
    'Windows': LOG_PATHS_WINDOWS
}
LOG_PATHS = LOG_PATHS_ALL [platform.system()]
LOG_CHOICES = list (LOG_PATHS.keys())
LOG_CHOICES.sort()

SET_CHOICES = ['interval', 'clientstats', 'fmsdebug', 'logsize', 'topcall']
print (SET_CHOICES)

ALL_CHOICES = LOG_CHOICES + SET_CHOICES

def get_log_path (log: str) -> str:
    return BASE_PATH + LOG_PATHS [log]


def get_file_timestamps (path: str) -> tuple:
    """Return a file's creation and modification timestamps"""
    return (os.path.getmtime(path), pathlib.Path(path).stat().st_mtime)


def count_fixed_log_references (args: argparse.ArgumentParser) -> int:
    """Return the number of logs referenced for output, except if following."""
    return 0


def setup_parser() -> argparse.ArgumentParser:
    """Setup parameters used for command interface. Does not attempt to parse."""
    
    parser = argparse.ArgumentParser(
        prog='fmslogs',
        add_help=False,
        description='View FileMaker Server logs and set logging options')

    parser.add_argument('-f', '--filter', nargs=1, help='only return lines matching regex expression')
    parser.add_argument('-h', '--head', nargs='*', help='display the start of the specified log file')
    parser.add_argument('--help', action='help', help='display command details')
    parser.add_argument('-l', '--list', action='store_true', help='list all log files, including size, date created & modified, sorted by modification time')
    parser.add_argument('-L', '--lognames', action='store_true', help='list log names supported by command')
    parser.add_argument('-m', '--merge', action='store_true', help='combine output of two or more logs')
    parser.add_argument('-r', '--range', nargs=1, default='1S', help='range or number of lines to print')
    parser.add_argument('-S', '--set', nargs=1, type=int, help='change log configuration option')
    parser.add_argument('-s', '--succinct', action='store_true', help='strip less useful details from log output')
    parser.add_argument('-t', '--tail', action='store_true', help='wait for any new messages after printing current end of log')
    parser.add_argument('--truncate', action='store_true', help='cut off any output if beyond width of screen')
    parser.add_argument('-v', '--version', action='store_true', help='version info')

    parser.add_argument('log1', nargs='?', choices=ALL_CHOICES, help='log name to display')
    parser.add_argument('log2', nargs='?', choices=LOG_CHOICES, help='additional log to display')

    return parser


def init_curses():
    global STDSCR, SCREENCOLS, SCREENROWS
    STDSCR = curses.initscr()
    curses.noecho()
    SCREENROWS, SCREENCOLS = STDSCR.getmaxyx()
    STDSCR.scrollok(1)


def tail_F(some_file):
    first_call = True
    while True:
        try:
            with open(some_file) as input:
                if first_call:
                    input.seek(0, 2)
                    first_call = False
                latest_data = input.read()
                while True:
                    if '\n' not in latest_data:
                        latest_data += input.read()
                        if '\n' not in latest_data:
                            yield ''
                            if not os.path.isfile(some_file):
                                break
                            continue
                    latest_lines = latest_data.split('\n')
                    if latest_data[-1] != '\n':
                        latest_data = latest_lines[-1]
                    else:
                        latest_data = input.read()
                    for line in latest_lines[:-1]:
                        yield line + '\n'
        except IOError:
            yield ''


def log_full_path(log: str) -> str:
    if LOG_PATHS[log][0] != '/':
        return BASE_PATH + '/' + LOG_PATHS[log]
    else:
        return LOG_PATHS[log]


def list_log_names():
    """Print out log names as used by command with their expected paths."""
    print ('LOG NAME           PATH')
    for log in LOG_CHOICES:
        print('{:18} {:<40}'.format (log, log_full_path(log)))

def list_logs():
    """Print one line per supported log with path, size, creation & mod timestamps."""
    print ('LOG NAME                 SIZE  MODIFIED')
    for log in LOG_CHOICES:
        fullPath = log_full_path (log)
        #TODO: check for permissions issue
        
        while True:
            try:
                modTime = os.path.getmtime(fullPath)
            except FileNotFoundError:
                modTime = 0;
                break
            modTimestamp = time.ctime(modTime)
            size = os.path.getsize(fullPath)
            break
        
        if modTime > 0:
            print('{:18} {:>10}  {:>24}'.format (log, size, modTimestamp))
        else:
            print('{:18}            <missing>'.format (log))


def print_log_header (logName:str) -> bool:
    
    headerStr = ''
    
    try:
        headerStr = LOG_HEADERS [logName]
    except:
        pass
    
    print (headerStr)


def show_file_head_faster (filePath: str, lines: int) -> bool:
    
    """Print up to the given number of lines of text from the start of the file at the provided path.
    If MAX_READ_LEN is reached, stop output and append a '+++'.
    Result is False if there was an error opening or reading the file."""
    
    result = False
    
    if lines > 0:
        with open (filePath, 'r') as logfile:
            lines = logfile.readlines (MAX_READ_LEN)
            for line in lines[0:SCREENROWS-1]:
                print (line, end="")
            #STDSCR.erase()
            #for line in lines:
            #    STDSCR.addstr(line)
            result = True
            if len (lines) == MAX_READ_LEN:
                # indicate that we reached read limit
                print ('+++')
    else:
        # We never opened the file, but will consider this a success.
        result = True
    
    #STDSCR.getch()
    return result

def show_file_head (logName:str, lines:int) -> bool:
    
    filePath = LOG_PATHS [logName]
    
    with open (filePath, 'r') as logFile:
        print_log_header (logName)

def handle_head (logNames: list):
    for log in logNames:
        show_file_head (get_log_path(log), SCREENROWS)


def show_file_tail (filePath: str, lines: int) -> bool:
    
    """Print up to 'lines' number of lines of text from the end of the file at path.
    Result is False if there was an error opening or reading the file."""
    
    result = False
    iter = 0
    bufSize = 8192
    fileSize = os.stat(fname).st_size
    
    with open(filePath, 'r') as f:
        if bufSize > fileSize:
            bufSize = fileSize - 1
            data = []
            while True:
                iter += 1
                f.seek (fileSize - bufSize * iter)
                data.extend (f.readlines(MAX_READ_LEN))
                if len (data) >= lines or f.tell() == 0:
                    #TODO: truncate if > MAX_READ_LEN
                    print(''.join(data[-lines:]))
                    result = True
                    break
    
    return result


# https://gist.github.com/pylixm/e6bd4f5456740c12e462eecbc66692fb # tail/follow a file


def main():
    parser = setup_parser()
    args = parser.parse_args()
    
    #print(args.count, args.verbose)
    print ()
    print (args)
    print ()

    #init_curses()
    
    while True:
        if args.lognames:
            list_log_names()
            break
        if args.list:
            list_logs()
            break
        if args.set:
            # Do first in case enabling a log
            handle_set (args.set)
            break
        if args.head:
            handle_head (args.head)
        if args.tail:
            handle_tail (args.tail)
        if args.succinct:
            print ('using succinct mode')
        
        break
        
    #curses.endwin()

if __name__=="__main__":
    main()
