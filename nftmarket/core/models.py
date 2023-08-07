import json
import re
import secrets
from datetime import timedelta
from functools import cached_property

from django.conf import settings
from django.core.validators import (
    MinValueValidator, MaxValueValidator, MinLengthValidator, RegexValidator)
from django.db import models, transaction
from django.utils import timezone
from django.utils.translation import gettext as _
from nftmarket.core.notify_messages import NOTIFICATION_MESSAGES


INDEX_PAGE_OBJECTS_LIMIT = 20
NAME_LIMIT = 16


class AccountManager(models.Manager):
    def get_wallet(self, wallet, ref_name=None):
        secret_nonce = secrets.token_hex(32)
        created = False
        with transaction.atomic():
            account, created = self.get_or_create(wallet=wallet)
            if created:
                AccountRating.objects.create(account=account)
                AccountNonce.objects.create(
                    account=account,
                    value=secret_nonce
                )
                AccountTelegramLink.objects.create(
                    account=account,
                    is_active=True
                )
                if ref_name:
                    account.ref_name = ref_name
                    account.save()
            else:
                try:
                    account.nonce.value = secret_nonce
                    account.nonce.save()
                except AccountNonce.DoesNotExist:
                    AccountNonce.objects.create(
                        account=account,
                        value=secret_nonce
                    )
        return account


class Account(models.Model):
    wallet = models.CharField(
        _('Wallet'), max_length=42, unique=True, blank=True, null=True)
    name = models.CharField(
        _('Username'), max_length=64, unique=True, blank=True, null=True,
        validators=[
            MinLengthValidator(3),
            RegexValidator(
                '^[a-z0-9_]+$',
                message='May consist only of a-z, 0–9, and _',
                flags=re.IGNORECASE)
        ])
    telegram = models.CharField(
        _('Telegram'), max_length=32, unique=True, null=True,
        validators=[
            MinLengthValidator(5),
            RegexValidator(
                '^[a-z0-9_]+$',
                message='May consist only of a-z, 0–9, and _',
                flags=re.IGNORECASE)
        ])
    twitter = models.CharField(
        _('Twitter'), max_length=15, unique=True, null=True,
        validators=[
            MinLengthValidator(4),
            RegexValidator(
                '^[a-z0-9_]+$',
                message='May consist only of a-z, 0–9, and _',
                flags=re.IGNORECASE)
        ])
    use_dark_theme = models.BooleanField(
        _('Dark theme'), blank=True, default=False)
    ref_name = models.CharField(
        _('Reference Url Param Name'), max_length=32, blank=True,
        default='undefined')
    is_active = models.BooleanField('Active account', blank=True, default=True)
    created_at = models.DateTimeField(
        _('Registered on'), blank=True, null=False)

    objects = AccountManager()

    class Meta:
        db_table = 'core_account'

    def save(self, *args, **kwargs):
        if not self.created_at:
            self.created_at = timezone.now()
        super().save(*args, **kwargs)

    @cached_property
    def avatar(self):
        return self.avatars.active().first()

    def short_wallet(self):
        return f'{self.wallet[:5]}...{self.wallet[-4:]}'

    def is_long_name(self):
        name = self.full_name()
        return len(name) > NAME_LIMIT

    def full_name(self):
        return self.name or self.short_wallet()

    def is_profile_filled(self):
        return (
            bool(self.name) and self.name.strip()
            and bool(self.telegram) and self.telegram.strip()
            and bool(self.twitter) and self.twitter.strip())

    def new_count_in_my_deals(self):
        count_for_seller = Offer.objects.changed_for_seller(self)
        count_for_buyer = Offer.objects.changed_for_buyer(self)
        return count_for_seller + count_for_buyer

    def has_open_deals(self):
        return Offer.objects.in_deal().for_account(self).exists()

    def num_success_deals(self):
        num_closed_deals = self.sale_offers.closed().count()
        return num_closed_deals - self.num_cancelled_deals

    @cached_property
    def num_cancelled_deals(self):
        closed_sale_offers = self.sale_offers.closed()
        closed_sale_offers_deals =\
            Deal.objects.filter(offer__in=closed_sale_offers)
        return DealArbitration.objects.filter(
            deal__in=closed_sale_offers_deals).count()

    def toggle_theme(self):
        self.use_dark_theme = not self.use_dark_theme
        self.save()

    def set_tg_active(self, is_tg_active):
        tg_link, is_created =\
            AccountTelegramLink.objects.get_or_create(account=self)
        tg_link.is_active = is_tg_active
        tg_link.save()

    def telegram_link_is_active(self):
        try:
            return self.telegram_link.is_active
        except Exception:
            pass
        return True

    def deals_unseen_notifications(self):
        return self.notifications.for_deals().unseen().count()

    def wts_unseen_notifications(self):
        return self.notifications.for_wts().unseen().count()

    def wtb_unseen_notifications(self):
        return self.notifications.for_wtb().unseen().count()

    def total_unseen_notifications(self):
        total_count = 0
        total_count += self.deals_unseen_notifications()
        total_count += self.wts_unseen_notifications()
        total_count += self.wtb_unseen_notifications()

        return total_count

    def __str__(self):
        name = self.full_name()
        return name


class AccountAvatarQuerySet(models.QuerySet):
    def active(self):
        return self.filter(is_deleted=False)


class AccountAvatarManager(models.Manager):
    def get_queryset(self):
        return AccountAvatarQuerySet(self.model, using=self._db)

    def active(self):
        return self.get_queryset().active()


class AccountAvatar(models.Model):
    account = models.ForeignKey(
        Account, verbose_name=_('Account'), related_name='avatars',
        on_delete=models.CASCADE)
    image = models.ImageField(_('Image'), upload_to='images/', max_length=256)
    is_deleted = models.BooleanField(
        _('Deleted image'), blank=True, default=False)

    objects = AccountAvatarManager()

    class Meta:
        db_table = 'core_account_avatar'
        verbose_name = _('Account')
        verbose_name_plural = _('Accounts')


class AccountNonce(models.Model):
    account = models.OneToOneField(
        Account, verbose_name=_('Account'), primary_key=True,
        related_name='nonce', on_delete=models.CASCADE)
    value = models.TextField(_('Nonce value'))
    created_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'core_account_nonce'
        verbose_name = _('Account Nonce')
        verbose_name_plural = _('Accounts Nonces')

    def is_expired(self):
        return self.created_at + timedelta(minutes=5) < timezone.now()

    def __str__(self):
        return self.value


class AccountRating(models.Model):
    account = models.OneToOneField(
        Account, verbose_name=_('Account'), primary_key=True,
        related_name='rating', on_delete=models.CASCADE)
    value = models.FloatField(
        _('Rating'), blank=True, default=0,
        validators=[MinValueValidator(0.0), MaxValueValidator(5.0)])

    class Meta:
        db_table = 'core_account_rating'
        verbose_name = _('Account Rating')
        verbose_name_plural = _('Accounts Ratings')

    def __str__(self):
        return str(self.value)


class AccountTelegramLink(models.Model):
    account = models.OneToOneField(
        Account, verbose_name=_('Account'), primary_key=True,
        related_name='telegram_link', on_delete=models.CASCADE)
    telegram_id = models.BigIntegerField(
        _('Telegram ID'), blank=True, null=True)
    is_active = models.BooleanField(blank=True, default=True)

    class Meta:
        db_table = 'core_account_tg_link'

    def __str__(self):
        return str(self.telegram_id)


class BlockchainNetwork(models.TextChoices):
    BNB = 'bnb', 'BNB Smart Chain'
    ARBITRUM = 'arbitrum', 'Arbitrum One'
    OPTIMISM = 'optimism', 'Optimism'


class TokenType(models.TextChoices):
    NFT = 'nft', 'NFT'
    IDO = 'ido', 'Tokens'
    WORKER = 'worker', 'Workers'
    OTHER = 'other', 'Other'


class OfferStatus(models.TextChoices):
    MODERATION = 'moderation', 'On moderation'
    ACTIVE = 'active', 'Active'
    DEAL = 'deal', 'In process'
    CLOSED = 'closed', 'Closed'
    DELETED = 'deleted', 'Deleted'
    REJECTED = 'rejected', 'Rejected'


class OfferQuerySet(models.QuerySet):
    def not_deleted(self):
        return self.exclude(status=OfferStatus.DELETED)

    def changed_for_seller(self, account):
        return self.exclude(status_changed_at=None)\
            .filter(seller=account)\
            .filter(status_changed_at__gt=models.F('last_seen_seller'))\
            .count()

    def changed_for_buyer(self, account):
        return self.exclude(status_changed_at=None)\
            .filter(buyer=account)\
            .filter(status_changed_at__gt=models.F('last_seen_buyer'))\
            .count()

    def update_last_seen_for(self, account, offers):
        pk_list = [offer.pk for offer in offers]
        self.filter(seller=account)\
            .filter(pk__in=pk_list)\
            .update(last_seen_seller=timezone.now())
        self.filter(buyer=account)\
            .filter(pk__in=pk_list)\
            .update(last_seen_buyer=timezone.now())

    def active(self):
        return self.filter(status=OfferStatus.ACTIVE)\
            .filter(seller__is_active=True)

    def active_or_moderation(self):
        return self.filter(status__in=[
            OfferStatus.MODERATION,
            OfferStatus.ACTIVE
        ])

    def rejected(self):
        return self.filter(status=OfferStatus.REJECTED)

    def in_deal(self):
        return self.filter(status=OfferStatus.DEAL)

    def closed(self):
        return self.filter(status=OfferStatus.CLOSED)

    def latest_for_type(self, offer_type):
        return self.filter(offer_type=offer_type)

    def search(self, search_text, order_by):
        offers_ids = OfferSearchTerm.objects.search(search_text)
        return self.filter(id__in=offers_ids).order_by(order_by)

    def for_account(self, account):
        return self.filter(
            models.Q(seller_id=account.pk) | models.Q(buyer_id=account.pk))

    def latest_closed(self):
        latest_for = timezone.now() - timedelta(days=6 * 30)
        return self.filter(status_changed_at__gte=latest_for).closed()\
            .order_by('-status_changed_at')


class OfferManager(models.Manager):
    def get_queryset(self):
        return OfferQuerySet(self.model, using=self._db)

    def active(self):
        return self.get_queryset().active()

    def active_or_moderation(self):
        return self.get_queryset().active_or_moderation()

    def in_deal(self):
        return self.get_queryset().in_deal()

    def closed(self):
        return self.get_queryset().closed()

    def rejected(self):
        return self.get_queryset().rejected()

    def latest_nft(self):
        return self.get_queryset()\
            .active()\
            .latest_for_type(TokenType.NFT)[:INDEX_PAGE_OBJECTS_LIMIT]

    def latest_ido(self):
        return self.get_queryset()\
            .active()\
            .latest_for_type(TokenType.IDO)[:INDEX_PAGE_OBJECTS_LIMIT]

    def latest_other(self):
        return self.get_queryset()\
            .active()\
            .latest_for_type(TokenType.OTHER)[:INDEX_PAGE_OBJECTS_LIMIT]

    def latest_worker(self):
        return self.get_queryset()\
            .active()\
            .latest_for_type(TokenType.WORKER)[:INDEX_PAGE_OBJECTS_LIMIT]

    def search(self, search_text, order_by):
        return self.get_queryset().active().search(search_text, order_by)

    def for_account(self, account):
        return self.get_queryset().for_account(account)

    def changed_for_seller(self, account):
        return self.get_queryset().changed_for_seller(account)

    def changed_for_buyer(self, account):
        return self.get_queryset().changed_for_buyer(account)

    def update_last_seen_for(self, account, offers):
        return self.get_queryset().update_last_seen_for(account, offers)

    def activate_from_moderation(self):
        hour_ago = timezone.now() - timezone.timedelta(hours=1)
        offers_to_activate = self.get_queryset()\
            .filter(status=OfferStatus.MODERATION, created_at__lt=hour_ago)
        id_list = list(offers_to_activate.values_list('id', flat=True))
        offers_to_activate.update(status=OfferStatus.ACTIVE)
        for offer_id in id_list:
            offer = Offer.objects.get(pk=offer_id)
            Notification.add_event(
                NotifyEvent.WTS_OFFER_ACTIVE, offer.seller, offer=offer)

    def latest_closed(self):
        return self.get_queryset().latest_closed()


class Offer(models.Model):
    class Meta:
        db_table = 'core_offer'
        verbose_name = _('Offer')
        verbose_name_plural = _('Offers')
        ordering = ['-pk']

    objects = OfferManager()

    network = models.TextField(
        _('Network'), choices=BlockchainNetwork.choices,
        default=BlockchainNetwork.BNB)
    offer_type = models.TextField(_('Token type'), choices=TokenType.choices)
    seller = models.ForeignKey(
        Account, verbose_name=_('Account'), related_name='sale_offers',
        on_delete=models.CASCADE)
    buyer = models.ForeignKey(
        Account, verbose_name=_('Buyer'), related_name='buy_offers',
        blank=True, null=True, on_delete=models.SET_NULL)
    status = models.TextField(
        _('Offer status'), choices=OfferStatus.choices,
        default=OfferStatus.ACTIVE)
    name = models.CharField(
        _('Name'), max_length=128, validators=[
            MinLengthValidator(3),
            RegexValidator(
                '^[a-z0-9 #_-]+$',
                message='May consist only of a-z, 0–9, and _-',
                flags=re.IGNORECASE)
        ])
    price = models.FloatField(
        _('Price'), validators=[MinValueValidator(settings.MIN_PRICE)])
    collateral = models.FloatField(
        _('Collateral'), validators=[MinValueValidator(settings.MIN_PRICE)])
    details = models.TextField(
        _('Offer details'), validators=[
            RegexValidator(
                '^[a-z0-9 -.,]+$',
                message='May consist only of a-z, 0–9, and -.,',
                flags=re.IGNORECASE)
        ], blank=True, default='')
    status_changed_at = models.DateTimeField(
        _('Offer status changed'), blank=True, null=True)
    last_seen_buyer = models.DateTimeField(
        auto_now_add=True, blank=True, null=True)
    last_seen_seller = models.DateTimeField(
        auto_now_add=True, blank=True, null=True)
    created_at = models.DateTimeField(
        _('Created at'), auto_now_add=True, blank=True, null=True)

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)
        search_term = self.get_search_term()
        search_term_model, _ =\
            OfferSearchTerm.objects.get_or_create(offer_id=self.pk)
        search_term_model.term = search_term
        search_term_model.save()

    def calc_fee(self, percent):
        return (self.price / 100.0) * float(percent)

    def reopen(self):
        self.status = OfferStatus.ACTIVE
        self.buyer = None
        self.save()

    def reject(self):
        self.status = OfferStatus.REJECTED
        self.save()

    def set_update(self):
        self.status_changed_at = timezone.now()
        self.save()

    def get_search_term(self):
        return ''.join(map(clean_search_term, (
            self.name,
            self.details)))

    def is_long_name(self):
        return len(self.name) > NAME_LIMIT

    def is_in_favorites_of_account(self, account):
        return self.favorites.filter(account=account).exists()

    def toggle_favorite(self, account):
        account_fovorite = self.favorites.filter(account=account)
        if account_fovorite.exists():
            account_fovorite.delete()
        else:
            AccountFavorites.objects.create(account=account, offer=self)
            return True
        return False

    def remove_favorite(self, account):
        self.favorites.filter(account=account).delete()

    def has_changes_for(self, account):
        if self.status_changed_at is None:
            return False
        if (
                self.seller == account
                and self.status_changed_at > self.last_seen_seller):
            return True
        if (
                self.buyer == account
                and self.status_changed_at > self.last_seen_buyer):
            return True
        return False

    def __str__(self):
        name = self.name
        return name

    def is_active(self):
        return self.status == OfferStatus.ACTIVE

    def is_locked(self):
        return self.status not in [OfferStatus.MODERATION, OfferStatus.ACTIVE]

    def set_deleted(self):
        self.status = OfferStatus.DELETED
        self.save()

    def close(self):
        self.status = OfferStatus.CLOSED
        self.set_update()

    def is_closed(self):
        return self.status == OfferStatus.CLOSED

    def is_deleted(self):
        return self.status == OfferStatus.DELETED

    @staticmethod
    def buyer_confirm(offer_pk, buyer_pk):
        is_confirmed = False
        with transaction.atomic():
            count = Offer.objects.filter(
                pk=offer_pk, buyer_id=None, status=OfferStatus.ACTIVE)\
                .update(buyer_id=buyer_pk)
            offer = Offer.objects.get(pk=offer_pk)
            if count > 0 and offer.buyer.pk == buyer_pk:
                Deal.objects.filter(offer_id=offer_pk)\
                    .update(status=DealStatus.DELETED)
                Deal.objects.create(
                    offer=offer,
                    status=DealStatus.WAITING_SELLER_CONFIRM,
                    fee=offer.calc_fee(settings.FEE_PERCENT)
                )
                offer.status = OfferStatus.DEAL
                offer.status_changed_at = timezone.now()
                offer.save()
                Notification.add_event(
                    NotifyEvent.BUYER_CONFIRM, offer.seller, offer=offer)
                is_confirmed = True
        return is_confirmed

    @staticmethod
    def seller_confirm(offer_pk, seller_pk):
        offer = Offer.objects.get(pk=offer_pk)
        if offer.seller.pk == seller_pk:
            offer.current_deal.seller_confirm()

    @cached_property
    def current_deal(self):
        deals = self.deals.all().not_deleted()
        if not len(deals):
            return None
        if len(deals) > 1:
            raise RuntimeError(f'too many deals for offer {self.pk}')
        return deals[0]

    @cached_property
    def deal_stage_number(self):
        deal = self.current_deal
        if not deal:
            return 0
        return deal.stage_number()

    def is_canceled(self):
        deal = self.current_deal
        if not deal:
            return False
        try:
            cancelation = deal.cancelation
        except DealCancelation.DoesNotExist:
            return False
        return bool(cancelation.pk)

    @staticmethod
    def total_summary():
        closed_count = Offer.objects.closed().count()
        closed_summ =\
            Offer.objects.closed().aggregate(
                summ=models.Sum('price'))\
            .get('summ')
        return {
            'closed_count': closed_count,
            'closed_summ': closed_summ
        }

    def render_token_name(self):
        return settings.NETWORKS.get(
            self.network, dict()).get('token_name', '').upper()

    def get_escrow_addr(self):
        return settings.NETWORKS[self.network]['escrow_addr']

    def get_token_addr(self):
        return settings.NETWORKS[self.network]['token_addr']

    def get_token_decimals(self):
        return settings.NETWORKS[self.network]['token_decimals']

    def get_chain_id(self):
        return settings.NETWORKS[self.network]['chain_id']


def clean_search_term(str_val):
    return re.sub('[^A-Z0-9]+', '', str_val.upper())


class OfferSearchTermManager(models.Manager):
    def search(self, search_text):
        search_term = clean_search_term(search_text)
        return self.get_queryset()\
            .filter(term__contains=search_term)\
            .values_list('offer_id', flat=True)


class OfferSearchTerm(models.Model):
    offer = models.OneToOneField(
        Offer, related_name='search_term', on_delete=models.CASCADE)
    term = models.TextField()

    objects = OfferSearchTermManager()

    class Meta:
        db_table = 'core_offer_search_term'


class DealStatus(models.TextChoices):
    OPEN = 'open', 'Open'
    WAITING_SELLER_CONFIRM = 'waiting_seller_confirm', 'Waiting Seller Confirm'
    WAITING_BUYER_PAYMENT = 'waiting_buyer_payment', 'Waiting Buyer Payment'
    WAITING_BUYER_PAYMENT_CONFIRM =\
        'waiting_buyer_payment_confirm', 'Waiting Buyer Payment'
    WAITING_SELLER_COLLATERAL =\
        'waiting_seller_collateral', 'Waiting Seller Collateral'
    WAITING_SELLER_COLLATERAL_CONFIRM =\
        'waiting_seller_collateral_confirm', 'Waiting Seller Collateral'
    WAITING_FOR_COMPLETION = 'waiting_for_completion', 'Waiting For Completion'
    COMPLETION_DELAY = 'completion_delay', 'Completion Delay'
    WAITING_BUYER_CLAIM = 'waiting_buyer_claim', 'Waiting Buyer Claim'
    WAITING_SELLER_CLAIM = 'waiting_seller_claim', 'Waiting Seller Claim'
    CONFIRMED_FINISH = 'confirmed_finish', 'Confirmed Finish'
    WAITING_MODERATOR = 'waiting_moderator', 'Waiting Moderator'
    WAITING_SIDES_CLAIM = 'waiting_sides_claim', 'Waiting Sides Claims'
    CLOSED = 'closed', 'Closed'
    DELETED = 'deleted', 'Deleted'


class DealQuerySet(models.QuerySet):
    def not_deleted(self):
        return self.exclude(status=DealStatus.DELETED)

    def started(self):
        return self.filter(
            status__in=(
                DealStatus.OPEN,
                DealStatus.WAITING_SELLER_CONFIRM,
            )
        )

    def expired(self):
        return self.filter(expires__lt=timezone.now())

    def closed(self):
        return self.filter(status=DealStatus.CLOSED)

    def not_closed(self):
        return self.exclude(status=DealStatus.CLOSED)

    def waiting_for_buyer_deposit_confirm(self):
        return self.filter(status__in=[
            DealStatus.WAITING_BUYER_PAYMENT,
            DealStatus.WAITING_BUYER_PAYMENT_CONFIRM,
        ])

    def waiting_for_seller_collateral_confirm(self):
        return self.filter(status__in=[
            DealStatus.WAITING_SELLER_COLLATERAL,
            DealStatus.WAITING_SELLER_COLLATERAL_CONFIRM
        ])

    def waiting_for_completion(self):
        return self.filter(status=DealStatus.WAITING_FOR_COMPLETION)

    def waiting_for_sides_claim(self):
        return self.filter(status=DealStatus.WAITING_SIDES_CLAIM)

    def finished(self):
        return self.filter(status=DealStatus.CONFIRMED_FINISH)

    def check_is_finished(self):
        return self.filter(status__in=[
            DealStatus.WAITING_SIDES_CLAIM,
            DealStatus.CONFIRMED_FINISH
        ])

    def latest_closed(self):
        latest_for = timezone.now() - timedelta(days=6 * 30)
        return self.filter(
                offer__status_changed_at__gte=latest_for,
                arbitration__id=None)\
            .closed()\
            .order_by('-offer__status_changed_at')

    def closed_without_arbitrage(self):
        return self.filter(arbitration__id=None).closed()


class DealManager(models.Manager):
    def get_queryset(self):
        return DealQuerySet(self.model, using=self._db)

    def started(self):
        return self.get_queryset().started()

    def closed(self):
        return self.get_queryset().closed()

    def expired(self):
        return self.get_queryset().expired()

    def waiting_for_buyer_deposit_confirm(self):
        return self.get_queryset().waiting_for_buyer_deposit_confirm()

    def waiting_for_seller_collateral_confirm(self):
        return self.get_queryset().waiting_for_seller_collateral_confirm()

    def waiting_for_sides_claim(self):
        return self.get_queryset().waiting_for_sides_claim()

    def waiting_for_completion(self):
        return self.get_queryset().waiting_for_completion()

    def finished(self):
        return self.get_queryset().finished()

    def check_is_finished(self):
        return self.get_queryset().check_is_finished()

    def latest_closed(self):
        return self.get_queryset().latest_closed()

    def closed_without_arbitrage(self):
        return self.get_queryset().closed_without_arbitrage()


class Deal(models.Model):
    offer = models.ForeignKey(
        Offer, verbose_name=_('Offer'), related_name='deals',
        on_delete=models.CASCADE)
    start_date = models.DateTimeField(_('Deal start date'), auto_now_add=True)
    status = models.TextField(_('Deal status'), choices=DealStatus.choices)
    expires = models.DateTimeField(
        _('Deal status expiration'), blank=True, null=True)
    fee = models.FloatField(_('Fee'), validators=[MinValueValidator(0.0)])
    hash_id = models.TextField(_('Deal Hash'), blank=True, null=True)
    is_buyer_approved = models.BooleanField(
        _('Buyer approved'), blank=True, default=False)
    is_seller_approved = models.BooleanField(
        _('Seller approved'), blank=True, default=False)

    objects = DealManager()

    class Meta:
        db_table = 'core_deal'
        verbose_name = _('Deal')
        verbose_name_plural = _('Deals')

    @staticmethod
    def total_summary():
        closed_count =\
            Deal.objects.closed_without_arbitrage().count()
        closed_summ =\
            Deal.objects.closed_without_arbitrage().aggregate(
                summ=models.Sum('offer__price'))\
            .get('summ')
        return {
            'closed_count': closed_count,
            'closed_summ': closed_summ
        }

    def save(self, *args, **kwargs):
        if self.status == DealStatus.WAITING_SELLER_CONFIRM:
            self.expires = self.gen_expires()
        if self.status == DealStatus.COMPLETION_DELAY:
            self.expires = self.gen_expires_long()
        super().save(*args, **kwargs)

    def has_feedback_for(self, account):
        if self.offer.buyer == account or self.offer.seller == account:
            return DealFeedback.objects\
                .filter(deal=self, feedback_for=account).exists()
        return True

    def get_status_short(self):
        status = self.get_status_display()
        return status

    def start_timestamp(self):
        return int(self.start_date.timestamp())

    def gen_expires(self):
        return timezone.now() + timedelta(
            minutes=settings.DEAL_STATUS_TIMEOUT_MINUTES)

    def gen_expires_long(self):
        return timezone.now() + timedelta(
            minutes=settings.DEAL_COMPLETION_TIMEOUT_MINUTES)

    def stage_number(self):
        if self.status in (DealStatus.OPEN, DealStatus.WAITING_SELLER_CONFIRM):
            return 1
        if self.status in (
            DealStatus.WAITING_BUYER_PAYMENT,
            DealStatus.WAITING_BUYER_PAYMENT_CONFIRM
        ):
            return 2
        if self.status in (
            DealStatus.WAITING_SELLER_COLLATERAL,
            DealStatus.WAITING_SELLER_COLLATERAL_CONFIRM
        ):
            return 3
        if self.status in (
            DealStatus.WAITING_FOR_COMPLETION,
            DealStatus.COMPLETION_DELAY
        ):
            return 4
        if self.status in (
            DealStatus.WAITING_SELLER_CLAIM,
            DealStatus.CONFIRMED_FINISH
        ):
            return 5
        if self.status == DealStatus.CLOSED:
            return 6

    def is_waiting_seller_confirm(self):
        return self.status == DealStatus.WAITING_SELLER_CONFIRM

    def seller_confirm(self):
        with transaction.atomic():
            self.status = DealStatus.WAITING_BUYER_PAYMENT
            self.expires = self.gen_expires()
            self.save()
            self.offer.set_update()
            Notification.add_event(
                NotifyEvent.SELLER_CONFIRM, self.offer.buyer, offer=self.offer)

    def is_waiting_buyer_payment(self):
        return self.status == DealStatus.WAITING_BUYER_PAYMENT

    def buyer_deposited(self):
        with transaction.atomic():
            self.status = DealStatus.WAITING_BUYER_PAYMENT_CONFIRM
            self.save()
            self.offer.set_update()

    def is_buyer_deposited(self):
        return self.status == DealStatus.WAITING_BUYER_PAYMENT_CONFIRM

    def buyer_deposit_confirmed(self):
        with transaction.atomic():
            self.status = DealStatus.WAITING_SELLER_COLLATERAL
            self.expires = self.gen_expires()
            self.save()
            self.offer.set_update()
            Notification.add_event(
                NotifyEvent.BUYER_PAYED, self.offer.seller, offer=self.offer)

    def is_waiting_seller_collateral(self):
        return self.status == DealStatus.WAITING_SELLER_COLLATERAL

    def seller_payed_collateral(self):
        with transaction.atomic():
            self.status = DealStatus.WAITING_SELLER_COLLATERAL_CONFIRM
            self.save()
            self.offer.set_update()

    def is_seller_deposited(self):
        return self.status == DealStatus.WAITING_SELLER_COLLATERAL_CONFIRM

    def seller_collateral_confirmed(self):
        with transaction.atomic():
            self.status = DealStatus.WAITING_FOR_COMPLETION
            self.expires = None
            self.save()
            self.offer.set_update()
            Notification.add_event(
                NotifyEvent.SELLER_PAYED, self.offer.buyer, offer=self.offer)

    def is_waiting_for_completion(self):
        return self.status == DealStatus.WAITING_FOR_COMPLETION

    def buyer_complete(self):
        with transaction.atomic():
            self.status = DealStatus.COMPLETION_DELAY
            self.save()
            self.offer.set_update()

    def is_completion_delay(self):
        return self.status == DealStatus.COMPLETION_DELAY

    def process_expire(self):
        if self.is_waiting_seller_confirm():
            buyer = self.offer.buyer
            self.cancel_and_reopen_offer()
            Notification.add_event(
                NotifyEvent.DEAL_EXPIRED_SELLER_CONFIRM, buyer,
                offer=self.offer)
        if self.is_waiting_buyer_payment():
            seller = self.offer.seller
            self.cancel_and_reopen_offer()
            Notification.add_event(
                NotifyEvent.DEAL_EXPIRED_BUYER_PAYMENT, seller,
                offer=self.offer)
        if self.is_waiting_seller_collateral():
            buyer = self.offer.buyer
            self.cancel_payed()
            Notification.add_event(
                NotifyEvent.DEAL_EXPIRED_SELLER_PAYMENT, buyer,
                offer=self.offer)
        if self.is_completion_delay():
            with transaction.atomic():
                self.status = DealStatus.WAITING_SELLER_CLAIM
                self.expires = None
                self.save()
                self.offer.set_update()
                Notification.add_event(
                    NotifyEvent.DEAL_COMPLETED, self.offer.seller,
                    offer=self.offer)
                Notification.add_event(
                    NotifyEvent.DEAL_COMPLETED, self.offer.buyer,
                    offer=self.offer)

    def is_waiting_seller_claim(self):
        return self.status == DealStatus.WAITING_SELLER_CLAIM

    def is_waiting_buyer_claim(self):
        return self.status == DealStatus.WAITING_BUYER_CLAIM

    def is_waiting_moderator(self):
        return self.status == DealStatus.WAITING_MODERATOR

    def is_waiting_sides_claim(self):
        return self.status == DealStatus.WAITING_SIDES_CLAIM

    def confirm_finish(self):
        self.status = DealStatus.CONFIRMED_FINISH
        self.save()

    def is_confirmed_finish(self):
        return self.status == DealStatus.CONFIRMED_FINISH

    def close_deal(self):
        with transaction.atomic():
            self.status = DealStatus.CLOSED
            self.expires = None
            self.save()
            self.offer.close()
            Notification.add_event(
                NotifyEvent.DEAL_CLOSED, self.offer.buyer, offer=self.offer)
            Notification.add_event(
                NotifyEvent.DEAL_CLOSED, self.offer.seller, offer=self.offer)

    def cancel_and_reopen_offer(self):
        with transaction.atomic():
            self.status = DealStatus.DELETED
            self.expires = None
            self.save()
            self.offer.reopen()

    def cancel_payed(self):
        with transaction.atomic():
            DealCancelation.objects.create(
                deal=self, reasons=[DealCancelReason.CANCELED_BY_TIMER])
            self.status = DealStatus.WAITING_BUYER_CLAIM
            self.expires = None
            self.save()

    def call_arbitration(self, is_seller, reasons_text, details):
        reasons = []
        if is_seller:
            reasons.append(DealCancelReason.CANCELED_BY_SELLER)
        else:
            reasons.append(DealCancelReason.CANCELED_BY_BUYER)
        reasons.extend(filter(None, reasons_text.split(',')))
        with transaction.atomic():
            DealCancelation.objects.create(
                deal=self, reasons=reasons, details=details)
            self.status = DealStatus.WAITING_MODERATOR
            self.expires = None
            self.save()
            notify_account = self.offer.buyer if is_seller\
                else self.offer.seller
            Notification.add_event(
                NotifyEvent.DEAL_CANCELED, notify_account, offer=self.offer)

    def resolve_arbitration(
            self, pay_to_seller, pay_to_buyer, txn_receipt_str):
        with transaction.atomic():
            DealArbitration.objects.create(
                deal=self, pay_to_seller=pay_to_seller,
                pay_to_buyer=pay_to_buyer,
                txn_receipt=json.loads(txn_receipt_str))
            self.status = DealStatus.WAITING_SIDES_CLAIM
            self.save()
            self.offer.set_update()
            Notification.add_event(
                NotifyEvent.DEAL_RESOLVED, self.offer.buyer, offer=self.offer)
            Notification.add_event(
                NotifyEvent.DEAL_RESOLVED, self.offer.seller, offer=self.offer)

    @cached_property
    def current_arbitration(self):
        arbitration = None
        try:
            arbitration = self.arbitration
        except DealArbitration.DoesNotExist:
            pass
        return arbitration

    def has_unclaimed_arbitration(self):
        arbitration = self.current_arbitration
        if not arbitration:
            return False
        return arbitration.is_still_unclaimed()

    def buyer_claim_after_arbitrage(self):
        arbitration = self.current_arbitration
        if arbitration:
            arbitration.is_buyer_claimed = True
            arbitration.save()
            if arbitration.pay_to_seller == 0 or arbitration.is_seller_claimed:
                self.confirm_finish()

    def is_buyer_claim_allowed(self):
        arbitration = self.current_arbitration
        if arbitration:
            return arbitration.pay_to_buyer > 0
        return False

    def is_buyer_claimed_after_arbitrage(self):
        arbitration = self.current_arbitration
        if arbitration:
            return arbitration.is_buyer_claimed
        return False

    def seller_claim_after_arbitrage(self):
        arbitration = self.current_arbitration
        if arbitration:
            arbitration.is_seller_claimed = True
            arbitration.save()
            if arbitration.pay_to_buyer == 0 or arbitration.is_buyer_claimed:
                self.confirm_finish()

    def is_seller_claim_allowed(self):
        arbitration = self.current_arbitration
        if arbitration:
            return arbitration.pay_to_seller > 0
        return False

    def is_seller_claimed_after_arbitrage(self):
        arbitration = self.current_arbitration
        if arbitration:
            return arbitration.is_seller_claimed
        return False

    def is_closed(self):
        return self.status == DealStatus.CLOSED

    def retry_approve(self, account):
        offer = self.offer
        if offer.seller_id == account.pk:
            self.is_seller_approved = False
        if offer.buyer_id == account.pk:
            self.is_buyer_approved = False
        self.save()


class DealCancelReason(models.TextChoices):
    CANCELED_BY_SELLER = 'canceled_by_seller', 'Canceled by seller'
    CANCELED_BY_BUYER = 'canceled_by_buyer', 'Canceled by buyer'
    CANCELED_BY_TIMER = 'canceled_by_timer', 'Canceled by timer'
    ITEM_NOT_PROVIDED = 'item_not_provided', 'The item has not been provided'
    SELLER_NOT_REPLIED = 'seller_not_replied', 'The seller does not reply'
    OTHER = 'other', 'Other'


class DealCancelation(models.Model):
    deal = models.OneToOneField(
        Deal, verbose_name=_('Deal'), related_name='cancelation',
        on_delete=models.CASCADE)
    reasons = models.JSONField('Reasons list')
    details = models.TextField('Feedback details', blank=True, null=True)

    class Meta:
        db_table = 'core_deal_cancelation'


class DealArbitration(models.Model):
    deal = models.OneToOneField(
        Deal, verbose_name=_('Deal'), related_name='arbitration',
        on_delete=models.CASCADE)
    pay_to_seller = models.FloatField(
        _('Pay to seller'), validators=[MinValueValidator(0.0)])
    pay_to_buyer = models.FloatField(
        _('Pay to buyer'), validators=[MinValueValidator(0.0)])
    is_seller_claimed = models.BooleanField(
        _('Seller claimed money'), blank=True, default=False)
    is_buyer_claimed = models.BooleanField(
        _('Buyer claimed money'), blank=True, default=False)
    txn_receipt = models.JSONField('txn', blank=True, null=True)

    class Meta:
        db_table = 'core_deal_arbitration'

    def is_still_unclaimed(self):
        return (
            (self.pay_to_seller > 0 and not self.is_seller_claimed)
            or
            (self.pay_to_buyer > 0 and not self.is_buyer_claimed)
        )


class DealFeedback(models.Model):
    deal = models.ForeignKey(
        Deal, verbose_name=_('Deal'), related_name='feedbacks',
        on_delete=models.CASCADE)
    account = models.ForeignKey(
        Account, verbose_name=_('Reporter'), related_name='sent_feedbacks',
        on_delete=models.CASCADE)
    feedback_for = models.ForeignKey(
        Account, verbose_name=_('Account'), related_name='received_feedbacks',
        on_delete=models.CASCADE)
    rating = models.FloatField(
        _('Rating'), blank=True, default=0,
        validators=[MinValueValidator(1.0), MaxValueValidator(5.0)])
    details = models.TextField(_('Feedback details'))
    created_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'core_deal_feedback'
        verbose_name = _('Deal Feedback')
        verbose_name_plural = _('Deals Feedbacks')
        ordering = ['-pk']


class AccountBackendMessage(models.Model):
    account = models.ForeignKey(
        Account, verbose_name=_('Account'), related_name='backend_messages',
        on_delete=models.CASCADE)
    title = models.CharField(_('Title'), max_length=16)
    message = models.CharField(_('Message'), max_length=128)
    tag = models.CharField(max_length=16)

    @staticmethod
    def add_info(account, message):
        AccountBackendMessage.objects.create(
            account=account, message=message, title='Info', tag='success')


class AccountFavorites(models.Model):
    account = models.ForeignKey(
        Account, verbose_name=_('Account'), related_name='favorites',
        on_delete=models.CASCADE)
    offer = models.ForeignKey(
        Offer, verbose_name=_('Offer'), related_name='favorites',
        on_delete=models.CASCADE)

    class Meta:
        db_table = 'core_favorites'
        verbose_name = _('Account Favorites')
        verbose_name_plural = _('Account Favorites')
        unique_together = ['account', 'offer']
        ordering = ['-pk']


class PriceRequest(models.Model):
    account = models.ForeignKey(
        Account, verbose_name=_('Account'), related_name='price_requests',
        on_delete=models.CASCADE)
    name = models.CharField(
        _('Name'), max_length=128, validators=[
            MinLengthValidator(3),
            RegexValidator(
                '^[a-z0-9 #_-]+$',
                message=_('May consist only of a-z, 0–9, and _-'),
                flags=re.IGNORECASE)
        ])
    max_price = models.FloatField(
        _('Max Price'), validators=[MinValueValidator(settings.MIN_PRICE)])
    created_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'core_requests'
        verbose_name = _('Account Request')
        verbose_name_plural = _('Account Requests')
        ordering = ['-pk']


class WTBRequestStatus(models.TextChoices):
    MODERATION = 'moderation', 'On moderation'
    ACTIVE = 'active', 'Active'
    DELETED = 'deleted', 'Deleted'


class WTBRequestQuerySet(models.QuerySet):
    def not_deleted(self):
        return self.exclude(status=WTBRequestStatus.DELETED)

    def active(self):
        return self.filter(status=WTBRequestStatus.ACTIVE)\
            .filter(account__is_active=True)

    def latest_for_type(self, token_type):
        return self.filter(token_type=token_type)

    def active_or_moderation(self):
        return self.filter(status__in=[
            WTBRequestStatus.MODERATION,
            WTBRequestStatus.ACTIVE
        ])

    def search(self, search_text, order_by):
        search_term = clean_search_term(search_text)
        return self.filter(name__icontains=search_term).order_by(order_by)


class WTBRequestManager(models.Manager):
    def get_queryset(self):
        return WTBRequestQuerySet(self.model, using=self._db).not_deleted()

    def active(self):
        return self.get_queryset().active()

    def active_or_moderation(self):
        return self.get_queryset().active_or_moderation()

    def activate_from_moderation(self):
        hour_ago = timezone.now() - timezone.timedelta(hours=1)
        wtb_requests_to_activate = self.get_queryset()\
            .filter(
                status=WTBRequestStatus.MODERATION,
                created_at__lt=hour_ago)
        id_list = list(wtb_requests_to_activate.values_list('id', flat=True))
        wtb_requests_to_activate.update(status=WTBRequestStatus.ACTIVE)
        for wtb_request_id in id_list:
            wtb_request = WTBRequest.objects.get(pk=wtb_request_id)
            Notification.add_event(
                NotifyEvent.WTB_REQUEST_ACTIVE, wtb_request.account,
                wtb_request=wtb_request)

    def latest_nft(self):
        return self.get_queryset()\
            .active()\
            .latest_for_type(TokenType.NFT)[:INDEX_PAGE_OBJECTS_LIMIT]

    def latest_ido(self):
        return self.get_queryset()\
            .active()\
            .latest_for_type(TokenType.IDO)[:INDEX_PAGE_OBJECTS_LIMIT]

    def latest_other(self):
        return self.get_queryset()\
            .active()\
            .latest_for_type(TokenType.OTHER)[:INDEX_PAGE_OBJECTS_LIMIT]

    def latest_worker(self):
        return self.get_queryset()\
            .active()\
            .latest_for_type(TokenType.WORKER)[:INDEX_PAGE_OBJECTS_LIMIT]

    def search(self, search_text, order_by):
        return self.get_queryset().search(search_text, order_by)


class WTBRequest(models.Model):
    account = models.ForeignKey(
        Account, verbose_name=_('Account'), related_name='wtb_requests',
        on_delete=models.CASCADE)
    status = models.TextField(
        _('WTB offer status'), choices=WTBRequestStatus.choices,
        default=WTBRequestStatus.ACTIVE)
    network = models.TextField(
        _('Network'), choices=BlockchainNetwork.choices,
        default=BlockchainNetwork.BNB)
    token_type = models.TextField(_('Token type'), choices=TokenType.choices)
    name = models.CharField(
        _('Name'), max_length=128, validators=[
            MinLengthValidator(3),
            RegexValidator(
                '^[a-z0-9 #_-]+$',
                message=_('May consist only of a-z, 0–9, and _-'),
                flags=re.IGNORECASE)
        ])
    price = models.FloatField(
        _('Price'), validators=[MinValueValidator(settings.MIN_PRICE)])
    created_at = models.DateTimeField(
        _('Created at'), auto_now_add=True, blank=True, null=True)

    objects = WTBRequestManager()

    class Meta:
        db_table = 'core_wtb_requests'
        verbose_name = _('WTB Offer')
        verbose_name_plural = _('WTB Offers')
        ordering = ['-pk']

    def set_deleted(self):
        self.status = WTBRequestStatus.DELETED
        self.save()

    def is_long_name(self):
        return len(self.name) > NAME_LIMIT

    def suggest_offer(self, offer):
        Notification.add_event(
            NotifyEvent.WTB_REQUEST_OFFER, self.account,
            offer=offer, wtb_request=self)

    def __str__(self):
        return self.name


class ClickApiTokens(models.Model):
    ref_name = models.CharField(
        _('Reference Url Param Name'), max_length=32, db_index=True,
        unique=True)
    token = models.CharField(_('Click API Token'), max_length=32)

    class Meta:
        db_table = 'core_click_api_tokens'
        verbose_name = _('Click API Token')
        verbose_name_plural = _('Click API Tokens')


class NotifyEvent(models.TextChoices):
    WTS_OFFER_ACTIVE = 'wts_offer_active', 'WTS offer became active'
    WTB_REQUEST_ACTIVE = 'wtb_request_active', 'WTB offer became active'
    WTB_REQUEST_OFFER = 'wtb_request_offer', 'New suggestion for WTB offer'
    BUYER_CONFIRM = 'buyer_confirm', 'Buyer confirmed deal'
    SELLER_CONFIRM = 'seller_confirm', 'Seller confirmed deal'
    DEAL_EXPIRED_SELLER_CONFIRM =\
        'deal_expired_seller_confirm', 'Deal expired seller confirm'
    DEAL_EXPIRED_BUYER_PAYMENT =\
        'deal_expired_buyer_payment', 'Deal expired buyer payment'
    DEAL_EXPIRED_SELLER_PAYMENT =\
        'deal_expired_seller_payment', 'Deal expired seller payment'
    BUYER_PAYED = 'buyer_payed', 'Buyer payed'
    SELLER_PAYED = 'seller_payed', 'Seller payed'
    DEAL_COMPLETED = 'deal_completed', 'Deal completed'
    DEAL_CANCELED = 'deal_canceled', 'Deal arbitration created'
    DEAL_RESOLVED = 'deal_resolved', 'Deal arbitration resolved'
    DEAL_CLOSED = 'deal_closed', 'Deal closed'
    DEAL_FEEDBACK = 'deal_feedback', 'Deal feedback created'

    @staticmethod
    def deal_events():
        return [
            NotifyEvent.BUYER_CONFIRM,
            NotifyEvent.SELLER_CONFIRM,
            NotifyEvent.DEAL_EXPIRED_SELLER_CONFIRM,
            NotifyEvent.DEAL_EXPIRED_BUYER_PAYMENT,
            NotifyEvent.DEAL_EXPIRED_SELLER_PAYMENT,
            NotifyEvent.BUYER_PAYED,
            NotifyEvent.SELLER_PAYED,
            NotifyEvent.DEAL_COMPLETED,
            NotifyEvent.DEAL_CANCELED,
            NotifyEvent.DEAL_RESOLVED,
            NotifyEvent.DEAL_CLOSED,
            NotifyEvent.DEAL_FEEDBACK
        ]

    @staticmethod
    def wts_events():
        return [
            NotifyEvent.WTS_OFFER_ACTIVE
        ]

    @staticmethod
    def wtb_events():
        return [
            NotifyEvent.WTB_REQUEST_ACTIVE,
            NotifyEvent.WTB_REQUEST_OFFER
        ]


class NotificationStatus(models.TextChoices):
    NEW = 'new', 'New notification'
    SENT = 'sent', 'Sent notification'


class NotificationType(models.TextChoices):
    DEAL = 'deal', 'Deal notification'
    WTS = 'wts', 'WTS offer notification'
    WTB = 'wtb', 'WTB offer notification'


class NotificationQuerySet(models.QuerySet):
    def for_type(self, notification_type):
        return self.filter(notification_type=notification_type)

    def for_deals(self):
        return self.for_type(NotificationType.DEAL)

    def for_wts(self):
        return self.for_type(NotificationType.WTS)

    def for_wtb(self):
        return self.for_type(NotificationType.WTB)

    def unseen(self):
        return self.filter(is_seen=False)


class NotificationManager(models.Manager):
    def get_queryset(self):
        return NotificationQuerySet(self.model, using=self._db)

    def for_type(self, notification_type):
        return self.get_queryset().for_type(notification_type)

    def for_deals(self):
        return self.get_queryset().for_deals()

    def for_wts(self):
        return self.get_queryset().for_wts()

    def for_wtb(self):
        return self.get_queryset().for_wtb()

    def unseen(self):
        return self.get_queryset().unseen()


class Notification(models.Model):
    class Meta:
        db_table = 'core_notification'
        verbose_name = _('Notification')
        verbose_name_plural = _('Notifications')
        ordering = ['-pk']

    offer = models.ForeignKey(
        Offer, verbose_name=_('Offer'), related_name='notifications',
        on_delete=models.CASCADE, blank=True, null=True)
    wtb_request = models.ForeignKey(
        WTBRequest, verbose_name=_('WTB offer'), related_name='notifications',
        on_delete=models.CASCADE, blank=True, null=True)
    object_id = models.BigIntegerField()

    account = models.ForeignKey(
        Account, verbose_name=_('Account'), related_name='notifications',
        on_delete=models.CASCADE)
    notification_type = models.TextField(
        _('Notification type'), choices=NotificationType.choices,
        default=NotificationType.DEAL)
    notify_event = models.TextField(
        _('Notify event'), choices=NotifyEvent.choices)
    status = models.TextField(
        _('Notification status'), choices=NotificationStatus.choices,
        default=NotificationStatus.NEW)
    created_at = models.DateTimeField(auto_now=True)
    is_seen = models.BooleanField(
        _('Notification is seen'), blank=True, default=False)

    objects = NotificationManager()

    @staticmethod
    def add_event(notify_event, account, **kwargs):
        offer = kwargs.get('offer')
        wtb_request = kwargs.get('wtb_request')
        if offer:
            object_id = offer.pk
        if wtb_request:
            object_id = wtb_request.pk
        object_id = object_id or 0
        if notify_event in NotifyEvent.deal_events():
            notification_type = NotificationType.DEAL
        if notify_event in NotifyEvent.wts_events():
            notification_type = NotificationType.WTS
        if notify_event in NotifyEvent.wtb_events():
            notification_type = NotificationType.WTB
        try:
            Notification.objects.create(
                account=account, notify_event=notify_event,
                notification_type=notification_type,
                offer=offer, wtb_request=wtb_request,
                object_id=object_id
            )
        except Exception:
            pass

    def is_wtb(self):
        return self.notification_type == NotificationType.WTB

    def is_wtb_offer(self):
        return self.notify_event == NotifyEvent.WTB_REQUEST_OFFER

    def render_message(self):
        profile_id = None
        username = None
        offer_link_class = 'default'
        if self.notification_type == NotificationType.WTB:
            obj = self.wtb_request
            if self.offer_id:
                obj = self.offer
                seller = obj.seller
                profile_id = seller.pk
                username = str(seller)
                if obj.is_deleted():
                    offer_link_class = 'js-deleted-offer-link'
        if self.notification_type == NotificationType.WTS:
            obj = self.offer
            if obj.is_deleted():
                offer_link_class = 'js-deleted-offer-link'
        if self.notification_type == NotificationType.DEAL:
            obj = self.offer
            seller = obj.seller
            if seller == self.account:
                if obj.buyer_id:
                    profile_id = obj.buyer.pk
                    username = str(obj.buyer)
                else:
                    profile_id = seller.pk
                    username = str(seller)
            else:
                profile_id = seller.pk
                username = str(seller)
            if obj.is_deleted():
                offer_link_class = 'js-deleted-offer-link'
        name = str(obj)
        return NOTIFICATION_MESSAGES[self.notify_event].format(
            offer_id=self.offer_id,
            name=name,
            profile_id=profile_id,
            username=username,
            offer_link_class=offer_link_class
        )
