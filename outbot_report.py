import requests
import json
from datetime import datetime
import secrets

PLUGIN_URL   = "https://api.outbreak.info/resources/query?sort=-date&fields=date&q=curatedBy.name:{name}&size=1"
METADATA_URL = "https://api.outbreak.info/resources/query?aggs=curatedBy.name&facet_size:1000&size=1"
EPI_URL = "https://api.outbreak.info/covid19/query?q=mostRecent:true%20AND%20admin_level:%221%22%20AND%20country_iso3:USA&size=1&_sorted=false"

today = datetime.now()

def date_diff(url):
    plugin_request  = requests.get(url)
    plugin_info     = plugin_request.json()
    latest_date_str = plugin_info['hits'][0]['date']
    latest_date     = datetime.strptime(latest_date_str, '%Y-%m-%d')
    date_difference = (today - latest_date).days

    return date_difference

def get_icon(date_difference):
    if date_difference < 3:
        return "🟢"
    elif date_difference < 7:
        return "🟡"
    elif date_difference < 30:
        return "🟠"
    else:
        return "🔴"

meta_request = requests.get(METADATA_URL)
metadata     = meta_request.json()
plugin_names = [i['term'] for i in metadata['facets']['curatedBy.name']['terms']]

messages = []

def format_days(date_difference):
    if date_difference == 0:
        return "today"
    elif date_difference == 1:
        return "yesterday"

    return f"{date_difference} days old"

def create_message(date_difference, name):
    icon = get_icon(date_difference)
    date_str = format_days(date_difference)
    message = f"{icon} *{name}* {date_str}"
    return message

for name in plugin_names:
    # surround with quotes only if there's a space
    # if there isn't a space, the quotes mess it up!
    # gotta be single quotes too! because ES!
    if ' ' in name:
        name = f"'{name}'"
    date_difference = date_diff(PLUGIN_URL.format(name=name))
    messages.append((create_message(date_difference, name), date_difference))

ordered_messages = [i[0] for i in sorted(messages, key=lambda x: x[1])]

epi_date = date_diff(EPI_URL)
# running epi data today means getting epi data from yesterday
ordered_messages.append(create_message(epi_date - 1, "Epi Data"))

for m in ordered_messages:
    requests.post(secrets.SLACK_HOOK_URL, json={'text': m})
