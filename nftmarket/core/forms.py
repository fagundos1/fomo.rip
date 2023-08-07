from django import forms
from django.core.validators import MinLengthValidator, MaxLengthValidator
from django.utils.translation import gettext as _

from nftmarket.core.models import Account, Offer, TokenType, WTBRequest
from nftmarket.core.utils import clean_text


class AccountForm(forms.ModelForm):
    class Meta:
        model = Account
        fields = [
            'name',
            'telegram',
            'twitter',
        ]

    name = forms.CharField(
        label=_('Username'), required=True,
        validators=[MinLengthValidator(3), MaxLengthValidator(64)])
    avatar = forms.ImageField(required=False)
    is_tg_active = forms.BooleanField(required=False)

    def __init__(self, *args, **kwargs):
        account = kwargs['instance']
        kwargs['initial']['is_tg_active'] = True
        try:
            kwargs['initial']['is_tg_active'] =\
                account.telegram_link.is_active
        except Exception:
            pass
        return super().__init__(*args, **kwargs)


class OfferForm(forms.ModelForm):
    offer_type = forms.ChoiceField(choices=TokenType.choices, required=True)

    class Meta:
        model = Offer
        fields = [
            'network',
            'offer_type',
            'name',
            'price',
            'collateral',
            'details'
        ]

    def clean_details(self):
        details = self.cleaned_data['details']
        return clean_text(details)


class WTBRequestForm(forms.ModelForm):
    class Meta:
        model = WTBRequest
        fields = [
            'network',
            'token_type',
            'name',
            'price',
        ]
