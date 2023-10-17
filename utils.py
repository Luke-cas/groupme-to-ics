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

# ... (rest of your functions like groupme_json_to_ics and groupme_ics_error remain the same)
