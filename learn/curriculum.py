"""The curriculum in docs/learning, adapted into seed data for the app.

The Markdown lessons, catalogue.json and sources.json stay the source of
truth: `curriculum_chapters()` reads them at seed time and turns every lesson
and case study into a chapter dict shaped like seed_content.CHAPTERS. Notes
come from each document's sections; objectives, prerequisites and sources go
into Concept.curriculum. Quiz questions are not converted automatically: the
catalogue's checks are short-answer, so learn/curriculum_questions.py holds
deliberately authored MCQ and multi-select versions.

sd-01 keeps its hand-adapted notes, questions and request walkthrough below.
"""
import json
import re
from pathlib import Path

LEARNING_DIR = Path(__file__).resolve().parent.parent / 'docs' / 'learning'

ENGINEERING_NOTES = {
    'slug': 'system-design-engineering-notes',
    'title': 'System Design Engineering Notes',
    'author': 'SysDesign Quest · original teaching notes',
    'order': 1,
    'description': 'Original lessons grounded in standards and official technical references.',
}

DNS_TCP_TLS = {
    'id': 'sd-01',
    'slug': 'dns-tcp-tls',
    'estimated_minutes': 25,
    'objectives': [
        'Trace a new HTTPS connection from name lookup to response.',
        'Separate name resolution, transport reliability, and transport security.',
        'Explain why a timeout does not prove an operation failed.',
    ],
    'sources': [
        {'title': 'RFC 1034 · DNS', 'url': 'https://www.rfc-editor.org/rfc/rfc1034'},
        {'title': 'RFC 9293 · TCP', 'url': 'https://www.rfc-editor.org/rfc/rfc9293.html'},
        {'title': 'RFC 8446 · TLS 1.3', 'url': 'https://www.rfc-editor.org/rfc/rfc8446'},
        {'title': 'RFC 9114 · HTTP/3', 'url': 'https://www.rfc-editor.org/rfc/rfc9114'},
    ],
    'steps': [
        {
            'key': 'dns', 'title': 'DNS', 'job': 'Find the address', 'ms': 20,
            'detail': 'A resolver checks cached records or follows the DNS hierarchy to an authoritative answer. The browser gets an address for the requested hostname.',
            'boundary': 'A DNS answer does not establish a connection. A TTL limits cache lifetime; changing a record does not revoke cached answers or existing connections.',
        },
        {
            'key': 'tcp', 'title': 'TCP', 'job': 'Establish transport', 'ms': 40,
            'detail': 'The client and server establish a TCP connection. TCP carries an ordered byte stream, retransmits lost data, and controls flow and congestion.',
            'boundary': 'A TCP acknowledgement confirms transport receipt. It does not confirm that the application processed an order or committed it to a database.',
        },
        {
            'key': 'tls', 'title': 'TLS', 'job': 'Secure the connection', 'ms': 40,
            'detail': 'TLS 1.3 authenticates the server and negotiates encryption keys. The client validates the certificate, including its trust chain and the requested hostname.',
            'boundary': 'TLS provides confidentiality and integrity for this connection. Client certificates are optional. If TLS ends at a proxy, the next hop needs its own security decision.',
        },
        {
            'key': 'http', 'title': 'HTTP', 'job': 'Request and response', 'ms': 90,
            'detail': 'The client sends its request over the secure connection. This interval includes request delivery, server work, and response delivery.',
            'boundary': 'The server can commit an order even if the response never reaches the client. A timeout leaves the business outcome uncertain.',
        },
    ],
}

DNS_TCP_TLS_CHAPTER = {
    'book': ENGINEERING_NOTES['slug'],
    'slug': 'dns-tcp-tls',
    'title': 'DNS, TCP, and TLS: follow a request',
    'topic': 'system-design-fundamentals',
    'difficulty': 1, 'order': 0, 'unlock_level': 1,
    'summary': 'Start here: trace an HTTPS request, compare connection setup costs, and reason about an ambiguous timeout.',
    'concept': {
        'slug': DNS_TCP_TLS['slug'],
        'title': 'DNS, TCP, and TLS: follow a request',
        'summary': 'Find the address. Establish transport. Secure the connection. Follow one request all the way to its response.',
        'source_note': 'sd-01 · System Design Engineering Notes · RFCs 1034, 9293, 8446, 9114',
        'notes': [
            {
                'heading': 'Three jobs before the response',
                'body': 'Opening a website resembles finding an office, starting a conversation, and checking whom you are speaking to. DNS resolves the name, TCP carries an ordered byte stream, and TLS protects the connection. HTTP defines the application request and response. A failure in any layer can look like a page that never loads.\n\nThis walkthrough models HTTP/2 over TLS over TCP. HTTP/1.1 commonly uses this stack too; HTTP/3 uses QUIC instead of TCP. Sources: RFC 1034, RFC 9293, RFC 8446, RFC 9114.',
            },
            {
                'heading': 'DNS: cached answers and routing changes',
                'body': 'A resolver answers from cache or follows the DNS hierarchy toward authoritative servers. Cached records have a time to live (TTL). A DNS change does not instantly switch every client: cached answers can still name the old address, and established connections can continue using it.\n\nShorter TTLs can make routing changes visible sooner, at the cost of more lookup traffic. They do not revoke established connections. Source: RFC 1034.',
            },
            {
                'heading': 'TCP and TLS: guarantees with boundaries',
                'body': 'TCP provides ordered bytes, retransmission, and flow and congestion control. It does not define application messages or confirm database commits. A transport acknowledgement is not a receipt for a saved order.\n\nTLS 1.3 normally authenticates the HTTPS server and negotiates keys for confidentiality and integrity. Validation includes the requested hostname and certificate trust chain. Client certificates are optional. When a proxy terminates TLS, securing the next hop is a separate decision. Sources: RFC 9293 and RFC 8446.',
            },
            {
                'heading': 'Worked example: 190 ms becomes 90 ms',
                'body': 'Assume a cold HTTP/2 connection spends 20 ms on DNS, 40 ms on TCP setup, 40 ms on TLS, and 90 ms on request delivery, server work, and response delivery. The total is 190 ms.\n\nA valid cached DNS answer alone removes only the 20 ms lookup: a new connection still costs 170 ms. Reusing a valid established connection removes all three setup costs in this simplified example, leaving 90 ms. These are illustrative costs, not a universal latency table. Geography, packet loss, connection reuse, and TLS session resumption change the result.',
            },
            {
                'heading': 'A timeout leaves two possible histories',
                'body': 'In one history, an order request never reaches the server. In another, the server commits the order but the response never reaches the client. Both can end in the same client timeout. TCP cannot tell the client which business outcome happened.\n\nResolve the ambiguity through server-side state or a stable operation identifier and an application contract for safe retries. Do not assume that a timeout means it is safe to create the order again. Practice: draw both timelines and mark the last event each participant can observe.',
            },
        ],
        'questions': [
            {
                'prompt': 'Does a TCP acknowledgement prove an order was saved?',
                'choices': [('No. It confirms transport receipt, not application processing or durable commit.', True), ('Yes. TCP acknowledges only after the database commits.', False), ('Yes, provided the connection uses TLS.', False)],
                'explanation': 'TCP knows about bytes, not business transactions. The application can fail after receiving the request.',
            },
            {
                'kind': 'multi',
                'prompt': 'Why can users still reach the old server after a DNS update? Select all that apply.',
                'choices': [('A cached DNS answer can still name the old address.', True), ('An established connection can still use the old destination.', True), ('TLS forces all traffic to stay at the first address forever.', False), ('Updating authoritative DNS immediately closes every client connection.', False)],
                'explanation': 'Authoritative DNS changes do not revoke cached records or established connections. A DNS cache and a connection are separate resources.',
            },
            {
                'prompt': 'In the lesson model (20 ms DNS, 40 ms TCP, 40 ms TLS, 90 ms request/response), what does a second request cost on a valid established connection?',
                'choices': [('90 ms', True), ('170 ms', False), ('190 ms', False)],
                'explanation': 'This simplified model reuses the established transport and TLS connection, so only the 90 ms request/response interval remains.',
            },
            {
                'prompt': 'The DNS answer is cached, but there is no reusable connection. What is the total in the same model?',
                'choices': [('170 ms: TCP + TLS + request/response.', True), ('90 ms: a cached DNS answer also reuses TCP and TLS.', False), ('190 ms: DNS must always run again.', False)],
                'explanation': 'DNS caching removes 20 ms only. The new connection still needs 40 ms TCP setup and 40 ms TLS before the 90 ms request/response.',
            },
            {
                'prompt': 'An order submission times out. Which conclusion is justified?',
                'choices': [('The outcome is unknown; the server may have committed before the response was lost.', True), ('The order definitely failed and can be recreated without checking.', False), ('TLS guarantees the order was saved.', False)],
                'explanation': 'A lost request and a lost response can look identical to the client. Check server-side state or use an operation identifier and a safe retry contract.',
            },
            {
                'prompt': 'Which statement correctly describes this lesson’s protocol stack?',
                'choices': [('The example is HTTP/2 over TLS over TCP; HTTP/3 uses QUIC instead.', True), ('Every HTTPS request uses TCP, including HTTP/3.', False), ('DNS encrypts application traffic, so TLS is optional in this example.', False)],
                'explanation': 'DNS resolves names, TCP provides transport, and TLS secures the example connection. HTTP/3 uses QUIC, so TCP does not belong under every HTTP request.',
            },
        ],
    },
}


# ---------------------------------------------------------------------------
# Stages. Each curriculum stage is one dashboard topic, in path order, and
# its lessons unlock at an XP level. The case studies share a topic; each
# unlocks one level after the lessons of its own stage. Chapter difficulty is
# the catalogue's legacy_difficulty (production and expert both map to 3).
# ---------------------------------------------------------------------------

TOPICS = [
    {'slug': 'system-design-fundamentals', 'title': 'Beginner: Understand a Request', 'order': 1,
     'description': 'Trace one user request, derive a measurable requirement, and explain the first '
                    'resource bottleneck without guessing a server count.'},
    {'slug': 'scale-a-service', 'title': 'Intermediate: Scale a Service', 'order': 2,
     'description': 'Design a service with bounded resource use, clear cache freshness, durable background '
                    'work, and predictable collection traversal.'},
    {'slug': 'distributed-failures', 'title': 'Advanced: Handle Distributed Failures', 'order': 3,
     'description': 'Trace an ambiguous timeout or crash across state boundaries and show how the system '
                    'recovers without violating its business rule.'},
    {'slug': 'operate-reliably', 'title': 'Production: Operate Reliably', 'order': 4,
     'description': 'Define user-visible reliability, gather diagnostic evidence, release compatible changes, '
                    'isolate tenants, and demonstrate recovery.'},
    {'slug': 'reason-about-guarantees', 'title': 'Expert: Reason About Guarantees', 'order': 5,
     'description': 'State the failure model and guarantee precisely, produce a counterexample to a weaker '
                    'design, and defend where coordination is necessary.'},
    {'slug': 'system-design-case-studies', 'title': 'System Design Case Studies', 'order': 6,
     'description': 'Six end-to-end designs to defend against double clicks, lost responses, stale workers '
                    'and regional outages, each with a reference architecture and a scoring rubric.'},
]
STAGE_TOPICS = {
    'beginner': 'system-design-fundamentals', 'intermediate': 'scale-a-service',
    'advanced': 'distributed-failures', 'production': 'operate-reliably', 'expert': 'reason-about-guarantees',
}
CASE_STUDY_TOPIC = 'system-design-case-studies'
LESSON_UNLOCK_LEVELS = {'beginner': 1, 'intermediate': 2, 'advanced': 4, 'production': 6, 'expert': 8}
CASE_STUDY_UNLOCK_LEVELS = {'advanced': 5, 'production': 7, 'expert': 9}

LESSON_NOTES = ['Intuition', 'How it works', 'Worked example', 'Trade-offs and failure modes', 'Practice']
# Case-study sections that are not notes: objectives and sources go to
# Concept.curriculum, knowledge checks become the quiz, and the answer
# guidance and builder brief are folded into the Practice and Reference
# architecture notes as deep dives.
CASE_STUDY_SKIPPED = {
    'Learning objectives', 'Knowledge check', 'Sources and scope', 'Answer guidance', 'Architecture-builder brief',
}

_LINK = re.compile(r'\[([^\]]+)\]\([^)]+\)')


def _read_json(name):
    return json.loads((LEARNING_DIR / name).read_text(encoding='utf-8'))


def _sections(text):
    """[(level, heading, body)] for every level-2 and level-3 heading. Fenced
    blocks (the Mermaid diagrams) are dropped; the catalogue carries the same
    graph as components and connections."""
    sections, fenced = [], False
    for line in text.splitlines():
        if line.startswith('```'):
            fenced = not fenced
        elif fenced:
            continue
        elif line.startswith('## ') or line.startswith('### '):
            sections.append((3 if line.startswith('### ') else 2, line.lstrip('#').strip(), []))
        elif sections:
            sections[-1][2].append(line)
    return [(level, heading, '\n'.join(lines).strip()) for level, heading, lines in sections]


def _clean(body):
    """Markdown paragraphs to the plain text the notes template renders with
    |linebreaks: links keep their text, and the 'Technical references' line
    goes because the lesson lists its sources separately."""
    paragraphs = [p.strip() for p in re.split(r'\n\s*\n', body) if p.strip()]
    return '\n\n'.join(
        _LINK.sub(r'\1', ' '.join(p.split()))
        for p in paragraphs if not p.startswith('Technical references:')
    )


def _rubric(body):
    intro, rows = [], []
    for line in body.splitlines():
        if not line.startswith('|'):
            intro.append(line.strip())
            continue
        criterion, evidence, maximum = (cell.strip() for cell in line.strip('|').split('|'))
        if criterion != 'Criterion' and not set(criterion) <= set('-: '):
            rows.append(f'{criterion} (0 to {maximum}): {evidence}')
    return ' '.join(filter(None, intro)) + '\n\n' + '\n'.join(rows)


def _lesson_notes(path, sections):
    bodies = {heading: body for level, heading, body in sections}
    notes = []
    for heading in LESSON_NOTES:
        if heading not in bodies:
            raise ValueError(f'{path.name}: missing "## {heading}"')
        note = {'heading': heading, 'body': _clean(bodies[heading])}
        if heading == 'Practice':
            note['deep_dive'] = {'title': 'Answer guidance', 'body': _clean(bodies['Answer guidance'])}
        notes.append(note)
    return notes


def _case_study_notes(item, sections):
    bodies = {heading: body for level, heading, body in sections if level == 2}
    architecture = item['architecture']
    labels = {c['id']: c['label'] for c in architecture['components']}
    notes = []
    for heading, body in bodies.items():
        if heading in CASE_STUDY_SKIPPED:
            continue
        note = {'heading': heading, 'body': _clean(body)}
        if heading == 'Reference architecture':
            edges = '\n'.join(
                f"{labels[e['from']]} → {labels[e['to']]}: {e['label']}" for e in architecture['connections']
            )
            note['body'] = f"{edges}\n\n{note['body']}"
            note['deep_dive'] = {'title': 'Architecture-builder brief',
                                 'body': _clean(bodies['Architecture-builder brief'])}
        elif heading == 'Assessment rubric':
            note['body'] = _rubric(body)
        elif heading == 'Practice':
            note['deep_dive'] = {'title': 'Answer guidance', 'body': _clean(bodies['Answer guidance'])}
        notes.append(note)
    return notes


def curriculum_chapters():
    """Every lesson and case study in the catalogue as a seed_content chapter
    dict, in curriculum order. Raises if a document is missing a section the
    notes rely on or an item has no authored questions."""
    from .curriculum_questions import QUESTIONS

    catalogue = _read_json('catalogue.json')
    sources = {s['id']: s for s in _read_json('sources.json')['sources']}
    items = {item['id']: item for item in catalogue['items']}
    stage_titles = {stage['id']: stage['title'] for stage in catalogue['stages']}

    chapters = []
    for item in sorted(catalogue['items'], key=lambda i: i['order']):
        path = LEARNING_DIR / item['path']
        text = path.read_text(encoding='utf-8')
        sections = _sections(text)
        is_case = item['type'] == 'case_study'
        scope = [line.replace('targets below', 'targets in this case study')
                 for line in text.splitlines() if line.startswith('All scale figures')]
        scope += [_clean(body).split('\n\n')[0] for level, heading, body in sections if heading == 'Sources and scope']
        cited = [sources[s] for s in item['source_ids']]
        concept = {
            'slug': item['slug'], 'title': item['title'], 'summary': item['summary'],
            'source_note': f"{item['id']} · {ENGINEERING_NOTES['title']} · references: "
                           + ', '.join(dict.fromkeys(s['publisher'] for s in cited)),
            'notes': _case_study_notes(item, sections) if is_case else _lesson_notes(path, sections),
            'questions': QUESTIONS.get(item['id']),
            'curriculum': {
                'id': item['id'], 'type': item['type'], 'stage': item['stage'],
                'stage_title': stage_titles[item['stage']], 'minutes': item['estimated_minutes'],
                'objectives': item['objectives'],
                'prerequisites': [
                    {'id': p, 'title': items[p]['title'], 'slug': items[p]['slug']} for p in item['prerequisite_ids']
                ],
                'sources': [{'title': s['title'], 'url': s['url'], 'publisher': s['publisher']} for s in cited],
                'scope': ' '.join(scope),
            },
        }
        chapter = {
            'book': ENGINEERING_NOTES['slug'], 'slug': item['slug'], 'title': item['title'],
            'topic': CASE_STUDY_TOPIC if is_case else STAGE_TOPICS[item['stage']],
            'difficulty': item['legacy_difficulty'], 'order': item['order'],
            'unlock_level': (CASE_STUDY_UNLOCK_LEVELS if is_case else LESSON_UNLOCK_LEVELS)[item['stage']],
            'summary': item['summary'], 'concept': concept,
        }
        if item['id'] == DNS_TCP_TLS['id']:
            # sd-01 keeps its hand-adapted notes, questions and wording.
            adapted = DNS_TCP_TLS_CHAPTER['concept']
            chapter['summary'] = DNS_TCP_TLS_CHAPTER['summary']
            concept.update({key: adapted[key] for key in ('summary', 'source_note', 'notes', 'questions')})
        if not concept['questions']:
            raise ValueError(f"{item['id']}: no questions in learn/curriculum_questions.py")
        chapters.append(chapter)
    return chapters
