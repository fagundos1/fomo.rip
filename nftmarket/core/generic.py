from functools import wraps

from django.http import JsonResponse
from django.shortcuts import render, redirect


def context_view(template_name=None):
    def decorator(view_func):
        @wraps(view_func)
        def wrapper(request, *args, **kwargs):
            if template_name is None:
                func_name = f'{view_func.__module__}.{view_func.__name__}'
                raise RuntimeError(
                    f'template_name not set for {func_name}')
            context = view_func(request, *args, **kwargs)
            return render(request, template_name, context)
        return wrapper
    return decorator


def json_view(view_func):
    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        response_obj = view_func(request, *args, **kwargs)
        return JsonResponse(response_obj)
    return wrapper


def redirect_view(pattern_name=None):
    def decorator(view_func):
        @wraps(view_func)
        def wrapper(request, *args, **kwargs):
            if pattern_name is None:
                func_name = f'{view_func.__module__}.{view_func.__name__}'
                raise RuntimeError(
                    f'pattern_name not set for {func_name}')
            redirect_kw = view_func(request, *args, **kwargs)
            redirect_kw = redirect_kw or dict()
            return redirect(pattern_name, **redirect_kw)
        return wrapper
    return decorator


def form_view(**options):
    def decorator(view_func):
        @wraps(view_func)
        def wrapper(request, *args, **kwargs):
            template_name = options['template']
            success_pattern = options['redirect']
            form_kwargs = {
                'prefix': None,
                'initial': {},
            }
            if request.method == 'POST':
                form_kwargs.update({
                    'data': request.POST,
                    'files': request.FILES,
                })
            result = view_func(request, form_kwargs, *args, **kwargs)
            form = result.get('form') if isinstance(result, dict) else result
            if form is None:
                func_name = f'{view_func.__module__}.{view_func.__name__}'
                raise RuntimeError(
                    f'form is missing for {func_name}')
            if request.method == 'POST' and form.is_valid():
                redirect_args = result.get('redirect_args', list())\
                    if isinstance(result, dict) else list()
                return redirect(success_pattern, *redirect_args)
            context = dict(form=form)
            if isinstance(result, dict):
                extra_context = result.get('context', dict())
                context.update(extra_context)
            return render(request, template_name, context)
        return wrapper
    return decorator
