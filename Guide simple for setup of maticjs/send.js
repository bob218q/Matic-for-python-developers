const Matic = require('maticjs').default

const from = '0x87b917F40f7a031e13577200801b5f2f0D3E1b91' // from address
const recipient = '0xdea6D214E7505391FD64405fE8fbA206C2073Ee4' // receipent address

const token = '0xcc5de81d1af53dcb5d707b6b33a50f4ee46d983e' // test token address
const amount = '1000000000000000000' // amount in wei

// Create object of Matic
const matic = new Matic({
  maticProvider: 'https://testnet2.matic.network',
  parentProvider: 'https://ropsten.infura.io/v3/70645f042c3a409599c60f96f6dd9fbc',
  rootChainAddress: '0x60e2b19b9a87a3f37827f2c8c8306be718a5f9b4',
  syncerUrl: 'https://matic-syncer2.api.matic.network/api/v1',
  watcherUrl: 'https://ropsten-watcher2.api.matic.network/api/v1',
})

matic.wallet = '0x01161625139843901B1BD54D04904DE80F875978900D369A25817F6CE970CA14' // prefix with `0x`

// Send Tokens
matic.transferTokens(token, recipient, amount, {
  from,
  onTransactionHash: (hash) => {
    // action on Transaction success
    console.log('Transaction Hash ---->', hash) // eslint-disable-line
  },
})
