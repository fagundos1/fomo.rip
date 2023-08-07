from django.http import HttpResponseRedirect


class AccountRequiredMixin:
    def dispatch(self, request, *args, **kwargs):
        if not hasattr(request, 'account') or request.account is None:
            return HttpResponseRedirect('/')
        return super().dispatch(request, *args, **kwargs)
