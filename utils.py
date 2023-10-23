from icalendar import Calendar, Event
from flask import Response, current_app
import dateutil.parser
import requests
from requests.exceptions import ConnectionError, Timeout, RequestException
import urllib.parse

def return_ics_Response(response_body):
    return Response(
        response_body,
        mimetype='text/calendar',
        headers={'Content-Disposition': 'attachment'}
    )

def build_ics_urls(ics_url):
    google_calendar_url_base = 'http://www.google.com/calendar/render?cid='

    parsed_ics_url = urllib.parse.urlparse(ics_url)
    parsed_ics_url = parsed_ics_url._replace(scheme='http' if parsed_ics_url.scheme != 'https' else 'https')
    ics_url_http = urllib.parse.urlunparse(parsed_ics_url)

    parsed_ics_url = parsed_ics_url._replace(scheme='webcal')
    ics_url_webcal = urllib.parse.urlunparse(parsed_ics_url)

    parsed_google_url = urllib.parse.urlparse(google_calendar_url_base)
    query = urllib.parse.parse_qs(parsed_google_url.query)
    query['cid'] = ics_url_webcal
    parsed_google_url = parsed_google_url._replace(query=urllib.parse.urlencode(query, doseq=True))
    ics_url_google = urllib.parse.urlunparse(parsed_google_url)

    return ics_url_http, ics_url_webcal, ics_url_google

def load_groupme_json(app, groupme_api_key, groupme_group_id):
    url_group_info = f'https://api.groupme.com/v3/groups/{groupme_group_id}'
    url_calendar = f'https://api.groupme.com/v3/conversations/{groupme_group_id}/events/list'
    headers = {'X-Access-Token': groupme_api_key}

    try:
        response = requests.get(url_calendar, headers=headers)
        response.raise_for_status()
    except ConnectionError:
        app.logger.error("Failed to connect to GroupMe API.")
        return False
    except Timeout:
        app.logger.error("Request to GroupMe API timed out.")
        return False
    except RequestException as e:
        app.logger.error(f"An error occurred while making a request to GroupMe API: {e}")
        return False
    except Exception as e:
        app.logger.error(f"An unexpected error occurred: {e}")
        return False

    current_app.groupme_calendar_json_cache = response.json()

    response = requests.get(url_group_info, headers=headers)
    if response.status_code == 200:
        current_app.groupme_calendar_name = response.json().get('response', {}).get('name', '')

    current_app.groupme_load_successfully = True
    return True

def groupme_json_to_ics(groupme_json, static_name=None):
    Try:
    cal = Calendar()
    cal['prodid'] = '-//Andrew Mussey//GroupMe-to-ICS 0.1//EN'
    cal['version'] = '2.0'
    cal['calscale'] = 'GREGORIAN'
    cal['method'] = 'PUBLISH'
    cal['x-wr-calname'] = 'GroupMe: {}'.format(current_app.groupme_calendar_name)
    cal['x-wr-timezone'] = current_app.calendar_timezone

    for json_blob in groupme_json.get('response', {}).get('events', []):
            if 'deleted_at' not in json_blob:
                event = Event()
            event['uid'] = json_blob['event_id']
            event.add('dtstart', dateutil.parser.parse(json_blob['start_at']))
            if json_blob.get('end_at'):
                event.add('dtend', dateutil.parser.parse(json_blob['end_at']))
            event['summary'] = json_blob['name']
            event['description'] = json_blob.get('description', '')
            if json_blob.get('location'):
                location = json_blob.get('location', {})

                if json_blob.get('description'):
                    event['description'] += '\n\n'
                event['description'] += 'Location:\n'

                if location.get('name') and location.get('address'):
                    event['location'] = f"{location.get('name')}, {location.get('address').strip().replace('\n', ', ')}"
                    event['description'] += f"{location.get('name')}\n{location.get('address')}"
                    event['description'] += '\n'
                    event['description'] += location.get('address')
                elif location.get('name'):
                    event['location'] = location.get('name')
                    event['description'] += location.get('name')
                elif location.get('address'):
                    event['location'] = location.get('address').strip().replace("\n", ", ")
                    event['description'] += location.get('address')

                if location.get('lat') and location.get('lng'):
                    location_url = 'https://www.google.com/maps?q={},{}'.format(location.get('lat'), location.get('lng'))
                    if not event.get('location'):
                        event['location'] = location_url
                    else:
                        event['description'] += '\n'
                    event['description'] += location_url

            if json_blob.get('updated_at'):
                event['last-modified'] = dateutil.parser.parse(json_blob.get('updated_at'))
            cal.add_component(event)

    return cal.to_ical()
except Exception as e:
        print(f"An error occurred: {e}")
        return None

def groupme_ics_error(error_text, static_name=None):
    cal = Calendar()
    cal['prodid'] = '-//Andrew Mussey//GroupMe-to-ICS 0.1//EN'
    cal['version'] = '2.0'
    cal['calscale'] = 'GREGORIAN'
    cal['method'] = 'PUBLISH'
    cal['x-wr-calname'] = 'GroupMe: {} ({})'.format(current_app.groupme_calendar_name, error_text)
    cal['x-wr-timezone'] = 'America/Los_Angeles'

    return cal.to_ical()
