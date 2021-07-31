from maticvigil.EVCore import EVCore

evc = EVCore(verbose=False)
# put in a contract address deployed from your MaticVigil account
contract_instance = evc.generate_contract_sdk(
    contract_address='0xContractAddress',
    app_name='microblog')
# calling the blogTitle() function on the contract. This is a 'read' call, does not change state of the contract
print(contract_instance.blogTitle())
