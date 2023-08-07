import requests

from nftmarket.core.models import ClickApiTokens


def _click_api_url(token):
    return f'https://fomoaffiliates.click/click_api/v3?token={token}&info=1'


def get_subid(ref_name):
    try:
        click_api_token = ClickApiTokens.objects.get(ref_name=ref_name)
    except ClickApiTokens.DoesNotExist:
        return None

    api_url = _click_api_url(click_api_token.token)
    try:
        api_response = requests.get(api_url)
        return api_response.json().get('info', dict()).get('sub_id')
    except Exception:
        pass
    return None


def get_pixel(ref_name, params):
    sub_id = get_subid(ref_name)
    if not sub_id:
        return
    params['subid'] = sub_id
    postback_url = 'https://fomoaffiliates.click/5e33ca7/postback'
    try:
        resp = requests.get(postback_url, params=params)
    except Exception:
        pass
    return resp
