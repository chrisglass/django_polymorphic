"""
Internal utils
"""



def add_media(dest, media):
    """
    Optimized version of django.forms.Media.__add__() that doesn't create new objects.
    """
    dest._css_lists.extend(media._css_lists)
    dest._js_lists.extend(media._js_lists)
