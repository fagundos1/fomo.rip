from django.core.exceptions import ImproperlyConfigured
from django.utils.deprecation import MiddlewareMixin
from nftmarket.core.models import Account


def get_account(request):
    account_pk = request.session.get('_account_pk')
    if account_pk:
        try:
            return Account.objects.get(pk=account_pk)
        except Account.DoesNotExist:
            pass
    return None


class AccountMiddleware(MiddlewareMixin):
    def process_request(self, request):
        if not hasattr(request, 'session'):
            raise ImproperlyConfigured(
                'AccountMiddleware requires session')
        request.account = get_account(request)


class ForceDefaultLanguageMiddleware(MiddlewareMixin):
    """
    Ignore Accept-Language HTTP headerss
    This will force the I18N machinery to always choose settings.LANGUAGE_CODE
    as the default initial language, unless another one is set via sessions or
    cookies. Should be installed *before* any middleware that checks
    request.META['HTTP_ACCEPT_LANGUAGE'], namely
    django.middleware.locale.LocaleMiddleware
    """
    def process_request(self, request):
        if 'HTTP_ACCEPT_LANGUAGE' in request.META:
            del request.META['HTTP_ACCEPT_LANGUAGE']
