# -*- coding: utf-8 -*-
import json
from eth_utils import encode_hex, keccak
import eth_utils
from eth_abi import is_encodable

class MissingContractException(Exception):
    pass

class SentinelInfoNotFoundError(RuntimeError):
    pass

class ContractNotMinedException(Exception):
    pass

class ABIParse:
    def __init__(self, abi_json):
        self._fill_allowed_ints()
        self._fill_allowed_bytes()
        self._events_mapping = {}
        self._functions_mapping = {}
        self._functions_name_to_hash = {}
        self._functions_selector_to_hash = {}
        self._abi_def = abi_json
        self._map_abi()

    def _fill_allowed_ints(self):
        self._allowed_int_types = allowed_int_types()

    def _fill_allowed_bytes(self):
        self._allowed_byte_types = allowed_byte_types()

    def load_abi(self):
        self._map_abi()
        # print(self._events_mapping)

    def _map_events(self, events):
        for event in events:
            canonical_types = ""
            for types in event["inputs"]:
                canonical_types += types["type"] + ","
            # remove extra , in the end
            canonical_types = canonical_types.rstrip(',')
            canonical_full_name = "{0}({1})".format(event["name"], canonical_types)
            event_hash = encode_hex(keccak(text=canonical_full_name))
            # initialize event signature based hash storage
            # also add a redundant one based on the name to refer back to the hash
            self._events_mapping[event_hash] = {}
            self._events_mapping[event["name"]] = event_hash
            # begin filling
            self._events_mapping[event_hash]["nickname"] = event["name"]
            self._events_mapping[event_hash]["canonical"] = canonical_full_name
            # strip out the '0x' and take the first (32 bits/4 bytes/8 hex digits) as the method selector
            # defined according to the function encoding standards defined by the Solidity compiler
            self._events_mapping[event_hash]["selector"] = event_hash[2:10]
            # types_full_list = list(map(lambda x: x["type"], event["inputs"]))
            # params_full_list = list(map(lambda x: x["name"], event["inputs"]))
            unindexed_params_list = list(
                map(lambda x: x["name"], filter(lambda x: x["indexed"] == False, event["inputs"])))
            unindexed_types_list = list(
                map(lambda x: x["type"], filter(lambda x: x["indexed"] == False, event["inputs"])))
            indexed_params_list = list(
                map(lambda x: x["name"], filter(lambda x: x["indexed"] == True, event["inputs"])))
            indexed_types_list = list(map(lambda x: x["type"], filter(lambda x: x["indexed"] == True, event["inputs"])))
            self._events_mapping[event_hash]["unindexed_types"] = unindexed_types_list
            self._events_mapping[event_hash]["unindexed_params"] = unindexed_params_list
            self._events_mapping[event_hash]["indexed_params"] = indexed_params_list
            self._events_mapping[event_hash]["indexed_types"] = indexed_types_list
            # print('...')

    def _map_functions(self, functions):
        for function in functions:
            canonical_types = ""
            if function['name'] == 'decimals':
                self._is_erc20 = True
            # --- expand tuple types to elementary types where necessary ---
            fn_types_list = list()
            tuple_encodings = dict()
            for fn_input in function['inputs']:
                if 'tuple' not in fn_input['type']:
                    fn_types_list.append(fn_input['type'])
                    canonical_types += fn_input['type'] + ','
                else:
                    # prepare string to be passed to eth_abi.encode_single('(component1, component2)', [val1, val2])
                    is_array = False
                    if fn_input['type'][-2:] == '[]':  # could be an array of tuples
                        is_array = True
                    enc_string = self._expand_components(fn_input['components'], is_array)
                    tuple_encodings[fn_input['name']] = enc_string
                    # the type to be included in the canonical sig is the same
                    # for eg 'f_name((uint256,string,address))' instead of f_name(tuple)
                    fn_types_list.append(enc_string)
                    canonical_types += enc_string + ','
            # END --- expand tuple types to elementary types where necessary ---
            canonical_types = canonical_types.rstrip(',')
            canonical_full_name = "{0}({1})".format(function["name"], canonical_types)
            function_hash = encode_hex(keccak(text=canonical_full_name))
            # initialize function signature based hash storage
            # also add a redundant one based on the name to refer back to the hash
            self._functions_mapping[function_hash] = {}
            self._functions_name_to_hash[function["name"]] = function_hash
            # begin filling
            self._functions_mapping[function_hash]["nickname"] = function["name"]
            self._functions_mapping[function_hash]["canonical"] = canonical_full_name
            # strip out the '0x' and take the first (32 bits/4 bytes/8 hex digits) as the method selector
            # defined according to the function encoding standards defined by the Solidity compiler
            self._functions_mapping[function_hash]["selector"] = function_hash[2:10]
            fn_params_list = list(map(lambda x: x["name"], function["inputs"]))
            # fn_types_list = list(map(lambda x: x["type"], function["inputs"]))

            self._functions_mapping[function_hash]["params"] = fn_params_list
            self._functions_mapping[function_hash]["types"] = fn_types_list
            if tuple_encodings:
                self._functions_mapping[function_hash]['input_tuple_encodings'] = tuple_encodings
            # add output types now
            return_params_list = list(map(lambda x: x["name"], function["outputs"]))
            self._functions_mapping[function_hash]["output_params"] = return_params_list
            # self._functions_mapping[function_hash]["output_types"] = return_types_list
            # --- OUTPUT params: expand tuple types to elementary types where necessary ---
            fn_op_types_list = list()
            op_tuple_encodings = dict()
            for fn_output in function['outputs']:
                if 'tuple' not in fn_output['type']:
                    fn_op_types_list.append(fn_output['type'])
                else:
                    # prepare string to be passed to eth_abi.encode_single('(component1, component2)', [val1, val2])
                    is_array = False
                    if fn_output['type'][-2:] == '[]':  # could be an array of tuples
                        is_array = True
                    enc_string = self._expand_components(fn_output['components'], is_array)
                    op_tuple_encodings[fn_output['name']] = enc_string
                    # the type to be included in the canonical sig is the same
                    # for eg 'f_name((uint256,string,address))' instead of f_name(tuple)
                    fn_op_types_list.append(enc_string)
            # END --- OUTPUT params: expand tuple types to elementary types where necessary ---
            self._functions_mapping[function_hash]["output_types"] = fn_op_types_list
            if op_tuple_encodings:
                self._functions_mapping[function_hash]['output_tuple_encodings'] = op_tuple_encodings
            self._functions_mapping[function_hash]["stateMutability"] = function["stateMutability"]
            # fill up function selector to function canonical signature hash mapping
            self._functions_selector_to_hash[function_hash[2:10]] = function_hash

            
    def _expand_components(self, components_list, is_tuple_array):
        encoding_type_str = '('
        for component in components_list:
            if 'tuple' not in component['type']:
                encoding_type_str += component['type']+','
            else:
                is_nested_tuple_an_array = component['type'][-2:] == '[]'
                encoding_type_str += self._expand_components(component['components'], is_nested_tuple_an_array)
        if encoding_type_str[-1:] == ',':
            encoding_type_str = encoding_type_str[:-1]  # remove the final comma
        encoding_type_str += ')'  # final enclosing parantheses
        if is_tuple_array:
            encoding_type_str += '[]'

        return encoding_type_str

    
    def _map_constructor(self, constr_):
        for constr in constr_:
            self._constructor_mapping = {"constructor": {}}
            inputs = constr["inputs"]
            input_params_list = list(map(lambda x: x["name"], inputs))
            input_types_list = list(map(lambda x: x["type"], inputs))
            self._constructor_mapping["constructor"]["input_params"] = input_params_list
            self._constructor_mapping["constructor"]["input_types"] = input_types_list

    def _map_erc20_values(self):
        pass
        # if 'decimals' in

        
    def _map_abi(self):
        events = list(filter(lambda x: x["type"] == "event", self._abi_def))
        functions = list(filter(lambda x: x["type"] == "function", self._abi_def))
        constr_ = list(filter(lambda x: x["type"] == "constructor", self._abi_def))
        # print("Events: ", events)
        self._map_events(events)
        self._map_functions(functions)
        self._map_constructor(constr_)
        # print("\n Function mapping.... \n {0}".format(self._functions_mapping))
        # print("\n Event mapping.... \n {0}".format(self._events_mapping))

        
    def _only_getters(self):
        hash_keys = list(
            filter(lambda x: self._functions_mapping[x]["stateMutability"] == "view", self._functions_mapping))
        hash_entries = list(map(lambda x: self._functions_mapping[x], hash_keys))
        return dict(zip(hash_keys, hash_entries))

    
    def _only_getters_by_name(self):
        hash_keys = list(
            filter(lambda x: self._functions_mapping[x]["stateMutability"] == "view", self._functions_mapping))
        hash_names = list(map(lambda x: self._functions_mapping[x]["nickname"], hash_keys))
        hash_entries = list(map(lambda x: self._functions_mapping[x], hash_keys))
        return dict(zip(hash_names, hash_entries))

    
    def _only_writers_by_name(self):
        hash_keys = list(
            filter(lambda x: self._functions_mapping[x]["stateMutability"] != "view", self._functions_mapping))
        hash_names = list(map(lambda x: self._functions_mapping[x]["nickname"], hash_keys))
        hash_entries = list(map(lambda x: self._functions_mapping[x], hash_keys))
        return dict(zip(hash_names, hash_entries))

    
    def is_valid(self, method, params):
        if method in self._functions_name_to_hash:
            cn_hash = self._functions_mapping[self._functions_name_to_hash[method]]
            # logging.info("IN VALID CHECK: ABI params of length {1}: {0}".format(cn_hash["params"], len(cn_hash["params"])))
            # logging.info("IN VALID CHECK: Received params of length {1}: {0}".format(params, len(params)))
            if len(cn_hash["params"]) is not len(params):
                return (False, -2, "Argument list mismatch")
            else:
                return (True, 1, "Success")
        else:
            return (False, -1, "Invalid method: {0}".format(method))

        
    def is_valid_param_dict(self, method, params):  # params is a dictionary here.
        if method in self._functions_name_to_hash:
            cn_hash = self._functions_mapping[self._functions_name_to_hash[method]]
            # logging.info("IN VALID CHECK: ABI params of length {1}: {0}".format(cn_hash["params"], len(cn_hash["params"])))
            # logging.info("IN VALID CHECK: Received params of length {1}: {0}".format(params, len(params)))
            if len(cn_hash["params"]) is not len(params):
                return (False, -2, "Argument list mismatch")
            else:
                return (True, 1, "Success")
        else:
            return (False, -1, "Invalid method")

        
    def type_category(self, sol_type):  # type category that is used in Swagger API specs, not Solidity specific at all
        if sol_type in self._allowed_int_types:
            return "integer"
        elif sol_type in self._allowed_byte_types or sol_type == "address" or sol_type == "string":
            return "string"
        elif sol_type == "bool":
            return "boolean"
        else:
            if sol_type[-2:] == "[]":
                return "array"
            else:
                return " "

class ABIHelper:
    '''
    Array check methods have lists passed and modified "in place".
    '''

    @classmethod
    def first_pass_check_int(cls, single_param, param_name, param_type, conversion_errors):
        error_flag = False
        try:
            ret = int(single_param)
        except (ValueError, AttributeError):
            conversion_errors[param_name] = "Expected type: {0}. Supplied argument not a valid integer".format(
                param_type)
            error_flag = True
            ret = 0
        return (ret, error_flag)

    @classmethod
    def first_pass_check_byte(cls, single_param, param_name, param_type, conversion_errors):
        error_flag = False
        if eth_utils.is_0x_prefixed(single_param):
            pc = eth_utils.remove_0x_prefix(single_param)
            pc_to_bytes = bytes.fromhex(pc)
            ret = pc_to_bytes
        else:
            try:
                ret = single_param.encode('utf-8')
            except:
                conversion_errors[param_name] = "Expected type: {0}. Supplied argument not a valid byte object.".format(
                    param_type)
                error_flag = True
                ret = "".encode('utf-8')
        return (ret, error_flag)

    @classmethod
    def first_pass_check_address(cls, single_param, param_name, param_type, conversion_errors):
        error_flag = False
        ret = "0x"
        single_param = str(single_param)
        if not eth_utils.is_0x_prefixed(single_param):
            conversion_errors[
                param_name] = "Expected type: address. Supplied argument {0} not a hexadecimal value".format(
                single_param)
            error_flag = True
        else:
            if not eth_utils.is_address(single_param):
                conversion_errors[
                    param_name] = "Expected type: address. Supplied argument {0} is not a valid Ethereum address".format(
                    single_param)
                error_flag = True
            else:
                ret = single_param
        return (ret, error_flag)

    @classmethod
    def first_pass_check_string(cls, single_param, param_name, param_type, conversion_errors):
        error_flag = False
        try:
            ret = str(single_param)
        except:
            conversion_errors[param_name] = "Expected type: {0}. Supplied argument not a valid string".format(
                param_type)
            error_flag = True
            ret = ""
        return (ret, error_flag)

     @classmethod
    def first_pass_check_bool(cls, single_param, param_name, param_type, conversion_errors):
        error_flag = False
        try:
            if single_param.lower() == "true" or single_param == "1":
                ret = True
            elif single_param.lower() == "false" or single_param == "0":
                ret = False
            else:
                ret = False
                conversion_errors[param_name] = "Expected type: bool. Supplied argument not a boolean."
                error_flag = True
        except:
            conversion_errors[param_name] = "Expected type: {0}. Supplied argument not a boolean".format(param_type)
            error_flag = True
            ret = False
        return (ret, error_flag)

    @classmethod
    def first_pass_check_int_arr(cls, int_param_lst, param_name, base_param_type, conversion_errors):
        error_flag = False
        ret = int_param_lst
        for idx, each_int in enumerate(int_param_lst):
            try:
                ret[idx] = int(each_int)
            except (ValueError, AttributeError):
                if param_name not in conversion_errors:
                    conversion_errors[param_name] = {"message": [], "failed_indexes": []}
                error_msg = "Expected type: {0}. One or more supplied argument is not a valid integer".format(
                    base_param_type)
                conversion_errors[param_name]["message"].append(error_msg)
                conversion_errors[param_name]["failed_indexes"].append(idx)
                error_flag = True
                ret[idx] = 0
        return (ret, error_flag)

    @classmethod
    def first_pass_check_bytes_arr(cls, bytes_param_lst, param_name, base_param_type, conversion_errors):
        error_flag = False
        ret = bytes_param_lst
        for idx, bytes_param in enumerate(bytes_param_lst):
            if eth_utils.is_0x_prefixed(bytes_param):
                pc = eth_utils.remove_0x_prefix(bytes_param)
                pc_to_bytes = bytes.fromhex(pc)
                ret[idx] = pc_to_bytes
            else:
                try:
                    ret[idx] = bytes_param.encode('utf-8')
                except:
                    error_msg = "Expected type: {0}. Supplied argument not a valid byte object.".format(base_param_type)
                    conversion_errors[param_name]["message"].append(error_msg)
                    conversion_errors[param_name]["failed_indexes"].append(idx)
                    error_flag = True
                    ret[idx] = "".encode('utf-8')
        return (ret, error_flag)

    @classmethod
    def first_pass_check_address_arr(cls, address_param_lst, param_name, base_param_type, conversion_errors):
        error_flag = False
        ret = address_param_lst
        for idx, each_addr in enumerate(address_param_lst):
            each_addr = str(each_addr)
            ret[idx] = "0x"
            if not eth_utils.is_0x_prefixed(each_addr):
                if param_name not in conversion_errors:
                    conversion_errors[param_name] = {"message": [], "failed_indexes": []}
                e_m = "Expected type: address. Supplied argument {0} not a hexadecimal value".format(each_addr)
                conversion_errors[param_name]["message"].append(e_m)
                conversion_errors[param_name]["failed_indexes"].append(idx)
                error_flag = True
            else:
                if not eth_utils.is_address(each_addr):
                    if param_name not in conversion_errors:
                        conversion_errors[param_name] = {"message": [], "failed_indexes": []}
                    e_m = "Expected type: address. Supplied argument {0} is not a valid Ethereum address".format(
                        each_addr)
                    conversion_errors[param_name]["message"].append(e_m)
                    conversion_errors[param_name]["failed_indexes"].append(idx)
                    error_flag = True
                else:
                    ret[idx] = each_addr
        return (ret, error_flag)

    @classmethod
    def first_pass_check_string_arr(cls, str_param_lst, param_name, base_param_type, conversion_errors):
        error_flag = False
        ret = str_param_lst
        for idx, each_str in enumerate(str_param_lst):
            try:
                ret[idx] = str(each_str)
            except:
                if param_name not in conversion_errors:
                    conversion_errors[param_name] = {"message": [], "failed_indexes": []}
                e_m = "Expected type: {0}. Supplied argument not a valid string".format(base_param_type)
                conversion_errors[param_name]["message"].append(e_m)
                conversion_errors[param_name]["failed_indexes"].append(idx)
                error_flag = True
                ret[idx] = ""
        return (ret, error_flag)

    @classmethod
    def first_pass_check_bool_arr(cls, bool_param_lst, param_name, base_param_type, conversion_errors):
        error_flag = False
        ret = bool_param_lst
        for idx, each_bool in enumerate(bool_param_lst):
            try:
                if each_bool.lower() == "true" or each_bool == "1":
                    ret[idx] = True
                elif each_bool.lower() == "false" or each_bool == "0":
                    ret[idx] = False
                else:
                    ret[idx] = False
                    if param_name not in conversion_errors:
                        conversion_errors[param_name] = {"message": [], "failed_indexes": []}
                    conversion_errors[param_name]["message"].append(
                        "Expected type: bool. Supplied argument not a boolean.")
                    conversion_errors[param_name]["failed_indexes"].append(idx)
                    error_flag = True
            except:
                if param_name not in conversion_errors:
                    conversion_errors[param_name] = {"message": [], "failed_indexes": []}
                e_m = "Expected type: {0}. Supplied argument not a boolean".format(base_param_type)
                conversion_errors[param_name]["message"].append(e_m)
                conversion_errors[param_name]["failed_indexes"].append(idx)
                error_flag = True
                ret[idx] = False
        return (ret, error_flag)

    
    @classmethod
    def first_pass_check_tuple_arr(cls, param_list, param_name, param_type, conversion_errors):
        # we expect the entire type string in case of tuples to be passed here
        # because we gon run a check using the eth_abi.is_encodable feature
        error_flag = not is_encodable(param_type, param_list)
        return param_list, error_flag

    
def allowed_int_types():
    int_type = "int"
    uint_type = "uint"
    allowed_ints = [int_type + str((i + 1) * 8) for i in range(32)]
    allowed_uints = [uint_type + str((i + 1) * 8) for i in range(32)]
    allowed_ints.append(int_type)
    allowed_uints.append(uint_type)

    return allowed_ints + allowed_uints


def allowed_byte_types():
    byte_type = "bytes"
    allowed_byte_types = [byte_type + str(i) for i in range(1, 33)]
    return allowed_byte_types + ["byte", "bytes"]

if __name__ == "__main__":
    with open('abi.json', 'r') as fd:
        abi_json = json.load(fd)
        ab = ABIParse(source='abi', abi_json=abi_json)
    ab.load_abi()
    print(json.dumps(ab._only_getters_by_name()))
