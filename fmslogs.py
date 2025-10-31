#!/usr/bin/env python3
# -*- Mode:Python; indent-tabs-mode:nil; tab-width:3; encoding:utf-8 -*-

"""
Filename: fmslogs.py
Author: Simon Brown on 10/15/2025
Version: 0.10, 2025-10-27
Purpose: Display FileMaker Server logs and change logging options.
"""

import argparse, curses, linecache, os, pathlib, platform, sys, textwrap, time
from collections import OrderedDict
from enum import Enum

"""
non-standard install location?
'top' or iostat option
Show column headers if relevant
have merged logs
summarize results where possible (eg, count, min, max, sum)?
convert table IDs
paged output


fmslogs [show|tail] all|access|dapi|events|fmsdebug|odata|topcall|wpe [-l|--last] [-h|head] [-t|tail]

fmslogs dapi # tail of log (but not following), printing as many lines as rows on screen
fmslogs -h access events
fmslogs -h -n 100 access events
fmslogs -s topcall 1 # enable TopCall.log
paging output
open either directory or log file in text editor, eg $EDITOR

"""

TIMESTAMP_REGEX = None
FILTER_STR = '.*'   # -f may replace this value
FILTER_REGEX = None
TEXTWRAP = textwrap.TextWrapper(width=120,tabsize=10)

class OutputMode (Enum):
	HEAD = 1
	TAIL = 2
	OTHER = 3

OUTPUT_MODE = OutputMode.TAIL
SHOW_HEADERS = False
SUCCINCT_MODE = False

SCREENCOLS, SCREENROWS = os.get_terminal_size()
LINE_COUNT = SCREENROWS     # may get overriden by options, or reduced to make room for header

MAXREADLEN = 1048576*10

#LOG_CHOICES = ['access', 'admin', 'clientstats', 'dapi', 'events', 'install', 'odata', 'scriptevent', 'stats', 'stderr', 'stderrserverscripting', 'stdout', 'syslog', 'stats', 'topcall', 'wpe']

# Default deployment paths (Windows paths will have forward slashes converted)
DEF_BASE_PATHS = {
	'Darwin': '/Library/FileMaker Server',
	'Linux': '/opt/FileMaker/FileMaker Server',
	'Windows': 'C:/Programs/FileMaker/FileMaker Server'
}

# This may get overridden by user option,
BASE_PATH = DEF_BASE_PATHS [platform.system()]

LOG_SPECS = {
	'access': {
		'path': 'Logs/Access.log',
		#        ----------1---------2---------3---------4---------5---------6---------7---------8---------9---------0---------
		#        2025-09-15 01:12:45.831 -0700  Information  228   some-dev.filemaker.beezwax.net         The previous log file reached maximum size, and was renamed to "Access-old.log".
		'head': 'TIMESTAMP                      LEVEL        CODE  HOST                                   MESSAGE',
		'tbst': [32,45,51,90],
		#        2025-09-15 01:12:45.831  Information  228   The previous log file reached maximum size, and was renamed to "Access-old.log".
		'shed': 'TIMESTAMP                LEVEL        CODE  MESSAGE',
		'shtb': [26,39,45]
	},
	'admin': {
		'path': 'Admin/FAC/logs/fac.log',
		#        ----------1---------2---------3---------4---------5---------6---------7---------8---------9---------0---------
		#			2022-05-17 14:29:56 -0700	 Execute /opt/FileMaker/FileMaker Server/Admin/FAC/facstart.sh
		#			2022-05-17 14:30:00 -0700 - warn:   fmi   127.0.0.1   notifications   general   n/a   "New system notification generated, type: CPU_USAGE_EXCEED_HARD_LIMIT"
		# Only uses tabs with regular messages (eg, not error or warn) after timestamp.
		'head': 'TIMESTAMP                 {LEVEL}   {END} {ADDRESS}   {COMPONENT}    {TYPE}    {CODE}  MESSAGE',
		'tbst': [29],
		'shed': 'TIMESTAMP           {LEVEL}   {END} {ADDRESS}   {COMPONENT}    {TYPE}    {CODE}  MESSAGE',
		'shtb': [23]
	},
	'clientstats': {
		'path': 'Logs/ClientStats.log',
		#        ----------1---------2---------3---------4---------5---------6---------7---------8---------9---------0---------
		#			2025-10-16 15:46:18.054 -0700  37781   8559   209   0     46442     0    28    Xeronthia Shilnow (XS ETMD6M) [255.143.244.179]
		'head': '                               NET BYTES  NET BYTES  CALLS      CALLS      TIME       TIME       TIME' + \
				  'TIMESTAMP                      IN         OUT        COMPLETE   IN PROG    ELAPSED    WAIT       I/O        CLIENT NAME',
		'tbst': [32,43,54,65,76,87,98,109],
		#			2025-10-16 15:46:18.054  37781    8559    209     0    46442    0     28   Xeronthia Shilnow (XS ETMD6M) [255.143.144.79]
		'shed': '                         NET BYTES  NET BYTES CALLS     CALLS     TIME      TIME      TIME' + \
				  'TIMESTAMP                IN         OUT       COMPLETE  IN PROG   ELAPSED   WAIT      I/O       CLIENT NAME',
		'shtb': [26,37,48,59,70,81,92,103]
	},
	
	'dapi': {
		'path': 'Logs/fmdapi.log',
		#        ----------1---------2---------3---------4---------5---------6---------7---------8---------9---------0---------
		#			2025-08-27 11:08:10.055 -0700  4101   ERROR	250.130.228.236  some-user-name   POST  Script Error -- Script File: 'Tool', Script Name: 'create update topic [PSoS]', Script Step: 'Set Field By Name'  0
		# Size at end (re-arrange columns?). Rarely a 4 digit error code.
		'head': 'TIMESTAMP	                   CODE   LEVEL   HOST            USER             HTTP  MESSAGE  SIZE',
		'tbst': [32,39,47,63,81,87],
		#			2025-08-27 11:08:10.055  301   ERROR  some-user-name   POST  Script Error -- Script File: 'Tool', Script Name: 'create update topic [PSoS]', Script Step: 'Set Field By Name'  0
		'shed': 'TIMESTAMP	             CODE  LEVEL  USER             HTTP  MESSAGE  SIZE',
		'shtb': [26,32,39,56,62]
	},
	
	'events': {
		'path': 'Logs/Event.log',
		#        ---------1---------2---------3---------4---------5---------6---------7---------8---------9---------0---------
		#			2025-08-18 23:15:30.125 -0700  Information  228   some-dev.filemaker.beezwax.net  The previous log file reached maximum size, and was renamed to "Event-old.log".
		'head': 'TIMESTAMP                ZONE  LEVEL        CODE  HOST                            MESSAGE',
		'tbst': [32,45,51,83],
		#			2025-08-18 23:15:30.125  Information  228   some-dev.filemaker.beezwax.net  The previous log file reached maximum size, and was renamed to "Event-old.log".
		'shed': 'TIMESTAMP                LEVEL        CODE  HOST                            MESSAGE',
		'shtb': [26,39,45,77]
	},
	
	'fmshelper': {
		'path': 'Logs/fmshelper.log',
			# This log has no consistent format
			#		2025-08-03 20:12:38.182 -0700   Log file /opt/FileMaker/FileMaker Server/Logs/fmshelper.log size: 478 bytes (0 MB), threshold ratio: 0
			#		2025-08-03 20:12:38.185 -0700 === stopSystemWebServer()
			#		(Use `facstart.sh --trace-warnings ...` to show where the warning was created)
			#		Thrift: Sun Aug  3 20:12:47 2025 TNonblockingServer: Serving with 5 io threads.
			#		127.0.0.1 POST /fmi/admin/internal/v1/dbs-notification/xPR2AgRM1TODanCZ56eikiYXcbzvTDdtLIbd9Avs3Z4kuxie - - - ms
			#		Aug 03, 2025 8:12:53 PM org.apache.jasper.servlet.TldScanner scanJars
			#		2025/08/03 20:39:27.0128: [ 2525]:    TRACE:       mongoc: ENTRY: _mongoc_linux_distro_scanner_get_distro():389
		'head': None,
		'tbst': []	# replace any tabs with two spaces
	},
	
	'loadschedules': {
		'path': 'Logs/install.log',
		'head': None,
		'tbst': []
	},

	'odata': {
		'path': 'Logs/fmodata.log',
		#        ---------1---------2---------3---------4---------5---------6---------7---------8---------9---------0---------
		#		  '2025-10-14T13:01:31.232452-08:00  0     INFO   170.255.255.218  GET   /fmi/odata/v4	 75'
		'head': 'TIMESTAMP                         CODE  LEVEL  HOST             OP    ENDPOINT  SIZE',
		'tbst': [35,41,48,65,71],  # 'size' value will be padded on end
		#		  '2025-10-14T13:01:31.232452  0     INFO   GET   /fmi/odata/v4	 75'
		'shed': 'TIMESTAMP                   CODE  LEVEL  OP    ENDPOINT  SIZE',
		'shtb': [29,35,48]
	},
	'scriptevent': {
		'path': 'Logs/scriptEvent.log',
		#        ---------1---------2---------3---------4---------5---------6---------7---------8---------9---------0---------
		#			2025-08-11 03:00:26.470 -0700  401   Schedule "daily mailing" scripting error (401) at "TOOL : delete mailing batches without queued logs [PSoS] : 22 : Perform Find".
		'head': 'TIMESTAMP                ZONE  CODE  MESSAGE',
		'tbst': [32,38],
		#			2025-08-11 03:00:26.470  401   Schedule "daily mailing" scripting error (401) at "TOOL : delete mailing batches without queued logs [PSoS] : 22 : Perform Find".
		'shtb': [26,32],
	},
	
	'stats': {
		'path': 'Logs/Stats.log',
		#			---------1---------2---------3---------4---------5---------6---------7---------8---------9---------0---------1---------2---------3---------4---------5---------6---------7---------8---------
		#			2025-10-17 17:54:42.335 -0700	0	14	11	0	98	0	0	1	0	0	0	2	0	546	40	81	0
		'head': '                               NET      NET       DISK       DISK        CACHE   CACHE     PRO      OPEN  CLIENTS  CLIENTS  CLIENTS  CALLS/s   CALLS   TIME     TIME     TIME     CLIENTS' + \
				  'TIMESTAMP                ZONE  KB/s In  KB/s OUT  KB/s READ  KB/s WRITE  HIT %   UNSAVD %  CLIENTS  DBS   XDBC     WEBD     CWP      COMPLETE  ACTIVE  ELAPSED  WAIT     I/O      GO',
		'tbst': [32,41,51,62,74,82,92,101,107,116,125,134,144,152,161,170,179],
		'shed': '                         NET      NET       DISK       DISK        CACHE   CACHE     PRO      OPEN  CLIENTS  CLIENTS  CLIENTS  CALLS/s   CALLS   TIME     TIME     TIME     CLIENTS' + \
				  'TIMESTAMP                KB/s In  KB/s OUT  KB/s READ  KB/s WRITE  HIT %   UNSAVD %  CLIENTS  DBS   XDBC     WEBD     CWP      COMPLETE  ACTIVE  ELAPSED  WAIT     I/O      GO',
		'shtb': [26,35,45,56,68,76,86,95,101,110,119,128,138,146,155,164,173]
	},
	
	'stderrserverscripting': {
		'path': 'Logs/StdErrServerScripting.log',
		'head': None,
		'tbst': []
	}

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
	'install': 'Logs/install.log',
	'fmsgetpasskeyebug': 'Database Server/bin/fmsgetpasskeyDebug.log',
	'loadschedules': 'Logs/LoadSchedules.log',
	'odata': 'Logs/fmodata.log',
	'odatadebug': 'Database Server/bin/fmodataDebug.log',
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
#	'syslog': '/var/log/syslog'
}
LOG_PATHS_LINUX.update (LOG_PATHS_STANDARD)

LOG_PATHS_DARWIN = {
	'stderr': 'Logs/stderr',
	'stdout': 'Logs/stdout',
	#'syslog': '/var/log/system.log'
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

#
#	s t r i p _ l i n e
#

def strip_line (logName: str, line: str) -> str:
	"""
	When possible, remove repetitive or extraneous text in the logs.
	This is done after expanding tabs so columns should be at fixed positions.
	"""
	
	if logName in ['access','events']:
		if line [24] == '-':
			line = line [:23] + line [29:51] + line [90:]		# remove timezone and hostname
	if logname == 'admin':
		if line [20] == '-':
			line = line [:20] + line [26:]							# remove timezone
	if logName in ['clientstats','dapi','topcall']:
			line = line [:23] + line [29]								# remove timezone
	if logname == 'dapi':
			line = line [:23] + line [29:45] + line[62:]			# remove timezone & hostname

	return line

#
#	g e t _ l o g _ p a t h
#

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

	parser.add_argument('-b', '--begin', nargs=1, help='start at first message on or after time or time interval')
	parser.add_argument('-f', '--filter', nargs=1, help='only return lines matching regex expression')
	parser.add_argument('-h', '--head', nargs='*', help='display the start of the specified log file')
	parser.add_argument('-H', '--headers', action='store_true', help='display column headers as first line for logs with fixed columns')
	parser.add_argument('--help', action='help', help='display command details')
	parser.add_argument('-l', '--list', action='store_true', help='list all log files, including size, date created & modified, sorted by modification time')
	parser.add_argument('-L', '--lognames', action='store_true', help='list log names supported by command')
	parser.add_argument('-m', '--merge', action='store_true', help='combine output of two or more logs')
	parser.add_argument('-n', '--number', nargs=1, default='1S', help='range or number of lines to print')
	parser.add_argument('-S', '--set', nargs=1, type=int, help='change log configuration option')
	parser.add_argument('-s', '--succinct', action='store_true', help='strip less useful details from log output')
	parser.add_argument('-t', '--tail', action='store_true', help='wait for any new messages after printing current end of log')
	parser.add_argument('--truncate', nargs='?', action='store_true', help='cut off any output if beyond width of screen')
	parser.add_argument('-v', '--version', action='store_true', help='version info')
	# Hack to avoid error if there is only an option specified but no positional argument
	parser.add_argument('log1', nargs='?', choices=ALL_CHOICES, help='log name to display')
	parser.add_argument('log2', nargs='?', help='additional log to display')

	return parser

#
#	f i n d _ f i r s t _ t i m e s t a m p
#

def find_first_timestamp (filePath: str, timestamp: datetime) -> int:
	
	"""
	Scan file until the first log timestamp equal or greater than the search
	timestamp is found, returning the line number (base 1) of matching line.
	Note that a few logs don't emit timestamps consistently. 
	If a match is never found -1 is returned.
	"""
	
	lineResult = -1
	lineNum = 0
	
	while True:
		lineTS = None
		lineNum += 1
		line = linecache.getline (filePath, lineNum)
		if line == '': break
		# Sniff the line to guess the date format.
		try:
			if line[4] == '-' and line [24] == '-':
				# Access, ClientStats, Event, Stats, etc.
				# 2025-10-27 04:13:24.101 -0700	Information	228	tool.beezwax.net	The previous log file reached maximum size, and was renamed to "Access-old.log".
				lineTS = datetime.datetime.fromisoformat(line [:23])
			elif line [4] == '/' and line [24] == ':':
				# 2025/10/25 17:49:09.0162
				lineTS = datetime.strptime(line [:23], "%Y/%m/%d %H:%M:%S.%f")
			elif line [6] == ',' and line [22] in 'APM':
				# Sep 11, 2025 12:40:52 PM org.atmosphere.cpr.AtmosphereFramework addInterceptorToAllWrappers
				# Oct 22, 2025 2:16:56 PM org.atmosphere.util.IOUtils guestRawServletPath
				lineTS = datetime.datetime.strptime(line [:24].rstrip(), '%b %d, %Y %I:%M:%S %p')
			elif line [:7] == 'Thrift:':
				# Thrift: Sat Jun  7 10:47:03 2025
				lineTS = datetime.datetime.strptime (line [8:32], '%a %b %d %H:%M:%S %Y')
			else:
				continue
		
		# Skip over any lines that have too few characters (very few) or where we can't evaluate date.
		
		except IndexError:
			continue
		#except ValueError:
		#	continue

		# If we reached the timestamp, go into next while loop to match by text value.
		if lineTS != None and timestamp <= lineTS:
			lineResult = lineNum
			break
	
	return lineResult


#
#	e x p a n d _ t a b s _ f o r _ l i n e
#

def expand_tabs_for_line(line: str, tabstops) -> str:
	"""
	Expands tabs in the string `line` using the given tabstops.
	`tabstops` can be a list of column positions (e.g., [4, 8, 12]) or a single integer for fixed tab width.
	"""
	if isinstance(tabstops, int):
		return line.expandtabs(tabstops)

	result = []

	parts = line.split('\t')
	col = 0
	tab_iter = iter(tabstops)
	next_tab = next(tab_iter, None)
	for i, part in enumerate(parts):
		result.append(part)
		col += len(part)
		if i < len(parts) - 1:
			if next_tab is not None and col < next_tab:
				spaces = next_tab - col
				result.append(' ' * spaces)
				col = next_tab
				next_tab = next(tab_iter, None)
			else:
				result.append('  ')	# pad two spaces if no stop specified
				col += 1
	return ''.join(result)


#
#	r e a d _ t a i l _ f i l t e r e d
#

def read_tail_filtered (filePath: str, linesFromEnd: int) -> list:
	"""
	Search file for any matching lines, return up to linesFromEnd
	line numbers from the end of file that match. Line numbers are base 1
	for use with linecache.getline.
	"""
	
	matching = []
	lineNum = 1
	while True:
		line = linecache.getline (filePath, lineNum)
		if line == '': break
		if FILTER_REGEX.search (line):
			matching.append (lineNum)
		lineNum += 1
	
	return matching [-linesFromEnd:]
		

#
#	r e a d _ t a i l _ f i l t e r _ a n d _ t i m e
#

def read_tail_filtered_and_time (filePath: str, linesFromEnd: int) -> list:
	"""
	Search file for any matching lines that are on or after the matching timestamp.
	From there, then return line numbers from the end of file that match the text filter.
	Line numbers are base 1 for use with linecache.getline.
	"""
	
	matching = []
	lastTimeLine = -1
	
	# First, find the first line containing some kind of message date
	# that is on or after our start date.
	
	lineNum = find_first_timestamp (filePath, TIMESTAMP_START)
	
	if lineNum > 0:
		# Now, filter anything after start date.
		while True:
			line = linecache.getline (filePath, lineNum)

			if line == '': break

			if FILTER_REGEX.search (line):
				matching.append (lineNum)
			lineNum += 1
	
	# Cut result down to no more than requested lines from end of file.
	return matching [-linesFromEnd:]


#
#	r e a d _ t a i l _ t i m e
#

def read_tail_time (filePath: str, linesFromEnd: int) -> list:
	"""
	Search file for any matching lines that are on or after the matching timestamp.
	Then return line numbers from the end of file that match the text filter.
	Line numbers are base 1 for use with linecache.getline.
	"""

	matching = []
	
	# First, find the first line containing some kind of message date
	# that is on or after our start date.
	
	lineNum = find_first_timestamp (filePath, TIMESTAMP_START)

	# Find the last line
	while True:
		line = linecache.getline (filePath, lineNum)
		if line == '': break
		# TODO: purge line list when it gets too big
		matching.append (lineNum)
		lineNum += 1

	# Cut result down to no more than requested lines from end of file.
	return matching [-linesFromEnd:]


def init_curses():
    global STDSCR, SCREENCOLS, SCREENROWS
    STDSCR = curses.initscr()
    curses.noecho()
    SCREENROWS, SCREENCOLS = STDSCR.getmaxyx()
    STDSCR.scrollok(1)


def follow_file(some_file):
	"""
	was tail_F
	Capture output as it is added to the file.
	"""
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
			`		else:
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

#
#	p r i n t _ l o g _ n a m e s
#

def print_log_names():
	"""Print out log names as used by command with their expected paths."""
	print ('LOG NAME           PATH')
	for log in LOG_CHOICES:
		print('{:18} {:<40}'.format (log, log_full_path(log)))

#
#	p r i n t _ l o g s
#

def print_logs():
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

#
#   p r i n t _ f i l e _ h e a d
#

def print_file_head (logName:str, lines:int) -> bool:
    
    filePath = LOG_PATHS [logName]
    lineCount = 0

    try:
        with open(filePath, "r+b") as f:
            m=mmap.mmap(f.fileno(), 0, prot=mmap.PROT_READ)
            print_log_header (logName)
            while True:
                line=m.readline()
                if line == '': break
                if FILTER_REGEX.search (line):
                    print line.rstrip()
                    lineCount =+ 1
    except IOError:
        print ('File Error:', filePath, 'could not be opened')
        return False
    
    return True

#
#   p r i n t _ h e a d
#

def print_head (logName: str, count: int, header: bool, succinct: bool) -> bool:
    
	matching = []
	
	# First, find first line containing some kind of message date
	# that is on or after our start date.
	
	print_log_header(logName, succinct)
	result = False
	lineNum = find_first_timestamp (filePath, TIMESTAMP_START)
	
	if lineNum > 0:
		maxLine = lineNum + count
		result = True
		
		while True:
			line = linecache.getline (filePath, lineNum)
			if line == '': break
			if FILTER_REGEX.search (line):
				matching.append (lineNum)
			lineNum += 1
			if lineNum > maxLine then break
	
	# TODO: should result be: there is more data, that the file exists, or that something was printed?
	return result

    
#
#	p r i n t _ t a i l
#

def print_tail (logName: str, count: int, header: bool, succinct: bool) -> bool:
    
    """
    Print up to 'count' number of lines of text from the end of the file at path.
    Result is False if there was an error opening or reading the file.
    If 'header' is true, display the log headers (if any) as first line.
    If 'succinct' is true, strip less useful info from lines.
    """
    
    result = False
    lineList = []
    lineCount = LINE_COUNT
    
    logPath =  get_log_path (logName)
    headerUsed = False
    
    if header:
        # TODO: only print headers if there's log output
        try:
            if succinct:
                print (LOG_SPECS [logName]['shed'])
                lineCount -= 1 # TODO: check if header is two lines
            else:
                print (LOG_SPECS [logName]['head'])
            headerUsed = True
            
        except IndexError:
            pass

    # Below we can files only, creating a list of records to later print.
    
    # JUST DETERMINE START LINE AND USE THAT AS PARAM TO SINGLE READ FUNC?
    
	if TIMESTAMP_START != None:
		if FILTER_REGEX != None:
			lineList = read_tail_filtered_and_time (logPath, lineCount)
		else:
			lineList = read_tail_time (logPath, lineCount)
	else:
		if FILTER_REGEX != None:
			lineList = read_tail_filtered (logPath, lineCount)
		else:
			lineList = read_tail (logPath, lineCount)
	
	if succinct:
		for lineNum in lineList:
			line = strip_line (logName, linecache.getline (filePath, lineNum)
			print (expand_tabs_for_line (line))
	else:
		for lineNum in lineList:
			print (expand_tabs_for_line (linecache.getline (filePath, lineNum)))
    
	return result


# https://gist.github.com/pylixm/e6bd4f5456740c12e462eecbc66692fb # tail/follow a file

#
#	c o m p i l e _ f i l t e r
#

def compile_filter -> bool:
    
    global FILTER_REGEX
    isValid = False
    
    try:
        FILTER_REGEX = re.compile(FILTER_STR)
        isValid = True
    except re.error as e:       # aliased to PatternError as of 3.13
        print(f"Regex Error: {e}")

    return isValid


def main():
	global FILTER_STR, OUTPUT_MODE, SHOW_HEADERS, SUCCINCT_MODE
	
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
		if args.filter:
			FILTER_STR = args.filter
		  
		if !compile_filter():	# Compile the default or the filter that was just set
			break						# bad regex
	  
		if args.head:
			OUTPUT_MODE = OutputMode.HEAD
		
		if args.headers:
			SHOW_HEADERS = True
		
		if args.succinct:
			SUCCINCT_MODE = True
		
		if args.log1:
			if OUTPUT_MODE == OutputMode.TAIL:
				print_tail (args.log1, LINE_COUNT, SHOW_HEADERS, USE_SUCCINCT)
			
			elif OUTPUT_MODE == OutputMode.HEAD:
				print_head (args.log1, LINE_COUNT, SHOW_HEADERS, USE_SUCCINCT)

		if args.log1:
			if OUTPUT_MODE == OutputMode.TAIL:
				print_tail (args.log1, LINE_COUNT, SHOW_HEADERS, USE_SUCCINCT)
			
			elif OUTPUT_MODE == OutputMode.HEAD:
				print_head (args.log1, LINE_COUNT, SHOW_HEADERS, USE_SUCCINCT)

		break
		
		#curses.endwin()

if __name__=="__main__":
    main()

