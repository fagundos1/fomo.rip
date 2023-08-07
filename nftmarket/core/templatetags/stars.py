from django import template


register = template.Library()


@register.inclusion_tag('include/star-rating.html')
def starrating(rating):
    stars = []
    for i in range(1, 6):
        if rating >= i:
            stars.append(2)
        else:
            if i - rating >= 1:
                stars.append(0)
            else:
                stars.append(1)
    return {
        'ratestars': stars
    }
