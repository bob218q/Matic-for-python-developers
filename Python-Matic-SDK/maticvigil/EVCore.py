from datetime import datetime
import os
import pwd
import json
from eth_account.messages import defunct_hash_message
from eth_account.account import Account
import requests
from .EVContractUtils import ABIParser, extract_abi
from types import MethodType
import inspect
from solidity_parser import parser
import sys
import logging
from .exceptions import *
from .http_helper import make_http_call
from typing import List

CLEAN_SLATE_SETTINGS = {
  "PRIVATEKEY": None,
  "INTERNAL_API_ENDPOINT": "https://mainnet.maticvigil.com/api",
  "REST_API_ENDPOINT": None,
  "MATICVIGIL_USER_ADDRESS": "",
  "MATICVIGIL_API_KEY": ""

}

formatter = logging.Formatter('%(levelname)-8s %(name)-4s %(asctime)s,%(msecs)d : %(message)s')
ev_core_logger = logging.getLogger('EVCore')
ev_core_logger.addHandler(logging.NullHandler())

def read_file_by_chunks(fp, chunk_size=1024):
    chunk = ''
    for p in fp:
        chunk += p
        if len(p) == chunk_size:
            yield chunk
            chunk = ''
    if chunk:
        yield chunk

def generate_contract_function(**outer_kwargs):
    def fn(self, *params_args, **params_kwargs):
        request_url = outer_kwargs['method_url']
        request_type = outer_kwargs['request_type']
        ev_core_logger.debug('Calling MaticVigil contract function')
        ev_core_logger.debug(request_url)
        if request_type == 'get':
            for arg in params_args:
                # to construct get request like /getPostId/{id} or /2daccessor/{param1}/{param2}
                request_url +=  '/' + arg
            request_url = request_url.rstrip('/')
            r = make_http_call(request_type='get', url=request_url)
            return r
        elif request_type == 'post':
            r = make_http_call(request_type='post', url=request_url, params=params_kwargs, headers={'X-API-KEY': self._api_write_key})
            txhash = r['data'][0]['txHash']
            self._pending_txhashes.add(txhash)
            return r['data']
    return fn

class EVCore(object):
    def __init__(self, verbose=False):
        self._verbose = verbose
        self._account = None
        try_login = False
        try:
            with open(pwd.getpwuid(os.getuid()).pw_dir + '/.maticvigil/settings.json', 'r') as f:
                s = json.load(f)
        except:
            # settings file does not exist, copy over empty settings
            try:
                os.stat(pwd.getpwuid(os.getuid()).pw_dir + '/.maticvigil')
            except:
                os.mkdir(pwd.getpwuid(os.getuid()).pw_dir + '/.maticvigil')
            # create settings file from empty JSON file
            with open(pwd.getpwuid(os.getuid()).pw_dir + '/.maticvigil/settings.json', 'w') as f2:
                json.dump(obj=CLEAN_SLATE_SETTINGS, fp=f2)
            s = CLEAN_SLATE_SETTINGS
        else:
            try_login = True
        finally:
            self._settings = s
            if self._verbose:
                ev_core_logger.debug('Loaded settings:')
                ev_core_logger.debug(s)
            if try_login:
                try:
                    r = self._login(internal_api_endpoint=self._settings['INTERNAL_API_ENDPOINT'], private_key=self._settings['PRIVATEKEY'])
                except:
                    # try to load account info from cached file
                    if self._verbose:
                        ev_core_logger.info('Could not connect to MaticVigil endpoint. Attempting to load account information from cache.')
                    try:
                        with open(pwd.getpwuid(os.getuid()).pw_dir + '/.maticvigil/account_info.json', 'r') as f:
                            self._account = json.load(f)
                            if self._verbose:
                                ev_core_logger.info('Loaded account information from cache')
                                if 'cached_time' in self._account:
                                    ev_core_logger.info('Account information cached on: ')
                                    ev_core_logger.info(self._account['cached_time'])
                    except:
                        if self._verbose:
                            ev_core_logger.error('Could not load account information from cache.')
                else:
                    if self._verbose:
                        for k in r:
                            d = r[k]
                            if k == 'contracts':
                                ev_core_logger.info('Contracts deployed/verified:\n=============')
                                for _k in d:
                                    del (_k['appId'])
                                    ev_core_logger.info(f'Name: {_k["name"]}')
                                    ev_core_logger.info(f'Address: {_k["address"]}')
                                    ev_core_logger.info('--------------------')
                            elif k == 'key':
                                ev_core_logger.info(f'MaticVigil API key: \t {d}\n=============\n')
                            elif k == 'api_prefix':
                                ev_core_logger.info(f'REST API prefix: \t {d}\n=============\n')
                            elif k == 'hooks':
                                ev_core_logger.info(f'Registered integrations/hooks: \t {d}\n=============\n')
                            elif k == 'hook_events':
                                ev_core_logger.info(f'Contracts events fired to registered hooks: \t {d}\n=============\n')
                    with open(pwd.getpwuid(os.getuid()).pw_dir + '/.maticvigil/account_info.json', 'w') as f:
                        r.update({'cached_time': datetime.now().strftime('%d/%m/%Y %H:%M:%S')})
                        json.dump(obj=r, fp=f)
                    self._account = r
                    self._api_read_key = r['readKey']
                    self._api_write_key = r['key']

    @property
    def contracts(self):
        return self._account['contracts'] if self._account else None

    """ def _get_sdk_from_spec(self, contract_address, app_name):
         r = requests.post(url='https://generator3.swagger.io/api/generate', json= {
             'specURL': f"{self._account['api_prefix']}/swagger/{contract_address}/?key={self._api_read_key}",
             'lang': 'python',
             'type': 'CLIENT',
             'codegenVersion': 'V3'
         })
         z = zipfile.ZipFile(io.BytesIO(r.content))
         try:
             os.stat(pwd.getpwuid(os.getuid()).pw_dir + '/.../contracts')
         except:
             os.mkdir(pwd.getpwuid(os.getuid()).pw_dir + '/.../contracts')
         os.mkdir(pwd.getpwuid(os.getuid()).pw_dir + f'/.../contracts/{app_name}')
         z.extractall(pwd.getpwuid(os.getuid()).pw_dir + f'/.../contracts/{app_name}')
         sys.path.append(pwd.getpwuid(os.getuid()).pw_dir + f'/.../contracts/{app_name}') """

    def generate_contract_sdk(self, contract_address, app_name):
        # download client SDK from online generator
        # self._get_sdk_from_spec(contract_address, app_name)
        # return pwd.getpwuid(os.getuid()).pw_dir + f'/.maticvigil/contracts/{app_name}'
        openapi_spec = make_http_call(request_type='get', url=f"{self._account['api_prefix']}/swagger/{contract_address}/?key={self._api_read_key}")
        fnname_to_fnimpl_map = dict()
        for endpoint in openapi_spec['paths']:
            fn_name = endpoint[1:]  # to remove prefixed '/'
            trailing_slash = fn_name.find('/')   # possible with GET calls like /getObject/{id}
            if trailing_slash != -1:
                fn_name = fn_name[:trailing_slash]
            http_request_type = list(openapi_spec['paths'][endpoint].keys())[0]  # get or post
            params_list = list()
            if http_request_type == 'get':
                for each_param in openapi_spec['paths'][endpoint]['get']['parameters']:
                    params_list.append(each_param['name'])
            elif http_request_type == 'post':
                for each_param in openapi_spec['paths'][endpoint]['post']['requestBody']['content']['application/x-www-form-urlencoded']['schema']['properties'].keys():
                    params_list.append(each_param)
            method_url = f"{self._account['api_prefix']}/contract/{contract_address}/{fn_name}"
            contract_fn = generate_contract_function(method_url=method_url, request_type=http_request_type)
            # print(inspect.signature(contract_fn))
            fnname_to_fnimpl_map[fn_name] = contract_fn
            # setattr(contract_obj, fn_name, contract_fn)
            # contract_obj.__setattr__(fn_name, contract_fn)
        contract_obj = EVContract(contract_address, self._api_read_key, self._api_write_key, self._settings)
        for each_fn in fnname_to_fnimpl_map:
            contract_obj.__setattr__(each_fn, MethodType(fnname_to_fnimpl_map[each_fn], contract_obj))
        contract_obj._initialized = True
        return contract_obj

      
    def login(self):
        return self._login(internal_api_endpoint=self._settings['INTERNAL_API_ENDPOINT'], private_key=self._settings['PRIVATEKEY'])

    def signup(self, invite_code):
        msg = "Trying to signup"
        message_hash = defunct_hash_message(text=msg)
        signed_msg = Account.signHash(message_hash, self._settings['PRIVATEKEY'])
        request_json = {'msg': msg, 'sig': signed_msg.signature.hex(), 'code': invite_code}
        # --MATICVIGIL API CALL to /signup---
        ev_core_logger.debug('Attempting to signup with MaticVigil')
        signup_url = self._settings['INTERNAL_API_ENDPOINT'] + '/signup'
        r = make_http_call(request_type='post', url=signup_url, params=request_json)
        return r

      
    def deploy(self, contract_file, contract_name, inputs):
        """
        Deploys a smart contract from the solidity source code specified
        :param contract_file : path to the contract file name
        :param contract_name : the contract name to be deployed from the file
        :param inputs : mapping of constructor arguments
        """
        contract_src = ""
        if self._verbose:
            print('Got unordered constructor inputs: ')
            print(inputs)

        sources = dict()

        if contract_file[0] == '~':
            contract_full_path = os.path.expanduser(contract_file)
        else:
            contract_full_path = contract_file
        resident_directory = ''.join(map(lambda x: x + '/', contract_full_path.split('/')[:-1]))
        contract_file_name = contract_full_path.split('/')[-1]
        contract_file_obj = open(file=contract_full_path)

        main_contract_src = ''
        while True:
            chunk = contract_file_obj.read(1024)
            if not chunk:
                break
            main_contract_src += chunk
        sources[f'ev-py-sdk/{contract_file_name}'] = {'content': main_contract_src}
        # loop through imports and add them to sources
        source_unit = parser.parse(main_contract_src)
        source_unit_obj = parser.objectify(source_unit)

        for each in source_unit_obj.imports:
            import_location = each['path'].replace("'", "")
            # TODO: follow specified relative paths and import such files too
            if import_location[:2] != './':
                ev_core_logger.error('You can only import files from within the same directory as of now')
                raise EVBaseException('You can only import files from within the same directory as of now')
            # otherwise read the file into the contents mapping
            full_path = resident_directory + import_location[2:]
            imported_contract_obj = open(full_path, 'r')
            contract_src = ''
            while True:
                chunk = imported_contract_obj.read(1024)
                if not chunk:
                    break
                contract_src += chunk
            sources[f'ev-py-sdk/{import_location[2:]}'] = {'content': contract_src}

        abi_json = extract_abi(self._settings, {'sources': sources, 'sourceFile': f'ev-py-sdk/{contract_file_name}'})
        abp = ABIParser(abi_json=abi_json)
        abp.load_abi()
        c_inputs = abp.ordered_map_to_ev_constructor_args(inputs)
        if self._verbose:
            print('Ordered constructor inputs: \n', c_inputs)

        msg = "Trying to deploy"
        message_hash = defunct_hash_message(text=msg)
        signed_msg = Account.signHash(message_hash, self._settings['PRIVATEKEY'])
        deploy_json = {
            'msg': msg,
            'sig': signed_msg.signature.hex(),
            'name': contract_name,
            'inputs': c_inputs,
            'sources': sources,
            'sourceFile': f'ev-py-sdk/{contract_file_name}'
        }
        # --MATICVIGIL API CALL---
        r = make_http_call(request_type='post', url=self._settings['INTERNAL_API_ENDPOINT'] + '/deploy', params=deploy_json)
        if self._verbose:
            ev_core_logger.debug('MaticVigil deploy response: ')
            ev_core_logger.debug(r)
        return r['data']

      
    def _login(self, internal_api_endpoint, private_key):
        msg = "Trying to login"
        message_hash = defunct_hash_message(text=msg)
        signed_msg = Account.signHash(message_hash, private_key)
        # --MATICVIGIL API CALL---
        headers = {'accept': 'application/json', 'Content-Type': 'application/json'}
        r = requests.post(internal_api_endpoint + '/login',
                          json={'msg': msg, 'sig': signed_msg.signature.hex()}, headers=headers)
        if self._verbose:
            print(r.text)
        if r.status_code == requests.codes.ok:
            r = r.json()
            return r['data']
        else:
            return None

          
class EVContract(object):
    def __init__(self, contract_address, api_read_key, api_write_key, ev_settings):
        self._contract_address = contract_address
        self._initialized = False
        self._api_read_key = api_read_key
        self._api_write_key = api_write_key
        self._ev_settings = ev_settings
        self._ev_private_key = self._ev_settings['PRIVATEKEY']
        self._pending_txhashes = set()

    @property
    def integrations(self):
        if not self._initialized:
            return None
        url = self._ev_settings['INTERNAL_API_ENDPOINT']+'/hooks/list'
        msg = 'dummystring'
        message_hash = defunct_hash_message(text=msg)
        sig_msg = Account.signHash(message_hash, self._ev_settings['PRIVATEKEY'])
        method_args = {
            "msg": msg,
            "sig": sig_msg.signature.hex(),
            "key": self._api_write_key,
            "type": "web",
            "contract": self._contract_address
        }
        list_response = make_http_call(
            request_type='post',
            url=url,
            params=method_args,
            headers={'accept': 'application/json', 'Content-Type': 'application/json'}
        )
        if list_response['success']:
            return list_response['data']
        else:
            return None

    def deactivate_integration(self, hook_id):
        msg = 'dummystring'
        message_hash = defunct_hash_message(text=msg)
        sig_msg = Account.signHash(message_hash, self._ev_settings['PRIVATEKEY'])
        method_args = {
            "msg": msg,
            "sig": sig_msg.signature.hex(),
            "key": self._api_write_key,
            "type": "web",
            "contract": self._contract_address,
            "id": hook_id
        }
        integration_response = make_http_call(
            request_type='post',
            url=self._ev_settings['INTERNAL_API_ENDPOINT'] + '/hooks/deactivate',
            params=method_args,
            headers={'accept': 'application/json', 'Content-Type': 'application/json'}
        )
        if not integration_response['success']:
            return False
        else:
            return True

    def activate_integration(self, hook_id):
        msg = 'dummystring'
        message_hash = defunct_hash_message(text=msg)
        sig_msg = Account.signHash(message_hash, self._ev_settings['PRIVATEKEY'])
        method_args = {
            "msg": msg,
            "sig": sig_msg.signature.hex(),
            "key": self._api_write_key,
            "type": "web",
            "contract": self._contract_address,
            "id": hook_id
        }
        integration_response = make_http_call(
            request_type='post',
            url=self._ev_settings['INTERNAL_API_ENDPOINT'] + '/hooks/activate',
            params=method_args,
            headers={'accept': 'application/json', 'Content-Type': 'application/json'}
        )
        if not integration_response['success']:
            return False
        else:
            return True

          
    def add_event_integration(self, events: List, callback_url, integration_channel='web'):
        hook_id = self._register_integration(callback_url)
        if not hook_id:
            return None
        if not integration_channel == 'web':
            err_msg = 'Only integrations of type \'web\' are supported by SDK currently'
            ev_core_logger.error(err_msg)
            raise EVBaseException(err_msg)
        if '*' in events:
            events = ['*']
        msg = 'dummystring'
        message_hash = defunct_hash_message(text=msg)
        sig_msg = Account.signHash(message_hash, self._ev_settings['PRIVATEKEY'])
        method_args = {
            "msg": msg,
            "sig": sig_msg.signature.hex(),
            "key": self._api_write_key,
            "type": "web",
            "contract": self._contract_address,
            "id": hook_id,
            "events": events
        }
        integration_response = make_http_call(
            request_type='post',
            url=self._ev_settings['INTERNAL_API_ENDPOINT']+'/hooks/updateEvents',
            params=method_args,
            headers={'accept': 'application/json', 'Content-Type': 'application/json'}
        )
        return hook_id if integration_response.get('success', False) else None

      
    def add_contract_monitoring_integration(self, callback_url, integration_channel='web'):
        hook_id = self._register_integration(callback_url)
        if not hook_id:
            return None
        if not integration_channel == 'web':
            err_msg = 'Only integrations of type \'web\' are supported by SDK currently'
            ev_core_logger.error(err_msg)
            raise EVBaseException(err_msg)
        msg = 'dummystring'
        message_hash = defunct_hash_message(text=msg)
        sig_msg = Account.signHash(message_hash, self._ev_settings['PRIVATEKEY'])
        method_args = {
            "msg": msg,
            "sig": sig_msg.signature.hex(),
            "key": self._api_write_key,
            "type": "web",
            "contract": self._contract_address,
            "id": hook_id,
            "action": "set"
        }
        integration_response = make_http_call(
            request_type='post',
            url=self._ev_settings['INTERNAL_API_ENDPOINT'] + '/hooks/transactions',
            params=method_args,
            headers={'accept': 'application/json', 'Content-Type': 'application/json'}
        )
        return hook_id if integration_response.get('success', False) else None

      
    def _register_integration(self, url):
        headers = {'accept': 'application/json', 'Content-Type': 'application/json',
                   'X-API-KEY': self._api_write_key}
        msg = 'dummystring'
        message_hash = defunct_hash_message(text=msg)
        sig_msg = Account.signHash(message_hash, self._ev_private_key)
        method_args = {
            "msg": msg,
            "sig": sig_msg.signature.hex(),
            "key": self._ev_private_key,
            "type": "web",
            "contract": self._contract_address,
            "web": url
        }
        reg_webhook_args = dict(
            url=self._ev_settings['INTERNAL_API_ENDPOINT']+'/hooks/add',
            params=method_args,
            headers=headers
        )
        ev_core_logger.debug('Registering webhook')
        ev_core_logger.debug(reg_webhook_args)
        r = make_http_call(
            request_type='post',
            **reg_webhook_args
        )
        ev_core_logger.debug('Registration response')
        ev_core_logger.debug(r)
        if not r['success']:
            return None
        else:
            hook_id = r["data"]["id"]
            return hook_id
