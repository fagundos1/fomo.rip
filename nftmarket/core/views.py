import json

from django.contrib import messages
from django.conf import settings
from django.core.exceptions import SuspiciousOperation, PermissionDenied
from django.http import JsonResponse, Http404
from django.shortcuts import get_object_or_404, redirect
from django.template import loader
from django.views.decorators.csrf import csrf_exempt
from eth_account.messages import encode_defunct
from sorl.thumbnail import get_thumbnail
from django.utils.translation import gettext as _

from nftmarket.core.chain import (
    is_valid_address, recover_message, sign_deal, get_contract_deal)
from nftmarket.core.forms import AccountForm, OfferForm, WTBRequestForm
from nftmarket.core.generic import (
    context_view, redirect_view, form_view, json_view)
from nftmarket.core.helpers import account_required, active_account_required
from nftmarket.core.models import (
    Account, AccountAvatar, Offer, Deal, DealFeedback, Notification,
    NotifyEvent, WTBRequest, NotificationType)
from nftmarket.core.utils import clean_text
from nftmarket.core.click_api import get_pixel


@context_view('core/index.html')
def index_view(request):
    return {
        'nft_offers': Offer.objects.latest_nft(),
        'ido_offers': Offer.objects.latest_ido(),
        'worker_offers': Offer.objects.latest_worker(),
        'other_offers': Offer.objects.latest_other(),
        'nft_wtb_requests': WTBRequest.objects.latest_nft(),
        'ido_wtb_requests': WTBRequest.objects.latest_ido(),
        'worker_wtb_requests': WTBRequest.objects.latest_worker(),
        'other_wtb_requests': WTBRequest.objects.latest_other()
    }


@context_view('core/search.html')
def search_view(request):
    search_text = request.GET.get('q', '')
    search_order = request.GET.get('o', '')
    if search_order not in [
        'price', '-price', 'date', '-date', 'rating', '-rating'
    ]:
        search_order = '-date'
    order_by = search_order.replace('date', 'pk')
    order_by = order_by.replace('rating', 'seller__rating__value')
    return {
        'offer_list': Offer.objects.search(search_text, order_by),
        'wtb_request_list': WTBRequest.objects.search(search_text, order_by),
        'search_text': search_text,
        'search_order': search_order
    }


@context_view('core/profile.html')
def profile_view(request, *args, **kwargs):
    account = get_object_or_404(Account, **kwargs)
    return {
        'object': account
    }


@account_required
@context_view('core/my-wts-offers.html')
def my_wts_offers_view(request, *args, **kwargs):
    return {
        'account': request.account
    }


@account_required
@context_view('core/notifications.html')
def notifications_view(request, *args, **kwargs):
    account = request.account

    notifications_on_page = 5

    deals_notifications = account.notifications.for_deals().prefetch_related()
    deals_notifications = list(deals_notifications[:notifications_on_page+1])
    has_more_deal_notifications =\
        len(deals_notifications) > notifications_on_page
    if has_more_deal_notifications:
        deals_notifications = deals_notifications[:-1]

    wts_notifications = account.notifications.for_wts().prefetch_related()
    wts_notifications = list(wts_notifications[:notifications_on_page+1])
    has_more_wts_notifications =\
        len(wts_notifications) > notifications_on_page
    if has_more_wts_notifications:
        wts_notifications = wts_notifications[:-1]

    wtb_notifications = account.notifications.for_wtb().prefetch_related()
    wtb_notifications = list(wtb_notifications[:notifications_on_page+1])
    has_more_wtb_notifications =\
        len(wtb_notifications) > notifications_on_page
    if has_more_wtb_notifications:
        wtb_notifications = wtb_notifications[:-1]

    deals_unseen_notifications = account.deals_unseen_notifications()
    wts_unseen_notifications = account.wts_unseen_notifications()
    wtb_unseen_notifications = account.wtb_unseen_notifications()

    account.notifications.for_deals().unseen().update(is_seen=True)

    return {
        'deals_unseen_notifications': deals_unseen_notifications,
        'wts_unseen_notifications': wts_unseen_notifications,
        'wtb_unseen_notifications': wtb_unseen_notifications,
        'deals_notifications': deals_notifications,
        'has_more_deal_notifications': has_more_deal_notifications,
        'wts_notifications': wts_notifications,
        'has_more_wts_notifications': has_more_wts_notifications,
        'wtb_notifications': wtb_notifications,
        'has_more_wtb_notifications': has_more_wtb_notifications
    }


@account_required
@json_view
def notifications_page_view(request, *args, **kwargs):
    account = request.account
    page = kwargs['page']
    notification_type = kwargs['notification_type']
    if page < 2:
        raise SuspiciousOperation('invalid request')
    notifications_on_page = 5
    offset = notifications_on_page * (page - 1)
    notifications = Notification.objects.none()
    if notification_type == NotificationType.DEAL:
        notifications = account.notifications.for_deals()
    if notification_type == NotificationType.WTB:
        notifications = account.notifications.for_wtb()
    if notification_type == NotificationType.WTS:
        notifications = account.notifications.for_wts()
    notifications = list(notifications[offset:offset+notifications_on_page+1])
    has_more_notifications = len(notifications) > notifications_on_page
    if has_more_notifications:
        notifications = notifications[:-1]
    template = loader.get_template('core/notifications-list.html')
    context = {
        'auth': {
            'account': account
        },
        'notifications': notifications
    }
    html_block = template.render(context)
    return {
        'html': html_block,
        'has_more_notifications': has_more_notifications
    }


@account_required
@json_view
def notifications_update_seen_view(request, *args, **kwargs):
    account = request.account
    notification_type = kwargs['notification_type']
    account.notifications.for_type(notification_type)\
        .unseen().update(is_seen=True)
    return {
        'total_unseen_notifications': account.total_unseen_notifications()
    }


@account_required
@json_view
def account_messages_view(request):
    messages = request.account.backend_messages.all()
    result = list()
    for message in messages:
        result.append({
            'title': message.title,
            'message': message.message,
            'tag': message.tag
        })
    request.account.backend_messages.all().delete()
    return dict(messages=result)


@active_account_required
@json_view
def create_wts_or_wtb_request_view(request):
    form_data = json.loads(request.body)
    form_type = form_data.pop('form_type', '')
    errors = None
    result = dict()
    if form_type == 'wts':
        form = OfferForm(form_data)
        if form.is_valid():
            wts_offer = form.save(commit=False)
            wts_offer.seller = request.account
            wts_offer.save()
            result = dict(object_type='wts', pk=wts_offer.pk)
        else:
            errors = form.errors
    if form_type == 'wtb':
        form_data['token_type'] = form_data['offer_type']
        form = WTBRequestForm(form_data)
        if form.is_valid():
            wtb_request = form.save(commit=False)
            wtb_request.account = request.account
            wtb_request.save()
            result = dict(object_type='wtb', pk=wtb_request.pk)
        else:
            errors = form.errors
    if errors is not None:
        result['errors'] = errors
    else:
        messages.success(request, _('Offer send on moderation'))
    return result


@account_required
@form_view(template='core/offer-form.html', redirect='core:my_wts_offers')
def edit_offer_view(request, form_kwargs, *args, **kwargs):
    offer = get_object_or_404(Offer, **kwargs)
    if offer.is_deleted():
        raise Http404
    if request.account != offer.seller or offer.is_locked():
        raise PermissionDenied(_('cant edit object'))
    form_kwargs['instance'] = offer
    form = OfferForm(**form_kwargs)
    if request.method == 'POST':
        if form.is_valid():
            form.save()
            messages.success(request, _('Offer saved'))
        else:
            messages.error(request, _('Fix offer form errors'))
    return {
        'form': form,
        'context': {
            'is_edit': True
        }
    }


@account_required
@redirect_view('core:my_wts_offers')
def delete_offer_view(request, *args, **kwargs):
    offer = get_object_or_404(Offer, **kwargs)
    if request.account != offer.seller or offer.is_locked():
        raise PermissionDenied(_('cant delete object'))
    offer.set_deleted()
    messages.success(request, _('Offer deleted'))


@context_view('core/offer-detail.html')
def offer_view(request, *args, **kwargs):
    offer = get_object_or_404(Offer, **kwargs)
    if offer.is_deleted():
        raise Http404
    account_pk = None
    if request.account:
        account_pk = request.account.pk
    if offer.is_locked():
        if not account_pk:
            raise PermissionDenied(_('offer is locked'))
        if offer.seller_id != account_pk and offer.buyer_id != account_pk:
            raise PermissionDenied(_('not your offer'))
    is_seller = offer.seller_id == account_pk
    is_show_confirmation =\
        (offer.deal_stage_number == 0 and not is_seller)\
        or (offer.deal_stage_number == 1 and is_seller)
    is_watch_deal_stage = \
        (offer.deal_stage_number == 2 and is_seller)\
        or (offer.deal_stage_number == 3 and not is_seller)
    is_in_favorites = offer.is_in_favorites_of_account(request.account)
    return {
        'object': offer,
        'is_seller': is_seller,
        'is_show_confirmation': is_show_confirmation,
        'is_watch_deal_stage': is_watch_deal_stage,
        'is_in_favorites': is_in_favorites
    }


@account_required
@form_view(
    template='core/wtb-request-form.html',
    redirect='core:my_wtb_requests')
def edit_wtb_request_view(request, form_kwargs, *argks, **kwargs):
    wtb_request = get_object_or_404(WTBRequest, **kwargs)
    if request.account != wtb_request.account:
        raise PermissionDenied(_('cant edit object'))
    form_kwargs['instance'] = wtb_request
    form = WTBRequestForm(**form_kwargs)
    if request.method == 'POST':
        if form.is_valid():
            form.save()
            messages.success(request, _('WTB offer saved'))
        else:
            messages.error(request, _('Fix offer form errors'))
    return {
        'form': form
    }


@account_required
@redirect_view('core:my_wtb_requests')
def delete_wtb_request_view(request, *args, **kwargs):
    wtb_request = get_object_or_404(WTBRequest, **kwargs)
    if request.account != wtb_request.account:
        raise PermissionDenied(_('cant delete object'))
    wtb_request.set_deleted()
    messages.success(request, _('WTB offer deleted'))


@account_required
@redirect_view('core:index_page')
def make_offer_for_wtb_request_view(request, *args, **kwargs):
    offer_pk = request.POST['offer']
    offer = get_object_or_404(Offer, pk=offer_pk)
    wtb_request_pk = request.POST['wtb_request']
    wtb_request = get_object_or_404(WTBRequest, pk=wtb_request_pk)
    if offer.seller != request.account:
        raise SuspiciousOperation('invalid request')
    wtb_request.suggest_offer(offer)
    messages.success(request, _('WTB offer sent'))


@account_required
@form_view(template='core/settings.html', redirect='core:settings_page')
def settings_page_view(request, form_kwargs):
    account = request.account
    before_is_profile_filled = account.is_profile_filled()
    form_kwargs['instance'] = account
    form = AccountForm(**form_kwargs)
    if request.method == 'POST':
        if form.is_valid():
            new_account = form.save()
            is_tg_active = form.cleaned_data['is_tg_active']
            new_account.set_tg_active(is_tg_active)
            after_is_profile_filled = new_account.is_profile_filled()
            if not before_is_profile_filled and after_is_profile_filled:
                request.session['profile_event'] = True
            messages.success(request, _('Profile settings saved'))
        else:
            messages.error(request, _('Fix form errors'))
    context = dict()
    if request.method == 'GET' and request.session.get('profile_event'):
        request.session['profile_event'] = False
        params = dict(sub_id_3='reg')
        get_pixel(account.ref_name, params)
    return {
        'form': form,
        'context': context
    }


@account_required
@redirect_view('core:offer_page')
def create_close_feedback(request):
    rating = 5
    try:
        rating = float(request.POST['rating'])
        if rating <= 0 or rating > 5:
            raise ValueError
    except Exception:
        pass
    details = clean_text(request.POST.get('details', ''))
    offer_pk = 0
    try:
        offer_pk = int(request.POST['offer'])
    except Exception:
        pass
    offer = get_object_or_404(Offer, pk=offer_pk)
    deal = offer.current_deal
    account = request.account
    if offer.seller == account and not deal.has_feedback_for(offer.buyer):
        DealFeedback.objects.create(
            deal=deal,
            account=account,
            feedback_for=offer.buyer,
            rating=rating,
            details=details
        )
        Notification.add_event(
            NotifyEvent.DEAL_FEEDBACK, offer.buyer, offer=offer)
    if offer.buyer == account and not deal.has_feedback_for(offer.seller):
        DealFeedback.objects.create(
            deal=deal,
            account=account,
            feedback_for=offer.seller,
            rating=rating,
            details=details
        )
        Notification.add_event(
            NotifyEvent.DEAL_FEEDBACK, offer.seller, offer=offer)
    messages.success(request, _('Feedback created'))
    return {
        'pk': offer.pk
    }


@csrf_exempt
@account_required
@json_view
def upload_avatar_view(request):
    if 'avatar' in request.FILES:
        upload = request.FILES['avatar']
        if upload and upload.size > settings.MAX_UPLOAD_SIZE:
            return dict(error='filesize')
        account = request.account
        AccountAvatar.objects.filter(account=account).delete()
        avatar = AccountAvatar.objects.create(account=account, image=upload)
        thumbnail1 = get_thumbnail(avatar.image, '130x130', crop='center')
        thumbnail2 = get_thumbnail(avatar.image, '92x92', crop='center')
        return {
            'thumbnail1': thumbnail1.url,
            'thumbnail2': thumbnail2.url
        }
    return dict(error='unknown')


@csrf_exempt
@account_required
@json_view
def toggle_theme_view(request):
    request.account.toggle_theme()
    return dict(result='ok')


@account_required
@redirect_view('core:settings_page')
def delete_avatar_view(request):
    AccountAvatar.objects.filter(account=request.account).delete()
    messages.success(request, _('Photo deleted'))


@account_required
@redirect_view('core:index_page')
def logout_view(request):
    request.session.flush()


@active_account_required
def confirm_offer_view(request):
    if request.method != 'POST':
        raise SuspiciousOperation(_('invalid method'))
    if not hasattr(request, 'account') or request.account is None:
        return redirect('core:index_view')
    offer_pk = None
    try:
        offer_pk = int(request.POST['offer'])
        if not offer_pk:
            raise ValueError
    except Exception:
        pass
    if not offer_pk:
        raise SuspiciousOperation(_('invalid offer'))
    offer = Offer.objects.get(pk=offer_pk)
    if not offer.seller.is_active:
        messages.error(request, _('Your account was blocked'))
        return redirect('core:index_view')
    is_seller = request.account.pk == offer.seller_id
    deal_stage_number = offer.deal_stage_number
    is_valid_stage = (deal_stage_number == 0 and not is_seller)\
        or (deal_stage_number == 1 and is_seller)
    if not is_valid_stage:
        raise SuspiciousOperation(_('invalid offer stage'))
    if deal_stage_number == 0 and not is_seller:
        if Offer.buyer_confirm(offer_pk, request.account.pk):
            params = dict(sub_id_4='start_deal')
            get_pixel(request.account.ref_name, params)
            messages.success(request, _('Deal started'))
            return redirect('core:offer_page', pk=offer_pk)
    if deal_stage_number == 1 and is_seller:
        Offer.seller_confirm(offer_pk, request.account.pk)
        messages.success(request, _('Deal confirmed'))
        return redirect('core:offer_page', pk=offer_pk)
    return redirect('core:index_view')


@account_required
@context_view('core/my-deals.html')
def my_deals_view(request):
    account = request.account
    deals_on_page = 5
    # active deals
    deals = Offer.objects.in_deal().for_account(account)
    deals = list(deals[:deals_on_page+1])
    has_more_deals = len(deals) > deals_on_page
    if has_more_deals:
        deals = deals[:-1]
    Offer.objects.update_last_seen_for(account, deals)
    # closed deals
    closed_deals = Offer.objects.closed().for_account(account)
    closed_deals = list(closed_deals[:deals_on_page+1])
    has_more_closed_deals = len(closed_deals) > deals_on_page
    if has_more_closed_deals:
        closed_deals = closed_deals[:-1]
    Offer.objects.update_last_seen_for(account, closed_deals)
    return {
        'num_deals': Offer.objects.in_deal().for_account(account).count(),
        'deals': deals,
        'has_more_deals': has_more_deals,
        'num_closed_deals':
            Offer.objects.closed().for_account(account).count(),
        'closed_deals': closed_deals,
        'has_more_closed_deals': has_more_closed_deals
    }


@account_required
@json_view
def my_deals_page_view(request, *args, **kwargs):
    account = request.account
    page = kwargs['page']
    if page < 2:
        raise SuspiciousOperation('invalid request')
    deals_on_page = 5
    offset = deals_on_page * (page - 1)
    deals = Offer.objects.in_deal().for_account(account)
    deals = list(deals[offset:offset+deals_on_page+1])
    has_more_deals = len(deals) > deals_on_page
    if has_more_deals:
        deals = deals[:-1]
    Offer.objects.update_last_seen_for(account, deals)
    template = loader.get_template('core/my-deals-page.html')
    context = {
        'auth': {
            'account': account
        },
        'deals': deals
    }
    html_block = template.render(context)
    return {
        'html': html_block,
        'has_more_deals': has_more_deals
    }


@account_required
@json_view
def my_closed_deals_page_view(request, *args, **kwargs):
    account = request.account
    page = kwargs['page']
    if page < 2:
        raise SuspiciousOperation('invalid request')
    deals_on_page = 5
    offset = deals_on_page * (page - 1)
    closed_deals = Offer.objects.closed().for_account(account)
    closed_deals = list(closed_deals[offset:offset+deals_on_page+1])
    has_more_closed_deals = len(closed_deals) > deals_on_page
    if has_more_closed_deals:
        closed_deals = closed_deals[:-1]
    Offer.objects.update_last_seen_for(account, closed_deals)
    template = loader.get_template('core/my-closed-deals-page.html')
    context = {
        'auth': {
            'account': account
        },
        'closed_deals': closed_deals
    }
    html_block = template.render(context)
    return {
        'html': html_block,
        'has_more_closed_deals': has_more_closed_deals
    }


@account_required
@context_view('core/favorites.html')
def favorites_view(request):
    favorites = request.account.favorites.all()
    return {
        'favorites': favorites
    }


@account_required
@context_view('core/my-wtb-requests.html')
def my_wtb_requests_view(request):
    return {
        'account': request.account
    }


@context_view('core/latest-deals.html')
def latest_deals_view(request):
    summary = Deal.total_summary()
    deals_on_page = 5
    latest_deals = Deal.objects.latest_closed()
    latest_deals = list(latest_deals[:deals_on_page+1])
    has_more_deals = len(latest_deals) > deals_on_page
    if has_more_deals:
        latest_deals = latest_deals[:-1]
    return {
        'summary': summary,
        'latest_deals': list(latest_deals),
        'has_more_deals': has_more_deals
    }


@json_view
def latest_deals_page_view(request, *args, **kwargs):
    page = kwargs['page']
    if page < 2:
        raise SuspiciousOperation('invalid request')
    deals_on_page = 5
    offset = deals_on_page * (page - 1)
    latest_deals = Deal.objects.latest_closed()
    latest_deals = list(latest_deals[offset:offset+deals_on_page+1])
    has_more_deals = len(latest_deals) > deals_on_page
    if has_more_deals:
        latest_deals = latest_deals[:-1]
    template = loader.get_template('include/latest-deals.html')
    context = {
        'latest_deals': latest_deals
    }
    html_block = template.render(context)
    return {
        'html': html_block,
        'has_more_deals': has_more_deals
    }


@active_account_required
@form_view(
    template='core/request-form.html',
    redirect='core:my_wtb_requests'
)
def create_price_request_view(request, form_kwargs):
    form = WTBRequestForm(**form_kwargs)
    if request.method == 'POST':
        if form.is_valid():
            price_request = form.save(commit=False)
            price_request.account = request.account
            price_request.save()
            messages.success(request, _('Request created'))
        else:
            messages.error(request, _('Fix request form errors'))
    return {
        'form': form
    }


@account_required
@json_view
def toggle_favorite(request, *args, **kwargs):
    offer = get_object_or_404(Offer, **kwargs)
    in_favorites = offer.toggle_favorite(request.account)
    return {
        'in_favorites': in_favorites
    }


@account_required
@redirect_view('core:favorites_page')
def remove_favorite(request, *args, **kwargs):
    offer = get_object_or_404(Offer, **kwargs)
    offer.remove_favorite(request.account)


def ajax_action_with_deal(func):
    def wrapper(request):
        if request.method != 'POST':
            raise SuspiciousOperation('invalid method')
        if not hasattr(request, 'account') or request.account is None:
            raise SuspiciousOperation('account required')
        deal_pk = None
        try:
            deal_pk = int(request.POST['deal'])
        except Exception:
            pass
        if not deal_pk:
            raise SuspiciousOperation('invalid deal')
        deal = Deal.objects.get(pk=deal_pk)
        result = func(request.account, deal, request)
        if result is None:
            result = dict(result='OK')
        return JsonResponse(result)
    return wrapper


@ajax_action_with_deal
def approved_token(account, deal, request):
    offer = deal.offer
    if offer.buyer.pk == account.pk:
        deal.is_buyer_approved = True
    else:
        deal.is_seller_approved = True
    deal.save()


@ajax_action_with_deal
def sign_deal_view(account, deal, request):
    offer = deal.offer
    if offer.buyer.pk != account.pk:
        raise SuspiciousOperation('invalid deal')
    deal_obj = sign_deal(deal)
    response_obj = {'deal': deal_obj}
    return response_obj


@ajax_action_with_deal
def buyer_deposited(account, deal, request):
    offer = deal.offer
    if offer.buyer.pk != account.pk:
        raise SuspiciousOperation('invalid deal')
    if not deal.is_waiting_buyer_payment():
        return {'action': 'reload', 'supress_message': 'on'}
    deal_class = get_contract_deal(deal)
    response_obj = {'action': 'wait'}
    if (
        deal_class.exists
        and deal_class.buyer_deposited == deal_class.price
    ):
        deal.buyer_deposit_confirmed()
        response_obj = {'action': 'reload'}
    else:
        deal.buyer_deposited()
    return response_obj


@ajax_action_with_deal
def seller_payed_collateral(account, deal, request):
    offer = deal.offer
    if offer.seller.pk != account.pk:
        raise SuspiciousOperation('invalid deal')
    if not deal.is_waiting_seller_collateral():
        return {'action': 'reload', 'supress_message': 'on'}
    deal_class = get_contract_deal(deal)
    response_obj = {'action': 'wait'}
    if (
        deal_class.exists
        and deal_class.seller_deposited == deal_class.collateral
    ):
        deal.seller_collateral_confirmed()
        response_obj = {'action': 'reload'}
    else:
        deal.seller_payed_collateral()
    return response_obj


@ajax_action_with_deal
def buyer_complete(account, deal, request):
    offer = deal.offer
    if offer.buyer.pk != account.pk:
        raise SuspiciousOperation('invalid deal')
    if not deal.is_waiting_for_completion():
        raise SuspiciousOperation('invalid deal status')
    rating = 5
    try:
        rating = float(request.POST['rating'])
        if rating <= 0 or rating > 5:
            raise ValueError
    except Exception:
        pass
    details = clean_text(request.POST.get('details', ''))
    deal.buyer_complete()
    DealFeedback.objects.create(
        deal=deal,
        account=offer.buyer,
        feedback_for=offer.seller,
        rating=rating,
        details=details
    )
    params = {
        'sub_id_5': 'success_deal',
        'payout': offer.price
    }
    get_pixel(account.ref_name, params)


@ajax_action_with_deal
def confirm_finish(account, deal, request):
    offer = deal.offer
    if offer.seller.pk != request.account.pk:
        raise SuspiciousOperation('invalid deal')
    if not deal.is_waiting_seller_claim():
        raise SuspiciousOperation('invalid deal status')
    deal.confirm_finish()


@ajax_action_with_deal
def buyer_claim_after_cancelation(account, deal, request):
    offer = deal.offer
    if offer.buyer_id != account.pk:
        raise SuspiciousOperation('invalid deal')
    if not deal.is_waiting_buyer_claim():
        raise SuspiciousOperation('invalid deal status')
    deal.cancel_and_reopen_offer()


@ajax_action_with_deal
def buyer_claim_after_arbitrage(account, deal, request):
    offer = deal.offer
    if offer.buyer_id != account.pk:
        raise SuspiciousOperation('invalid deal')
    if (
        not deal.is_waiting_sides_claim()
        and not deal.has_unclaimed_arbitration()
    ):
        raise SuspiciousOperation('invalid deal status')
    deal.buyer_claim_after_arbitrage()


@ajax_action_with_deal
def seller_claim_after_arbitrage(account, deal, request):
    offer = deal.offer
    if offer.seller_id != account.pk:
        raise SuspiciousOperation('invalid deal')
    if (
        not deal.is_waiting_sides_claim()
        and not deal.has_unclaimed_arbitration()
    ):
        raise SuspiciousOperation('invalid deal status')
    deal.seller_claim_after_arbitrage()


@ajax_action_with_deal
def retry_approve(account, deal, request):
    offer = deal.offer
    if offer.seller_id != account.pk and offer.buyer_id != account.pk:
        raise SuspiciousOperation('invalid deal')
    deal.retry_approve(account)


@ajax_action_with_deal
def call_arbitration(account, deal, request):
    offer = deal.offer
    if offer.buyer_id != account.pk and offer.seller_id != account.pk:
        raise SuspiciousOperation('invalid deal')
    deal.call_arbitration(
        offer.seller_id == account.pk,
        clean_text(request.POST.get('reasons', '')),
        clean_text(request.POST.get('details', ''))
    )


@account_required
def deal_offer_stage_view(request, *args, **kwargs):
    offer = get_object_or_404(Offer, **kwargs)
    account_pk = request.account.pk
    if offer.seller_id != account_pk and offer.buyer_id != account_pk:
        raise PermissionDenied('not your offer')
    return JsonResponse({
        'stage': offer.deal_stage_number
    })


def _nonce_text(nonce):
    return f'Your nonce is: {nonce}'


def auth_nonce_view(request):
    eth_address = request.GET.get('account', '')
    if not is_valid_address(eth_address):
        raise SuspiciousOperation('invalid ethereum address')

    ref_name = request.COOKIES.get('refname')
    account = Account.objects.get_wallet(eth_address, ref_name)
    response_obj = {
        'nonce': _nonce_text(account.nonce.value)
    }
    return JsonResponse(response_obj)


def auth_validate_view(request):
    eth_address = request.POST.get('account', '')
    if not is_valid_address(eth_address):
        raise SuspiciousOperation('invalid ethereum address')

    account = None
    try:
        account = Account.objects.get(wallet=eth_address)
    except Account.DoesNotExist:
        pass

    if account is None:
        raise SuspiciousOperation('invalid account')

    if account.nonce.is_expired():
        raise SuspiciousOperation('expired nonce')

    network = request.POST.get('network', '')
    if network not in settings.NETWORKS.keys():
        raise SuspiciousOperation(f'invalid network: {network}')

    signature = request.POST.get('signature', '')
    message = encode_defunct(text=_nonce_text(account.nonce.value))
    test_wallet = recover_message(network, message, signature)
    if test_wallet != account.wallet:
        raise PermissionDenied('invalid signature')

    request.session['_account_pk'] = account.pk
    return JsonResponse(dict(result='OK'))


@redirect_view('core:index_page')
def debug(request):
    request.session['_account_pk'] = 32
