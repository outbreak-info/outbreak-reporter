import requests
import json
from datetime import datetime
import secrets
import sys

PLUGIN_URL   = "https://api.outbreak.info/resources/query?sort=-date&fields=date&q=curatedBy.name:{name}&size=1"
METADATA_URL = "https://api.outbreak.info/resources/query?aggs=curatedBy.name&facet_size=1000"
EPI_URL      = "https://api.outbreak.info/covid19/query?fields=date&size=1&sort=-date"
GEN_URL      = "https://api.outbreak.info/genomics/metadata"

today = datetime.now()

def get_icon(date_difference, priority=None):
    ALERTS = ["🟢", "🟡", "🟠", "🔴"]
    SCHEDULES = {"high": [1, 3, 7], "default": [3, 7, 30], "low": [7, 10, 30]}
    schedule = SCHEDULES[priority if priority else "default"]

    if date_difference   < schedule[0]:
        return "🟢"
    elif date_difference < schedule[1]:
        return "🟡"
    elif date_difference < schedule[2]:
        return "🟠"
    else:
        return "🔴"

def format_days(date_difference):
    if date_difference == 0:
        return "today"
    elif date_difference == 1:
        return "yesterday"

    return f"{date_difference} days old"

class Plugin:
    def __init__(self, name, url=None, priority="default", headers=None):
        if ' ' in name:
            name = f'"{name}"'
        self.name     = name
        self.url      = PLUGIN_URL.format(name=name)
        self.priority = priority
        self.total    = None
        self.headers  = headers or {}
        if url:
            self.url = url

        self.set_info()

    def set_info(self):
        plugin_request  = requests.get(self.url, headers=self.headers)
        try:
            plugin_info     = plugin_request.json()
            if self.name == 'genomics':
                self.total      = plugin_info['stats']['total']
                # truncate out HH-MM to ignore while parsing
                latest_date_str = plugin_info['src']['genomics_api']['version'][:10]

            else:
                self.total      = plugin_info['total']
                latest_date_str = plugin_info['hits'][0]['date']

                if latest_date_str is None:
                    raise Exception

        except:
            self.date_difference = -1
            return

        latest_date     = datetime.strptime(latest_date_str, '%Y-%m-%d')
        date_difference = (today - latest_date).days

        self.date_difference = date_difference

    def set_message(self):
        if self.date_difference == -1:
            self.message         = f"⚪️ *{self.name}*: age unknown ({self.total:,})"
            return

        icon = get_icon(self.date_difference)
        date_str = format_days(self.date_difference)
        message = f"{icon} *{self.name}*: {date_str}"
        if self.total:
            message += f" ({self.total:,})"
        self.message = message

    def __lt__(self, other):
        try:
            return self.date_difference < other.date_difference
        except:
            return True

    def __str__(self):
        try:
            self.set_message()
            return self.message or ""
        except Exception as e:
            return f"Plugin info for {self.name} raised error {e}"


meta_request = requests.get(METADATA_URL)
metadata     = meta_request.json()
plugin_names = [i['term'] for i in metadata['facets']['curatedBy.name']['terms']]
plugins      = [Plugin(name) for name in plugin_names]
plugins.sort()

epi = Plugin("epidemiological data", url=EPI_URL)
epi.date_difference = epi.date_difference - 1
plugins.append(epi)

genomics = Plugin("genomics", url=GEN_URL, headers={'Authorization': secrets.GEN_AUTH})
plugins.append(genomics)

printmode = '--log' in sys.argv
for m in [str(i) for i in plugins]:
    if printmode:
        print(m)
    else:
        requests.post(secrets.SLACK_HOOK_URL, json={'text': m})
