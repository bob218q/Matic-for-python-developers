from maticvigil.EVCore import EVCore

evc = EVCore(verbose=False)

# put in a contract address deployed from your MaticVigil account
contract_instance = evc.generate_contract_sdk(
    contract_address='0xContractAddress',
    app_name='microblog'
)
# -- expanding keyword params from a mapping --
print(contract_instance.addPost(**{'title': 'New2', 'body': '', 'url': '', 'photo': ''}))

# another transaction sent to the addPost() function on the contract
# print(contract_instance.addPost(title='New3', body='TestBody', url='', photo=''))
