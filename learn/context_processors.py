from django.urls import reverse

from .services import due_review_cards, get_profile


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


# Short labels for the topic tab dividers. Full titles are long ("Advanced:
# Handle Distributed Failures") and a tab has room for one or two words;
# anything not listed here falls back to its full title.
TOPIC_TAB_LABELS = {
    'system-design-fundamentals': 'Fundamentals',
    'scale-a-service': 'Scaling',
    'distributed-failures': 'Failures',
    'operate-reliably': 'Production',
    'reason-about-guarantees': 'Guarantees',
    'system-design-case-studies': 'Case Studies',
    'operating-systems-linux': 'OS',
    'python-internals': 'Python',
}

# Challenge routes: url name -> (model name, activity label).
CHALLENGE_ROUTES = {
    'design_challenge': ('DesignChallenge', 'Architecture Builder'),
    'matching_challenge': ('MatchingChallenge', 'Matching'),
    'ordering_challenge': ('OrderingChallenge', 'Ordering'),
    'coding_challenge': ('CodingChallenge', 'Coding'),
    'flaw_challenge': ('FlawChallenge', 'Spot the Flaw'),
    'traffic_challenge': ('TrafficChallenge', 'Traffic Day'),
    'quorum_challenge': ('QuorumChallenge', 'Quorum Casino'),
    'ring_challenge': ('RingChallenge', 'Ring Balancer'),
}


def _chapter_href(chapter):
    """Most chapters hold exactly one concept; linking them straight to that
    concept skips a page that would only ever list one item."""
    concepts = list(chapter.concepts.all()[:2])
    if len(concepts) == 1:
        return reverse('learn:concept_detail', args=[concepts[0].slug])
    return reverse('learn:chapter_detail', args=[chapter.slug])


def _resolve_location(request):
    """Works out which topic tab the current page files under, plus the
    breadcrumb trail back up to it, from the resolved URL alone, so no view
    has to pass navigation context by hand."""
    from .models import (
        Chapter, CodingChallenge, Concept, DesignChallenge, FlawChallenge, MatchingChallenge,
        OrderingChallenge, QuorumChallenge, RingChallenge, Topic, TrafficChallenge,
    )
    models = {
        'DesignChallenge': DesignChallenge, 'MatchingChallenge': MatchingChallenge,
        'OrderingChallenge': OrderingChallenge, 'CodingChallenge': CodingChallenge,
        'FlawChallenge': FlawChallenge, 'TrafficChallenge': TrafficChallenge,
        'QuorumChallenge': QuorumChallenge, 'RingChallenge': RingChallenge,
    }
    match = getattr(request, 'resolver_match', None)
    if not match or match.app_name != 'learn':
        return None, []
    name, kwargs = match.url_name, match.kwargs

    topic = chapter = concept = None
    tail = []
    try:
        if name == 'topic_detail':
            topic = Topic.objects.get(slug=kwargs['topic_slug'])
        elif name == 'chapter_detail':
            chapter = Chapter.objects.select_related('topic').filter(slug=kwargs['chapter_slug']).first()
        elif name in ('concept_detail', 'concept_quiz'):
            concept = Concept.objects.select_related('chapter__topic').get(slug=kwargs['concept_slug'])
            if name == 'concept_quiz':
                tail = [{'label': 'Quiz', 'url': None}]
        elif name in CHALLENGE_ROUTES:
            model_name, label = CHALLENGE_ROUTES[name]
            challenge = models[model_name].objects.select_related('concept__chapter__topic').get(
                slug=kwargs['challenge_slug'])
            concept = challenge.concept
            tail = [{'label': label, 'url': None}]
    except Exception:  # a 404 page still renders the shell; it just has no trail
        return None, []

    if concept:
        chapter = concept.chapter
    if chapter:
        topic = chapter.topic

    trail = []
    if topic:
        trail.append({'label': topic.title, 'url': reverse('learn:topic_detail', args=[topic.slug])})
    if chapter and (concept is None or chapter.concepts.count() > 1):
        trail.append({'label': chapter.title, 'url': reverse('learn:chapter_detail', args=[chapter.slug])})
    if concept:
        trail.append({'label': concept.title, 'url': reverse('learn:concept_detail', args=[concept.slug])})
    trail.extend(tail)
    if trail and not tail:
        trail[-1]['url'] = None  # the page you're on isn't a link
    return (topic.slug if topic else None), trail


def navigation(request):
    """The file-drawer shell every page shares: topic tab dividers, the
    header's level/XP/streak readout, the due count on the Review tab, and a
    breadcrumb trail for wherever the page sits in Topic > Chapter > Concept."""
    user = getattr(request, 'user', None)
    if not user or not user.is_authenticated:
        return {}
    from .models import Topic

    profile = get_profile(user)
    current_topic, trail = _resolve_location(request)
    tabs = [
        {
            'slug': t.slug,
            'title': t.title,
            'label': TOPIC_TAB_LABELS.get(t.slug, t.title),
            'number': i,
            'stock': (i - 1) % 6 + 1,
            'url': reverse('learn:topic_detail', args=[t.slug]),
            'current': t.slug == current_topic,
        }
        for i, t in enumerate(Topic.objects.all(), start=1)
    ]
    match = getattr(request, 'resolver_match', None)
    url_name = match.url_name if match else ''
    return {
        'nav_tabs': tabs,
        'nav_trail': trail,
        'nav_section': url_name,
        'nav_profile': profile,
        'nav_due_count': due_review_cards(user).count(),
        'nav_xp_pct': int(100 * profile.xp_into_level / profile.xp_for_next_level)
        if profile.xp_for_next_level else 100,
    }
