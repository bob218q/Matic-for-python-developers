from maticvigil.EVCore import EVCore

evc = EVCore(verbose=False)
r = evc.deploy(
    contract_file='microblog.sol',
    contract_name='Microblog',
    inputs={
        '_ownerName': 'anomit',
        '_blogTitle': 'TheBlog'
    }
)

print('Contract Address deployed at')
print(r['contract'])
