import tenacity
import requests
from .exceptions import *
import logging

ev_logger = logging.getLogger('EVCore')

@tenacity.retry(
    stop=tenacity.stop_after_delay(60),
    wait=tenacity.wait_random_exponential(multiplier=1, max=60),
    reraise=True
)
def get(url):
    r = requests.get(url)
    return r

@tenacity.retry(
    stop=tenacity.stop_after_delay(60),
    wait=tenacity.wait_random_exponential(multiplier=1, max=60),
    reraise=True
)

def post(url, json_params, headers):
    r = requests.post(url=url, json=json_params, headers=headers)
    return r

def make_http_call(request_type, url, params={}, headers={}):
    response = None
    request_details = {'requestType': request_type, 'url': url, 'params': params, 'headers': headers}
    ev_logger.debug('HTTPRequest')
    ev_logger.debug(request_details)
    if request_type == 'get':
        try:
            response = get(url)
        except (
                requests.exceptions.ConnectionError,
                requests.exceptions.Timeout,
                requests.exceptions.ConnectTimeout
        ) as e:
            raise EVConnectionError("Error connecting to MaticVigil API %s" % url, e)
        except Exception as e:
            raise EVBaseException(e.__str__())
        try:
            response.raise_for_status()
        except requests.exceptions.HTTPError:
            request_details.update({'response': {'code': response.status_code, 'text': response.text}})
            ev_logger.debug(request_details)
            raise EVHTTPError(
                request_url=url,
                request_body='',
                status_code=response.status_code,
                response_body=response.text
            )
    elif request_type == 'post':
        try:
            response = post(url=url, json_params=params, headers=headers)
        except (
                requests.exceptions.ConnectionError,
                requests.exceptions.Timeout,
                requests.exceptions.ConnectTimeout
        ) as e:
            raise EVConnectionError("Error connecting to MaticVigil API %s" % url, e)
        except Exception as e:
            raise EVBaseException(e.__str__())
        try:
            response.raise_for_status()
        except requests.exceptions.HTTPError as e:
            request_details.update({'response': {'code': response.status_code, 'text': response.text}})
            ev_logger.debug(request_details)
            raise EVHTTPError(
                request_url=url,
                request_body=params,
                status_code=response.status_code,
                response_body=response.text
            )
            
    if not(request_type == 'get' and 'swagger' in url):
        return_status = response.status_code
        return_content = response.text
        request_details.update({'response': {'text': return_content, 'status': return_status}})
        ev_logger.debug('HTTPResponse')
        ev_logger.debug(request_details)
    response = response.json()

    api_success = response.get('success', False)
    # ignoring GET returns for OpenAPI spec. Does not carry a 'success' field
    if not api_success and request_type == 'get' and 'openapi' not in response:
        raise EVAPIError(request_url=url, request_body=params, status_code=return_status,
                                    response_body=return_content)
    return response
