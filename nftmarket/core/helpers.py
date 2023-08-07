from functools import wraps

from django.contrib import messages
from django.shortcuts import redirect


def account_required(view_func):
    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        if not hasattr(request, 'account') or request.account is None:
            return redirect('core:index_page')
        return view_func(request, *args, **kwargs)
    return wrapper


def active_account_required(view_func):
    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        if not hasattr(request, 'account') or request.account is None:
            return redirect('core:index_page')
        if not request.account.is_active:
            messages.error(request, _('Your account was blocked'))
            return redirect('core:index_view')
        return view_func(request, *args, **kwargs)
    return wrapper
