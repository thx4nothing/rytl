#!/usr/bin/python

import sys
import urllib.request, urllib.error, urllib.parse
import xml.etree.ElementTree as ET
from datetime import datetime
import pytz
import time
from multiprocessing import Pool
from contextlib import contextmanager
import requests

WAIT_TIME = 30 * 60
DAYS = 4
LOCAL_TZ = pytz.timezone("Europe/Berlin")
FOLDER = 'C:/rytl/'
THREADS = 12
SINGLE_CORE = True



def get_date(date):
	date = datetime.strptime(date, '%Y-%m-%dT%H:%M:%S+00:00').replace(tzinfo=pytz.utc).astimezone(LOCAL_TZ)
	return date

def prepend_ns(s):
	return '{http://www.w3.org/2005/Atom}' + s

def download(channel):
	#print(channel)
	list1 = []
	response = requests.get(channel)
	data = response.text
	if "<?xml" not in data:
		print("No xml format ", channel)
		return None
	#print(data)
	parser = ET.XMLParser(encoding="utf-8")
	e = ET.fromstring(data, parser=parser)
	author = e.find(prepend_ns('author')).find(prepend_ns('name')).text
	for entry in e.findall(prepend_ns('entry')):
		link = entry.find(prepend_ns('link'))
		title = entry.find(prepend_ns('title')).text
		published = get_date(entry.find(prepend_ns('published')).text) if entry.find(prepend_ns('published')) is not None else datetime.now(LOCAL_TZ)
		if abs((published - datetime.now(LOCAL_TZ)).days) > DAYS:
			continue
		for name, value in link.attrib.items():
			if name == 'href':
				list1.append([author, title, published, value.replace('https://www.youtube.com/watch?v=', '')])
				break
	return list1

@contextmanager
def poolcontext(*args, **kwargs):
    pool = Pool(*args, **kwargs)
    yield pool
    pool.terminate()

def read_xml():
	print('Reading XML...')
	links = []
	f = open(FOLDER + 'channels.txt')
	channels = ["https://www.youtube.com/feeds/videos.xml?channel_id={0}".format(channel).replace("\n", "") for channel in f]
	if SINGLE_CORE:
		for channel in channels:
			l = download(channel)
			if l:
				links += l
		return links
	else:
		with poolcontext(processes=THREADS) as pool:
			l = pool.map(download, channels)
			for ll in l:
				if ll: links += ll
			print('Finished reading')
			return links

def build_html(xml):
	print('Building HTML file...')
	html = ''
	start = '''<!DOCTYPE html>
<html>
	<head>
		<meta http-equiv="refresh" content="''' + str(WAIT_TIME) + '''">
		<meta charset="utf-8">
		<link rel="shortcut icon" href="YouTube-icon.png">
		<title>Subscriptions</title>
		<style>
			table, th, td {
				border: 1px solid black;
				border-collapse: collapse;
				padding: 5px;
			}
		</style>
		<script> window.onbeforeunload = function () { window.scrollTo(0, 0); } </script>
		<link rel="stylesheet" href="dark.css">
	</head>
	<body onload="sortTable(0)">
		<p align="center">Last update: ''' + str(datetime.now().hour) + ':' + str(datetime.now().minute) + '''</p>
		<table style="margin: 0px auto;" id="subsTable">
			<tr>
				<th onclick="sortTable(0)">Published</th>
				<th>Title</th>
			</tr>
'''
	end = '''		</table>
	<script src="sort.js"></script>
	</body>
</html>'''
	middle = ''
	for entry in xml:
		author = entry[0]
		title = entry[1]
		published = str(entry[2]).replace('+01:00', '').replace('+02:00', '')
		videoid = entry[3]
		middle += '			<tr>\n				<td align="center">' + published + '</td>\n				<td align="center"><a href="https://www.youtube.com/watch?v=' + videoid + '" target="_blank">' + '<img src="https://i.ytimg.com/vi/' + videoid + '/hqdefault.jpg" style="width:128px;height:96px;"><br>' + title + '</a><br>' + author + '</td>\n				</tr>\n'
	html = start + middle + end
	f = open(FOLDER + 'subs.html', "w+", encoding="utf8")
	f.write(html)
	f.close()
	print('Finished Building HTML file')


def update_entries():
	print('Updating...')
	build_html(read_xml())

def auto_update():
	while True:
		while not internet_on():
			print('No internet')
			time.sleep(30)
		update_entries()
		print('Waiting for ', (WAIT_TIME / 60), ' minutes')
		time.sleep(WAIT_TIME)

def internet_on():
	try:
		urllib.request.urlopen('https://google.de', timeout=5)
		return True
	except urllib.error.URLError as err:
		print('No internet connection available')
		return False

if __name__ == '__main__':
	auto_update()
