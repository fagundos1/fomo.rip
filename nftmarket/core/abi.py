import json
from django.conf import settings


def get_escrow_abi():
    json_path = settings.BASE_DIR / 'abijson' / 'EscrowContract.json'
    with open(json_path) as json_fobj:
        info = json.load(json_fobj)
        return info.get('abi')
