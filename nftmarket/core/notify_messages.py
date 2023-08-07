NOTIFICATION_MESSAGES = {
    'offer_active':
        'Offer <a class="{offer_link_class}" href="/offer/{offer_id}/">{name}</a> became active',
    'wts_offer_active':
        'WTS offer <a class="{offer_link_class}" href="/offer/{offer_id}/">{name}</a> became active',
    'wtb_request_active':
        'WTB offer <a href="/my-wtb-offers/">{name}</a> became active',
    'wtb_request_offer':
        '<a href="/profile/{profile_id}/">{username}</a> made an offer of <a class="{offer_link_class}" href="/offer/{offer_id}/">{name}</a> for your request',
    'buyer_confirm':
        '<a href="/profile/{profile_id}/">{username}</a> confirmed deal <a class="{offer_link_class}" href="/offer/{offer_id}/">{name}</a>',
    'seller_confirm':
        '<a href="/profile/{profile_id}/">{username}</a> confirmed deal <a class="{offer_link_class}" href="/offer/{offer_id}/">{name}</a>',
    'deal_expired_seller_confirm':
        'Deal <a class="{offer_link_class}" href="/offer/{offer_id}/">{name}</a> is expired - <a href="/profile/{profile_id}/">{username}</a> doesn\'t confirmed',
    'deal_expired_buyer_payment':
        'Deal <a class="{offer_link_class}" href="/offer/{offer_id}/">{name}</a> is expired - <a href="/profile/{profile_id}/">{username}</a> doesn\'t pay',
    'deal_expired_seller_payment':
        'Deal <a class="{offer_link_class}" href="/offer/{offer_id}/">{name}</a> is expired - <a href="/profile/{profile_id}/">{username}</a> doesn\'t pay',
    'buyer_payed':
        '<a href="/profile/{profile_id}/">{username}</a> payed for deal - <a class="{offer_link_class}" href="/offer/{offer_id}/">{name}</a>',
    'seller_payed':
        '<a href="/profile/{profile_id}/">{username}</a> payed for deal - <a class="{offer_link_class}" href="/offer/{offer_id}/">{name}</a>',
    'deal_completed':
        'Deal <a class="{offer_link_class}" href="/offer/{offer_id}/">{name}</a> completed',
    'deal_canceled':
        'Arbitration created for deal - <a class="{offer_link_class}" href="/offer/{offer_id}/">{name}</a>',
    'deal_resolved':
        'Arbitration resolved for deal - <a class="{offer_link_class}" href="/offer/{offer_id}/">{name}</a>',
    'deal_closed':
        'Deal <a class="{offer_link_class}" href="/offer/{offer_id}/">{name}</a> closed',
    'deal_feedback':
        '<a href="/profile/{profile_id}/">{username}</a> created feedback for deal <a class="{offer_link_class}" href="/offer/{offer_id}/">{name}</a>'
}
