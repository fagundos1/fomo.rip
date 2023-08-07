from web3 import Web3
from eth_account.messages import encode_structured_data
from dataclasses import dataclass
from django.conf import settings


@dataclass
class DealClass:
    seller: str
    buyer: str
    price: int
    fee: int
    collateral: int
    timestamp: int
    buyer_deposited: int
    seller_deposited: int
    buyer_claim: int
    seller_claim: int
    claim_time: int
    signature: bytes
    exists: bool
    arbitration: bool
    buyer_completed: bool
    closed: bool


def is_valid_address(addr: str) -> bool:
    if hasattr(Web3, 'is_address'):
        return Web3.is_address(addr)
    return Web3.isAddress(addr)


def recover_message(network: str, message: str, signature: str) -> str:
    chain_settings = settings.NETWORKS[network]
    w3_chain = Web3(Web3.HTTPProvider(chain_settings['url']))
    return w3_chain.eth.account.recover_message(
        message, signature=signature)


def make_deal_tx_message(deal: type) -> dict:
    offer = deal.offer
    chain_settings = settings.NETWORKS[offer.network]
    token_decimals = chain_settings['token_decimals']
    deal_tx_message = {
        'domain': {
            'chainId': chain_settings['chain_id'],
            'name': 'Deal',
            'verifyingContract': chain_settings['escrow_addr'],
            'version': '1',
        },
        'message': {
             'seller': offer.seller.wallet,
             'buyer': offer.buyer.wallet,
             'price': int(offer.price * pow(10, token_decimals)),
             'fee': int(deal.fee * pow(10, token_decimals)),
             'collateral': int(offer.collateral * pow(10, token_decimals)),
             'timestamp': deal.start_timestamp()
        },
        'primaryType': 'Deal',
        'types': {
            'EIP712Domain': [
                {'name': 'name', 'type': 'string'},
                {'name': 'version', 'type': 'string'},
                {'name': 'chainId', 'type': 'uint256'},
                {'name': 'verifyingContract', 'type': 'address'},
            ],
            'Deal': [
                {'name': 'seller', 'type': 'address'},
                {'name': 'buyer', 'type': 'address'},
                {'name': 'price', 'type': 'uint256'},
                {'name': 'fee', 'type': 'uint256'},
                {'name': 'collateral', 'type': 'uint256'},
                {'name': 'timestamp', 'type': 'uint256'}
            ]
        }
    }
    return deal_tx_message


def sign_deal(deal: type) -> dict:
    tx_message = make_deal_tx_message(deal)
    encoded_message = encode_structured_data(tx_message)
    chain_settings = settings.NETWORKS[deal.offer.network]
    w3_chain = Web3(Web3.HTTPProvider(chain_settings['url']))
    signed_tx_message = w3_chain.eth.account.sign_message(
        encoded_message, settings.SIGNER_KEY)
    hash_id = signed_tx_message.messageHash.hex()
    deal.hash_id = hash_id
    deal.save()
    deal_obj = tx_message['message']
    deal_obj['signature'] = signed_tx_message.signature.hex()
    deal_obj['price'] = str(deal_obj['price'])
    deal_obj['collateral'] = str(deal_obj['collateral'])
    deal_obj['fee'] = str(deal_obj['fee'])
    return deal_obj


def get_contract_deal(deal: type) -> type:
    escrow_abi = get_escrow_abi()
    chain_settings = settings.NETWORKS[deal.offer.network]
    w3_chain = Web3(Web3.HTTPProvider(chain_settings['url']))
    contract = w3_chain.eth.contract(
        address=chain_settings['escrow_addr'],  abi=escrow_abi)
    deal_data = contract.functions.getDeal(deal.hash_id).call()
    return DealClass(*deal_data)
