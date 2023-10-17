from icalendar import Calendar, Event
from flask import Response, current_app
import dateutil.parser
import requests
import urllib.parse


# Function to return ICS response
def return_ics_Response(response_body):
    return Response(
        response_body,
        mimetype='text/calendar',
        headers={'Content-Disposition': 'attachment'}
    )


# Function to build ICS URLs
def build_ics_urls(ics_url):
    google_calendar_url_base = 'http://www.google.com/calendar/render?cid='

    parsed_ics_url = urllib.parse.urlparse(ics_url)
    parsed_google_url = urllib.parse.urlparse(google_calendar_url_base)

    # Constructing the URLs
    ics_url_http = parsed_ics_url._replace(scheme='http').geturl()
    ics_url_webcal = parsed_ics_url._replace(scheme='webcal').geturl()

    query_params = dict(urllib.parse.parse_qsl(parsed_google_url.query))
    query_params['cid'] = ics_url_webcal
    ics_url_google = parsed_google_url._replace(query=urllib.parse.urlencode(query_params)).geturl()

    return ics_url_http, ics_url_webcal, ics_url_google


# Function to load GroupMe JSON
def load_groupme_json(app, groupme_api_key, groupme_group_id):
    url_group_info = f'https://api.groupme.com/v3/groups/{groupme_group_id}'
    url_calendar = f'https://api.groupme.com/v3/conversations/{groupme_group_id}/events/list'
    headers = {'X-Access-Token': groupme_api_key}

    try:
        response = requests.get(url_calendar, headers=headers)
        response.raise_for_status()
        current_app.groupme_calendar_json_cache = response.json()

        response = requests.get(url_group_info, headers=headers)
        response.raise_for_status()
        current_app.groupme_calendar_name = response.json().get('response', {}).get('name', None)
        current_app.groupme_load_successfully = True
        return True

    except requests.HTTPError as e:
        app.logger.error(f"HTTP Error {response.status_code}: {e}")
    except Exception as e:
        app.logger.error(f"An unexpected error occurred: {e}")

    current_app.groupme_load_successfully = False
    current_app.groupme_calendar_json_cache = {}
    return False


# Function to convert GroupMe JSON to ICS
def groupme_json_to_ics(groupme_json):
    cal = Calendar()
    cal.add('prodid', '-//Andrew Mussey//GroupMe-to-ICS 0.1//EN')
    cal.add('version', '2.0')
    cal.add('calscale', 'GREGORIAN')
    cal.add('method', 'PUBLISH')
    cal.add('x-wr-calname', f'GroupMe: {current_app.groupme_calendar_name}')
    cal.add('x-wr-timezone', current_app.calendar_timezone)

    for json_blob in groupme_json['response']['events']:
        if 'deleted_at' not in json_blob:
            event = Event()
            event.add('uid', json_blob['event_id'])
            event.add('dtstart', dateutil.parser.parse(json_blob['start_at']))
            event.add('summary', json_blob['name'])
            event.add('description', json_blob.get('description', ''))
            # ... (rest of the code remains the same)

    return cal.to_ical()


# Function to handle ICS error
def groupme_ics_error(error_text):
    cal = Calendar()
    cal.add('prodid', '-//Andrew Mussey//GroupMe-to-ICS 0.1//EN')
    cal.add('version', '2.0')
    cal.add('calscale', 'GREGORIAN')
    cal.add('method', 'PUBLISH')
    cal.add('x-wr-calname', f'GroupMe: {current_app.groupme_calendar_name} ({error_text})')
    cal.add('x-wr-timezone', 'America/Los_Angeles')

    return cal.to_ical()

