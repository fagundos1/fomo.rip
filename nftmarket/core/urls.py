from django.urls import path, re_path
from nftmarket.core import views as core_views
from django.views.generic import TemplateView


app_name = 'core'


urlpatterns = [
    path('', core_views.index_view, name='index_page'),
    path('search/', core_views.search_view, name='search_page'),
    path(
        'my-wts-offers/', core_views.my_wts_offers_view,
        name='my_wts_offers'),
    re_path('^profile/(?P<name>[A-Za-z0-9_]+)/$', core_views.profile_view,
         name='profile_page'),
    path('my-messages/', core_views.account_messages_view),
    path('settings/', core_views.settings_page_view, name='settings_page'),
    path('upload-avatar/', core_views.upload_avatar_view),
    path('toggle-theme/', core_views.toggle_theme_view),
    path('deals/', core_views.my_deals_view, name='my_deals_page'),
    path('favorites/', core_views.favorites_view, name='favorites_page'),
    path('deals/<int:page>/', core_views.my_deals_page_view),
    path('closed-deals/<int:page>/', core_views.my_closed_deals_page_view),
    path(
        'my-wtb-offers/', core_views.my_wtb_requests_view,
        name='my_wtb_requests'),
    path(
        'settings/delete-avatar', core_views.delete_avatar_view,
        name='delete_avatar'),
    path('offer/<int:pk>/', core_views.offer_view, name='offer_page'),
    path(
        'add-wts-or-wtb-offer/', core_views.create_wts_or_wtb_request_view),
    path(
        'offer/edit/<int:pk>/', core_views.edit_offer_view,
        name='edit_offer_page'),
    path(
        'offer/delete/<int:pk>/', core_views.delete_offer_view,
        name='delete_offer'),
    path(
        'offer/favorite/<int:pk>/', core_views.toggle_favorite,
        name='toggle_favorite'),
    path(
        'offer/remove-favorite/<int:pk>/', core_views.remove_favorite,
        name='remove_favorite'),
    path('offer/stage/<int:pk>/', core_views.deal_offer_stage_view),
    path(
        'offer/confirm', core_views.confirm_offer_view, name='confirm_offer'),
    path('offer/approve-token', core_views.approved_token),
    path('offer/sign-deal', core_views.sign_deal_view, name='sign_deal'),
    path('offer/buyer-deposited', core_views.buyer_deposited),
    path('offer/seller-payed-collateral', core_views.seller_payed_collateral),
    path('offer/buyer-complete', core_views.buyer_complete),
    path('offer/retry-approve', core_views.retry_approve),
    path(
        'offer/buyer-claim-after-cancelation',
        core_views.buyer_claim_after_cancelation),
    path('offer/call-arbitration', core_views.call_arbitration),
    path(
        'offer/buyer-claim-after-arbitrage',
        core_views.buyer_claim_after_arbitrage),
    path(
        'offer/seller-claim-after-arbitrage',
        core_views.seller_claim_after_arbitrage),
    path('offer/confirm-finish', core_views.confirm_finish),
    path(
        'offer/feedback/', core_views.create_close_feedback,
        name='create_feedback'),
    path(
        'wtb-request/add/', core_views.create_price_request_view,
        name='create_request_page'),
    path(
        'wtb-request/edit/<int:pk>/', core_views.edit_wtb_request_view,
        name='edit_wtb_request_page'),
    path(
        'wtb-request/delete/<int:pk>/', core_views.delete_wtb_request_view,
        name='delete_wtb_request'),
    path(
        'wtb-request/make-offer/', core_views.make_offer_for_wtb_request_view,
        name='make_offer_for_wtb_request'),
    path(
        'rules/', TemplateView.as_view(template_name='core/rules.html'),
        name='rules_page'),
    path(
        'contacts/', TemplateView.as_view(template_name='core/contacts.html'),
        name='contacts_page'),
    path(
        'privacy-policy/',
        TemplateView.as_view(template_name='core/privacy-policy.html'),
        name='privacy_policy_page'),
    path(
        'terms-of-service/',
        TemplateView.as_view(template_name='core/terms-of-service.html'),
        name='terms_of_service_page'),
    path(
        'latest-deals/',
        core_views.latest_deals_view, name='latest_deals'),
    path('latest-deals/<int:page>/', core_views.latest_deals_page_view),
    path('auth/nonce', core_views.auth_nonce_view),
    path('auth/validate', core_views.auth_validate_view),
    path('logout/', core_views.logout_view, name='logout'),
    path(
        'notifications/', core_views.notifications_view, name='notifications'),
    path(
        'notifications/<slug:notification_type>/<int:page>/',
        core_views.notifications_page_view),
    path(
        'notifications/update-seen/<slug:notification_type>/',
        core_views.notifications_update_seen_view),
]
