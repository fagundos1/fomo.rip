from django.conf import settings as app_settings


def settings(request):
    return dict(settings=app_settings)


def auth(request):
    auth = dict(account=None, is_authenticated=False)
    account = request.account
    if account is not None:
        auth = dict(account=account, is_authenticated=True)
    return dict(auth=auth)


def urltag(request):
    tag = '-'.join(filter(None, request.path.split('/')))
    tag = tag or 'index'
    return dict(urltag=tag)


def tutorial(request):
    is_tutorial_shown = request.COOKIES.get('tutorial', '')
    return {
        'is_tutorial_shown': is_tutorial_shown
    }
