#!/bin/python3
import flask, flask_login
from flask import url_for, request, render_template, redirect
import jinja2
from flask_login import current_user
from collections import *
import glob, gzip, json, os.path, random, re
from datetime import datetime
from base import *

# -- Info for every Hack-A-Day project --
load_info({
    "project_name": "Hack-A-Stats",
    "source_url": "https://github.com/za3k/day14_stats",
    "subdir": "/hackaday/stats",
    "description": "stats for Hack-A-Day traffic",
    "login": False,
})

# -- Routes specific to this Hack-A-Day project --

class LogLine():
    def __init__(self, m):
        self.ip = m.group("ipaddress")
        self.datetime = m.group("dateandtime")
        self.status_code = int(m.group("status_code"))
        self.length = int(m.group("length"))
        self.referrer = None if m.group("referrer")=="-" else m.group("referrer")
        self.user_agent = m.group("http_user_agent")
        self.short_user_agent = self.user_agent.split()[0]
        self.address_type = 4 if m.group("ip4address") else 6
        self.url = m.group("url")
class LogParser():
    # 54.37.79.75 - - [14/Nov/2022:19:09:21 +0000] "GET /.env HTTP/1.1" 404 199 "-" "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/81.0.4044.129 Safari/537.36"
    LINEFORMAT = re.compile(r"""
        (?P<ipaddress>(?P<ip4address>\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})|(?P<ip6address>[a-f0-9:]+))\s+
        -\s+
        -\s+
        \[(?P<dateandtime>\d{2}\/[A-Za-z]{3}\/\d{4}:\d{2}:\d{2}:\d{2}\s(?:\+|\-)\d{4})\]\s+
        \"(?P<method>[A-Z]+)\s(?P<url>[^ ]+?)\s+HTTP\/1.1"\s+
        (?P<status_code>\d{3})\s+
        (?P<length>\d+)\s+
        "(?P<referrer>[^" ]+?)"\s+
        "(?P<http_user_agent>[^"]+?)"
        """,
        re.IGNORECASE | re.VERBOSE)
    if app.config["DEBUG"]:
        STATS_DIR="sample"
    else:
        STATS_DIR=""

    def __init__(self, stats):
        self.stats = stats
        self.dir = self.STATS_DIR
        self.spawn_tail_log()
        self.read_backlog()
    @staticmethod
    def read_log_file(file):
        if file.endswith(".gz"):
            f = gzip.open(file, 'rb')
            for line in f:
                yield line.decode("utf8")
        else:
            f = open(file, 'r')
            for line in f:
                yield line
    def spawn_tail_log(self):
        # TODO: Spawn a thread tailing access.log
        # for line in tail(os.path.join(self.dir, "access.log")):
        #     self.parse_line(line)
        pass
    def tail_log(self, file):
        pass # TODO
    def read_backlog(self):
        for x in glob.glob(os.path.join(self.dir, "access.log.*.gz")):
            for line in LogParser.read_log_file(x):
                self.parse_line(line)
        for x in [os.path.join(self.dir, x) for x in ["access.log.1", "access.log"]]:
            for line in LogParser.read_log_file(x):
                self.parse_line(line)
    def parse_line(self, line):
        m = LogParser.LINEFORMAT.match(line):
        if m:
            self.stats.update(LogLine(m))

BLACKLIST_IPS = {
    "174.101.140.242", # me
}
DAYS = {
    "blog": 3,
    "chat": 4,
    "paste": 5,
    "link": 5,
    "homepage": 5,
    "icecube": 6,
    "asteroid": 7,
    "dictionary": 8,
    "mandelbrot": 9,
    "machine": 10,
    "tile": 11,
    "line": 13,
    "stats": 14,
}
DAYS = defaultdict(int, DAYS)
class Stats():
    def __init__(self):
        self.lines = 0
        self.hits = defaultdict(int)
        self.ips = defaultdict(set)
        self.repeat = defaultdict(int)
        self.referrer = defaultdict(Counter)
        self.days = DAYS
    @property
    def ip_counts(self):
        return {k: len(v) for k,v in self.ips.items()}
    @property
    def top_referrer(self):
        return {k: v.most_common(1)[0] for k,v in self.referrer.items()}
    def update(self, line):
        if "hackaday" not in line.url: return # we only care about hack-a-day stats
        if line.ip in BLACKLIST_IPS: return # ignore requests from me
        if "ajax" in line.url: return # don't count ajax requests
        if line.url in ["/hackaday", "/hackaday/"]: return # ignore requests to the parent
        assert line.url.startswith("/hackaday/")
        url = line.url.removeprefix("/hackaday/")
        if "/" not in url:
            url = url + "/"
        project, url = url.split("/",1)
        self.lines += 1
        self.hits[project] += 1
        self.repeat[line.ip] += 1
        self.ips[project].add(line.ip)
        if line.referrer is None or ("za3k" not in line.referrer):
            self.referrer[project][line.referrer] += 1

@app.route("/")
def index():
    stats = Stats()
    parser = LogParser(stats)
    return flask.render_template('index.html', stats=stats)

