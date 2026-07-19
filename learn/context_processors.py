from .services import get_profile


def unlock_toggle(request):
    """Exposes the superuser-only 'unlock all content' toggle state to every
    template via base.html's nav, without every view needing to pass profile
    into its own context explicitly."""
    user = getattr(request, 'user', None)
    if not user or not user.is_authenticated or not user.is_superuser:
        return {}
    profile = get_profile(user)
    return {
        'show_unlock_toggle': True,
        'unlock_all_active': profile.unlock_all_content,
    }
