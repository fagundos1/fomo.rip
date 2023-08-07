from django import template
from django.utils import timezone
from django.template.defaultfilters import stringfilter
from django.utils.translation import gettext as _

from nftmarket.core.models import Offer
from nftmarket.core.utils import fix_words


register = template.Library()


@stringfilter
@register.filter
def priceformat(price_val):
    price_val = str(price_val)
    if price_val.endswith('.0'):
        price_val = price_val[:-2]
    return price_val


@stringfilter
@register.filter
def fix_long_words(text):
    return fix_words(text)


@register.filter
def timediff(date_val):
    diff = date_val - timezone.now()
    total_seconds = diff.total_seconds()
    if total_seconds < 0:
        return '0:00'
    mins = int(total_seconds // 60)
    seconds = int(total_seconds - mins * 60)
    if seconds < 10:
        seconds = f'0{seconds}'
    return f'{mins}:{seconds}'


@register.filter
def timediff_seconds(date_val):
    diff = date_val - timezone.now()
    total_seconds = diff.total_seconds()
    if total_seconds < 0:
        return '0'
    return str(int(total_seconds))


@register.filter
def is_buyer_or_seller(offer, account):
    if not account:
        return False
    if offer.seller_id == account.pk or offer.buyer_id == account.pk:
        return True
    return False


@register.filter
def has_changes_for(offer, account):
    return offer.has_changes_for(account)


@register.filter
def has_feedback_for(deal, account):
    return deal.has_feedback_for(account)


@register.filter
def naturaltimefix(text):
    if ',' in text:
        text = text.split(',')[0]
        ago_text = _('ago')
        text = f'{text} {ago_text}'
    return text


@register.filter
def notification_contragent(notification, account):
    if notification.is_wtb():
        if notification.is_wtb_offer():
            return notification.offer.seller
        else:
            return account
    offer = Offer.objects.get(pk=notification.object_id)
    if offer.seller_id == account.pk:
        if offer.buyer_id:
            return offer.buyer
    else:
        if offer.seller_id:
            return offer.seller
    return account
