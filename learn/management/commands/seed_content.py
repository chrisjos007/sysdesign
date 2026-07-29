from django.core.management.base import BaseCommand
from django.db import transaction

from learn.models import Book, Chapter, Concept, Question, Choice, Topic
from learn.services import ensure_badges_exist

# ---------------------------------------------------------------------------
# Content data.
#
# Two kinds of chapters live here now:
#   - "System design" items: a concrete named system to design (Design a URL
#     Shortener, Designing Twitter, etc). Each of these is its own chapter/
#     concept and is guaranteed a builder (DesignChallenge) game in
#     seed_games.py — see DESIGN_CHALLENGES there.
#   - "Domain" items: several loosely-related, non-system-specific chapters
#     from the original per-chapter breakdown, merged into one bigger
#     chapter/concept with a combined summary and quiz bank. These can span
#     books (e.g. Storage Engines pulls from both Database Internals and
#     DDIA) since the grouping is by topic, not by table of contents. Their
#     existing matching/ordering games stay as separate mini-games attached
#     to the same merged concept (a Concept can have many matching/ordering
#     challenges) — see seed_games.py.
#
# unlock_level gates chapter access based on the player's current level.
# ---------------------------------------------------------------------------

BOOK1 = {
    'slug': 'system-design-interview-xu',
    'title': "System Design Interview: An Insider's Guide",
    'author': 'Alex Xu',
    'order': 1,
    'description': 'Sixteen classic system design interview walkthroughs, from scaling basics to designing YouTube.',
}

BOOK2 = {
    'slug': 'grokking-system-design',
    'title': 'Grokking the System Design Interview',
    'author': 'Educative',
    'order': 2,
    'description': 'A step-by-step framework plus deep dives into Instagram, Dropbox, Twitter, Messenger and more.',
}

BOOK3 = {
    'slug': 'database-internals',
    'title': 'Database Internals',
    'author': 'Alex Petrov',
    'order': 3,
    'description': 'How storage engines and distributed databases actually work under the hood, from B-trees to consensus.',
}

BOOK4 = {
    'slug': 'designing-data-intensive-apps',
    'title': 'Designing Data-Intensive Applications',
    'author': 'Martin Kleppmann',
    'order': 4,
    'description': 'The definitive guide to the principles behind reliable, scalable, and maintainable data systems.',
}

BOOK5 = {
    'slug': 'linux-pocket-guide',
    'title': 'Linux Pocket Guide',
    'author': 'Daniel J. Barrett',
    'order': 5,
    'description': 'Essential Linux commands for navigating, managing, and troubleshooting a system from the shell.',
}

BOOK6 = {
    'slug': 'python-advanced-concepts',
    'title': 'Python: Advanced Concepts',
    'author': 'Compiled Reference Notes',
    'order': 6,
    'description': 'Dictionary internals, process/thread concurrency, and the CPython data model, one level below the docs.',
}

BOOK7 = {
    'slug': 'os-file-handling-systems',
    'title': 'Operating Systems: File Handling & Systems Programming',
    'author': 'Compiled Reference Notes',
    'order': 7,
    'description': 'How files, permissions, processes, and storage actually work underneath the shell commands that touch them.',
}

# ---------------------------------------------------------------------------
# Topics: the primary organizing unit for browsing (dashboard grouping).
# Unlike Book, a Topic groups content by system-logic and deliberately spans
# multiple books — e.g. every chapter touching replication/consensus/storage
# internals lands in "Databases & Distributed Storage" regardless of which
# of the 5 books it was drawn from. `book` stays on Chapter purely for
# provenance/attribution and the book_worm badge; it no longer drives any
# navigation or grouping.
# ---------------------------------------------------------------------------

TOPIC_FUNDAMENTALS = 'system-design-fundamentals'
TOPIC_PATTERNS = 'distributed-systems-patterns'
TOPIC_DATA = 'databases-distributed-storage'
TOPIC_CASE_STUDIES = 'system-design-case-studies'
TOPIC_OS = 'operating-systems-linux'
TOPIC_PYTHON = 'python-internals'

TOPICS = [
    dict(slug=TOPIC_FUNDAMENTALS, title='System Design Fundamentals', order=1,
         description='The repeatable framework, scaling basics, and estimation math every design question leans on.'),
    dict(slug=TOPIC_PATTERNS, title='Distributed Systems Building Blocks', order=2,
         description='Reusable infrastructure patterns — rate limiting, consistent hashing, unique ID generation — that show up across many different systems.'),
    dict(slug=TOPIC_DATA, title='Databases & Distributed Storage', order=3,
         description='How storage engines, replication, consensus, and consistency actually work under the hood, drawn from Database Internals, DDIA, and the key-value store chapter.'),
    dict(slug=TOPIC_CASE_STUDIES, title='System Design Case Studies', order=4,
         description='End-to-end designs for named, real systems — URL shorteners, crawlers, chat, and the big social/media platforms.'),
    dict(slug=TOPIC_OS, title='Operating Systems & Linux Fundamentals', order=5,
         description='The command-line and OS-level fundamentals for actually operating a system from the shell.'),
    dict(slug=TOPIC_PYTHON, title='Python Internals & Concurrency', order=6,
         description='What actually happens under `d[key]`, how subprocess/multiprocessing/threading differ, and the rest of the language’s advanced data model.'),
]

CHAPTERS = [
    # =========================================================================
    # --- Book 1: System Design Interview (Alex Xu) ---
    # =========================================================================

    # --- Domain item: merges the two foundational (non-system) chapters from
    # this book with Grokking's "framework" chapter (cross-book, since all
    # three are approach/methodology rather than a specific system).
    dict(book='system-design-interview-xu', slug='sysdesign-fundamentals', title='System Design Fundamentals: Framework, Scaling & Estimation',
         topic=TOPIC_FUNDAMENTALS, difficulty=1,
         order=1, unlock_level=1,
         summary='A repeatable approach to any design question, the building blocks of scaling one server to millions of users, and the back-of-the-envelope math to size a system before building it.',
         concept=dict(
            slug='fundamentals-framework-scaling-estimation', title='The 7-Step Framework, Scaling Basics & Estimation',
            source_note='Systematic Approach; Chapter 1: Scale From Zero to Millions of Users; Chapter 2: Back-of-the-Envelope Estimation',
            summary=(
                "A repeatable way to approach any system design question, plus the scaling and estimation "
                "math that framework leans on every time."
            ),
            notes=[
                dict(heading="The 7-Step Framework",
                     body=(
                        "Both of the interview-prep books used here open with the same idea: don't wing a "
                        "system design question, run it through a framework. Grokking the System Design "
                        "Interview's 'Systematic Approach' chapter lays out seven steps: (1) clarify "
                        "requirements — system design prompts are deliberately vague, so ask what the system "
                        "must actually do before designing anything; (2) define the system's interface/API — "
                        "what calls will clients make; (3) back-of-the-envelope estimation — size the "
                        "expected traffic, storage, and bandwidth; (4) define the data model — what entities "
                        "exist and how they relate; (5) produce a high-level design — boxes and arrows for "
                        "the major components; (6) detailed design — dig into the 2-3 components the "
                        "interviewer cares about most, rather than every component equally; and (7) identify "
                        "bottlenecks — single points of failure, scaling limits — and propose fixes.\n\n"
                        "The point of the framework isn't ritual for its own sake: each step protects you "
                        "from a specific failure mode, like building the wrong thing (step 1) or running out "
                        "of time going deep on a component nobody asked about (step 6)."
                     ),
                     deep_dive=dict(
                        title="Why do interviewers ask deliberately vague questions?",
                        body=(
                            "'Design Twitter' has no single correct answer, and that's the point — the "
                            "interviewer wants to see how you handle ambiguity, not whether you memorized a "
                            "reference architecture. Asking clarifying questions first (do we need to support "
                            "media attachments? what's the read:write ratio? how many users?) is itself part "
                            "of what's being evaluated. Skipping straight to a detailed design is one of the "
                            "most common ways candidates lose points early, because it signals a habit of "
                            "solving the wrong problem confidently."
                        ),
                     )),
                dict(heading="Scaling From One Server to Millions of Users",
                     body=(
                        "Alex Xu's System Design Interview, Chapter 1, builds the framework's step 7 "
                        "(bottlenecks) into a concrete story: everything starts on one server running the "
                        "web app, database, and cache together — fine for a prototype, but it has zero "
                        "redundancy and a hard ceiling. Vertical scaling ('scale up') buys more headroom by "
                        "adding CPU/RAM to that one box, but it's a dead end: there's a physical limit to how "
                        "big one machine gets, and a single box is still a single point of failure. "
                        "Horizontal scaling ('scale out') instead puts a load balancer in front of a pool of "
                        "identical web servers — it spreads traffic across them, routes around any server "
                        "that goes unhealthy, and lets you add capacity just by adding boxes. Once there's "
                        "more than one web server, the database usually gets split onto its own dedicated "
                        "tier, and then replicated: a single master server accepts writes and streams them to "
                        "one or more replicas, which serve read traffic. Because reads vastly outnumber "
                        "writes in most applications, this alone often relieves the biggest bottleneck."
                     ),
                     deep_dive=dict(
                        title="What actually goes wrong when a replica falls behind or dies?",
                        body=(
                            "Replication isn't free of trade-offs. If the master crashes, something has to "
                            "promote a replica to take over writes — done badly, this either loses in-flight "
                            "writes or produces two masters at once (split brain). If a replica falls behind "
                            "(replication lag), a user who just wrote data and immediately reads it back from "
                            "a lagging replica can see stale results — a subtle bug that only shows up under "
                            "load. Production systems handle this with health checks, automated failover, and "
                            "sometimes routing a user's own reads to the master right after they write."
                        ),
                     )),
                dict(heading="Back-of-the-Envelope Estimation & Latency Numbers",
                     body=(
                        "Chapter 2 of Alex Xu's book is about sizing a design before you commit to it: rough "
                        "QPS (queries per second), storage growth over 5 years, bandwidth, and number of "
                        "servers needed. None of this needs to be precise — the goal is to catch a design "
                        "that's obviously implausible (e.g. one server trying to hold a petabyte, or an "
                        "estimate implying 500,000 QPS to a single database) before investing in the details. "
                        "This kind of estimation leans on a mental table of 'latency numbers every programmer "
                        "should know', popularized by Google's Jeff Dean: operations that differ by orders of "
                        "magnitude in cost, which is easy to forget when everything just looks like a function "
                        "call in code."
                     ),
                     deep_dive=dict(
                        title="The full latency numbers table",
                        body=(
                            "Roughly: an L1 cache reference is ~1ns; a main memory (RAM) reference is ~100ns "
                            "(100x slower than L1); compressing 1KB with a fast compressor is ~10us; reading "
                            "1MB sequentially from memory is ~10us; an SSD random read is ~100us (1000x "
                            "slower than memory); reading 1MB sequentially from an SSD is ~1ms; a round trip "
                            "within the same datacenter is ~500us; a disk seek on a spinning HDD is ~10ms; "
                            "reading 1MB sequentially from a spinning disk is ~20ms; and a network round trip "
                            "between the US and Europe is ~150ms. The exact numbers drift as hardware "
                            "improves, but the relative gaps — memory vs. disk vs. cross-continent network — "
                            "are the part worth internalizing."
                        ),
                     )),
            ],
            questions=[
                dict(prompt="What should be the very first step when tackling a system design interview question?",
                     choices=[("Jump straight into drawing the database schema", False),
                              ("Clarify requirements and scope", True),
                              ("Pick the programming language", False),
                              ("Estimate the number of servers needed", False)],
                     explanation="System design questions are intentionally vague — clarifying scope prevents designing the wrong thing.",
                     difficulty=1),
                dict(prompt="What is the purpose of the final 'identifying bottlenecks' step?",
                     choices=[("To find single points of failure and scaling limits, and propose fixes", True),
                              ("To count the total lines of code", False),
                              ("To pick a company to work for", False),
                              ("To write unit tests", False)],
                     explanation="Good design isn't just building something that works — it's identifying where it will break under load and addressing that.",
                     difficulty=1),
                dict(prompt="What is the main limitation of vertical scaling (scaling up)?",
                     choices=[("It requires a load balancer", False),
                              ("It has a hard ceiling and no failover/redundancy", True),
                              ("It cannot handle read traffic", False),
                              ("It is more expensive than horizontal scaling in all cases", False)],
                     explanation="A single server can only get so big, and if it goes down the whole app goes down with it.",
                     difficulty=1),
                dict(prompt="In a typical database replication setup, what is the master node responsible for?",
                     choices=[("Only reads", False), ("Only writes", False),
                              ("Writes (reads can be served by replicas)", True),
                              ("Load balancing between replicas", False)],
                     explanation="Writes go to the master; replicas hold copies of the data and typically serve reads.",
                     difficulty=2),
                dict(prompt="Why put a load balancer in front of your web servers?",
                     choices=[("To encrypt traffic only", False),
                              ("To distribute traffic and hide unhealthy servers from users", True),
                              ("To replace the database", False),
                              ("It's required by HTTP", False)],
                     explanation="A load balancer spreads incoming requests across a pool of servers and routes around failed ones.",
                     difficulty=1),
                dict(prompt="If a database replica goes down in a master-slave setup, what typically happens?",
                     choices=[("The whole system goes down", False),
                              ("Reads are temporarily redirected to the master or another replica", True),
                              ("Writes stop being durable", False),
                              ("The master is promoted to a replica", False)],
                     explanation="Losing one replica shouldn't take down the system — reads can shift elsewhere while it's replaced.",
                     difficulty=2),
                dict(prompt="Roughly how much slower is reading from an SSD compared to reading from memory (RAM)?",
                     choices=[("About the same speed", False), ("~10x slower", False),
                              ("~1000x slower", True), ("~1,000,000x slower", False)],
                     explanation="Memory access ~100ns vs SSD read ~100us — about a 1000x difference.",
                     difficulty=2),
                dict(prompt="What is the primary purpose of back-of-the-envelope estimation in a system design interview?",
                     choices=[("To get an exact, production-ready capacity plan", False),
                              ("To sanity-check scale and surface bottlenecks early", True),
                              ("To calculate the exact salary needed for the team", False),
                              ("To avoid writing any code", False)],
                     explanation="It's a rough sanity check, not a precise calculation — it shapes design decisions.",
                     difficulty=1),
                dict(prompt="A cross-continent network round trip (e.g. US to Europe) is roughly how long?",
                     choices=[("500 nanoseconds", False), ("500 microseconds", False),
                              ("150 milliseconds", True), ("15 seconds", False)],
                     explanation="Cross-continent round trips are roughly 150ms — orders of magnitude slower than an in-datacenter round trip (~500us).",
                     difficulty=2),

                # --- Added from verified web sources (AWS/Azure docs, Cloudflare
                # docs, MongoDB docs, Wikipedia, Redis blog, Jeff Dean's "Numbers
                # Everyone Should Know") to broaden this topic's question bank
                # beyond the original book chapters. Each explanation cites its
                # source. Mix of single-answer (kind defaults to mcq) and
                # select-all-that-apply (kind='multi') questions. ---

                # Load balancing
                dict(prompt="Which load-balancing algorithm sends each new request to the next server in a fixed rotating order, regardless of current load?",
                     choices=[("Round robin", True), ("Least connections", False),
                              ("Consistent hashing", False), ("Sticky sessions", False)],
                     explanation="Round robin cycles through the server pool in order; it doesn't look at how busy each server currently is. (Source: AWS Elastic Load Balancing docs)",
                     difficulty=1),
                dict(prompt="Before November 2019, which single algorithm did AWS Application Load Balancers use for distributing HTTP/HTTPS traffic?",
                     choices=[("Round robin", True), ("Least outstanding requests", False),
                              ("Weighted random", False), ("Consistent hashing", False)],
                     explanation="AWS added the Least Outstanding Requests algorithm as an alternative in November 2019; round robin was the only option before that. (Source: AWS ELB documentation)",
                     difficulty=2),
                dict(prompt="Least-connections (a.k.a. least-outstanding-requests) load balancing tends to outperform round robin for which kind of traffic?",
                     choices=[("Long-lived connections like WebSockets or gRPC streams", True), ("One-off DNS lookups", False),
                              ("Static file downloads under 1KB", False), ("Health check pings", False)],
                     explanation="When connections stay open for a while, least-connections naturally avoids piling more work onto an already-busy server, which round robin can't see. (Source: AWS load-balancing guidance)",
                     difficulty=2),
                dict(prompt="Which of the following are legitimate reasons a load balancer might route a new request away from a particular server? (select all that apply)",
                     kind='multi',
                     choices=[("The server currently has more open connections than its peers", True), ("The server just failed its health check", True),
                              ("The server's hostname sorts alphabetically last", False), ("The server was the first one registered in the pool", False)],
                     explanation="Connection count (least-connections routing) and health status are real signals load balancers use; hostname order and registration order are not. (Source: AWS ELB target health docs)",
                     difficulty=2),
                dict(prompt="What does a Network Load Balancer's passive health check do that its active health check alone does not?",
                     choices=[("Detects an unhealthy target faster, by observing real connection behavior", True), ("Encrypts traffic between the load balancer and the target", False),
                              ("Replaces the need for DNS resolution", False), ("Balances traffic across separate AWS regions", False)],
                     explanation="Passive health checks watch how targets actually respond to live connections, catching failures before the next scheduled active check would. (Source: AWS Network Load Balancer docs)",
                     difficulty=3),
                dict(prompt="Per AWS's target health documentation, when does a newly registered server start receiving traffic from the load balancer?",
                     choices=[("Only after it passes its initial health checks", True), ("Immediately upon registration, health checks run afterward", False),
                              ("Only after a manual approval step", False), ("After exactly 24 hours, regardless of health", False)],
                     explanation="Registration alone isn't enough — the target must first pass the configured health checks before traffic is routed to it. (Source: AWS ELB docs)",
                     difficulty=1),

                # Caching
                dict(prompt="Which cache eviction policy removes the item that was accessed longest ago when the cache is full?",
                     choices=[("LRU (Least Recently Used)", True), ("LFU (Least Frequently Used)", False),
                              ("FIFO (First In First Out)", False), ("Random replacement", False)],
                     explanation="LRU tracks access recency and evicts whatever hasn't been touched in the longest time. (Source: Redis/AWS caching docs)",
                     difficulty=1),
                dict(prompt="Which cache eviction policy removes the item with the fewest total accesses, regardless of how recently it was used?",
                     choices=[("LFU (Least Frequently Used)", True), ("LRU (Least Recently Used)", False),
                              ("TTL expiry", False), ("Write-through", False)],
                     explanation="LFU counts accesses over time and evicts the least-accessed item, which can outperform LRU when a few items get occasional bursts of traffic. (Source: Redis engineering blog)",
                     difficulty=2),
                dict(prompt="What eviction policy does Amazon ElastiCache for Redis use by default?",
                     choices=[("volatile-lru — evict least-recently-used keys that have a TTL set", True), ("allkeys-lfu — evict least-frequently-used keys across the whole cache", False),
                              ("no-eviction — refuse new writes once the cache is full", False), ("allkeys-random — evict a uniformly random key", False)],
                     explanation="ElastiCache for Redis defaults to volatile-lru, which only considers keys that have an expiration set. (Source: AWS ElastiCache/Redis caching whitepaper)",
                     difficulty=3),
                dict(prompt="In the cache-aside (lazy-loading) pattern, what happens on a cache miss?",
                     choices=[("The application reads from the database, then writes the result into the cache", True), ("The cache automatically fetches from the database on its own", False),
                              ("The request fails until the cache is manually refreshed", False), ("The database is bypassed entirely for that request", False)],
                     explanation="Cache-aside puts the application in charge: on a miss it goes to the database itself and populates the cache for next time. (Source: AWS caching best practices)",
                     difficulty=1),
                dict(prompt="What's the defining trade-off of a write-through cache compared to cache-aside?",
                     choices=[("Every write goes to the cache and the database together, keeping them in sync at the cost of extra write latency", True), ("Writes only ever touch the cache; the database is updated later in a separate background batch job", False),
                              ("Reads are always served from the database and the cache is never consulted for any read operation", False), ("The entire cache is invalidated and rebuilt from scratch every time any single write occurs", False)],
                     explanation="Write-through keeps cache and database consistent by writing to both on every update, which adds latency to writes in exchange for read consistency. (Source: AWS caching best practices)",
                     difficulty=2),
                dict(prompt="Which of the following are valid cache eviction policies offered by Amazon ElastiCache for Redis? (select all that apply)",
                     kind='multi',
                     choices=[("allkeys-lru", True), ("volatile-ttl", True),
                              ("write-behind", False), ("read-through-random", False)],
                     explanation="ElastiCache exposes several real Redis eviction policies including allkeys-lru and volatile-ttl; 'write-behind' and 'read-through-random' aren't eviction policies at all. (Source: AWS ElastiCache documentation)",
                     difficulty=3),
                dict(prompt="Why might an engineer set a TTL (time-to-live) on cached entries even when using an LRU eviction policy?",
                     choices=[("To guarantee stale data eventually gets refreshed, independent of how often it's accessed", True), ("Because LRU cannot function without a TTL configured", False),
                              ("To make the cache evict the most recently used item first", False), ("Because TTL is required for the cache to accept writes", False)],
                     explanation="LRU only reacts to access patterns — a popular-but-stale key could stay cached forever without a TTL forcing a refresh. (Source: Redis/AWS caching docs)",
                     difficulty=2),

                # CDN
                dict(prompt="What does a CDN edge server do when it receives a request for content it already has cached?",
                     choices=[("Responds directly with the cached copy, without contacting the origin server", True), ("Forwards every request to the origin server regardless of cache state", False),
                              ("Redirects the client to the origin server's IP address", False), ("Discards the cached copy and fetches a fresh one every time", False)],
                     explanation="Serving straight from the edge cache is the whole point of a CDN — it avoids a round trip to the origin for content that's already local. (Source: Cloudflare CDN docs)",
                     difficulty=1),
                dict(prompt="What happens when a CDN edge server does NOT have the requested content cached (a cache miss)?",
                     choices=[("It fetches the content from the origin server, serves it, and caches it for future requests", True), ("It returns a 404 Not Found error directly to the client without contacting the origin", False),
                              ("It queries every other edge server in the network simultaneously before contacting the origin", False), ("It permanently blocks that piece of content from ever being cached at any edge location", False)],
                     explanation="A miss triggers a fetch from the origin; the edge server then caches the response so the next nearby request is a hit. (Source: Cloudflare CDN docs)",
                     difficulty=1),
                dict(prompt="What is the primary latency benefit a CDN provides to end users?",
                     choices=[("Content is served from a server geographically close to the user instead of a single distant origin", True), ("It permanently increases the origin server's CPU and memory capacity for handling requests", False),
                              ("It replaces the need for a database entirely by storing all application data at the edge", False), ("It encrypts data at rest on the origin server, which is unrelated to response speed", False)],
                     explanation="By caching content at many edge locations worldwide, a CDN cuts the physical distance (and round-trip time) between the user and the server answering the request. (Source: Cloudflare CDN docs)",
                     difficulty=1),
                dict(prompt="Besides lowering latency, which of these are benefits commonly attributed to using a CDN? (select all that apply)",
                     kind='multi',
                     choices=[("Reduced bandwidth usage on the origin server", True), ("Reduced CPU load on the origin server", True),
                              ("Guaranteed elimination of all cache invalidation bugs", False), ("Automatic horizontal scaling of the origin database", False)],
                     explanation="CDNs offload both bandwidth and CPU from the origin by absorbing repeat requests at the edge; they don't touch the origin's database scaling and cache invalidation is still a real problem to manage. (Source: Cloudflare CDN docs)",
                     difficulty=2),

                # DNS load balancing
                dict(prompt="How does round-robin DNS distribute load across multiple servers?",
                     choices=[("It returns a different IP address from a rotating list each time the domain is queried", True), ("It inspects each server's current CPU load before answering", False),
                              ("It always returns the IP address of the nearest server", False), ("It requires a dedicated load balancer appliance to function", False)],
                     explanation="Round-robin DNS is just the DNS server cycling through a list of A records — it has no visibility into server load at all. (Source: Cloudflare / Wikipedia round-robin DNS docs)",
                     difficulty=1),
                dict(prompt="What is a well-known limitation of round-robin DNS as a load-balancing technique?",
                     choices=[("DNS and client-side caching can pin a client to one IP far longer than intended, unevening the load", True), ("It cannot be used with IPv4 addresses at all, only with IPv6-based DNS records", False),
                              ("It requires every server in the pool to share the exact same hostname and certificate", False), ("It only works for UDP-based protocols and fails for any TCP-based application traffic", False)],
                     explanation="Because resolvers and clients cache DNS answers, round-robin's rotation doesn't translate into even real-time load distribution. (Source: Cloudflare round-robin DNS docs)",
                     difficulty=2),
                dict(prompt="What does anycast routing let a DNS provider like Cloudflare do?",
                     choices=[("Route a user's query to the nearest available server sharing the same announced IP address", True), ("Guarantee that every query returns the exact same physical server every single time", False),
                              ("Encrypt DNS queries end-to-end by default without any additional configuration", False), ("Replace the need for a CDN entirely by caching content inside the DNS resolver itself", False)],
                     explanation="Anycast lets many physical servers around the world answer for the same IP; network routing sends each query to whichever one is topologically closest. (Source: Cloudflare anycast docs)",
                     difficulty=2),
                dict(prompt="Compared to simple round-robin DNS, what extra capability does a service like AWS Route 53 or Cloudflare Load Balancing add?",
                     choices=[("Weighted and geo-aware routing decisions, plus automatic failover away from unhealthy endpoints", True), ("The ability to skip DNS resolution completely, connecting clients directly by raw IP", False),
                              ("Guaranteed sub-millisecond latency for every user worldwide, regardless of physical distance", False), ("Elimination of the need for any health checks anywhere in the routing pipeline", False)],
                     explanation="Managed DNS load balancers go beyond plain rotation — they can weight traffic, route by geography, and pull unhealthy endpoints out of rotation automatically. (Source: Cloudflare / AWS load balancing docs)",
                     difficulty=2),

                # Availability / SLA "nines"
                dict(prompt="Roughly how much downtime per year does 99.9% ('three nines') availability allow?",
                     choices=[("About 8.76 hours", True), ("About 52 minutes", False),
                              ("About 5 minutes", False), ("About 1 hour", False)],
                     explanation="99.9% availability allows roughly 8 hours and 46 minutes of downtime per year — each additional nine cuts that allowance by about 10x. (Source: Wikipedia 'Five nines')",
                     difficulty=2),
                dict(prompt="Roughly how much downtime per year does 99.99% ('four nines') availability allow?",
                     choices=[("About 52.6 minutes", True), ("About 8.76 hours", False),
                              ("About 5.3 minutes", False), ("About 26 minutes", False)],
                     explanation="Four nines allows roughly 52 minutes of downtime a year — one order of magnitude tighter than three nines. (Source: Wikipedia 'Five nines')",
                     difficulty=2),
                dict(prompt="Roughly how much downtime per year does 99.999% ('five nines') availability allow?",
                     choices=[("About 5.26 minutes", True), ("About 52.6 minutes", False),
                              ("About 8.76 hours", False), ("About 1 minute", False)],
                     explanation="Five nines is often called the gold standard for telecom/financial/healthcare systems, allowing only about 5 minutes of downtime a year. (Source: Wikipedia 'Five nines')",
                     difficulty=2),
                dict(prompt="What's the general relationship between adding one more '9' to an availability target and its allowed downtime?",
                     choices=[("Each additional nine reduces allowed downtime by roughly a factor of 10", True), ("Each additional nine doubles the allowed downtime", False),
                              ("Each additional nine has no effect on allowed downtime", False), ("Each additional nine reduces allowed downtime by a fixed 10 minutes", False)],
                     explanation="Going from 99.9% to 99.99% to 99.999% each time divides the yearly downtime budget by about 10. (Source: Wikipedia 'Five nines')",
                     difficulty=1),
                dict(prompt="Which availability tier is described as the de-facto standard SLA for most SaaS products?",
                     choices=[("99.9% (three nines)", True), ("99% (two nines)", False),
                              ("99.999% (five nines)", False), ("100% (zero downtime)", False)],
                     explanation="Three nines is the common baseline SLA offered by most SaaS products; five nines is reserved for telecom/financial/healthcare-grade systems. (Source: industry SLA references)",
                     difficulty=1),

                # Horizontal vs vertical scaling & statelessness
                dict(prompt="What does vertical scaling ('scaling up') mean, per cloud provider architecture guidance?",
                     choices=[("Increasing the capacity of an individual resource, e.g. a bigger VM or higher database tier", True), ("Adding more instances of the same resource so load is spread across all of them", False),
                              ("Moving a workload to run in a different geographic region for lower latency", False), ("Replacing a relational database with a NoSQL one to raise write throughput", False)],
                     explanation="Vertical scaling means making one unit bigger/stronger, as opposed to horizontal scaling which adds more units. (Source: AWS/Azure Well-Architected Framework)",
                     difficulty=1),
                dict(prompt="Why does horizontal scaling typically require an application to be stateless, or to externalize its state?",
                     choices=[("Because any request must be servable by any instance, with no dependency on data stored on one server", True), ("Because stateless services always execute every request faster than any stateful service can", False),
                              ("Because horizontal scaling technically only works when there is a single running server instance", False), ("Because application state can only ever be stored inside a CDN's edge cache layer", False)],
                     explanation="If a server keeps request-relevant state only in its own memory/disk, routing a later request to a different server would lose that state — so scaling out cleanly needs state to live somewhere shared. (Source: AWS Well-Architected Framework)",
                     difficulty=2),
                dict(prompt="Per AWS's Well-Architected guidance, what's a key operational trade-off of vertical scaling compared to horizontal scaling?",
                     choices=[("Automating vertical scaling requires extra custom tooling and can cause downtime during the resize", True), ("Vertical scaling is always fully automatic and never causes any downtime during a resize", False),
                              ("Vertical scaling requires no application code changes under any circumstances", False), ("Vertical scaling is always the cheaper option compared to horizontal scaling", False)],
                     explanation="Resizing a single resource up often means a restart or migration step, and automating that safely takes more custom work than adding/removing horizontal instances. (Source: AWS Well-Architected Framework)",
                     difficulty=2),
                dict(prompt="Which compute resources are commonly cited as naturally stateless, letting any instance service any request?",
                     choices=[("EC2 instances behind a load balancer and AWS Lambda functions", True), ("A single on-premises database server", False),
                              ("A developer's local laptop", False), ("A physical office file server", False)],
                     explanation="Stateless compute like load-balanced EC2 fleets or Lambda functions can serve any request interchangeably, which is what makes them easy to scale horizontally. (Source: AWS Well-Architected Framework)",
                     difficulty=1),
                dict(prompt="Which of the following are genuine benefits of horizontal scaling over vertical scaling, per cloud architecture guidance? (select all that apply)",
                     kind='multi',
                     choices=[("Better resilience — losing one instance doesn't take down the whole system", True), ("Easier to automate scaling up and down with demand", True),
                              ("Guaranteed lower cost at every possible scale", False), ("Removes the need for a load balancer", False)],
                     explanation="Horizontal scaling spreads risk across many replaceable instances and is generally easier to automate; it doesn't guarantee lower cost at all scales, and it actually needs a load balancer to work. (Source: AWS/Azure Well-Architected Framework)",
                     difficulty=2),
                dict(prompt="Why might a team choose vertical scaling for a stateful component even though horizontal scaling is generally more flexible?",
                     choices=[("Because that component has dependencies or stored state that make splitting it across instances impractical", True), ("Because vertical scaling is legally required for any service classified as stateful", False),
                              ("Because horizontal scaling is fundamentally incompatible with public cloud providers", False), ("Because stateful components are technically incapable of being scaled in any direction", False)],
                     explanation="Some components (e.g. certain databases) aren't easily distributed, so growing the single instance can be the pragmatic choice despite horizontal scaling's usual advantages. (Source: AWS Well-Architected Framework)",
                     difficulty=2),

                # Sharding / horizontal partitioning
                dict(prompt="What does it mean to 'shard' a database?",
                     choices=[("Split its data horizontally into smaller chunks distributed across multiple servers", True), ("Make a complete backup copy of the entire database onto one additional server", False),
                              ("Compress the database's stored data so it uses less physical disk space", False), ("Encrypt the database's contents at rest to protect it from unauthorized access", False)],
                     explanation="Sharding splits data horizontally (by rows, not columns) so each shard holds a subset of the overall dataset. (Source: MongoDB sharding documentation)",
                     difficulty=1),
                dict(prompt="What is the main motivation for sharding a database, per MongoDB's own documentation?",
                     choices=[("Supporting very large datasets and high throughput that a single server can't handle", True), ("Making application queries noticeably simpler and shorter for developers to write", False),
                              ("Avoiding the need to create and maintain indexes on any collection", False), ("Guaranteeing strong consistency across every replica in the cluster at all times", False)],
                     explanation="Sharding exists specifically to scale out storage and throughput beyond what one machine can provide. (Source: MongoDB sharding documentation)",
                     difficulty=1),
                dict(prompt="In a sharded database cluster, how is read and write workload typically handled?",
                     choices=[("Distributed across shards, with each shard processing only a subset of overall operations", True), ("Every single operation is broadcast to every shard in the cluster for redundancy", False),
                              ("All writes are routed to one designated shard while reads go to a separate shard", False), ("Sharding only ever affects read operations and has no effect on writes at all", False)],
                     explanation="Each shard owns a slice of the data and handles the operations that touch its slice, which is how sharding actually spreads out load. (Source: MongoDB sharding documentation)",
                     difficulty=2),
                dict(prompt="How does adding more shards to a cluster affect its scaling model?",
                     choices=[("Both read and write workloads can be scaled horizontally by adding more shards", True), ("Only read workload benefits; writes stay bottlenecked on one shard", False),
                              ("Only write workload benefits; reads stay bottlenecked on one shard", False), ("Adding shards has no effect on throughput, only on storage", False)],
                     explanation="More shards means more machines sharing both the read and the write load, not just extra storage capacity. (Source: MongoDB sharding documentation)",
                     difficulty=2),

                # More latency numbers (Jeff Dean's list — different entries than
                # the SSD-vs-memory and cross-continent ones already asked above)
                dict(prompt="In Jeff Dean's classic 'latency numbers every programmer should know', roughly how long does an L1 cache reference take?",
                     choices=[("About 0.5 nanoseconds", True), ("About 100 nanoseconds", False),
                              ("About 10 microseconds", False), ("About 1 millisecond", False)],
                     explanation="L1 cache is the fastest thing on the list — about half a nanosecond, roughly 200x faster than a main memory reference. (Source: Jeff Dean's 'Numbers Everyone Should Know')",
                     difficulty=2),
                dict(prompt="Roughly how much slower is an L2 cache reference than an L1 cache reference, per Jeff Dean's numbers?",
                     choices=[("Roughly 14x slower (about 7ns vs 0.5ns)", True), ("Roughly 2x slower", False),
                              ("Roughly 1000x slower", False), ("They're about the same speed", False)],
                     explanation="L2 cache reference (~7ns) is meaningfully slower than L1 (~0.5ns) but still vastly faster than main memory (~100ns). (Source: Jeff Dean's 'Numbers Everyone Should Know')",
                     difficulty=3),
                dict(prompt="What operation does Jeff Dean's latency table list at roughly 25 nanoseconds?",
                     choices=[("A mutex lock/unlock", True), ("A main memory reference", False),
                              ("An SSD random read", False), ("A datacenter round trip", False)],
                     explanation="Mutex lock/unlock sits between a branch mispredict (~5ns) and a main memory reference (~100ns) on the classic latency table. (Source: Jeff Dean's 'Numbers Everyone Should Know')",
                     difficulty=3),
                dict(prompt="Per Jeff Dean's numbers, roughly how long does it take to compress 1KB of data with a fast compressor (e.g. Zippy/Snappy)?",
                     choices=[("About 3 microseconds", True), ("About 3 nanoseconds", False),
                              ("About 3 milliseconds", False), ("About 3 seconds", False)],
                     explanation="Compressing 1KB with a fast compressor lands around 3,000 nanoseconds (3 microseconds) — fast, but far slower than a raw memory reference. (Source: Jeff Dean's 'Numbers Everyone Should Know')",
                     difficulty=3),
                dict(prompt="Which of these operations are on the order of milliseconds, per Jeff Dean's classic latency table? (select all that apply)",
                     kind='multi',
                     choices=[("A disk seek on a spinning drive", True), ("Reading 1MB sequentially from a spinning disk", True),
                              ("An L1 cache reference", False), ("A mutex lock/unlock", False)],
                     explanation="A disk seek (~10ms) and a 1MB sequential spinning-disk read (~20ms) are both millisecond-scale; L1 cache (~0.5ns) and a mutex lock (~25ns) are nanosecond-scale — many orders of magnitude faster. (Source: Jeff Dean's 'Numbers Everyone Should Know')",
                     difficulty=2),
             ]),
    ),

    # --- System design item: unchanged ---
    dict(book='system-design-interview-xu', slug='rate-limiter', title='Design a Rate Limiter',
         topic=TOPIC_PATTERNS, difficulty=1,
         order=2, unlock_level=2, summary='Throttling clients to protect your APIs from abuse and overload.',
         concept=dict(
            slug='rate-limiting-algorithms', title='Rate Limiting Algorithms',
            source_note='Chapter 4: Design a Rate Limiter',
            summary=(
                "How to cap how many requests a client can make in a given window — and the four classic "
                "algorithms for doing it, each with a different trade-off."
            ),
            notes=[
                dict(heading="Why Rate Limit at All?",
                     body=(
                        "Alex Xu's Chapter 4 frames rate limiting as protection, not just fairness: without a "
                        "limit, a buggy client (a retry loop with no backoff), a scraper, or an outright DDoS "
                        "attack can consume enough capacity to degrade service for everyone else, or run up a "
                        "huge cloud bill on auto-scaled infrastructure. A rate limiter sits in front of the "
                        "application and rejects (or delays) requests once a client crosses a threshold — "
                        "e.g. 100 requests per minute per API key — usually responding with HTTP 429 Too Many "
                        "Requests so well-behaved clients know to back off."
                     )),
                dict(heading="The Four Classic Algorithms",
                     body=(
                        "Token bucket: a bucket holds up to N tokens and refills at a fixed rate; each request "
                        "consumes one token, and the request is rejected if the bucket is empty. It's simple, "
                        "memory-efficient (just a counter and a timestamp per client), and — crucially — it "
                        "allows short bursts up to the bucket size, which matches real traffic patterns better "
                        "than a hard steady-rate cap.\n\n"
                        "Leaky bucket: the mirror image — requests queue up in a fixed-size buffer and are "
                        "drained (processed) at a constant rate, like water leaking from a bucket at a fixed "
                        "rate no matter how fast it's poured in. This smooths bursts into a steady output rate, "
                        "but a burst that overflows the queue is dropped outright rather than allowed through.\n\n"
                        "Fixed window counter: count requests in discrete windows (e.g. one counter per "
                        "minute, reset every minute). It's the simplest to implement, but has a real weakness "
                        "at window boundaries (see the deep dive below).\n\n"
                        "Sliding window log (or counter): keep a timestamp for every request (log variant) or "
                        "a weighted blend of the current and previous window's counts (counter variant), so "
                        "the 'window' is always exactly the last N seconds rather than a fixed clock-aligned "
                        "bucket. This is the most accurate of the four, at the cost of more memory (the log "
                        "variant) or a bit more bookkeeping (the counter variant)."
                     ),
                     deep_dive=dict(
                        title="The fixed window counter's boundary problem",
                        body=(
                            "Say the limit is 5 requests/minute, counted in clock-aligned windows (12:00:00-"
                            "12:00:59, 12:01:00-12:01:59, ...). A client could send 5 requests at 12:00:59 and "
                            "another 5 at 12:01:00 — ten requests in two seconds, twice the intended rate — "
                            "and the fixed window counter would allow every one of them, because each burst "
                            "landed in a different window and neither window individually exceeded its limit. "
                            "This is exactly the failure mode sliding window approaches are designed to close."
                        ),
                     )),
                dict(heading="Where It Lives in the Architecture",
                     body=(
                        "Rate limiters are usually implemented at the edge — an API gateway or dedicated "
                        "middleware layer — so abusive requests get rejected before they reach (and burn "
                        "capacity on) the actual application servers. Limits can be scoped differently "
                        "depending on the goal: per-user or per-API-key for fairness and billing tiers, "
                        "per-IP to blunt anonymous abuse, or per-endpoint since a search or login endpoint is "
                        "usually far more expensive per-request than a static asset fetch. In a distributed "
                        "deployment with many gateway instances, the counters themselves typically live in a "
                        "shared fast store like Redis, so all instances agree on how many requests a client "
                        "has already used."
                     )),
            ],
            questions=[
                dict(prompt="Which rate-limiting algorithm is known for allowing short bursts of traffic while still enforcing a long-term average rate?",
                     choices=[("Fixed window counter", False), ("Token bucket", True),
                              ("None — all algorithms forbid bursts", False), ("Round robin", False)],
                     explanation="Token bucket lets a client burst up to the bucket size, then throttles to the refill rate.",
                     difficulty=2),
                dict(prompt="What is a known weakness of the fixed window counter algorithm?",
                     choices=[("It uses too much memory", False),
                              ("It can allow up to 2x the intended rate right at window boundaries", True),
                              ("It cannot be distributed across servers", False),
                              ("It requires a database", False)],
                     explanation="Traffic clustered at the edges of two adjacent windows can spike to nearly double the allowed rate.",
                     difficulty=3),
                dict(prompt="Where is a rate limiter most commonly implemented in a web architecture?",
                     choices=[("Inside the client's mobile app only", False),
                              ("At the API gateway / middleware layer", True),
                              ("Only inside the database", False),
                              ("In the DNS server", False)],
                     explanation="Rate limiting is typically enforced server-side at the gateway, before requests reach backend services.",
                     difficulty=1),
                dict(prompt="What is a key downside of the sliding window log algorithm compared to a fixed window counter?",
                     choices=[("It allows unlimited requests", False),
                              ("It requires storing a timestamp for every request, using more memory", True),
                              ("It cannot run across multiple servers", False),
                              ("It ignores burst traffic entirely", False)],
                     explanation="Storing every request's timestamp gives precise limiting but costs memory proportional to traffic volume.",
                     difficulty=2),
                dict(prompt="In a distributed system, why is a centralized store like Redis often used to enforce rate limits across multiple servers?",
                     choices=[("Redis is required by the HTTP spec", False),
                              ("So all servers share the same counter state instead of each enforcing limits independently", True),
                              ("Redis encrypts requests automatically", False),
                              ("It removes the need for an API gateway", False)],
                     explanation="Without a shared store, each server would track its own count, letting a client multiply its effective limit by hitting different servers.",
                     difficulty=2),
                dict(prompt="What HTTP status code is conventionally returned when a client exceeds its rate limit?",
                     choices=[("404 Not Found", False), ("429 Too Many Requests", True),
                              ("500 Internal Server Error", False), ("302 Found", False)],
                     explanation="429 is the standard HTTP status for 'you've sent too many requests in a given time'.",
                     difficulty=1),
                dict(prompt="Why might a rate limiter apply different limits per API endpoint rather than one global limit?",
                     choices=[("Because all endpoints have identical cost, so it doesn't matter", False),
                              ("Because some endpoints (e.g. search, login) are more expensive or abuse-prone than others", True),
                              ("Because HTTP requires per-endpoint limits", False),
                              ("Because a single global limit is illegal under REST conventions", False)],
                     explanation="A cheap read endpoint and an expensive write or auth endpoint often warrant very different thresholds.",
                     difficulty=2),

                # --- Added from verified web sources: IETF drafts, nginx docs, AWS docs ---
                dict(prompt="Are the widely-used X-RateLimit-Limit / X-RateLimit-Remaining headers defined in any official RFC?",
                     choices=[("No — they're a de facto convention, not standardized in any RFC", True), ("Yes — RFC 6585 defines them precisely", False),
                              ("Yes — they were standardized alongside HTTP/1.1 itself", False), ("Yes — they're mandatory fields in the HTTP spec", False)],
                     explanation="The X-RateLimit-* headers are a widely-copied convention, but different APIs implement their exact semantics differently since no RFC ever pinned them down. (Source: IETF httpapi working group draft)",
                     difficulty=2),
                dict(prompt="What is the goal of the IETF's draft-ietf-httpapi-ratelimit-headers effort?",
                     choices=[("Replace the inconsistent X-RateLimit-* headers with standardized RateLimit and RateLimit-Policy fields", True), ("Remove all rate-limit information from HTTP responses so clients can't see their quota", False),
                              ("Require every API to implement exactly the token bucket algorithm and no other", False), ("Mandate that no API's rate limit can ever exceed 100 requests per minute", False)],
                     explanation="The draft defines two standardized fields, RateLimit and RateLimit-Policy, so clients can rely on one consistent format instead of guessing each API's X-RateLimit-* convention. (Source: IETF httpapi working group draft)",
                     difficulty=2),
                dict(prompt="Which rate-limiting algorithm does nginx's ngx_http_limit_req_module implement?",
                     choices=[("Leaky bucket", True), ("Token bucket", False),
                              ("Fixed window counter", False), ("Sliding window log", False)],
                     explanation="nginx's own documentation describes limit_req as based on the leaky bucket method: requests arrive at various rates but leave (are processed) at a fixed rate. (Source: nginx.org ngx_http_limit_req_module docs)",
                     difficulty=1),
                dict(prompt="In nginx's limit_req_zone directive, what does the configured 'rate' parameter (e.g. rate=1r/s) control?",
                     choices=[("The fixed rate at which queued requests are allowed to leave the bucket and be processed", True), ("The maximum number of concurrent client connections the server will accept", False),
                              ("The number of nginx worker processes spawned to handle incoming requests", False), ("The TTL (time-to-live) applied to every cached static asset on disk", False)],
                     explanation="The rate parameter sets how fast the leaky bucket drains — e.g. rate=1r/s processes at most one request per second, delaying the rest. (Source: nginx.org ngx_http_limit_req_module docs)",
                     difficulty=2),
                dict(prompt="In AWS API Gateway's token-bucket throttling model, what does the configured 'burst' limit represent?",
                     choices=[("The maximum capacity of the token bucket — concurrent requests it can absorb before returning 429s", True), ("The total number of requests an API is allowed to receive per calendar month", False),
                              ("The number of Lambda functions that can be invoked per second by clients", False), ("The maximum size in megabytes allowed for a single request payload body", False)],
                     explanation="The burst limit is literally the bucket's token capacity: once it's drained faster than it refills, further requests get HTTP 429 Too Many Requests. (Source: AWS API Gateway throttling documentation)",
                     difficulty=2),
                dict(prompt="What is AWS API Gateway's default account-level steady-state request rate limit per AWS Region?",
                     choices=[("10,000 requests per second", True), ("100 requests per second", False),
                              ("1,000,000 requests per second", False), ("1 request per second", False)],
                     explanation="Unless increased, API Gateway defaults to a 10,000 RPS steady-state limit (and a 5,000 burst limit) per account, per Region. (Source: AWS API Gateway throttling documentation)",
                     difficulty=3),
                dict(prompt="What is AWS API Gateway's default account-level burst limit per AWS Region?",
                     choices=[("5,000 requests", True), ("500 requests", False),
                              ("50,000 requests", False), ("Unlimited by default", False)],
                     explanation="The default burst (token bucket capacity) is 5,000 requests, separate from the 10,000 RPS steady-state refill rate. (Source: AWS API Gateway throttling documentation)",
                     difficulty=3),
                dict(prompt="Which of the following are genuine properties of AWS API Gateway's throttling model? (select all that apply)",
                     kind='multi',
                     choices=[("It refills tokens at a configured steady-state rate every second", True), ("Exceeding the token supply results in an HTTP 429 response", True),
                              ("It requires every client to pre-register a fixed IP address", False), ("It only throttles requests originating from outside AWS", False)],
                     explanation="API Gateway's throttling is a straightforward token-bucket: tokens refill at the rate limit, and running out yields 429s; there's no IP pre-registration requirement or AWS-origin exemption. (Source: AWS API Gateway throttling documentation)",
                     difficulty=2),
                dict(prompt="Without the 'nodelay' option, what does nginx's limit_req do with a request that exceeds the configured rate but still fits within the burst allowance?",
                     choices=[("Queues and delays it so the overall processing rate stays at the configured limit", True), ("Immediately rejects it with a 429 response", False),
                              ("Silently drops it without any response at all", False), ("Processes it instantly, ignoring the configured rate", False)],
                     explanation="By default limit_req queues excess requests up to the burst size and delays them, rather than rejecting outright — nodelay changes this to reject immediately instead. (Source: nginx.org ngx_http_limit_req_module docs)",
                     difficulty=3),
                dict(prompt="Per the IETF draft, what two header fields does the modern RateLimit proposal define, replacing the old X-RateLimit-* trio?",
                     choices=[("RateLimit and RateLimit-Policy", True), ("X-Limit and X-Remaining", False),
                              ("Retry-After and Rate-Status", False), ("Quota-Limit and Quota-Used", False)],
                     explanation="The current draft consolidated what used to be three separate X-RateLimit-* headers down to just RateLimit (current status) and RateLimit-Policy (the quota policy). (Source: IETF httpapi working group draft)",
                     difficulty=3),
             ]),
    ),
    dict(book='system-design-interview-xu', slug='consistent-hashing', title='Design Consistent Hashing',
         topic=TOPIC_PATTERNS, difficulty=2,
         order=3, unlock_level=2, summary='Distributing data across servers without a total reshuffle when nodes change.',
         concept=dict(
            slug='consistent-hashing-core', title='Consistent Hashing & Virtual Nodes',
            source_note='Chapter 5: Design Consistent Hashing',
            summary=(
                "Why naive hash-mod-N sharding falls apart when servers come and go, and how putting "
                "servers and keys on a ring fixes it."
            ),
            notes=[
                dict(heading="The Problem With Naive Hashing",
                     body=(
                        "The obvious way to shard data across N servers is server = hash(key) % N. It works "
                        "fine — until N changes. Add or remove a single server and N changes, which means "
                        "almost every key's hash(key) % N result changes too, so nearly the entire dataset "
                        "has to move between servers all at once. Alex Xu's Chapter 5 opens with exactly this "
                        "scenario: a cache cluster that, on losing one server, effectively invalidates itself "
                        "entirely — a 'cache stampede' where every request suddenly misses and hammers the "
                        "database at once."
                     )),
                dict(heading="Placing Servers and Keys on a Ring",
                     body=(
                        "Consistent hashing fixes this by hashing servers and keys into the same circular "
                        "keyspace (imagine a clock face, 0 to 2^32-1, that wraps back to 0). Each server "
                        "occupies one or more points on this ring; a key belongs to whichever server's point "
                        "is the first one found going clockwise from the key's own hashed position. The "
                        "payoff: removing a server only reassigns the keys that were mapped to it — they "
                        "simply fall through to the next server clockwise — and adding a server only claims "
                        "keys from its immediate neighborhood. Every other server, and every other key, is "
                        "completely undisturbed."
                     )),
                dict(heading="Virtual Nodes Smooth Out Hot Spots",
                     body=(
                        "One physical server occupying a single point on the ring can still end up owning a "
                        "disproportionate arc of the keyspace just by chance — a 'hot spot'. The fix is "
                        "virtual nodes: instead of one point per physical server, each server is given many "
                        "(e.g. 100-200) points scattered around the ring. Now each physical machine's share of "
                        "the keyspace is the sum of many small, scattered arcs rather than one large one, "
                        "which averages out to a much more even distribution — and also means that when a "
                        "server is removed, its load gets spread across many other servers instead of dumping "
                        "it all onto whichever single server happened to be its ring neighbor."
                     ),
                     deep_dive=dict(
                        title="Real systems that use this",
                        body=(
                            "This exact technique — a hash ring plus virtual nodes — underlies Amazon's "
                            "Dynamo paper and is used directly in Apache Cassandra and Riak, among others. "
                            "It's also the basis for client-side sharding in things like memcached client "
                            "libraries, where the client itself decides which cache server a key belongs to "
                            "without any central coordinator, and adding a new memcached node only reshuffles "
                            "a small slice of the keyspace instead of invalidating the whole cache."
                        ),
                     )),
            ],
            questions=[
                dict(prompt="What problem does consistent hashing solve compared to naive hash % N sharding?",
                     choices=[("It makes hashing faster", False),
                              ("It minimizes key remapping when servers are added or removed", True),
                              ("It encrypts the keys", False), ("It removes the need for replication", False)],
                     explanation="With hash % N, changing N remaps almost all keys; consistent hashing only remaps a small neighborhood.",
                     difficulty=2),
                dict(prompt="What are 'virtual nodes' used for in consistent hashing?",
                     choices=[("To encrypt traffic between nodes", False),
                              ("To smooth out uneven key distribution across physical servers", True),
                              ("To reduce the number of physical servers needed", False),
                              ("To replace the need for a hash ring", False)],
                     explanation="Giving each physical server multiple points on the ring avoids hot spots from uneven ring placement.",
                     difficulty=2),
                dict(prompt="On the consistent hashing ring, which server does a given key get assigned to?",
                     choices=[("A random server", False), ("The server with the lowest ID", False),
                              ("The first server found going clockwise from the key's position", True),
                              ("The server closest to the client geographically", False)],
                     explanation="Keys are assigned to the nearest server clockwise on the ring.",
                     difficulty=1),
                dict(prompt="Roughly how many keys need remapping when a server is added to a ring using virtual nodes, compared to naive hash % N?",
                     choices=[("All keys, same as naive hashing", False),
                              ("Only the keys that land between the new positions and their next clockwise neighbor", True),
                              ("None at all, ever", False),
                              ("Exactly half the keyspace, always", False)],
                     explanation="Consistent hashing's whole point is that adding a node only disturbs its local neighborhood on the ring, not the entire keyspace.",
                     difficulty=2),
                dict(prompt="Which real-world systems are commonly cited as using consistent hashing for data distribution?",
                     choices=[("Amazon Dynamo and Apache Cassandra", True),
                              ("Only relational databases like MySQL", False),
                              ("DNS servers exclusively", False),
                              ("Git version control", False)],
                     explanation="Both Dynamo and Cassandra popularized consistent hashing (with virtual nodes) as a core building block.",
                     difficulty=1),
                dict(prompt="What is a potential downside of using too few virtual nodes per physical server?",
                     choices=[("Lookups become impossible", False),
                              ("Uneven key distribution / hot spots can persist", True),
                              ("It eliminates the need for a hash function", False),
                              ("It automatically triggers replication", False)],
                     explanation="Virtual nodes smooth distribution by giving each server many ring positions — too few and the smoothing effect is weak.",
                     difficulty=2),
                dict(prompt="What happens to a key's assigned server if that server is removed from the ring?",
                     choices=[("The key is lost permanently", False),
                              ("The key moves to the next server found clockwise from its position", True),
                              ("All keys on the ring are reshuffled randomly", False),
                              ("The key stays unassigned until a human intervenes", False)],
                     explanation="Removing a server only affects the keys that were mapped to it — they simply fall through to the next server clockwise.",
                     difficulty=1),

                # --- Added from verified web sources: the original 1997 paper, Chord, and Jump Consistent Hash ---
                dict(prompt="What problem was consistent hashing originally introduced to solve, per Karger et al.'s 1997 paper?",
                     choices=[("Relieving hot spots in distributed web caching", True), ("Encrypting traffic between web browsers and servers", False),
                              ("Compressing images for faster web page loads", False), ("Detecting duplicate content across websites", False)],
                     explanation="The 1997 paper, 'Consistent hashing and random trees: Distributed caching protocols for relieving hot spots on the World Wide Web', targeted exactly that hot-spot problem. (Source: ACM STOC 1997, Karger/Lehman/Leighton/Levine/Lewin/Panigrahy)",
                     difficulty=3),
                dict(prompt="The Chord protocol, a well-known application of consistent hashing, organizes its nodes using what structure?",
                     choices=[("A one-dimensional ring with successor pointers", True), ("A two-dimensional grid with neighbor pointers", False),
                              ("A single centralized coordinator node", False), ("An unordered flat list of all nodes", False)],
                     explanation="Chord arranges nodes on a ring and has each node track its 'successor', which is exactly the consistent-hashing ring idea applied to peer-to-peer lookup. (Source: 'Chord: A scalable peer-to-peer lookup protocol', IEEE/ACM ToN 2003)",
                     difficulty=2),
                dict(prompt="Which institution's researchers developed the Chord distributed hash table protocol?",
                     choices=[("MIT", True), ("Stanford", False),
                              ("Carnegie Mellon", False), ("UC Berkeley", False)],
                     explanation="Chord was developed at MIT by Stoica, Morris, Karger, Kaashoek, and Balakrishnan. (Source: 'Chord: A scalable peer-to-peer lookup protocol', IEEE/ACM Transactions on Networking, 2003)",
                     difficulty=3),
                dict(prompt="What is Jump Consistent Hash's main practical advantage over classic ring-based consistent hashing with virtual nodes?",
                     choices=[("It needs essentially no memory and distributes keys more evenly, with no ring data structure to store", True), ("It guarantees that zero keys ever need remapping when a node is removed", False),
                              ("It eliminates the need for any hash function to be computed during lookups", False), ("It only works correctly when there is exactly one server in the entire pool", False)],
                     explanation="Ring-based hashing needs thousands of bytes per shard to get even distribution; Jump Consistent Hash achieves better evenness with essentially no stored state at all. (Source: Lamping & Veach, 'A Fast, Minimal Memory, Consistent Hash Algorithm', 2014)",
                     difficulty=3),
                dict(prompt="What is a stated limitation of Jump Consistent Hash compared to ring-based consistent hashing?",
                     choices=[("Buckets must be numbered sequentially, making it unsuited to arbitrary node IDs in web caching", True), ("It cannot run on any 64-bit computer architecture or operating system", False),
                              ("It only supports a fixed maximum of 256 total buckets in any single cluster", False), ("It requires an active network connection just to compute a lookup", False)],
                     explanation="Because buckets are just integers 0..n-1, removing an arbitrary node by ID (common in distributed caching) doesn't map cleanly onto Jump Consistent Hash the way it does onto a ring. (Source: Lamping & Veach, 'A Fast, Minimal Memory, Consistent Hash Algorithm', 2014)",
                     difficulty=3),
                dict(prompt="Roughly what time complexity does Jump Consistent Hash's core lookup loop run in, for n buckets?",
                     choices=[("O(ln n)", True), ("O(n)", False),
                              ("O(n^2)", False), ("O(1) with no dependence on n at all", False)],
                     explanation="The algorithm's loop executes O(ln n) times — a constant amount faster than the O(log n) binary search a typical ring-hash lookup needs. (Source: Lamping & Veach, 'A Fast, Minimal Memory, Consistent Hash Algorithm', 2014)",
                     difficulty=3),
                dict(prompt="Which company's researchers published the Jump Consistent Hash algorithm?",
                     choices=[("Google", True), ("Amazon", False),
                              ("Microsoft", False), ("Facebook", False)],
                     explanation="Jump Consistent Hash was published by Google researchers John Lamping and Eric Veach in 2014. (Source: 'A Fast, Minimal Memory, Consistent Hash Algorithm')",
                     difficulty=2),
                dict(prompt="What does the abbreviation 'DHT', as used to describe systems like Chord, stand for?",
                     choices=[("Distributed Hash Table", True), ("Dynamic Hashing Technique", False),
                              ("Data Hosting Topology", False), ("Deterministic Hash Tree", False)],
                     explanation="A DHT is a decentralized system that provides a lookup service similar to a hash table, spread across many cooperating nodes — Chord is a classic example. (Source: Chord paper, MIT)",
                     difficulty=1),
                dict(prompt="Which of the following are true of distributed hash tables (DHTs) like Chord? (select all that apply)",
                     kind='multi',
                     choices=[("Each node is responsible for a contiguous range of the hash space", True), ("They provide a decentralized key lookup service across many cooperating nodes", True),
                              ("They require a single always-on coordinator node to route every lookup", False), ("They can only store a fixed, hard-coded number of keys forever", False)],
                     explanation="Chord-style DHTs split the keyspace across nodes and route lookups peer-to-peer with no central coordinator, and they scale to arbitrary numbers of keys. (Source: Chord paper, MIT)",
                     difficulty=2),
                dict(prompt="In what year was the Chord paper, 'A scalable peer-to-peer lookup protocol for internet applications', published in IEEE/ACM Transactions on Networking?",
                     choices=[("2003", True), ("1997", False),
                              ("2010", False), ("1990", False)],
                     explanation="The Chord paper appeared in IEEE/ACM Transactions on Networking, volume 11, in 2003, six years after the original consistent hashing paper. (Source: IEEE/ACM ToN, 2003)",
                     difficulty=3),
             ]),
    ),
    dict(book='system-design-interview-xu', slug='key-value-store', title='Design a Key-Value Store',
         topic=TOPIC_DATA, difficulty=2,
         order=4, unlock_level=3, summary='CAP theorem trade-offs and conflict resolution in distributed storage.',
         concept=dict(
            slug='cap-theorem-quorum', title='CAP Theorem & Quorum Consensus',
            source_note='Chapter 6: Design a Key-Value Store',
            summary=(
                "Why a distributed store can't have it all during a network partition, and how quorum "
                "consensus lets you tune exactly how much consistency you're trading for availability."
            ),
            notes=[
                dict(heading="CAP Theorem: Pick Two, But Not Really",
                     body=(
                        "CAP theorem says a distributed system can only guarantee two of three properties "
                        "while a network partition is happening: Consistency (every read sees the latest "
                        "write, or an error), Availability (every request gets a non-error response, even if "
                        "it's not the latest data), and Partition tolerance (the system keeps functioning "
                        "despite the network splitting nodes apart). Alex Xu's Chapter 6 makes the practical "
                        "point clearly: partition tolerance isn't really a choice in a real distributed "
                        "system — networks do fail — so the actual decision every design has to make is CP "
                        "vs. AP: when a partition happens, do you refuse requests to avoid returning stale "
                        "data (CP), or keep serving requests and risk staleness (AP)?"
                     )),
                dict(heading="Quorum Consensus: Tuning the Trade-off",
                     body=(
                        "Rather than a binary CP/AP choice, systems like Amazon's Dynamo (which favors "
                        "availability) use quorum consensus to make the trade-off a dial instead of a switch. "
                        "With N replicas of each piece of data: a write must be acknowledged by W replicas "
                        "before it's considered successful, and a read queries R replicas and returns the "
                        "most recent value among them. The key relationship is W + R versus N: when "
                        "W + R > N, the read set and write set are mathematically guaranteed to overlap by at "
                        "least one replica, so a read is guaranteed to see the most recent write — strong "
                        "consistency. When W + R <= N, reads and writes can miss each other entirely, "
                        "trading that guarantee for lower latency and higher availability (fewer replicas "
                        "need to respond for an operation to succeed)."
                     ),
                     deep_dive=dict(
                        title="What happens when writes race each other?",
                        body=(
                            "Favoring availability means the system sometimes accepts two writes to the same "
                            "key concurrently, from two different clients, without either one seeing the "
                            "other. Dynamo-style systems detect this with vector clocks — a per-replica "
                            "counter attached to each version of a value that captures its causal history. "
                            "When a read finds multiple versions whose vector clocks don't show one strictly "
                            "descending from the other, the system knows they were genuinely concurrent (not "
                            "just late) and either resolves them automatically (e.g. 'last write wins' by "
                            "timestamp) or hands both versions back to the application to reconcile — the "
                            "classic example being a shopping cart that merges rather than picks one side."
                        ),
                     )),
            ],
            questions=[
                dict(prompt="According to CAP theorem, during a network partition a distributed system must choose between which two properties?",
                     choices=[("Consistency and Availability", True),
                              ("Consistency and Performance", False),
                              ("Availability and Durability", False), ("Partition tolerance and Performance", False)],
                     explanation="Partition tolerance isn't really optional in a real distributed system, so the practical trade-off is C vs A.",
                     difficulty=2),
                dict(prompt="In quorum consensus with N replicas, W writes-acks, and R reads-queried, what condition guarantees strong consistency?",
                     choices=[("W + R < N", False), ("W + R > N", True),
                              ("W = 0", False), ("R = N always", False)],
                     explanation="W + R > N ensures the read set and write set always overlap by at least one replica, so a read sees the latest write.",
                     difficulty=3),
                dict(prompt="What data structure is commonly used to detect and resolve conflicting concurrent writes in a distributed key-value store?",
                     choices=[("B-tree", False), ("Vector clock", True), ("Bloom filter", False), ("Trie", False)],
                     explanation="Vector clocks track causal history per replica, letting the system detect when two writes are genuinely concurrent (conflicting).",
                     difficulty=3),
                dict(prompt="In quorum consensus, what does 'W' represent?",
                     choices=[("The number of replicas that must acknowledge a write", True),
                              ("The number of replicas queried on a read", False),
                              ("The total number of replicas in the cluster", False),
                              ("The number of write conflicts detected", False)],
                     explanation="W is the write quorum size — how many replicas must ack a write before it's considered successful.",
                     difficulty=1),
                dict(prompt="What does W + R <= N favor in a distributed key-value store?",
                     choices=[("Strong consistency at all costs", False),
                              ("Availability and lower latency, at the risk of reading stale data", True),
                              ("Guaranteed zero data loss", False),
                              ("Elimination of vector clocks", False)],
                     explanation="When the read and write sets aren't guaranteed to overlap, reads can be faster/more available but may miss the latest write.",
                     difficulty=2),
                dict(prompt="What is 'sloppy quorum' used for in systems like Dynamo?",
                     choices=[("Ignoring all write requests during a partition", False),
                              ("Temporarily writing to reachable nodes outside the preferred list when some are unavailable, to preserve availability", True),
                              ("Permanently reducing the number of replicas", False),
                              ("Encrypting quorum votes", False)],
                     explanation="Sloppy quorum trades strict replica placement for availability during a partition, reconciling later via hinted handoff.",
                     difficulty=3),
                dict(prompt="Why might two replicas in an AP-favoring system briefly disagree on a value?",
                     choices=[("Because writes are always synchronous", False),
                              ("Because updates propagate asynchronously and a read can hit a replica that hasn't received the latest write yet", True),
                              ("Because CAP theorem forbids replication", False),
                              ("Because vector clocks prevent all conflicts", False)],
                     explanation="Favoring availability generally means writes are acknowledged before every replica has them, so brief staleness is expected.",
                     difficulty=2),
             ]),
    ),
    dict(book='system-design-interview-xu', slug='unique-id-generator', title='Design a Unique ID Generator',
         topic=TOPIC_PATTERNS, difficulty=2,
         order=5, unlock_level=3, summary='Generating globally unique, roughly sortable IDs at scale.',
         concept=dict(
            slug='snowflake-ids', title='Snowflake-Style ID Generation',
            source_note='Chapter 7: Design a Unique ID Generator in Distributed Systems',
            summary=(
                "Why auto-increment IDs stop working once you shard your database, and how Twitter's "
                "Snowflake scheme generates unique, roughly-ordered IDs with zero coordination."
            ),
            notes=[
                dict(heading="Why Auto-Increment Breaks Down",
                     body=(
                        "A single database's auto-increment column is trivially unique — there's one counter, "
                        "one source of truth. The moment you shard across multiple databases, that breaks: "
                        "each shard's own auto-increment would happily hand out '1', '2', '3', ... "
                        "independently, producing duplicate IDs across shards. Alex Xu's Chapter 7 frames the "
                        "requirements a replacement needs: unique across the whole system, ideally roughly "
                        "sortable by creation time (useful for pagination and debugging), and generated "
                        "without every machine having to ask a central authority for the next value, since "
                        "that authority would itself become a bottleneck and single point of failure."
                     )),
                dict(heading="Option 1: UUIDs",
                     body=(
                        "A 128-bit UUID (version 4, randomly generated) is close to certainly unique with no "
                        "coordination at all — any machine can generate one independently. The trade-offs: "
                        "UUIDs are twice the size of a 64-bit integer, and because they're random, they have "
                        "no inherent ordering, which hurts index locality when used as a primary/clustered "
                        "key (inserts land all over the index instead of appending to one end) and makes it "
                        "impossible to tell which of two IDs was created first just by comparing them."
                     )),
                dict(heading="Option 2: Snowflake IDs",
                     body=(
                        "Twitter's Snowflake approach packs a 64-bit ID as: 1 unused sign bit, a timestamp "
                        "(milliseconds since a custom epoch), a datacenter ID, a machine ID, and a "
                        "per-millisecond sequence number that increments if the same machine generates more "
                        "than one ID in the same millisecond. Because the timestamp is the most significant "
                        "bits, IDs generated later are numerically larger — roughly sortable by creation time "
                        "— while the datacenter+machine ID fields guarantee two different machines can never "
                        "collide, and the sequence number handles a single machine generating IDs faster than "
                        "once per millisecond. No machine ever needs to ask another machine or a central "
                        "service for permission to mint an ID."
                     ),
                     deep_dive=dict(
                        title="The clock-skew problem",
                        body=(
                            "Snowflake's ordering guarantee assumes each machine's clock only moves forward. "
                            "If NTP corrects a machine's clock backward (even by milliseconds), that machine "
                            "could generate an ID with a smaller timestamp than one it already generated, "
                            "risking a duplicate or out-of-order ID. Real implementations detect this "
                            "explicitly — if the current time is earlier than the last recorded timestamp, "
                            "the generator typically refuses to issue IDs (stalls or errors) until the clock "
                            "catches back up, rather than silently risking a collision."
                        ),
                     )),
            ],
            questions=[
                dict(prompt="What is a key advantage of Snowflake-style IDs over plain UUIDs for a distributed system?",
                     choices=[("They're smaller (64-bit) and roughly time-sortable", True),
                              ("They require a central database lock", False),
                              ("They are always exactly sequential with no gaps", False),
                              ("They eliminate the need for a timestamp", False)],
                     explanation="Snowflake IDs embed a timestamp so they sort roughly chronologically, and fit in 64 bits vs UUID's 128.",
                     difficulty=2),
                dict(prompt="Which components typically make up a Snowflake-style 64-bit ID?",
                     choices=[("Random bytes only", False),
                              ("Timestamp, datacenter ID, machine ID, and sequence number", True),
                              ("Username hash and password hash", False), ("IP address and port", False)],
                     explanation="These components let independent machines generate unique, roughly ordered IDs without coordination.",
                     difficulty=2),
                dict(prompt="Why can't a simple auto-incrementing integer ID work well across multiple database shards?",
                     choices=[("Integers are too small to represent large numbers", False),
                              ("Each shard would need to coordinate to avoid generating duplicate IDs, creating a bottleneck", True),
                              ("Auto-increment is not supported by SQL", False),
                              ("IDs would sort in the wrong order", False)],
                     explanation="Without coordination, two shards could independently generate the same next integer — coordinating that away reintroduces a bottleneck.",
                     difficulty=2),
                dict(prompt="What happens to Snowflake ID generation if a machine's clock moves backward (clock skew)?",
                     choices=[("Nothing, it's always perfectly safe", False),
                              ("It risks generating a duplicate or out-of-order ID, so implementations typically detect and stall/error on this", True),
                              ("IDs become negative", False),
                              ("The datacenter ID changes automatically", False)],
                     explanation="Since the timestamp component assumes time moves forward, clock regression is a known edge case implementations must guard against.",
                     difficulty=3),
                dict(prompt="Why are UUIDs generally less ideal than Snowflake IDs as a primary/clustered database index key?",
                     choices=[("UUIDs are not unique enough", False),
                              ("Their randomness causes poor index locality and larger index sizes compared to roughly time-ordered IDs", True),
                              ("UUIDs cannot be generated without a network call", False),
                              ("UUIDs are shorter than Snowflake IDs", False)],
                     explanation="Random UUIDs scatter insertions across a B-tree index, hurting locality; roughly-increasing IDs insert more sequentially.",
                     difficulty=3),
                dict(prompt="How many distinct machine IDs are typically needed within one datacenter for Snowflake-style generation to avoid collisions?",
                     choices=[("Exactly one — machine ID isn't really needed", False),
                              ("Enough to uniquely identify every ID-generating host in that datacenter", True),
                              ("Machine ID is randomly regenerated per request", False),
                              ("Machine ID always equals the sequence number", False)],
                     explanation="Every host minting IDs needs its own machine ID so two hosts in the same millisecond never produce the same ID.",
                     difficulty=2),

                # --- Added from verified web sources: RFC 9562, MongoDB docs, ULID spec ---
                dict(prompt="What does RFC 9562, published by the IETF in 2024, formally define?",
                     choices=[("UUIDs (Universally Unique Identifiers), including newer time-ordered versions", True), ("The HTTP/2 binary framing protocol used for multiplexed connections", False),
                              ("The JSON data interchange format used for structured API payloads", False), ("The TCP three-way handshake used to establish new connections", False)],
                     explanation="RFC 9562 is the current IETF specification for UUIDs, formally defining versions 1 through 8 including the newer, sortable UUID v7. (Source: RFC 9562, rfc-editor.org)",
                     difficulty=2),
                dict(prompt="Per RFC 9562, how many total bits make up a UUID, regardless of version?",
                     choices=[("128 bits", True), ("64 bits", False),
                              ("256 bits", False), ("32 bits", False)],
                     explanation="Every UUID version is 128 bits long; what differs between versions is how those bits are filled in (random, timestamp, MAC address, etc). (Source: RFC 9562)",
                     difficulty=1),
                dict(prompt="Roughly how much of UUID version 4's 128 bits is filled with random data?",
                     choices=[("122 bits — all but the fixed version and variant marker bits", True), ("64 bits — exactly half", False),
                              ("32 bits — the low-order word only", False), ("8 bits — a single byte", False)],
                     explanation="UUID v4 is 128 bits minus a 4-bit version field and a 2-bit variant field, leaving 122 bits of randomness. (Source: RFC 9562)",
                     difficulty=2),
                dict(prompt="Per RFC 9562's own guidance, which UUID version should new systems favor for sortable, time-ordered identifiers?",
                     choices=[("UUID version 7", True), ("UUID version 1", False),
                              ("UUID version 3", False), ("UUID version 4", False)],
                     explanation="RFC 9562 recommends UUID v7 for new systems that don't need legacy v1 compatibility, since it embeds a timestamp for natural sort order. (Source: RFC 9562)",
                     difficulty=2),
                dict(prompt="What kind of timestamp does UUID version 7 embed in its first 48 bits?",
                     choices=[("Unix time in milliseconds", True), ("Unix time in seconds", False),
                              ("Days since a custom 2020 epoch", False), ("A 48-bit random nonce, not a timestamp at all", False)],
                     explanation="UUID v7 leads with a 48-bit Unix millisecond timestamp, which is exactly what makes v7 IDs sort chronologically like Snowflake IDs do. (Source: RFC 9562)",
                     difficulty=2),
                dict(prompt="How many total bytes make up a MongoDB ObjectId?",
                     choices=[("12 bytes", True), ("8 bytes", False),
                              ("16 bytes", False), ("4 bytes", False)],
                     explanation="A MongoDB ObjectId is 12 bytes: a 4-byte timestamp, a 5-byte per-process random value, and a 3-byte incrementing counter. (Source: MongoDB Database Manual)",
                     difficulty=1),
                dict(prompt="Which of the following are genuine components of a MongoDB ObjectId's 12 bytes? (select all that apply)",
                     kind='multi',
                     choices=[("A 4-byte timestamp measured in seconds since the Unix epoch", True), ("A 5-byte random value generated once per process", True),
                              ("A 3-byte incrementing counter initialized to a random value", True), ("A 6-byte copy of the machine's MAC address", False)],
                     explanation="MongoDB's current ObjectId format is timestamp + per-process random value + counter; the older MAC-address-based layout was dropped from the spec. (Source: MongoDB Database Manual)",
                     difficulty=3),
                dict(prompt="What text encoding does a ULID (Universally Unique Lexicographically Sortable Identifier) use for its canonical string form?",
                     choices=[("Crockford's Base32", True), ("Base64", False),
                              ("Hexadecimal", False), ("Plain ASCII digits only", False)],
                     explanation="ULID uses Crockford's Base32 specifically because it's case-insensitive and avoids characters that are easy to misread, while staying URL-safe. (Source: ULID specification)",
                     difficulty=2),
                dict(prompt="How long is a ULID's canonical string representation, compared to a standard hyphenated UUID string (36 characters)?",
                     choices=[("26 characters — shorter than a UUID string", True), ("36 characters — exactly the same length", False),
                              ("52 characters — roughly double a UUID string", False), ("8 characters — much shorter than a UUID string", False)],
                     explanation="A ULID encodes the same 128 bits as a UUID but with denser Base32 encoding, producing a 26-character string versus UUID's 36. (Source: ULID specification)",
                     difficulty=2),
                dict(prompt="What property makes a ULID more attractive than a random UUID v4 as a database primary key?",
                     choices=[("Its first 48 bits are a timestamp, so ULIDs sort lexicographically in creation order", True), ("ULIDs are guaranteed to never collide, unlike UUID v4", False),
                              ("ULIDs are always exactly 8 bytes, half the size of a UUID", False), ("ULIDs don't require any randomness to generate", False)],
                     explanation="Because a ULID's leading bits encode a millisecond timestamp, sorting ULID strings lexicographically also sorts them by creation time — something a fully random UUID v4 can't offer. (Source: ULID specification)",
                     difficulty=2),
             ]),
    ),
    dict(book='system-design-interview-xu', slug='url-shortener', title='Design a URL Shortener',
         topic=TOPIC_CASE_STUDIES, difficulty=1,
         order=6, unlock_level=4, summary='Encoding long URLs into short, unique codes at scale.',
         concept=dict(
            slug='url-shortener-design', title='Base62 Encoding & Data Model',
            source_note='Chapter 8: Design a URL Shortener',
            summary=(
                "Two ways to turn a long URL into a short, unique code — one that hashes the URL, and one "
                "that encodes a guaranteed-unique ID — plus why caching matters so much for this system."
            ),
            notes=[
                dict(heading="Approach 1: Hash the URL",
                     body=(
                        "One instinct is to hash the long URL (e.g. with MD5 or CRC32) and take the first N "
                        "characters of the hash as the short code. It's simple, but Alex Xu's Chapter 8 is "
                        "careful to flag the catch: taking only the first N characters of a hash throws away "
                        "most of its uniqueness guarantee, so two different URLs can produce the same "
                        "truncated code. The system then needs explicit collision handling — checking whether "
                        "the code's already taken and, if so, retrying with a different hash or salt."
                     )),
                dict(heading="Approach 2: Encode a Unique ID",
                     body=(
                        "The more scalable approach sidesteps collisions entirely: generate a globally unique "
                        "ID first (from an auto-increment counter or a dedicated ID-generation service — see "
                        "the Unique ID Generator concept), then encode that ID in base62 (digits 0-9, "
                        "lowercase a-z, uppercase A-Z — 62 symbols, all safe to use directly in a URL path "
                        "without escaping). Because the underlying ID is unique by construction, the encoded "
                        "code can never collide with another one. Seven base62 characters give 62^7, "
                        "roughly 3.5 trillion possible codes — comfortably more than any single service is "
                        "likely to need."
                     ),
                     deep_dive=dict(
                        title="Why base62 instead of base64?",
                        body=(
                            "Base64 adds two more symbols to reach 64 total, conventionally '+' and '/' — and "
                            "both of those have special meaning inside a URL (they need percent-encoding to "
                            "appear literally in a path). Base62 sticks to purely alphanumeric characters, so "
                            "every generated code is safe to drop directly into a URL with no escaping logic "
                            "needed on either the server or any client that constructs links."
                        ),
                     )),
                dict(heading="The Data Model and Why Caching Matters",
                     body=(
                        "The core data model is almost embarrassingly simple: a table mapping short_code -> "
                        "long_url (plus maybe creation time and an expiry). What makes the system interesting "
                        "is its traffic shape: a link is created once but clicked — read — potentially "
                        "thousands of times afterward, so the read:write ratio is heavily skewed toward "
                        "reads. That makes the redirect path (short code in, HTTP redirect to the long URL "
                        "out) the hottest part of the system by far, and a strong candidate for a cache (e.g. "
                        "Redis) in front of the database so that popular links don't have to hit disk on "
                        "every single click."
                     )),
            ],
            questions=[
                dict(prompt="Why is base62 (not base64) commonly used for URL shortener codes?",
                     choices=[("Base64 is not case-sensitive", False),
                              ("Base62 avoids '+' and '/' characters, which aren't URL-safe without encoding", True),
                              ("Base62 is faster to compute", False),
                              ("Base64 can't represent numbers", False)],
                     explanation="Base62 uses only alphanumeric characters (0-9, a-z, A-Z), all safe to use directly in a URL path.",
                     difficulty=2),
                dict(prompt="A URL shortener's read:write ratio is typically what shape, and why does it matter?",
                     choices=[("Roughly 1:1, so caching doesn't help much", False),
                              ("Heavily read-dominant, so caching redirects is important", True),
                              ("Heavily write-dominant, so caching is pointless", False),
                              ("There is no meaningful read traffic", False)],
                     explanation="Every shortened link gets clicked many times after being created once, so redirects (reads) dominate — a great case for caching.",
                     difficulty=2),
                dict(prompt="What is a drawback of hashing the long URL (e.g. with MD5) and truncating it for the short code?",
                     choices=[("It's too slow to compute", False),
                              ("Truncated hashes can collide, requiring collision-handling logic on write", True),
                              ("Hashes cannot be shortened at all", False),
                              ("It requires a distributed ID generator", False)],
                     explanation="Truncating a hash shrinks the output space, making collisions likely enough that the write path needs a retry/handling strategy.",
                     difficulty=2),
                dict(prompt="Why is a URL shortener's redirect typically implemented as an HTTP 301 or 302 response?",
                     choices=[("Because it's required for base62 encoding", False),
                              ("301/302 responses tell the browser to navigate on to the original long URL", True),
                              ("Because it changes the HTTP request method", False),
                              ("Because it's the only way to serve HTML", False)],
                     explanation="3xx redirect status codes are the standard HTTP mechanism for pointing a client at a different URL.",
                     difficulty=1),
                dict(prompt="What's a reason to choose a 302 (temporary) redirect over a 301 (permanent) one for a URL shortener?",
                     choices=[("302 responses are cached forever by browsers, improving speed", False),
                              ("302 lets the service keep tracking click analytics on every visit, instead of browsers permanently caching the redirect", True),
                              ("301 is not supported by HTTP/1.1", False),
                              ("There is no practical difference in browser behavior", False)],
                     explanation="A 301 can get cached client-side, meaning future clicks skip the shortener entirely — bad for analytics.",
                     difficulty=2),
                dict(prompt="How does the ID-generation-plus-base62 approach avoid the collision problem that hashing has?",
                     choices=[("It doesn't — collisions are still equally likely", False),
                              ("Each underlying ID is unique by construction, so encoding it can never produce a duplicate code", True),
                              ("Base62 encoding removes duplicate letters from the alphabet", False),
                              ("It relies on retrying random codes until one happens to be free", False)],
                     explanation="Because the ID itself is guaranteed unique (e.g. auto-increment or Snowflake), encoding it deterministically can't collide.",
                     difficulty=2),
             ]),
    ),
    dict(book='system-design-interview-xu', slug='web-crawler', title='Design a Web Crawler',
         topic=TOPIC_CASE_STUDIES, difficulty=2,
         order=7, unlock_level=4, summary='Systematically discovering and fetching pages across the web.',
         concept=dict(
            slug='crawler-architecture', title='Crawler Architecture & Politeness',
            source_note='Chapter 9: Design a Web Crawler',
            summary=(
                "The basic fetch-extract-repeat loop of a web crawler, and the three things that make it "
                "hard at real scale: deduplication, DNS, and not getting the crawler banned."
            ),
            notes=[
                dict(heading="The Basic Loop, and Why It Doesn't Scale Naively",
                     body=(
                        "A web crawler's core loop is simple: start from a set of seed URLs, fetch each page, "
                        "extract the links it contains, add newly discovered URLs back into the queue, and "
                        "repeat. Alex Xu's Chapter 9 points out that this simple loop hides real scale "
                        "problems the moment you're crawling meaningful chunks of the web: a URL frontier "
                        "(the queue of URLs waiting to be fetched) that many fetcher workers pull from in "
                        "parallel, a way to avoid re-crawling URLs already visited, and a way to avoid "
                        "hammering any one website too hard."
                     )),
                dict(heading="Avoiding Re-Crawls at Scale",
                     body=(
                        "As the crawl grows, checking 'have I already seen this URL?' against billions of "
                        "previously visited URLs becomes its own bottleneck if done with something like a "
                        "hash set kept fully in memory or a full database lookup per URL. A Bloom filter — a "
                        "compact, probabilistic set-membership structure — answers 'definitely not seen' or "
                        "'possibly seen' using a small, fixed amount of memory regardless of how many URLs "
                        "have been recorded, trading a small, tunable false-positive rate for massive memory "
                        "savings."
                     )),
                dict(heading="Politeness: Not Getting Banned",
                     body=(
                        "'Politeness' is the crawler equivalent of good manners: don't send so many parallel "
                        "requests to one host that you effectively DoS it. In practice this means maintaining "
                        "a separate request queue per host with its own rate limit and delay between "
                        "requests, so the crawler can fetch many different sites at full speed in parallel "
                        "while still being gentle with any single one. Well-behaved crawlers also fetch and "
                        "respect each site's robots.txt file, which declares which paths the site owner does "
                        "or doesn't want automated crawlers to visit."
                     ),
                     deep_dive=dict(
                        title="Prioritizing what to crawl first",
                        body=(
                            "With a near-infinite web and finite crawl capacity, not every URL is equally "
                            "worth fetching right now. Crawlers assign priority using signals like PageRank "
                            "(how many other pages link to this one, and how important those are), historical "
                            "update frequency (a news homepage changes hourly; a static 'About Us' page "
                            "almost never does), or simple heuristics like domain reputation — so that time-"
                            "sensitive, high-value pages get re-crawled often while low-value pages are "
                            "visited rarely, if ever."
                        ),
                     )),
            ],
            questions=[
                dict(prompt="What is 'politeness' in the context of web crawler design?",
                     choices=[("Only crawling websites that allow ads", False),
                              ("Avoiding overwhelming a single host with too many concurrent requests", True),
                              ("Encrypting all crawled data", False), ("Crawling only HTTPS sites", False)],
                     explanation="Politeness policies (per-host queues, delays, respecting robots.txt) prevent a crawler from DoS-ing the sites it visits.",
                     difficulty=1),
                dict(prompt="Which data structure is commonly used to efficiently check whether a URL has already been visited, at huge scale?",
                     choices=[("Linked list", False), ("Bloom filter", True), ("Binary search tree", False), ("Stack", False)],
                     explanation="A Bloom filter gives fast, memory-efficient (probabilistic) membership checks — ideal for 'have we seen this URL' at billions of scale.",
                     difficulty=2),
                dict(prompt="Why does a web crawler maintain a separate request queue per host rather than one global queue?",
                     choices=[("To enforce politeness delays per host without slowing down crawling of other hosts", True),
                              ("Because HTTP requires per-host queues", False),
                              ("To reduce the size of the URL frontier", False),
                              ("Because DNS can only resolve one host at a time", False)],
                     explanation="Per-host queues let the crawler throttle any single site independently while still fetching other hosts at full speed.",
                     difficulty=2),
                dict(prompt="What is a common way to prioritize which URLs a crawler fetches first?",
                     choices=[("Alphabetical order of the URL", False),
                              ("Signals like PageRank, update frequency, or page importance", True),
                              ("Purely random order", False),
                              ("Whichever URL was submitted last", False)],
                     explanation="Prioritizing important or frequently-changing pages makes better use of limited crawl capacity.",
                     difficulty=1),
                dict(prompt="Why is a DNS resolver cache important for crawler performance?",
                     choices=[("DNS lookups are relatively slow and repeated often for the same domains, so caching avoids redundant lookups", True),
                              ("DNS caching is required by robots.txt", False),
                              ("It replaces the need for a dedup filter", False),
                              ("It prevents duplicate content across pages", False)],
                     explanation="A crawler hits the same domains repeatedly across many URLs, so caching DNS resolutions removes a real bottleneck.",
                     difficulty=2),
                dict(prompt="What does respecting `robots.txt` mean for a well-behaved crawler?",
                     choices=[("Ignoring all HTTPS sites", False),
                              ("Following the site's stated rules about which paths may or may not be crawled", True),
                              ("Only crawling during business hours", False),
                              ("Encrypting all crawled data", False)],
                     explanation="robots.txt is a site's own opt-out/opt-in policy for automated crawlers, and politeness means honoring it.",
                     difficulty=1),
             ]),
    ),
    dict(book='system-design-interview-xu', slug='notification-system', title='Design a Notification System',
         topic=TOPIC_CASE_STUDIES, difficulty=2,
         order=8, unlock_level=5, summary='Delivering push, SMS, and email notifications reliably at scale.',
         concept=dict(
            slug='notification-architecture', title='Notification System Architecture',
            source_note='Chapter 10: Design a Notification System',
            summary=(
                "How one event fans out to push, SMS, and email — and why message queues and third-party "
                "providers, not your own app servers, do the actual delivering."
            ),
            notes=[
                dict(heading="Fanning One Event Out Across Channels",
                     body=(
                        "Alex Xu's Chapter 10 treats a notification system as a fan-out problem: a single "
                        "triggering event (a new comment, a shipping update) may need to reach a user via "
                        "push notification, SMS, and/or email, depending on their preferences. Actually "
                        "delivering each of those isn't done in-house — the design leans on third-party "
                        "providers who own the relationship with each channel: APNs for iOS push, FCM "
                        "(Firebase Cloud Messaging) for Android push, and a provider like Twilio for SMS."
                     )),
                dict(heading="Decoupling With a Queue Per Channel",
                     body=(
                        "Rather than the app server calling APNs/FCM/Twilio directly and synchronously, "
                        "notification requests are placed on a message queue — typically one queue per "
                        "channel, so a slowdown or outage in, say, the SMS provider doesn't back up push or "
                        "email delivery. Producers (the application, when something notification-worthy "
                        "happens) and consumers (worker processes that pull from the queue and actually call "
                        "the third-party API) are fully decoupled: the app doesn't wait around for a "
                        "notification to actually send, and a burst of events doesn't overwhelm the "
                        "downstream providers, since the queue absorbs the spike and workers drain it at a "
                        "sustainable rate."
                     )),
                dict(heading="Reliability: Retries, Logging, and Rate Limits",
                     body=(
                        "Third-party APIs fail transiently sometimes — that's expected, not exceptional — so "
                        "workers retry failed sends with exponential backoff (wait a bit, then longer, then "
                        "longer still) instead of hammering an already-struggling provider. A notification "
                        "log records the delivery status of every attempt (queued, sent, failed, retried) so "
                        "engineers can debug 'did this actually go out' after the fact. And because retries, "
                        "duplicate event triggers, or plain bugs can otherwise spam a single user with the "
                        "same alert repeatedly, a per-user rate limit acts as a safety net independent of "
                        "whatever caused the flood."
                     ),
                     deep_dive=dict(
                        title="Why not just call the provider directly and skip the queue?",
                        body=(
                            "It's tempting for a simple system — call APNs right when the event happens, no "
                            "extra infrastructure. It breaks down at any real scale for two reasons: first, "
                            "if APNs is slow or down, every request that tries to notify a user now blocks or "
                            "fails along with it, coupling your app's reliability to a service you don't "
                            "control. Second, a sudden burst of events (a viral post generating thousands of "
                            "comment notifications at once) would try to call the provider thousands of times "
                            "in an instant instead of at a steady, sustainable rate — exactly the kind of "
                            "traffic spike a queue is built to absorb."
                        ),
                     )),
            ],
            questions=[
                dict(prompt="Why put a message queue between the app and the third-party notification providers?",
                     choices=[("To encrypt the notification content", False),
                              ("To decouple producers from consumers and absorb traffic spikes", True),
                              ("Queues are required by Apple and Google", False),
                              ("To avoid needing a database", False)],
                     explanation="Queues let notification producers keep working even if a downstream provider is slow, and smooth out bursts.",
                     difficulty=2),
                dict(prompt="What is a common technique for handling transient failures when calling a third-party notification API?",
                     choices=[("Give up immediately", False), ("Retry with exponential backoff", True),
                              ("Switch to a different user", False), ("Ignore the failure silently forever", False)],
                     explanation="Exponential backoff retries handle temporary provider outages without hammering the API.",
                     difficulty=1),
                dict(prompt="Why might a notification system deduplicate notifications before sending them?",
                     choices=[("To reduce database size only", False),
                              ("To avoid spamming a user with multiple copies of the same alert due to retries or duplicate triggers", True),
                              ("Deduplication is required by Apple/Google policy for every notification", False),
                              ("To increase delivery speed", False)],
                     explanation="Retries and duplicate event triggers are common — deduping keeps the user from getting the same alert three times.",
                     difficulty=2),
                dict(prompt="What role does a notification log/database play in this architecture?",
                     choices=[("It stores user passwords", False),
                              ("It tracks delivery status per notification for auditing and debugging failed sends", True),
                              ("It replaces the message queue", False),
                              ("It generates the notification content", False)],
                     explanation="A delivery log lets the system (and engineers) answer 'did this notification actually go out, and to whom'.",
                     difficulty=1),
                dict(prompt="Why use separate queues per channel (push, SMS, email) instead of one shared queue?",
                     choices=[("So a slowdown or outage in one channel's provider doesn't block delivery on the others", True),
                              ("Because HTTP requires channel separation", False),
                              ("To make notifications arrive louder", False),
                              ("Shared queues aren't supported by message brokers", False)],
                     explanation="Isolating channels means a struggling SMS provider, for example, can't back up push or email delivery.",
                     difficulty=2),
                dict(prompt="What is a risk of not rate-limiting notifications to an individual user?",
                     choices=[("Notifications become more secure", False),
                              ("A bug or retry storm could spam the same user with duplicate or excessive notifications", True),
                              ("Push notifications stop working entirely", False),
                              ("The message queue becomes unnecessary", False)],
                     explanation="Per-user rate limiting is a safety net against bugs or retries that would otherwise flood a single inbox.",
                     difficulty=2),
             ]),
    ),
    dict(book='system-design-interview-xu', slug='chat-system', title='Design a Chat System',
         topic=TOPIC_CASE_STUDIES, difficulty=2,
         order=9, unlock_level=5, summary='Real-time messaging with online presence and message ordering.',
         concept=dict(
            slug='chat-system-realtime', title='Real-Time Delivery with WebSockets',
            source_note='Chapter 12: Design a Chat System',
            summary=(
                "Why chat needs a persistent connection instead of HTTP polling, and how a system tracks "
                "which of many chat servers is holding a given user's connection."
            ),
            notes=[
                dict(heading="Why Not Just Poll?",
                     body=(
                        "The naive way to check for new messages is to have the client repeatedly ask the "
                        "server 'anything new?' every few seconds (polling). Alex Xu's Chapter 12 points out "
                        "this is a bad fit for chat: it's wasteful (most polls return nothing new) and it adds "
                        "latency up to the polling interval — a message can sit unseen for seconds before the "
                        "next poll picks it up. WebSockets solve this by keeping a single persistent, "
                        "bidirectional connection open between client and server, so the server can push a "
                        "new message to the client the instant it arrives, with no polling needed at all."
                     )),
                dict(heading="Stateless Services vs. Stateful Chat Servers",
                     body=(
                        "A chat backend typically splits into two kinds of service. Stateless services — "
                        "authentication, group/contact management, user search — hold no per-connection state "
                        "and can be freely load-balanced and scaled like any typical web service. Chat "
                        "servers, by contrast, are stateful: each one holds open WebSocket connections for "
                        "whichever subset of users happen to be connected to it right now. That statefulness "
                        "is what makes routing a message tricky — if Alice is connected to chat server 3 and "
                        "Bob is connected to chat server 7, delivering Alice's message to Bob means server 3 "
                        "has to somehow know to forward it to server 7."
                     ),
                     deep_dive=dict(
                        title="The presence service",
                        body=(
                            "This routing problem is solved with a presence service: a shared lookup (often "
                            "backed by something fast like Redis) mapping user ID -> which chat server "
                            "currently holds their live connection. When server 3 needs to deliver a message "
                            "to Bob, it looks up Bob's current server in the presence service and forwards "
                            "the message there. When a user disconnects and reconnects — possibly to a "
                            "different chat server, since a load balancer picks whichever one is free — the "
                            "presence service is updated so future messages route correctly."
                        ),
                     )),
                dict(heading="Ordering and Persistence",
                     body=(
                        "Within one conversation, messages need a stable order even if they arrive at the "
                        "server slightly out of sequence over the network. A local, per-conversation sequence "
                        "ID (rather than relying on wall-clock timestamps, which can be skewed between "
                        "machines) gives every message an unambiguous position. Messages are also persisted — "
                        "commonly in a key-value or wide-column store keyed by conversation ID — both so a "
                        "user can scroll back through chat history, and so a message sent to an offline user "
                        "isn't lost: it's durably stored and can be delivered (or pushed as a notification) "
                        "once they reconnect."
                     )),
            ],
            questions=[
                dict(prompt="Why are WebSockets preferred over repeated HTTP polling for a chat system?",
                     choices=[("WebSockets are easier to load balance", False),
                              ("WebSockets keep a persistent connection, enabling low-latency server-push", True),
                              ("Polling isn't supported by browsers", False),
                              ("WebSockets don't need a server", False)],
                     explanation="A persistent, bidirectional connection lets the server push new messages instantly instead of waiting for the client to ask.",
                     difficulty=1),
                dict(prompt="In a multi-server chat architecture, what does a 'presence service' track?",
                     choices=[("Which users are typing", False),
                              ("Which chat server currently holds a given user's live connection", True),
                              ("The battery level of mobile clients", False),
                              ("The geographic location of the datacenter", False)],
                     explanation="Since users can be connected to any of many chat servers, the system needs to know where to route a message meant for them.",
                     difficulty=2),
                dict(prompt="How is per-conversation message ordering typically preserved in a chat system?",
                     choices=[("By relying on client-side timestamps alone", False),
                              ("With a monotonically increasing sequence ID assigned per conversation", True),
                              ("Messages are processed in a random order", False),
                              ("By using the sender's IP address", False)],
                     explanation="A per-conversation sequence number sidesteps clock skew issues that client timestamps would introduce.",
                     difficulty=2),
                dict(prompt="What happens when a chat server holding a user's WebSocket connection crashes?",
                     choices=[("The user's messages are permanently lost", False),
                              ("The client reconnects (often to a different chat server) and the presence service is updated to route future messages there", True),
                              ("The entire chat system goes offline", False),
                              ("Nothing — WebSockets survive server crashes automatically", False)],
                     explanation="Because messages are persisted independently of the live connection, a server crash means a reconnect, not data loss.",
                     difficulty=2),
                dict(prompt="Why store chat messages in a key-value or wide-column store keyed by conversation ID?",
                     choices=[("It's the only format WebSockets support", False),
                              ("It makes fetching a conversation's message history a single efficient lookup", True),
                              ("It removes the need for a presence service", False),
                              ("It compresses message content automatically", False)],
                     explanation="Keying by conversation ID means loading chat history is one targeted read instead of scanning unrelated data.",
                     difficulty=1),
                dict(prompt="What's a benefit of keeping stateless auth/group-management services separate from stateful chat servers?",
                     choices=[("They can be scaled and load-balanced independently since they don't hold persistent connections", True),
                              ("Stateless services are always faster than stateful ones regardless of workload", False),
                              ("It eliminates the need for a database", False),
                              ("It removes the need for WebSockets", False)],
                     explanation="Stateless services can be scaled up/down freely behind a load balancer; stateful chat servers need connection-aware routing instead.",
                     difficulty=2),
             ]),
    ),

    # =========================================================================
    # --- Book 2: Grokking the System Design Interview ---
    # =========================================================================
    dict(book='grokking-system-design', slug='designing-instagram', title='Designing Instagram',
         topic=TOPIC_CASE_STUDIES, difficulty=2,
         order=1, unlock_level=6, summary='Photo sharing at scale: news feed generation and data sharding.',
         concept=dict(
            slug='newsfeed-fanout', title='News Feed Fan-out & Sharding',
            source_note='Chapter: Designing Instagram',
            summary=(
                "Why building a feed live at request time doesn't scale, and the hybrid pre-compute "
                "strategy Instagram-scale systems actually use instead."
            ),
            notes=[
                dict(heading="The Naive Approach: Query Live",
                     body=(
                        "The obvious way to build a user's feed is to, on every request, look up who they "
                        "follow and query each followee's recent posts, then merge and sort the results by "
                        "time. Grokking the System Design Interview's Designing Instagram chapter is blunt "
                        "about why this doesn't scale: a user following a few hundred accounts means a few "
                        "hundred queries (or one very expensive join) on every single feed load — fine for a "
                        "handful of users, brutal at real traffic volumes where feed reads happen constantly."
                     )),
                dict(heading="Fan-out on Write",
                     body=(
                        "The standard fix flips when the work happens: the moment a user posts, the system "
                        "immediately pushes that post into every one of their followers' pre-computed feed "
                        "caches ('fan-out on write'). Reading a feed then becomes a single fast cache lookup "
                        "instead of hundreds of live queries. The catch is symmetric to the benefit: for an "
                        "account with millions of followers, one post now means millions of cache writes — "
                        "potentially a huge, slow fan-out for every single post from a popular account."
                     )),
                dict(heading="Fan-out on Read, and the Hybrid Approach",
                     body=(
                        "'Fan-out on read' is the mirror image: don't pre-compute anything, build the feed at "
                        "request time by pulling recent posts from followees — cheap to write (a post is just "
                        "one write, not millions), expensive to read. Most large systems use neither approach "
                        "exclusively: fan-out on write for the vast majority of regular accounts (whose "
                        "follower counts are small enough that the write cost is trivial), and fan-out on "
                        "read — merging celebrity posts in at feed-load time — specifically for accounts with "
                        "huge followings, avoiding the worst-case write blowup while keeping reads fast for "
                        "everyone else."
                     ),
                     deep_dive=dict(
                        title="Sharding the underlying data",
                        body=(
                            "Underneath the feed logic, the actual user and photo data still has to live "
                            "somewhere, and it's sharded — commonly by user ID — across many database "
                            "machines so no single machine holds the whole dataset. Sharding by user ID keeps "
                            "a natural locality: most queries (a user's own posts, their profile) are scoped "
                            "to one user and therefore one shard, which is efficient. The trade-off, as with "
                            "any hash-based or ID-based sharding, is that an unlucky distribution can still "
                            "leave some shards hotter than others, which is one reason consistent hashing and "
                            "careful key design matter even at the storage layer, not just for the feed "
                            "caching logic above it."
                        ),
                     )),
            ],
            questions=[
                dict(prompt="What is the main trade-off of 'fan-out on write' for news feed generation?",
                     choices=[("Reads are slow, writes are fast", False),
                              ("Reads are fast, but writing a post is expensive for users with huge follower counts", True),
                              ("It requires no database at all", False),
                              ("It only works for text, not photos", False)],
                     explanation="Pre-computing everyone's feed makes reads instant, but a celebrity's post means writing to millions of feed caches.",
                     difficulty=2),
                dict(prompt="Why do large systems like Instagram often use a hybrid fan-out approach?",
                     choices=[("To reduce photo storage costs", False),
                              ("To combine fast reads for most users with cheaper writes for accounts with huge followings", True),
                              ("Because fan-out on write is illegal in some countries", False),
                              ("Hybrid approaches are always simpler to implement", False)],
                     explanation="Pure fan-out-on-write breaks down for celebrity accounts, so their posts are merged in at read time instead.",
                     difficulty=2),
                dict(prompt="In the hybrid fan-out approach, how are a celebrity's posts typically handled for a follower's feed?",
                     choices=[("They're never shown to followers", False),
                              ("They're excluded from the pre-computed feed cache and merged in at read time instead", True),
                              ("They're fanned out just like any regular user's post", False),
                              ("They're emailed to followers directly", False)],
                     explanation="This is the whole point of the hybrid approach: skip the expensive fan-out write for huge-follower accounts.",
                     difficulty=2),
                dict(prompt="Why is sharding by user ID a natural first choice for an Instagram-like system?",
                     choices=[("Because it guarantees perfectly even load in all cases", False),
                              ("Because most queries (a user's own photos, feed) are scoped to a single user, keeping related data together", True),
                              ("Because HTTP requires user-based sharding", False),
                              ("Because it eliminates the need for caching", False)],
                     explanation="Co-locating a user's own data on one shard makes the most common queries a single-shard operation.",
                     difficulty=2),
                dict(prompt="What's a downside of 'fan-out on read' for regular (non-celebrity) users?",
                     choices=[("It's more expensive to write a post", False),
                              ("Reads become slower since the feed must be assembled at request time", True),
                              ("It requires no database at all", False),
                              ("It only works for photos, not any other content type", False)],
                     explanation="Building the feed live at read time trades cheaper writes for slower, more expensive reads.",
                     difficulty=1),
                dict(prompt="Where are precomputed feed entries typically stored for fast retrieval?",
                     choices=[("On the client device only", False),
                              ("In an in-memory cache (e.g. Redis) as a list of post IDs per user", True),
                              ("In a plain text log file", False),
                              ("They aren't stored — feeds are always recomputed from scratch", False)],
                     explanation="A cached list of IDs is small and fast to read/update; full post content is fetched separately when rendering.",
                     difficulty=1),
             ]),
    ),
    dict(book='grokking-system-design', slug='designing-dropbox', title='Designing Dropbox',
         topic=TOPIC_CASE_STUDIES, difficulty=3,
         order=2, unlock_level=7, summary='Cloud file storage: sync, chunking, and deduplication.',
         concept=dict(
            slug='sync-dedup', title='File Sync & Deduplication',
            source_note='Chapter: Designing Dropbox',
            summary=(
                "Why cloud storage splits files into chunks instead of storing them whole, and how that "
                "one decision enables both deduplication and fast multi-device sync."
            ),
            notes=[
                dict(heading="Chunking Instead of Whole Files",
                     body=(
                        "Grokking the System Design Interview's Designing Dropbox chapter starts from a "
                        "simple but consequential design choice: split every file into fixed-size chunks "
                        "(commonly around 4MB) rather than storing it as one blob. Each chunk is stored keyed "
                        "by a hash of its own content, in cheap blob/object storage, while a separate metadata "
                        "database tracks which ordered sequence of chunks makes up each file (and each file "
                        "version)."
                     )),
                dict(heading="Why Chunking Enables Deduplication",
                     body=(
                        "Content-addressed chunks — where the chunk's storage key is derived from its own "
                        "bytes — mean identical content is only ever stored once, no matter how many files or "
                        "users reference it. If two users upload the exact same file, both point at the same "
                        "underlying chunks instead of duplicating storage. More importantly for everyday use: "
                        "if a user edits a small part of a large file, only the chunks whose bytes actually "
                        "changed need to be re-hashed, re-uploaded, and stored — every unaffected chunk is "
                        "untouched, so a one-line edit to a large document doesn't mean re-uploading the whole "
                        "document."
                     ),
                     deep_dive=dict(
                        title="What actually changes on a small edit?",
                        body=(
                            "Say a 40MB file is split into ten 4MB chunks and a user edits a paragraph that "
                            "happens to fall inside chunk 3. Only chunk 3's content (and therefore its hash) "
                            "changes; chunks 1, 2, and 4-10 are byte-for-byte identical to before. The sync "
                            "client only needs to upload the new chunk 3 and update the file's metadata "
                            "record to point at it instead of the old chunk 3 — the other 36MB never moves "
                            "over the network at all."
                        ),
                     )),
                dict(heading="Propagating Changes to Other Devices",
                     body=(
                        "A sync client running on each of a user's devices watches the local filesystem for "
                        "changes and talks to a synchronization service in the cloud. When a change is "
                        "detected and uploaded, that service uses a message queue to propagate the change out "
                        "to the user's other devices — decoupling the upload path from delivery, so a device "
                        "that's temporarily offline simply catches up on its backlog of changes once it "
                        "reconnects, rather than requiring every device to be online simultaneously for sync "
                        "to work."
                     )),
            ],
            questions=[
                dict(prompt="Why does a Dropbox-like service split files into chunks rather than storing whole files?",
                     choices=[("Chunking is required by law", False),
                              ("It enables deduplication and efficient re-upload of only changed portions", True),
                              ("It makes files load faster in a browser", False),
                              ("It reduces the need for a metadata database", False)],
                     explanation="Content-addressed chunks mean identical data (across files or versions) is stored only once, and edits only re-upload changed chunks.",
                     difficulty=2),
                dict(prompt="What is typically used to key/identify a chunk for deduplication purposes?",
                     choices=[("The file's original filename", False), ("A hash of the chunk's content", True),
                              ("The upload timestamp", False), ("The user's account ID", False)],
                     explanation="Content-based hashing means identical chunks (even from different files or users) map to the same stored object.",
                     difficulty=2),
                dict(prompt="What information does the metadata database track in a Dropbox-like sync service?",
                     choices=[("The raw bytes of every file chunk", False),
                              ("Which chunks make up each file, and file version history", True),
                              ("Only the user's login credentials", False),
                              ("The physical location of the datacenter", False)],
                     explanation="Metadata (which chunks, in what order, which version) is kept separate from the actual chunk bytes in blob storage.",
                     difficulty=1),
                dict(prompt="Why does a sync client watch the local filesystem for changes rather than requiring the user to manually trigger an upload?",
                     choices=[("Manual upload is faster", False),
                              ("So changes propagate automatically and promptly to other devices", True),
                              ("Filesystem watching is required by the OS", False),
                              ("It removes the need for chunking", False)],
                     explanation="Automatic change detection is what makes 'sync' feel seamless instead of requiring a manual save/upload step.",
                     difficulty=1),
                dict(prompt="What happens when a user edits a small part of a large file in a chunked sync system?",
                     choices=[("The entire file must be re-uploaded from scratch", False),
                              ("Only the chunks that changed need to be re-uploaded, since unaffected chunks are unchanged content", True),
                              ("The file is deleted and recreated", False),
                              ("All other users' copies are automatically overwritten", False)],
                     explanation="Content-addressed chunking means an edit only invalidates the chunks whose bytes actually changed.",
                     difficulty=2),
                dict(prompt="Why does a message queue help propagate file changes to a user's other devices?",
                     choices=[("It guarantees files are encrypted", False),
                              ("It decouples the write path from delivery, so other devices can catch up even if temporarily offline", True),
                              ("It replaces the need for a metadata database", False),
                              ("It compresses the file content", False)],
                     explanation="A queue lets an offline device receive its backlog of changes once it reconnects, instead of requiring it to be online at write time.",
                     difficulty=2),
             ]),
    ),
    dict(book='grokking-system-design', slug='designing-twitter', title='Designing Twitter',
         topic=TOPIC_CASE_STUDIES, difficulty=2,
         order=3, unlock_level=7, summary='Timeline generation and sharding for a write-heavy social graph.',
         concept=dict(
            slug='twitter-timeline', title='Timeline Generation & Data Sharding',
            source_note='Chapter: Designing Twitter',
            summary=(
                "The same fan-out problem as Instagram's feed, but pushed to more extreme scale and with a "
                "strict chronological ordering requirement that adds a second sharding dimension."
            ),
            notes=[
                dict(heading="Same Problem, Higher Stakes",
                     body=(
                        "Grokking the System Design Interview's Designing Twitter chapter builds directly on "
                        "the Instagram feed problem — most of the fan-out-on-write / fan-out-on-read / hybrid "
                        "reasoning carries over unchanged. What's different is scale (far more users, far "
                        "more tweets per second) and a stricter requirement: a Twitter home timeline is "
                        "expected to be strictly reverse-chronological, unlike a feed that can be freely "
                        "re-ordered by a ranking algorithm — which removes some flexibility other systems "
                        "have when smoothing out load."
                     )),
                dict(heading="Sharding by User ID Isn't Enough Alone",
                     body=(
                        "Sharding tweets purely by user ID (so all of one user's tweets live on one shard) "
                        "makes per-user queries efficient, but it creates the same celebrity problem as "
                        "Instagram, and worse: an account with tens of millions of followers generates "
                        "enormous read and write traffic concentrated on one shard, whichever machine that "
                        "happens to be. Twitter-scale systems commonly combine user-ID sharding with sharding "
                        "by tweet ID as well, spreading a single popular account's tweets and their associated "
                        "load across more machines instead of concentrating it all in one place."
                     ),
                     deep_dive=dict(
                        title="Tweet IDs double as timestamps",
                        body=(
                            "A tweet ID isn't just a random unique identifier — like a Snowflake ID, it can "
                            "embed a timestamp component, so higher tweet IDs are (roughly) newer tweets. "
                            "This is genuinely useful for a chronological timeline: sorting or filtering by "
                            "tweet ID gives you time-ordering for free, without needing a separate 'created "
                            "at' index lookup, which matters a lot when you're doing it billions of times a "
                            "day."
                        ),
                     )),
                dict(heading="Caching the Timeline Itself",
                     body=(
                        "Like Instagram's feed, a user's home timeline is cached in-memory (e.g. in Redis) as "
                        "a compact list of tweet IDs — not full tweet content, which is fetched separately "
                        "when actually rendering the timeline. This cache is refreshed via fan-out on write "
                        "for the overwhelming majority of accounts, with tweets from very high-follower "
                        "accounts merged in at read time instead, exactly mirroring Instagram's hybrid "
                        "strategy but tuned for Twitter's stricter chronological ordering."
                     )),
            ],
            questions=[
                dict(prompt="Why might sharding tweets purely by user ID create problems at Twitter's scale?",
                     choices=[("It would make usernames too long", False),
                              ("It can create hot shards for accounts with enormous tweet/follower volume", True),
                              ("User IDs cannot be hashed", False),
                              ("It violates HTTP standards", False)],
                     explanation="A celebrity's shard would take disproportionate load, so tweet ID-based sharding is often used alongside it.",
                     difficulty=2),
                dict(prompt="What's a common way to store a user's home timeline for fast reads?",
                     choices=[("A cached, in-memory list of tweet IDs, refreshed on write", True),
                              ("Recomputing it from scratch on every page load with a full table scan", False),
                              ("Storing it only on the client device", False),
                              ("Emailing the user their timeline daily", False)],
                     explanation="Precomputed, cached timelines (Redis-backed lists of tweet IDs) make reads fast at Twitter's scale.",
                     difficulty=2),
                dict(prompt="Why does Twitter need especially strict ordering guarantees compared to some other feed-based systems?",
                     choices=[("Because tweets don't have timestamps", False),
                              ("Because timelines are expected to be strictly reverse-chronological, unlike algorithmically-ranked feeds", True),
                              ("Because Twitter doesn't use sharding", False),
                              ("Because tweets are stored only in memory", False)],
                     explanation="Unlike a ranked feed, a chronological timeline has one 'correct' order, which the system must preserve under sharding.",
                     difficulty=2),
                dict(prompt="How can a tweet ID double as a rough timestamp for ordering, similar to Snowflake IDs?",
                     choices=[("It can't — tweet IDs are purely random", False),
                              ("By embedding a timestamp component in the ID itself, so higher IDs are roughly newer", True),
                              ("By using the tweet's character count", False),
                              ("By hashing the tweet author's username", False)],
                     explanation="A time-embedded ID lets the system sort or shard by ID and get roughly chronological order for free.",
                     difficulty=2),
                dict(prompt="Why might pure fan-out-on-write be impractical for celebrity accounts at Twitter's scale?",
                     choices=[("It isn't impractical — Twitter uses pure fan-out-on-write for everyone", False),
                              ("Writing a single celebrity tweet into millions of follower timeline caches at once is extremely expensive", True),
                              ("Writes are always free regardless of follower count", False),
                              ("Twitter has no high-follower accounts", False)],
                     explanation="This is exactly why a hybrid fan-out strategy (merging celebrity tweets in at read time) is used instead.",
                     difficulty=2),
                dict(prompt="What's an advantage of caching a user's timeline as a list of tweet IDs rather than full tweet content?",
                     choices=[("IDs take up more space than full content", False),
                              ("The list is small and fast to update/read; full tweet content can be fetched separately when rendering", True),
                              ("IDs cannot be cached", False),
                              ("It removes the need for sharding", False)],
                     explanation="A compact ID list keeps the cache small and cheap to update; content lookups are a separate, parallelizable step.",
                     difficulty=1),
             ]),
    ),
    dict(book='grokking-system-design', slug='designing-messenger', title='Designing Facebook Messenger',
         topic=TOPIC_CASE_STUDIES, difficulty=3,
         order=4, unlock_level=8, summary='One-on-one and group messaging with delivery guarantees.',
         concept=dict(
            slug='messenger-delivery', title='Message Delivery & Online Status',
            source_note='Chapter: Designing Facebook Messenger',
            summary=(
                "How reliable delivery works even when a recipient is offline, and why 'is this person "
                "online' turns out to be a surprisingly hard scaling problem of its own."
            ),
            notes=[
                dict(heading="Persist First, Deliver Second",
                     body=(
                        "Grokking the System Design Interview's Designing Facebook Messenger chapter centers "
                        "on a durability-first principle: when Alice sends Bob a message, it's persisted to "
                        "storage (commonly a wide-column store keyed by conversation ID) *before* any attempt "
                        "at live delivery. Only after that durable write succeeds does the system try to push "
                        "the message over Bob's live connection if he's online — and if he's not, the message "
                        "simply waits, already safely stored, until he reconnects or a push notification "
                        "nudges him back to the app."
                     ),
                     deep_dive=dict(
                        title="Why persist-first, not deliver-first?",
                        body=(
                            "If delivery were attempted first and persistence happened afterward (or not at "
                            "all if delivery 'succeeded'), a message could be shown to an online recipient "
                            "and then lost forever if the server crashed a moment later — no durable record "
                            "would exist. Persisting first means the message survives any downstream failure "
                            "in the live-delivery path; delivery becomes an optimization on top of an "
                            "already-safe write, not a replacement for one."
                        ),
                     )),
                dict(heading="Delivery Status: Sent, Delivered, Seen",
                     body=(
                        "Each message's lifecycle is tracked explicitly through a small state machine: "
                        "'sent' (the server has it), 'delivered' (it reached the recipient's device), and "
                        "'seen' (the recipient actually opened/read it) — the three states behind the "
                        "familiar check-mark UI in messaging apps. This status is stored per-message and "
                        "updated as delivery and read-receipt events come in from the recipient's client."
                     )),
                dict(heading="Presence Is Chattier Than It Looks",
                     body=(
                        "Online/offline status ('presence') seems like a small feature, but it's one of the "
                        "trickiest parts of the whole system at scale. The naive approach — broadcast every "
                        "status change to every one of a user's contacts, instantly — creates enormous fan-out "
                        "as social graphs grow: a user with a thousand contacts going online means a thousand "
                        "notifications sent out immediately, and that happens every single time anyone's "
                        "status flips. Real systems batch and throttle presence updates instead of pushing "
                        "every flip in real time, trading a small amount of freshness (your friend's status "
                        "might be a few seconds stale) for a massive reduction in message volume."
                     )),
            ],
            questions=[
                dict(prompt="Why is a message typically persisted to storage before being delivered live?",
                     choices=[("To make the UI look busier", False),
                              ("So the message isn't lost if the recipient is offline or the server crashes", True),
                              ("Persistence is only needed for group chats", False),
                              ("It's required for encryption", False)],
                     explanation="Durability first means the message can still be delivered later even if live delivery fails right now.",
                     difficulty=1),
                dict(prompt="Why do real-world messaging systems often throttle/batch online-status ('presence') updates instead of pushing them instantly to every contact?",
                     choices=[("Presence updates are illegal in some regions", False),
                              ("Broadcasting every status change to every contact doesn't scale", True),
                              ("Users don't want to know who's online", False),
                              ("It reduces the need for message persistence", False)],
                     explanation="With large contact graphs, naive real-time presence broadcasting creates enormous message fan-out, so it's batched/throttled.",
                     difficulty=3),
                dict(prompt="What are the typical delivery status states tracked per message in a messenger app?",
                     choices=[("Only 'sent'", False),
                              ("Sent, delivered, and seen", True),
                              ("Only 'seen'", False),
                              ("Draft and published", False)],
                     explanation="Tracking the full sent/delivered/seen lifecycle is what powers the read-receipt UI users expect.",
                     difficulty=1),
                dict(prompt="If Bob is offline when Alice sends a message, what happens after the server attempts live delivery and fails?",
                     choices=[("The message is discarded", False),
                              ("A push notification is triggered and the message waits, already persisted, for Bob to reconnect", True),
                              ("Alice's client retries sending forever", False),
                              ("The conversation is deleted", False)],
                     explanation="Because the message was persisted first, a failed live-delivery attempt just falls back to push notification + queued delivery.",
                     difficulty=2),
                dict(prompt="Why is presence ('online'/'offline' status) described as 'notoriously chatty' at scale?",
                     choices=[("Because presence data is never useful", False),
                              ("Because naively broadcasting every status change to every contact creates enormous message volume as the social graph grows", True),
                              ("Because presence requires a database", False),
                              ("Because it only affects group chats", False)],
                     explanation="Every status flip would otherwise fan out to every contact, which scales terribly with graph size.",
                     difficulty=2),
                dict(prompt="What is one way real systems reduce the cost of presence updates?",
                     choices=[("Disabling presence entirely for all users", False),
                              ("Batching/throttling updates instead of pushing every change instantly", True),
                              ("Sending presence updates via email", False),
                              ("Storing presence in the same table as message content", False)],
                     explanation="Batching trades a little freshness for a lot less fan-out traffic.",
                     difficulty=1),
             ]),
    ),
    dict(book='grokking-system-design', slug='designing-youtube', title='Designing YouTube / Netflix',
         topic=TOPIC_CASE_STUDIES, difficulty=3,
         order=5, unlock_level=8, summary='Video upload, encoding, and CDN-based delivery at scale.',
         concept=dict(
            slug='video-cdn-delivery', title='Video Encoding & CDN Delivery',
            source_note='Chapter: Designing Youtube or Netflix',
            summary=(
                "Video platforms split into two very different pipelines — upload/processing and delivery "
                "— and lean on transcoding and a CDN to make streaming feel instant worldwide."
            ),
            notes=[
                dict(heading="Upload & Processing: Transcoding",
                     body=(
                        "Grokking the System Design Interview's Designing YouTube/Netflix chapter splits the "
                        "system into two halves with very different concerns. On the upload side, a video is "
                        "transcoded into multiple resolutions and bitrates (and sometimes formats) right after "
                        "it's uploaded — not lazily at playback time. This upfront cost pays for adaptive "
                        "bitrate streaming: the player can switch between a lower-resolution/bitrate version "
                        "and a higher one on the fly, based on the viewer's current device and network "
                        "conditions, without ever re-encoding anything live."
                     )),
                dict(heading="Delivery: Why a CDN Is Non-Negotiable",
                     body=(
                        "The delivery side is dominated by a completely different problem: raw bandwidth at "
                        "global scale. Streaming every viewer's video directly from a single origin "
                        "datacenter would mean enormous latency for anyone far from that datacenter, and would "
                        "make the origin's bandwidth the hard ceiling on how many people can watch at once. A "
                        "CDN — a globally distributed network of edge caches — solves both problems by "
                        "serving cached video segments from a server physically close to each viewer, "
                        "dramatically cutting both latency and the load that ever reaches the origin."
                     ),
                     deep_dive=dict(
                        title="Why encode upfront instead of on-demand?",
                        body=(
                            "Transcoding a video into many resolutions is computationally expensive — it "
                            "would be wasteful to redo it for every single view. Paying that cost once, right "
                            "after upload, means every subsequent view (potentially millions of them for a "
                            "popular video) just reads a pre-encoded segment instead of triggering fresh "
                            "encoding work. This is the same 'pay once, benefit many times' logic behind "
                            "caching in general, just applied to compute instead of storage."
                        ),
                     )),
                dict(heading="Metadata Lives Separately From Video Bytes",
                     body=(
                        "Titles, descriptions, view counts, likes, and comments are structured, frequently "
                        "updated, and queried in very different ways than the video bytes themselves — so "
                        "they live in a separate, more conventional database, while the actual video segments "
                        "sit in blob/object storage behind the CDN. Keeping these two concerns apart means "
                        "each can be scaled and optimized independently: the metadata database for query "
                        "patterns and consistency, the video storage/CDN layer purely for raw throughput."
                     )),
            ],
            questions=[
                dict(prompt="Why does a video platform transcode uploads into multiple resolutions/bitrates?",
                     choices=[("To save the uploader money", False),
                              ("To support adaptive playback across different devices and network speeds", True),
                              ("Because the original format is always corrupted", False),
                              ("It's a legal requirement", False)],
                     explanation="Adaptive bitrate streaming lets the player switch quality based on the viewer's current bandwidth.",
                     difficulty=1),
                dict(prompt="Why is a CDN critical for a video streaming service's scalability?",
                     choices=[("It stores user passwords securely", False),
                              ("It serves video from edge locations near viewers, reducing latency and origin load", True),
                              ("It replaces the need for video encoding", False),
                              ("It's only useful for text-based websites", False)],
                     explanation="Streaming every viewer directly from one origin datacenter would be slow and unscalable — CDNs push content close to viewers.",
                     difficulty=2),
                dict(prompt="What is 'adaptive bitrate streaming'?",
                     choices=[("Encoding a video only once at maximum quality", False),
                              ("Dynamically switching between pre-encoded quality levels based on the viewer's current network conditions", True),
                              ("A method for compressing metadata only", False),
                              ("A way to skip video transcoding entirely", False)],
                     explanation="The player picks from several pre-transcoded quality levels on the fly as bandwidth changes.",
                     difficulty=1),
                dict(prompt="Why is video metadata (titles, view counts, comments) typically stored separately from the video bytes themselves?",
                     choices=[("Because metadata and video bytes have very different access patterns and storage needs", True),
                              ("Because HTTP forbids storing them together", False),
                              ("Because metadata is never queried", False),
                              ("Because video bytes are always stored in a SQL database directly", False)],
                     explanation="Metadata is small, structured, and frequently queried; video bytes are huge, immutable blobs best served from object storage/CDN.",
                     difficulty=2),
                dict(prompt="What's a benefit of transcoding a video into multiple resolutions right after upload rather than on-demand at playback time?",
                     choices=[("It avoids repeatedly re-encoding the same video for every viewer, trading upfront processing cost for fast playback later", True),
                              ("It reduces storage requirements to zero", False),
                              ("It removes the need for a CDN", False),
                              ("It's required by all video codecs", False)],
                     explanation="Paying the encoding cost once at upload time (instead of per-view) is far cheaper at any real scale.",
                     difficulty=2),
                dict(prompt="Why do CDNs cache video segments at edge locations rather than serving everyone from one origin datacenter?",
                     choices=[("To reduce latency and origin server load by serving viewers from a nearby location", True),
                              ("Because origin servers cannot physically store video", False),
                              ("Edge locations are required for video encoding", False),
                              ("It has no effect on latency", False)],
                     explanation="Geographic proximity to the viewer is the whole value proposition of a CDN.",
                     difficulty=1),
             ]),
    ),

    # =========================================================================
    # --- Book 3: Database Internals ---
    # =========================================================================

    # --- Domain item: merges B-Trees, LSM-Trees, and WAL/crash recovery from
    # this book with DDIA's "Storage and Retrieval" chapter (cross-book —
    # it's literally the LSM-tree read path, the natural second half of the
    # LSM-tree write path covered a paragraph earlier).
    dict(book='database-internals', slug='storage-engines-durability', title='Storage Engines: B-Trees, LSM-Trees & Crash Recovery',
         topic=TOPIC_DATA, difficulty=3,
         order=1, unlock_level=9,
         summary='How on-disk storage engines organize data, trade off read vs. write performance, and recover cleanly from a crash.',
         concept=dict(
            slug='storage-engines-btree-lsm-wal', title='How Storage Engines Read, Write, and Recover',
            source_note=(
                'Chapter 2: B-Tree Basics; Chapter 7: Log-Structured Storage; '
                'Chapter 5: Transaction Processing and Recovery; DDIA Chapter 3: Storage and Retrieval'
            ),
            summary=(
                "Two very different ways a database engine can organize data on disk — B-trees and "
                "LSM-trees — and the write-ahead log that lets either one survive a crash."
            ),
            notes=[
                dict(heading="B-Trees: The Read-Optimized Default",
                     body=(
                        "Alex Petrov's Database Internals, Chapter 2, describes the B-tree as the default "
                        "on-disk structure behind most relational databases (PostgreSQL, MySQL's InnoDB, and "
                        "many more). Data lives in fixed-size pages arranged as a balanced tree: internal "
                        "pages hold separator keys and pointers to child pages, purely to route a search down "
                        "the tree, while leaf pages hold the actual key-value pairs. Every leaf sits at "
                        "exactly the same depth — that balance is the core invariant that guarantees O(log n) "
                        "lookups, inserts, and deletes regardless of how the data was inserted. When a page "
                        "fills up during an insert, it splits into two pages and pushes one separator key up "
                        "to the parent; if that causes the root itself to split, the tree grows by one level."
                     ),
                     deep_dive=dict(
                        title="Why B-trees suffer under heavy writes",
                        body=(
                            "B-trees update pages in place — an update to a row rewrites that row's page "
                            "directly on disk, wherever it happens to live. Under a write-heavy workload, "
                            "those pages are scattered essentially randomly across the disk, so each logical "
                            "write can turn into a random disk I/O — much slower than a sequential one, "
                            "especially on spinning disks, and still a meaningful cost even on SSDs. This "
                            "'write amplification' (one logical write costing more than one physical write) "
                            "is the central motivation for LSM-trees."
                        ),
                     )),
                dict(heading="LSM-Trees: Trading Reads for Writes",
                     body=(
                        "Log-structured merge-trees, covered in Petrov's Chapter 7, take the opposite trade-"
                        "off: never update data in place at all. Writes land first in an in-memory structure "
                        "called a memtable (backed by a write-ahead log so nothing's lost if the process "
                        "crashes before the memtable is flushed). Once the memtable reaches a size threshold, "
                        "it's flushed to disk as an immutable, sorted file called an SSTable — 'immutable' "
                        "meaning it's never edited again, only eventually replaced. Because writes only ever "
                        "append new SSTables rather than modifying old ones, writes become sequential disk "
                        "operations instead of random ones — dramatically faster under write-heavy load. Over "
                        "time, many SSTables accumulate, so a background compaction process periodically "
                        "merges them together, discarding values that have since been overwritten or deleted "
                        "(tombstoned), which keeps both disk usage and the number of files a read has to check "
                        "under control."
                     )),
                dict(heading="Reading From an LSM-Tree",
                     body=(
                        "This design's cost shows up on the read side, covered in DDIA's Chapter 3 (Storage "
                        "and Retrieval). Because the most recent write to a given key could be sitting in the "
                        "memtable or in any of several SSTables (newest write wins), a read may have to check "
                        "several places before it can be sure of the answer: first the memtable, then each "
                        "on-disk SSTable from newest to oldest. Two structures make this tractable instead of "
                        "unbearably slow: a Bloom filter per SSTable gives a fast, memory-cheap 'definitely "
                        "not here' answer that lets the read skip most files outright, and a sparse index "
                        "within a matching SSTable lets it jump close to the key's likely location and scan a "
                        "small range, rather than scanning the whole file."
                     )),
                dict(heading="Write-Ahead Logging & Crash Recovery",
                     body=(
                        "Whichever engine you use, durability during a crash comes from the write-ahead log "
                        "(WAL), the subject of Petrov's Chapter 5. The rule is strict: before a change is "
                        "applied to the actual data pages, a record describing that change is appended to the "
                        "log and flushed to disk first. If the process crashes at any point after that, the "
                        "log itself contains everything needed to reconstruct the pre-crash state by replaying "
                        "it. A classic recovery algorithm like ARIES runs this replay in three distinct "
                        "phases: Analysis scans the log to identify which transactions were in progress at "
                        "the moment of the crash and which pages might be 'dirty' (modified but not yet "
                        "flushed); Redo then replays every logged change — including changes from "
                        "transactions that never actually committed — to reach the database's exact state at "
                        "the instant of the crash; and only after that does Undo roll back the specific "
                        "transactions that were never committed."
                     ),
                     deep_dive=dict(
                        title="Why redo everything before undoing anything?",
                        body=(
                            "It seems backwards to replay uncommitted work just to throw it away in the next "
                            "phase. The payoff is that it hugely simplifies the recovery logic: by getting the "
                            "database to the *exact* physical state it was in the instant before the crash "
                            "(no exceptions, no special-casing which transactions get replayed), the Undo "
                            "phase can then be a single, uniform 'roll back anything not committed' pass "
                            "instead of having to reason about a mix of partially-applied and fully-applied "
                            "changes at the same time."
                        ),
                     )),
            ],
            questions=[
                dict(prompt="What happens when a B-tree leaf node becomes full during an insert?",
                     choices=[("It's split into two nodes and a separator key is pushed to the parent", True),
                              ("It's discarded and the insert fails", False),
                              ("It's compressed to make room", False),
                              ("The whole tree is rebuilt from scratch", False)],
                     explanation="Splitting keeps the tree balanced; if the split propagates to the root, the tree grows by one level.",
                     difficulty=1),
                dict(prompt="Why do all leaf nodes in a B-tree sit at the same depth?",
                     choices=[("It's a coincidence of how data happens to be inserted", False),
                              ("Splits and merges are designed to keep the tree balanced, so every lookup takes the same number of hops", True),
                              ("Leaf nodes are sorted alphabetically by depth", False),
                              ("B-trees don't actually guarantee this", False)],
                     explanation="Balance is the core B-tree invariant — it's what guarantees O(log n) lookups regardless of insert order.",
                     difficulty=2),
                dict(prompt="What is a key downside of B-trees under heavy random write workloads?",
                     choices=[("They cannot support range scans", False),
                              ("In-place updates cause random disk writes, leading to write amplification", True),
                              ("They require more memory than hash tables for point lookups", False),
                              ("They cannot be used for read-heavy workloads", False)],
                     explanation="Because B-trees update pages in place, scattered writes translate to scattered disk I/O — the main motivation for LSM-trees in write-heavy systems.",
                     difficulty=2),
                dict(prompt="In an LSM-tree, where does a newly written key initially live?",
                     choices=[("Directly in a compacted SSTable on disk", False),
                              ("In an in-memory memtable, later flushed to disk", True),
                              ("In the Bloom filter", False),
                              ("In the WAL only, never in memory", False)],
                     explanation="Writes hit the memtable first for speed; the WAL provides durability in case of a crash before the memtable is flushed.",
                     difficulty=1),
                dict(prompt="What is the purpose of compaction in an LSM-tree?",
                     choices=[("To encrypt SSTables at rest", False),
                              ("To merge SSTables, discard overwritten/deleted data, and keep read amplification manageable", True),
                              ("To increase the number of files on disk", False),
                              ("To convert the LSM-tree into a B-tree", False)],
                     explanation="Without compaction, reads would need to check an ever-growing number of SSTables, and disk space would be wasted on stale data.",
                     difficulty=2),
                dict(prompt="Why do LSM-trees commonly use Bloom filters?",
                     choices=[("To compress SSTables", False),
                              ("To quickly rule out SSTables that definitely don't contain a given key, avoiding unnecessary disk reads", True),
                              ("To replace the memtable", False),
                              ("To guarantee strong consistency across replicas", False)],
                     explanation="A Bloom filter is a probabilistic set-membership check — exactly what's needed to cheaply skip irrelevant SSTables.",
                     difficulty=2),
                dict(prompt="Compared to B-trees, LSM-trees are generally optimized for:",
                     choices=[("Write-heavy workloads, at some cost to read latency", True),
                              ("Read-only workloads with no writes at all", False),
                              ("Reducing total disk space to zero", False),
                              ("Eliminating the need for compaction entirely", False)],
                     explanation="Sequential writes to immutable files make LSM-trees fast to write to; the trade-off is reads may need to check multiple files.",
                     difficulty=1),
                dict(prompt="Why must a change be written to the WAL before it's applied to the actual data pages?",
                     choices=[("It's purely a performance optimization with no correctness benefit", False),
                              ("So that if the database crashes before the data page write completes, the change can still be recovered from the log", True),
                              ("Because data pages cannot be written to directly, ever", False),
                              ("To avoid needing a database schema", False)],
                     explanation="This is the core write-ahead logging rule: the log record must be durable before the corresponding data change.",
                     difficulty=2),
                dict(prompt="In ARIES-style crash recovery, what is the correct order of phases?",
                     choices=[("Undo, then Redo, then Analysis", False),
                              ("Analysis, then Redo, then Undo", True),
                              ("Redo, then Analysis, then Undo", False),
                              ("Undo and Redo happen simultaneously with no Analysis phase", False)],
                     explanation="Analysis first determines what needs fixing; Redo replays everything to reach the pre-crash state; only then does Undo roll back uncommitted work.",
                     difficulty=3),
                dict(prompt="What does the Redo phase of recovery do?",
                     choices=[("It deletes all uncommitted transactions immediately", False),
                              ("It replays logged changes — including from transactions that never committed — to reach the exact pre-crash state", True),
                              ("It only replays committed transactions", False),
                              ("It rebuilds the WAL from the data pages", False)],
                     explanation="Redo intentionally reapplies everything logged, committed or not; cleaning up uncommitted work is left to the later Undo phase.",
                     difficulty=3),
                dict(prompt="In a log-structured (LSM-tree) storage engine, why must a read potentially check multiple SSTables?",
                     choices=[("Because SSTables are stored in random order with no way to know which is newest", False),
                              ("Because the most recent write to a key could be in any SSTable, so the engine checks from newest to oldest until it finds the key", True),
                              ("Because SSTables never contain the full data", False),
                              ("Because reads always scan the entire disk", False)],
                     explanation="Since writes are append-only, the same key can appear in multiple SSTables — the newest version wins, so search order matters.",
                     difficulty=2),
                dict(prompt="What role does a sparse index play when reading from an SSTable?",
                     choices=[("It stores every key in memory for instant lookup", False),
                              ("It stores periodic key offsets, letting the engine jump close to a key's location and then scan a small range", True),
                              ("It replaces the need for a Bloom filter", False),
                              ("It compresses the SSTable on disk", False)],
                     explanation="A sparse index trades a little scan time for a much smaller memory footprint than indexing every key.",
                     difficulty=2),
             ]),
    ),

    # --- Domain item: merges failure detection/leader election, replication
    # trade-offs, and consensus from this book with DDIA's "trouble with
    # distributed systems" and "consistency and consensus" chapters
    # (cross-book — all five are the "hard parts of distributed systems").
    dict(book='database-internals', slug='distributed-failure-replication-consensus', title='Distributed Systems: Failure Detection, Replication & Consensus',
         topic=TOPIC_DATA, difficulty=3,
         order=2, unlock_level=10,
         summary='Why nodes can never be certain another has failed, how replicas trade off consistency for speed, and how a majority of unreliable nodes agree on anything at all.',
         concept=dict(
            slug='failure-replication-consensus', title='Failure Detection, Replication Trade-offs & Consensus',
            source_note=(
                'Chapters 9-10: Failure Detection, Leader Election; '
                'Chapters 11-12: Replication and Consistency, Anti-Entropy; Chapter 14: Consensus; '
                'DDIA Chapter 8: The Trouble with Distributed Systems; DDIA Chapter 9: Consistency and Consensus'
            ),
            summary=(
                "The hard parts of distributed systems in one place: how nodes guess at failure, how "
                "replicas trade consistency for speed, and how a majority of them agree on anything at all."
            ),
            notes=[
                dict(heading="Failure Detection & Leader Election",
                     body=(
                        "Database Internals, Chapters 9-10, opens with an uncomfortable truth: a node can "
                        "never be *certain* another node has crashed rather than just being slow — all it can "
                        "observe is the absence of expected messages (like periodic heartbeats), and silence "
                        "is ambiguous. Simple failure detectors declare a node dead after missing a fixed "
                        "number of heartbeats in a row; more adaptive ones, like the Phi Accrual failure "
                        "detector, output a continuous suspicion level instead of a hard yes/no verdict, "
                        "tolerating normal network jitter better than a rigid timeout would. Once a failure is "
                        "suspected, something usually needs to elect a new leader — the Bully algorithm "
                        "(simplest: highest node ID wins) or Raft's randomized-timeout election are two common "
                        "approaches."
                     ),
                     deep_dive=dict(
                        title="Split brain",
                        body=(
                            "The nightmare scenario: a network partition splits the cluster into two halves, "
                            "each of which — unable to see the other — independently concludes the old leader "
                            "is dead and elects its own new leader. Now two nodes both believe they're the "
                            "sole leader and may both accept writes, silently diverging the data. This is "
                            "exactly why leader election is normally gated behind a quorum requirement (a "
                            "candidate needs votes from a *majority* of all nodes, not just the ones it can "
                            "currently see) — a partition can produce at most one side with a true majority, "
                            "so at most one new leader can legitimately emerge."
                        ),
                     )),
                dict(heading="Replication Trade-offs & Anti-Entropy",
                     body=(
                        "Chapters 11-12 turn to how strictly replicas must agree once you have more than one "
                        "copy of the data. Synchronous replication waits for a replica (or a quorum of them) "
                        "to acknowledge a write before telling the client it succeeded — strongly consistent, "
                        "but slower, and less available if a replica is temporarily unreachable. Asynchronous "
                        "replication reports success as soon as the leader itself applies the write, letting "
                        "replication to followers happen in the background — faster and more available, but a "
                        "leader crash in that window can lose a write the client was already told succeeded. "
                        "Because asynchronous replication can leave replicas out of sync, anti-entropy "
                        "processes — like read repair (fixing staleness opportunistically during a read) or "
                        "comparing Merkle trees to efficiently find which ranges of data differ — run in the "
                        "background to reconcile drift without needing a full data comparison."
                     )),
                dict(heading="Consensus with Paxos & Raft",
                     body=(
                        "Chapter 14 covers what it takes to get a group of unreliable nodes to agree on a "
                        "single value (or an ordered sequence of them) despite failures — as long as a "
                        "majority stay reachable. Paxos, the foundational algorithm, is provably correct but "
                        "notoriously difficult to reason about and implement correctly. Raft was designed "
                        "explicitly to be more approachable: it always has a single elected leader who "
                        "replicates a log to followers, and once a majority of nodes have acknowledged a "
                        "given log entry, that entry is considered committed. This majority requirement is "
                        "exactly what lets a 5-node Raft cluster keep making progress even if 2 nodes go down "
                        "— 3 remaining nodes is still a majority."
                     )),
                dict(heading="The Trouble with Distributed Systems",
                     body=(
                        "DDIA's Chapter 8 zooms out to why all of this is necessary in the first place: "
                        "distributed systems fail in ways a single machine simply doesn't. A network can "
                        "drop, delay, or reorder messages arbitrarily, with no way from the outside to "
                        "distinguish a slow node from a dead one (the same problem as the opening section, "
                        "restated at the network level). Machine clocks drift, and even NTP-corrected clocks "
                        "can jump backward or be off by tens of milliseconds — enough to make relying on "
                        "wall-clock timestamps to order events across machines unsafe. And a process can "
                        "pause unexpectedly for a surprisingly long time (a garbage collection pause is the "
                        "classic example) and then resume as if no time had passed, potentially violating an "
                        "assumption like 'I still hold this lock' that was true when it paused but isn't "
                        "anymore."
                     )),
                dict(heading="Linearizability & Total Order Broadcast",
                     body=(
                        "DDIA's Chapter 9 names the strongest guarantee a system can offer despite all of the "
                        "above: linearizability. Once a write completes, every subsequent read — from any "
                        "client, on any replica — must see that write or a later one, exactly as if there "
                        "were only a single, up-to-date copy of the data anywhere. It's expensive to provide "
                        "(usually requiring consensus under the hood) but it makes reasoning about the system "
                        "enormously simpler. A related but distinct guarantee is total order broadcast: all "
                        "nodes must deliver the same set of messages in the same relative order, though not "
                        "necessarily in real, wall-clock time."
                     ),
                     deep_dive=dict(
                        title="Why total order broadcast and consensus are the same problem",
                        body=(
                            "It turns out total order broadcast and consensus are equivalent — a solution to "
                            "one can be used to build the other. Intuitively: agreeing on the *n*-th message "
                            "in a total order is exactly agreeing on a single value (consensus) for position "
                            "*n*. This equivalence is why systems that need strong guarantees so often "
                            "implement a consensus algorithm like Raft or Paxos under the hood — a replicated, "
                            "totally-ordered log falls out of it almost for free."
                        ),
                     )),
            ],
            questions=[
                dict(prompt="Why can't a node be 100% certain that another node has actually crashed (versus just being slow)?",
                     choices=[("Because failure detection always requires a shared clock", False),
                              ("Because in an asynchronous network, there's no way to distinguish 'crashed' from 'slow to respond' with certainty", True),
                              ("Because heartbeats are always reliable so this never happens", False),
                              ("Because only the leader can detect failures", False)],
                     explanation="This is a fundamental result in distributed systems — perfect failure detection is impossible with unbounded network delay.",
                     difficulty=3),
                dict(prompt="What does a 'split brain' scenario refer to?",
                     choices=[("A single node running out of memory", False),
                              ("A network partition causing two sides to each elect their own leader, potentially both accepting writes", True),
                              ("A database schema having two primary keys", False),
                              ("A node restarting unexpectedly", False)],
                     explanation="Split brain is dangerous specifically because both sides may believe they're the sole leader and diverge independently.",
                     difficulty=2),
                dict(prompt="What is an advantage of the Phi Accrual failure detector over a simple fixed-heartbeat-timeout detector?",
                     choices=[("It never produces false positives", False),
                              ("It outputs an adaptive suspicion level rather than a hard binary alive/dead judgment, tolerating normal network jitter better", True),
                              ("It doesn't require heartbeats at all", False),
                              ("It only works for a single node", False)],
                     explanation="A continuous suspicion score lets applications set their own sensitivity threshold instead of one fixed cutoff.",
                     difficulty=3),
                dict(prompt="What is the main trade-off of synchronous replication compared to asynchronous replication?",
                     choices=[("Synchronous replication is always faster", False),
                              ("Synchronous replication offers stronger consistency but is slower and less available if a replica is unreachable", True),
                              ("Asynchronous replication guarantees zero data loss", False),
                              ("Synchronous replication doesn't require a leader", False)],
                     explanation="Waiting for replica acknowledgment before confirming a write guarantees durability across replicas, at the cost of latency and availability.",
                     difficulty=2),
                dict(prompt="What risk does asynchronous replication introduce that synchronous replication avoids?",
                     choices=[("Higher write latency", False),
                              ("A crash on the leader right after acknowledging a write can lose that write before it reaches any replica", True),
                              ("Replicas can never be read from", False),
                              ("It requires more replicas than synchronous replication", False)],
                     explanation="Since the leader confirms the write before replicas have it, a leader crash in that window means the write is gone even though the client was told it succeeded.",
                     difficulty=2),
                dict(prompt="What is the purpose of an anti-entropy process like read repair?",
                     choices=[("To encrypt replicated data", False),
                              ("To detect and reconcile replicas that have drifted out of sync over time", True),
                              ("To elect a new leader", False),
                              ("To compress the replication log", False)],
                     explanation="Anti-entropy runs in the background (or opportunistically during reads) to catch and fix inconsistencies asynchronous replication can leave behind.",
                     difficulty=2),
                dict(prompt="What is the primary design goal that distinguishes Raft from Paxos?",
                     choices=[("Raft doesn't require a majority quorum", False),
                              ("Raft was designed to be easier to understand and implement, by explicitly electing a single leader", True),
                              ("Raft eliminates the need for a network", False),
                              ("Paxos is faster in every scenario", False)],
                     explanation="Paxos is correct but famously hard to reason about; Raft restructures the same guarantees around explicit leader election.",
                     difficulty=2),
                dict(prompt="In Raft, how is a new leader elected?",
                     choices=[("The node with the lowest IP address always becomes leader", False),
                              ("Nodes use randomized election timeouts so whichever node times out first requests votes and typically wins a majority", True),
                              ("Leaders are assigned manually by an administrator every time", False),
                              ("There is no leader in Raft", False)],
                     explanation="Randomizing timeouts reduces the odds of two nodes starting an election simultaneously and splitting the vote.",
                     difficulty=2),
                dict(prompt="A consensus system with 5 nodes can safely continue operating if how many nodes fail?",
                     choices=[("Up to 4 nodes can fail and it still works", False),
                              ("Up to 2 nodes can fail (a majority of 3 must remain reachable)", True),
                              ("Any single node failure stops the whole system", False),
                              ("It requires all 5 nodes to be up at all times", False)],
                     explanation="Consensus requires a majority (quorum) — with 5 nodes, that's 3, so up to 2 can be down while the system keeps making progress.",
                     difficulty=2),
                dict(prompt="Why is it unsafe to rely on wall-clock timestamps to determine the order of events across different machines?",
                     choices=[("Wall clocks are always perfectly synchronized in practice", False),
                              ("Clocks drift and can even jump backward, so timestamp order doesn't reliably reflect actual event order", True),
                              ("Wall clocks only exist on a single machine", False),
                              ("Timestamps are always synchronized by the network layer automatically", False)],
                     explanation="Even NTP-synchronized clocks can be off by tens of milliseconds or jump when corrected — enough to misorder closely-timed events.",
                     difficulty=2),
                dict(prompt="What makes 'partial failure' uniquely hard to handle in distributed systems, compared to a single machine crashing?",
                     choices=[("Partial failure never actually happens in real systems", False),
                              ("There's no reliable way to distinguish a slow, still-alive node from a truly dead one, from the outside", True),
                              ("Partial failure only affects hardware, not software", False),
                              ("Single machines never fail, so there's nothing to compare to", False)],
                     explanation="On a single machine a crash is usually unambiguous; across a network, the only signal is silence, and silence could mean many things.",
                     difficulty=2),
                dict(prompt="What does linearizability guarantee about reads after a write completes?",
                     choices=[("Reads may return stale data indefinitely", False),
                              ("Every subsequent read, from any client, must see that write or a later one, as if there were only one copy of the data", True),
                              ("Only the client who performed the write can see it", False),
                              ("Reads are guaranteed to be faster than writes", False)],
                     explanation="Linearizability makes a distributed, replicated system behave, from the outside, like a single up-to-date copy of the data.",
                     difficulty=2),
                dict(prompt="What is total order broadcast a guarantee about?",
                     choices=[("Encrypting messages between nodes", False),
                              ("All nodes delivering the same set of messages in the same order", True),
                              ("Guaranteeing messages arrive within a fixed time limit", False),
                              ("Preventing any node from ever going offline", False)],
                     explanation="Total order broadcast says nothing about timing — only that all nodes deliver messages in the same relative order.",
                     difficulty=2),
                dict(prompt="What is the relationship between total order broadcast and consensus?",
                     choices=[("They are unrelated problems solved with completely different techniques", False),
                              ("They are equivalent problems — a solution to one can be used to build the other", True),
                              ("Total order broadcast is always faster than any consensus algorithm", False),
                              ("Consensus is only relevant to single-node systems", False)],
                     explanation="This equivalence is why consensus algorithms like Raft are so often used under the hood to implement a replicated, totally-ordered log.",
                     difficulty=3),
             ]),
    ),

    # =========================================================================
    # --- Book 4: Designing Data-Intensive Applications ---
    # =========================================================================

    # --- Domain item: merges DDIA's reliability/scalability/maintainability,
    # data models, partitioning, and transactions chapters. (Storage and
    # Retrieval, and the two "trouble with distributed systems" chapters,
    # moved into the Database Internals domains above since they're the same
    # topics.)
    dict(book='designing-data-intensive-apps', slug='data-systems-fundamentals', title='Data Systems Fundamentals: Models, Partitioning & Transactions',
         topic=TOPIC_DATA, difficulty=3,
         order=1, unlock_level=12,
         summary='What makes a data system "good", how relational/document/graph models differ, how datasets get split across machines, and what isolation levels actually promise.',
         concept=dict(
            slug='data-systems-models-partitioning-transactions', title='Reliability, Data Models, Partitioning & Isolation',
            source_note=(
                'Chapter 1: Reliable, Scalable, and Maintainable Applications; '
                'Chapter 2: Data Models and Query Languages; Chapter 6: Partitioning; Chapter 7: Transactions'
            ),
            summary=(
                "What makes a data system 'good,' how relational/document/graph models differ, how you split "
                "a dataset across machines, and what isolation levels actually promise you."
            ),
            notes=[
                dict(heading="Reliable, Scalable, Maintainable",
                     body=(
                        "DDIA Chapter 1 frames good data systems around three properties. Reliability means "
                        "the system keeps working correctly even when things go wrong, by tolerating faults "
                        "(one component deviating from spec) rather than assuming they won't happen, so a "
                        "single fault doesn't cascade into a failure (the system as a whole ceasing to provide "
                        "the required service). Scalability is the ability to cope with growing load, and "
                        "Kleppmann insists on measuring it with response-time percentiles like p50/p95/p99 "
                        "rather than the average, since an average dominated by fast requests can completely "
                        "hide the tail latency that actually frustrates users. Maintainability covers "
                        "operability, simplicity, and evolvability — how easily the system can be understood, "
                        "operated, and adapted to new requirements as they inevitably change."
                     )),
                dict(heading="Relational, Document & Graph Data Models",
                     body=(
                        "Chapter 2 walks through how the shape of your data should drive the choice of model. "
                        "The relational model organizes data into tables of rows with a fixed schema and "
                        "excels at many-to-many relationships via joins. The document model (JSON documents, "
                        "as in MongoDB) stores nested, self-contained records that map naturally to "
                        "application objects and suits tree-like, one-to-many data that's usually fetched as a "
                        "single unit — but it's more awkward once many-to-many relationships enter the "
                        "picture. The graph model (nodes and edges) shines when the relationships between "
                        "records are just as important as the records themselves: social networks, "
                        "recommendation engines, and fraud detection are classic examples."
                     )),
                dict(heading="Partitioning: Splitting Data Across Machines",
                     body=(
                        "Chapter 6 covers what happens once a dataset outgrows a single machine: partitioning "
                        "(sharding) splits it across many nodes. Key-range partitioning assigns contiguous "
                        "ranges of keys to each partition, which keeps range queries efficient but risks hot "
                        "spots if access patterns cluster around particular key ranges (e.g. all of 'today's' "
                        "writes). Hash partitioning distributes keys much more evenly across partitions, "
                        "avoiding those hot spots, but it sacrifices the ability to run efficient range "
                        "queries, since adjacent keys end up scattered across unrelated partitions. Either "
                        "way, as data keeps growing, partitions need to be rebalanced across nodes — ideally "
                        "without stopping reads or writes while it happens."
                     )),
                dict(heading="Transaction Isolation Levels",
                     body=(
                        "Chapter 7 makes the point that ACID's 'isolation' is a spectrum of guarantees, not "
                        "one fixed thing. Read Committed prevents dirty reads (seeing another transaction's "
                        "uncommitted writes) but still allows non-repeatable reads (the same query run twice "
                        "in one transaction can return different results). Snapshot Isolation gives each "
                        "transaction a consistent view of the database as of when it started, which prevents "
                        "most common anomalies but still permits write skew. Serializability is the strongest "
                        "level: it guarantees a result equivalent to running every transaction one at a time "
                        "in some order, even though they may have actually executed concurrently."
                     ),
                     deep_dive=dict(
                        title="Write skew: the anomaly snapshot isolation doesn't catch",
                        body=(
                            "Write skew happens when two transactions each read the same overlapping data, "
                            "and — based on what they read — each makes a different, disjoint write that "
                            "together violates an invariant that neither transaction violated on its own. "
                            "Classic example: two on-call doctors each check 'is at least one other doctor "
                            "on call?', both see yes, and both then remove themselves from on-call duty, "
                            "leaving nobody on call — even though each transaction's own snapshot looked "
                            "perfectly valid in isolation. Snapshot isolation can't catch this because "
                            "neither transaction ever saw the other's write; preventing it requires either "
                            "true serializable isolation or an explicit lock on the invariant being checked."
                        ),
                     )),
            ],
            questions=[
                dict(prompt="What is the distinction between a 'fault' and a 'failure' in Kleppmann's framing?",
                     choices=[("They are exactly the same thing", False),
                              ("A fault is one component deviating from spec; a failure is the system as a whole ceasing to provide the required service", True),
                              ("A fault only applies to hardware, a failure only to software", False),
                              ("A failure is less serious than a fault", False)],
                     explanation="Reliable systems are built to tolerate faults so they don't cascade into full failures.",
                     difficulty=2),
                dict(prompt="Why do engineers typically care more about p95/p99 response time percentiles than the average?",
                     choices=[("Percentiles are easier to calculate than averages", False),
                              ("Averages can hide tail latency — the slow requests that disproportionately affect real users' experience", True),
                              ("p99 is always lower than the average", False),
                              ("Percentiles eliminate the need for load testing", False)],
                     explanation="A handful of very slow requests can be masked by an average dominated by many fast ones, but those slow requests are often what customers notice.",
                     difficulty=2),
                dict(prompt="What does 'evolvability' refer to as an aspect of maintainability?",
                     choices=[("How fast the system runs under peak load", False),
                              ("How easily the system can be adapted to new, unanticipated requirements over time", True),
                              ("How many servers the system uses", False),
                              ("How much the system costs to operate", False)],
                     explanation="Software requirements change constantly — evolvability is about keeping the system easy to change.",
                     difficulty=1),
                dict(prompt="When is the document model a particularly good fit?",
                     choices=[("When data has many-to-many relationships that need frequent joins", False),
                              ("When data has a tree-like, self-contained structure that's usually accessed as a whole unit", True),
                              ("When strict schema enforcement is the top priority", False),
                              ("Only for numerical/scientific data", False)],
                     explanation="Documents map naturally to one-to-many, nested application objects — many-to-many relationships fit the relational model better.",
                     difficulty=2),
                dict(prompt="What is a key advantage of declarative query languages like SQL over imperative code for fetching data?",
                     choices=[("Declarative languages always run on a single thread", False),
                              ("They state the desired result and let the database choose and optimize the execution strategy", True),
                              ("They cannot express joins", False),
                              ("They require manually specifying an index for every query", False)],
                     explanation="Because the database controls execution, it can parallelize and optimize a declarative query in ways hard to retrofit onto hand-written fetch logic.",
                     difficulty=2),
                dict(prompt="The graph data model is especially well suited to which kind of problem?",
                     choices=[("Storing a single flat list of unrelated records", False),
                              ("Problems where relationships between records are as important as the records themselves, like social networks or fraud detection", True),
                              ("Only storing images and binary files", False),
                              ("Enforcing a rigid, unchanging schema", False)],
                     explanation="Graphs make traversing and querying complex, evolving relationships natural in a way repeated joins can struggle with at scale.",
                     difficulty=1),
                dict(prompt="What is the main downside of key-range partitioning?",
                     choices=[("It makes range queries impossible", False),
                              ("Access patterns can create hot spots if writes/reads cluster around specific key ranges", True),
                              ("It always requires more storage than hash partitioning", False),
                              ("It cannot be combined with replication", False)],
                     explanation="If all 'today's' writes land in one range-based partition, that partition becomes a bottleneck even with spare cluster capacity.",
                     difficulty=2),
                dict(prompt="What do you give up by switching from key-range partitioning to hash partitioning?",
                     choices=[("Nothing, hash partitioning is strictly better", False),
                              ("The ability to efficiently run range queries, since adjacent keys are scattered across partitions", True),
                              ("The ability to write to the database at all", False),
                              ("Fault tolerance", False)],
                     explanation="Hashing spreads load evenly but destroys the natural ordering that made scanning a range of keys efficient.",
                     difficulty=2),
                dict(prompt="What anomaly does Read Committed isolation prevent, and what does it still allow?",
                     choices=[("It prevents all anomalies including write skew", False),
                              ("It prevents dirty reads (seeing uncommitted data) but still allows non-repeatable reads", True),
                              ("It prevents non-repeatable reads but allows dirty reads", False),
                              ("It provides no guarantees at all", False)],
                     explanation="Read Committed is a relatively weak isolation level — it stops dirty reads, but the same query run twice in one transaction can still see different results.",
                     difficulty=2),
                dict(prompt="What is 'write skew' under snapshot isolation?",
                     choices=[("Two transactions writing to the exact same row and one being silently discarded", False),
                              ("Two transactions each read overlapping data and make disjoint writes based on it, together violating an invariant that neither violated alone", True),
                              ("A transaction that takes too long to commit", False),
                              ("A hardware error during a write", False)],
                     explanation="Because each transaction only checks its own snapshot, it can't see the other transaction's concurrent write.",
                     difficulty=3),
                dict(prompt="What does 'serializable' isolation guarantee?",
                     choices=[("Transactions run faster than any other isolation level", False),
                              ("The result is equivalent to running all transactions one at a time in some order, even if they actually ran concurrently", True),
                              ("Only one transaction can exist in the database at a time, ever", False),
                              ("It guarantees zero data loss on crash, unrelated to concurrency", False)],
                     explanation="Serializability is about the observable outcome matching some serial execution — it says nothing about actual physical concurrency.",
                     difficulty=2),
             ]),
    ),

    # --- System design item (kept as-is): a specific replication topology to
    # build, already has its own builder game.
    dict(book='designing-data-intensive-apps', slug='replication-ddia', title='Replication',
         topic=TOPIC_DATA, difficulty=2,
         order=2, unlock_level=13, summary='Keeping a copy of the same data on multiple machines.',
         concept=dict(
            slug='leader-based-replication', title='Leader-Based Replication',
            source_note='Chapter 5: Replication',
            summary=(
                "Why funneling all writes through a single leader is what makes replication ordering "
                "simple — and what that simplicity costs you when the leader fails."
            ),
            notes=[
                dict(heading="One Leader, Many Followers",
                     body=(
                        "Kleppmann's Designing Data-Intensive Applications, Chapter 5, describes leader-based "
                        "(also called master-slave, or primary-replica) replication as the default building "
                        "block for keeping the same data on multiple machines. All writes are directed to a "
                        "single leader node, which appends each change to its own replication log. Follower "
                        "nodes connect to the leader and replay that log in the exact order it was written, "
                        "which keeps them converging toward the same state the leader has. Reads, meanwhile, "
                        "can be served by the leader or by any follower, since followers (once caught up) "
                        "hold a valid copy of the data."
                     )),
                dict(heading="Why a Single Leader Simplifies Ordering",
                     body=(
                        "The reason this design is so common isn't just simplicity for its own sake — "
                        "centralizing writes on one node solves a genuinely hard problem for free. If two "
                        "different nodes could each accept writes independently, the system would need some "
                        "mechanism to decide which of two concurrent, conflicting writes 'wins' and in what "
                        "order. With a single leader, there's no ambiguity: the leader's replication log *is* "
                        "the order, and every follower just replays it faithfully. Offloading reads to "
                        "followers is the other major payoff — it scales read capacity horizontally (add more "
                        "followers, serve more reads) without touching or complicating the write path at all."
                     ),
                     deep_dive=dict(
                        title="What happens when the leader dies?",
                        body=(
                            "This is the design's biggest weakness: the leader is a single point of failure "
                            "for writes. When it goes down, something has to promote a follower to become "
                            "the new leader (failover) before writes can resume — done carelessly, this can "
                            "either lose recent writes that hadn't yet replicated to the promoted follower, "
                            "or, worse, produce two nodes simultaneously believing they're the leader (split "
                            "brain) if the old leader comes back online unaware it's been replaced. Robust "
                            "failover needs careful coordination (often via a consensus mechanism) to avoid "
                            "exactly these failure modes."
                        ),
                     )),
            ],
            questions=[
                dict(prompt="In leader-based replication, where do all writes go?",
                     choices=[("To any follower chosen at random", False),
                              ("To the single leader, which then propagates changes to followers", True),
                              ("Writes are split evenly across all nodes with no leader", False),
                              ("To a separate write-only server unrelated to the leader or followers", False)],
                     explanation="Centralizing writes on the leader is what makes ordering straightforward — the leader's log defines the order every follower replays.",
                     difficulty=1),
                dict(prompt="What can followers typically do in a leader-based replication setup?",
                     choices=[("Nothing — they exist only as passive backups", False),
                              ("Serve read queries, reducing load on the leader", True),
                              ("Accept writes just like the leader", False),
                              ("Elect a new leader without any coordination", False)],
                     explanation="Offloading reads to followers is one of the main reasons to use leader-based replication — it scales read capacity horizontally.",
                     difficulty=1),
                dict(prompt="Why does centralizing all writes on a single leader simplify replication ordering?",
                     choices=[("It doesn't — ordering is still ambiguous", False),
                              ("The leader's replication log defines a single, unambiguous order that every follower replays identically", True),
                              ("Because followers write directly to each other", False),
                              ("Because writes are randomly ordered anyway", False)],
                     explanation="A single writer producing one log removes any question of 'which write happened first' — every follower sees the same sequence.",
                     difficulty=2),
                dict(prompt="What typically needs to happen if the leader in a leader-based replication setup fails?",
                     choices=[("The system halts permanently with no recovery process", False),
                              ("A new leader typically needs to be elected/promoted so writes can resume", True),
                              ("Followers automatically become read-only forever", False),
                              ("All replicated data is lost", False)],
                     explanation="Failover — promoting a follower to leader — is how the system keeps accepting writes after a leader crash.",
                     difficulty=2),
                dict(prompt="Why might a client reading from a follower shortly after writing to the leader see stale data?",
                     choices=[("Because followers never receive updates", False),
                              ("Because replication to that follower may not have caught up yet (replication lag)", True),
                              ("Because followers only store metadata", False),
                              ("Because reads are always served by the leader", False)],
                     explanation="Asynchronous replication lag means a follower can briefly lag behind the leader's latest committed write.",
                     difficulty=2),
                dict(prompt="What is one reason NOT to let followers accept writes directly in a simple leader-based scheme?",
                     choices=[("It would create multiple sources of truth and complicate conflict resolution and ordering", True),
                              ("Followers are technically incapable of processing any writes", False),
                              ("It would violate HTTP standards", False),
                              ("There's no downside — many systems do this without issue", False)],
                     explanation="Allowing writes at multiple nodes reintroduces the exact ordering/conflict problems a single leader was meant to avoid.",
                     difficulty=2),
             ]),
    ),

    # =========================================================================
    # --- Book 5: Linux Pocket Guide ---
    # =========================================================================

    # --- Domain item: all six Linux Pocket Guide chapters merged into one
    # "practical CLI skills" domain — these were always a loosely related
    # grab-bag of commands rather than a single narrative.
    dict(book='linux-pocket-guide', slug='linux-command-line-essentials', title='Linux Command-Line Essentials',
         topic=TOPIC_OS, difficulty=1,
         order=1, unlock_level=16,
         summary='Navigation, permissions, processes, text pipelines, package management, and networking — the day-to-day shell toolkit.',
         concept=dict(
            slug='linux-cli-essentials', title='Navigation, Permissions, Processes, Pipelines, Packages & Networking',
            source_note=(
                'Navigating the Filesystem; File Permissions; Process Management; '
                'Searching Files, Viewing Files; Installing Software; Networking'
            ),
            summary=(
                "The Linux Pocket Guide's day-to-day shell toolkit: getting around the filesystem, "
                "permissions, processes, chaining commands, installing software, and basic networking."
            ),
            notes=[
                dict(heading="Navigating the Filesystem",
                     body=(
                        "A handful of commands cover most day-to-day filesystem navigation. pwd prints your "
                        "current working directory. cd changes into another directory, and cd - specifically "
                        "jumps back to whichever directory you were in before the last cd. ls -la lists "
                        "directory contents including hidden (dotfile) entries, in long format showing "
                        "permissions and sizes. mkdir -p creates a directory along with any missing parent "
                        "directories in the path, without erroring if some of them already exist. find "
                        "searches a directory tree recursively, matching by name, type, size, or modification "
                        "time."
                     )),
                dict(heading="File Permissions",
                     body=(
                        "Every file carries permissions for three separate classes of user — owner, group, "
                        "and others — each with its own read/write/execute bits. chmod changes those "
                        "permissions, either symbolically (chmod u+x adds execute permission for the owner "
                        "only) or numerically (chmod 755 sets rwx for the owner and r-x for group and others, "
                        "since each digit is a sum of read=4, write=2, execute=1). chown changes which user "
                        "and group own a file. umask sets the default permission bits that get stripped away "
                        "from every newly created file, without needing to chmod each one afterward."
                     )),
                dict(heading="Process Management",
                     body=(
                        "ps aux (or the equivalent ps -ef) lists every running process along with its PID "
                        "(process ID), which is what you need to target it. kill <PID> sends SIGTERM, which "
                        "politely asks the process to shut down and gives it a chance to clean up first."
                     ),
                     deep_dive=dict(
                        title="SIGTERM vs. SIGKILL",
                        body=(
                            "kill -9 <PID> sends SIGKILL instead of the default SIGTERM. The critical "
                            "difference: SIGTERM is a request the process can intercept and handle (to save "
                            "state, close files, or otherwise clean up before exiting), while SIGKILL is "
                            "enforced directly by the OS kernel and cannot be caught, blocked, or ignored by "
                            "the process at all — it dies immediately, with no chance to clean up. That makes "
                            "SIGKILL a last resort for a genuinely stuck process, not a first move, since "
                            "skipping cleanup can leave behind locked resources or corrupted partial state."
                        ),
                     )),
                dict(heading="Searching & Viewing Files: Chaining Commands with Pipes",
                     body=(
                        "The Unix philosophy is small, single-purpose tools chained together with the pipe "
                        "(|) operator, which feeds one command's output directly into the next command's "
                        "input. grep filters lines matching a pattern; sort puts lines in order; uniq -c "
                        "collapses adjacent duplicate lines into one and counts how many times each appeared "
                        "— note that uniq only compares *neighboring* lines, which is exactly why it needs "
                        "sorted input to work correctly. Chaining these together — "
                        "grep pattern file | sort | uniq -c | sort -rn — is one of the most common shell "
                        "idioms there is, for counting and ranking how often something appears in a file."
                     )),
                dict(heading="Installing Software",
                     body=(
                        "On Debian/Ubuntu-family systems, apt is the high-level package manager most day-to-"
                        "day work goes through: apt update refreshes the local list of available packages and "
                        "their versions, apt install resolves and installs a package's dependencies "
                        "automatically, and apt remove uninstalls it again. dpkg sits one level lower — it can "
                        "install a .deb package file directly, but it doesn't resolve or fetch dependencies on "
                        "its own, which is exactly why apt (which wraps dpkg and adds dependency resolution) "
                        "is what's normally used instead."
                     )),
                dict(heading="Networking",
                     body=(
                        "A small set of commands covers most basic networking tasks. ping checks whether a "
                        "host is reachable and reports round-trip latency. curl fetches a URL's content "
                        "directly from the command line, useful for testing an API or downloading a file "
                        "without a browser. ssh opens a secure, encrypted remote shell on another machine. scp "
                        "copies files to or from a remote machine over that same underlying SSH connection, so "
                        "it inherits SSH's authentication and encryption for free."
                     )),
            ],
            questions=[
                dict(prompt="What does `cd -` do?",
                     choices=[("Deletes the current directory", False),
                              ("Switches back to the previous working directory", True),
                              ("Creates a new directory", False),
                              ("Lists hidden files", False)],
                     explanation="`cd -` is a shortcut for toggling between your current and previous directory.",
                     difficulty=1),
                dict(prompt="What does the `-p` flag do when used with `mkdir`?",
                     choices=[("It prints the directory path after creating it", False),
                              ("It creates any missing parent directories along the way, without erroring if they already exist", True),
                              ("It permanently locks the directory", False),
                              ("It sets permissions to private", False)],
                     explanation="Without `-p`, `mkdir a/b/c` fails if `a` or `a/b` don't already exist; with `-p`, all are created as needed.",
                     difficulty=1),
                dict(prompt="Which command would you use to recursively find all `.log` files modified in the last 7 days?",
                     choices=[("ls -la *.log", False),
                              ('find . -name "*.log" -mtime -7', True),
                              ('grep -r ".log" .', False),
                              ("cd *.log", False)],
                     explanation="`find` is built for exactly this kind of recursive, attribute-based search.",
                     difficulty=2),
                dict(prompt="What does the numeric permission `644` grant?",
                     choices=[("Read+write for everyone", False),
                              ("Read+write for the owner, read-only for group and others", True),
                              ("Full access (rwx) for everyone", False),
                              ("No access for anyone", False)],
                     explanation="6 = read(4)+write(2) for the owner, 4 = read only for group, 4 = read only for others.",
                     difficulty=2),
                dict(prompt="What does `chmod u+x script.sh` do?",
                     choices=[("Removes execute permission from everyone", False),
                              ("Adds execute permission for the file's owner only", True),
                              ("Adds execute permission for everyone", False),
                              ("Deletes the script", False)],
                     explanation="The symbolic form `u+x` targets just the 'user' (owner) class and adds the execute bit.",
                     difficulty=1),
                dict(prompt="What does the `chown` command do?",
                     choices=[("Changes a file's read/write/execute permissions", False),
                              ("Changes a file's owner and/or group", True),
                              ("Compresses a file", False),
                              ("Renames a file", False)],
                     explanation="`chmod` controls what actions are allowed; `chown` controls who the owner and group are.",
                     difficulty=1),
                dict(prompt="What is the difference between `kill PID` and `kill -9 PID`?",
                     choices=[("They are identical commands", False),
                              ("`kill PID` sends SIGTERM (a polite request the process can catch and clean up after); `kill -9` sends SIGKILL, which the OS enforces immediately", True),
                              ("`kill -9` is gentler than plain `kill`", False),
                              ("`kill PID` only works on your own processes while `kill -9` works on any process", False)],
                     explanation="SIGTERM gives a process a chance to clean up; SIGKILL gives it no choice at all.",
                     difficulty=2),
                dict(prompt="What information does `ps aux` help you find that you need before killing a process?",
                     choices=[("The process's source code", False),
                              ("The process's PID (process ID)", True),
                              ("The process's IP address", False),
                              ("The process's file permissions", False)],
                     explanation="`kill` operates on a PID, not a process name, so you need `ps` (often piped through grep) to look it up first.",
                     difficulty=1),
                dict(prompt="Why must input be sorted before piping it into `uniq -c`?",
                     choices=[("`uniq` doesn't actually need sorted input", False),
                              ("`uniq` only compares adjacent lines, so duplicates must already be next to each other to be counted correctly", True),
                              ("Sorting is only needed for numeric data", False),
                              ("`uniq -c` sorts the data itself internally", False)],
                     explanation="`uniq` has no memory of lines it saw earlier — it only catches duplicates directly next to each other.",
                     difficulty=2),
                dict(prompt="In the pipeline `grep 'ERROR' file | sort | uniq -c | sort -rn`, what does the final `sort -rn` accomplish?",
                     choices=[("It removes duplicate lines", False),
                              ("It sorts the counted, unique lines numerically with the highest count first", True),
                              ("It searches for the word 'ERROR' again", False),
                              ("It reverses the alphabetical order of the original file", False)],
                     explanation="After `uniq -c` prefixes each unique line with its count, `sort -rn` lists the most frequent lines at the top.",
                     difficulty=2),
                dict(prompt="What is the key difference between `apt` and `dpkg`?",
                     choices=[("They are unrelated tools for different operating systems", False),
                              ("`apt` is a high-level manager that resolves dependencies automatically; `dpkg` installs .deb files directly but does not resolve dependencies", True),
                              ("`dpkg` is newer and replaces `apt` entirely", False),
                              ("`apt` only removes packages, never installs them", False)],
                     explanation="`apt` actually uses `dpkg` under the hood, but adds dependency resolution and repository management on top.",
                     difficulty=2),
                dict(prompt="What does `apt update` do?",
                     choices=[("Installs all available updates immediately", False),
                              ("Refreshes the local list of available packages and versions from the configured repositories", True),
                              ("Removes unused packages", False),
                              ("Upgrades the Linux kernel", False)],
                     explanation="`apt update` only refreshes package metadata; actually installing newer versions is a separate step (apt upgrade).",
                     difficulty=1),
                dict(prompt="What does `ping` measure?",
                     choices=[("Disk read/write speed", False),
                              ("Whether a host is reachable and the round-trip latency to it", True),
                              ("The number of open ports on a host", False),
                              ("DNS resolution time only", False)],
                     explanation="`ping` sends ICMP echo requests and times the replies — the simplest 'is this host up' check.",
                     difficulty=1),
                dict(prompt="What is `scp` used for?",
                     choices=[("Compressing files", False),
                              ("Copying files to or from a remote machine over SSH", True),
                              ("Searching file contents", False),
                              ("Changing file permissions", False)],
                     explanation="`scp` reuses SSH's encrypted connection specifically to transfer files instead of opening an interactive shell.",
                     difficulty=1),

                # --- Added from verified web sources: man7.org, kernel.org, GNU coreutils
                # manual, Red Hat/SUSE/Oracle systemd docs, OpenSSH man pages ---

                # Permissions deep-dive
                dict(prompt="What is the default umask value for a typical non-root user on most Linux distributions?",
                     choices=[("0002", True), ("0000", False),
                              ("0777", False), ("0644", False)],
                     explanation="A umask of 0002 subtracts write permission for 'others' from the base 666/777 permissions, which is the common default for regular users. (Source: Red Hat / nixCraft umask documentation)",
                     difficulty=2),
                dict(prompt="Given a umask of 0022, what permissions will a newly created regular file end up with?",
                     choices=[("644 (rw-r--r--)", True), ("755 (rwxr-xr-x)", False),
                              ("666 (rw-rw-rw-)", False), ("600 (rw-------)", False)],
                     explanation="Files start from a base of 666; a umask of 022 subtracts write permission from group and others, leaving 644. (Source: Red Hat file permissions documentation)",
                     difficulty=2),
                dict(prompt="What does the setuid bit do when set on an executable file?",
                     choices=[("Runs the program with the permissions of the file's owner, not the user running it", True), ("Prevents the file from ever being executed by anyone", False),
                              ("Forces the file to run only when invoked by the root account", False), ("Makes the file permanently read-only for every user", False)],
                     explanation="setuid lets a program temporarily run with its owner's privileges — classic examples are tools like passwd that need brief root access. (Source: setuid/setgid/sticky bit documentation)",
                     difficulty=2),
                dict(prompt="What does the sticky bit do when set on a shared directory?",
                     choices=[("Only the file's owner, the directory's owner, or root can delete or rename files inside it", True), ("It prevents any new files from ever being created in the directory", False),
                              ("It makes every file inside the directory execute automatically", False), ("It hides the directory entirely from directory listings", False)],
                     explanation="The sticky bit is what makes shared directories like /tmp usable: anyone can add files, but only the owner (or root) can remove someone else's. (Source: setuid/setgid/sticky bit documentation)",
                     difficulty=2),
                dict(prompt="In octal chmod notation (e.g. `chmod 4755 file`), what numeric value represents the setuid bit?",
                     choices=[("4", True), ("1", False),
                              ("2", False), ("8", False)],
                     explanation="The special-permissions digit is setuid=4, setgid=2, sticky=1 — they can be added together and combined with the normal rwx digits. (Source: setuid/setgid/sticky bit documentation)",
                     difficulty=2),
                dict(prompt="What does setting the setgid bit on a directory (rather than on a file) do?",
                     choices=[("New files created inside automatically inherit the directory's group ownership", True), ("It permanently deletes the directory's existing group ownership", False),
                              ("It prevents any group members from being able to read the directory", False), ("It converts the directory into a symbolic link to another path", False)],
                     explanation="setgid on a directory is commonly used for shared team folders, so every new file lands in the right group without anyone remembering to chgrp it. (Source: setuid/setgid/sticky bit documentation)",
                     difficulty=3),

                # Process management
                dict(prompt="What range of nice values can a Linux process have, from highest scheduling priority to lowest?",
                     choices=[("-20 (highest priority) to 19 (lowest priority)", True), ("0 to 100, with 100 being highest priority", False),
                              ("-100 to 100, with 0 as the midpoint default", False), ("1 to 10, with 10 being highest priority", False)],
                     explanation="Nice values run from -20 (most favored by the scheduler) to 19 (least favored); the name comes from how 'nice' a process is being to its peers. (Source: renice(1) Linux manual page)",
                     difficulty=2),
                dict(prompt="Who is allowed to set a negative (higher-priority) nice value for a process?",
                     choices=[("Only the root user", True), ("Any user at all, with no restriction", False),
                              ("Only the process's original parent process", False), ("No one — negative nice values are always disallowed", False)],
                     explanation="Unprivileged users can only raise their own processes' nice value (lower priority), never lower it — that's reserved for root. (Source: renice(1) Linux manual page)",
                     difficulty=2),
                dict(prompt="What is the key difference between the `nice` and `renice` commands?",
                     choices=[("`nice` sets priority when starting a new process; `renice` changes the priority of one already running", True), ("`nice` only works on processes owned by root; `renice` works on any process", False),
                              ("`nice` changes CPU priority only; `renice` changes disk I/O priority only", False), ("They are two completely different names for exactly the same underlying command", False)],
                     explanation="`nice` launches a fresh process at a given priority, while `renice` adjusts the priority of a process that's already running. (Source: Linux process management documentation)",
                     difficulty=1),
                dict(prompt="What does prefixing a command with `nohup` accomplish?",
                     choices=[("Keeps the command running even after the user logs out, immune to hangup signals", True), ("Pauses the command's execution until the terminal window is closed", False),
                              ("Automatically restarts the command if it happens to crash", False), ("Runs the command silently, suppressing all of its output", False)],
                     explanation="nohup specifically ignores the SIGHUP signal a process would otherwise get when its controlling terminal closes, so it keeps running after logout. (Source: Linux process management documentation)",
                     difficulty=2),
                dict(prompt="What does the `jobs` command show in an interactive shell?",
                     choices=[("The background and suspended jobs running in the current shell session", True), ("Every process running anywhere on the entire system", False),
                              ("The system's scheduled cron jobs and their next run times", False), ("A list of every user currently logged into the machine", False)],
                     explanation="`jobs` is scoped to the current shell session — it won't show processes from other terminals or other users. (Source: Linux job control documentation)",
                     difficulty=1),
                dict(prompt="After suspending a foreground process with Ctrl+Z, which command resumes it running in the background?",
                     choices=[("`bg`", True), ("`fg`", False),
                              ("`jobs`", False), ("`nohup`", False)],
                     explanation="Ctrl+Z suspends the process; `bg` resumes it in the background, while `fg` would instead bring it back to the foreground. (Source: Linux job control documentation)",
                     difficulty=1),
                dict(prompt="What does the Linux kernel's /proc filesystem represent?",
                     choices=[("A virtual, in-memory filesystem exposing live kernel and process information, not stored on disk", True), ("A physical disk partition reserved specifically for temporary files", False),
                              ("A backup location where deleted process logs are archived", False), ("A configuration directory that's only read once, at boot time", False)],
                     explanation="/proc is generated by the kernel on the fly — reading a file under /proc/PID/ gives you a live snapshot of that process's state, not a file that exists on disk. (Source: kernel.org /proc filesystem documentation)",
                     difficulty=2),

                # systemd / systemctl
                dict(prompt="What is the difference between `systemctl start` and `systemctl enable` for a service?",
                     choices=[("`start` runs it immediately; `enable` configures it to start automatically on future boots", True), ("`start` makes the change permanent; `enable` only lasts until the next reboot", False),
                              ("They are equivalent aliases that do exactly the same thing", False), ("`enable` runs it immediately; `start` only schedules it for later", False)],
                     explanation="The two are independent: you can start a service without enabling it (won't survive reboot) or enable it without starting it now (will start next boot). (Source: Red Hat systemd service management docs)",
                     difficulty=1),
                dict(prompt="What information does `systemctl status <service>` provide?",
                     choices=[("Whether the service is running, its process ID, and recent log output", True), ("Only whether the service's unit file exists on disk", False),
                              ("The host machine's CPU temperature and fan speed readings", False), ("A complete list of every other service installed on the system", False)],
                     explanation="`systemctl status` gives a quick operational snapshot — running/stopped state, PID, and a tail of recent journal log lines for that unit. (Source: systemd service management documentation)",
                     difficulty=1),
                dict(prompt="What does `systemctl enable` actually do under the hood?",
                     choices=[("Creates symbolic links in systemd's unit directories so the service starts automatically at boot", True), ("Recompiles the service's underlying binary from its source code", False),
                              ("Downloads and installs the service's package from a repository", False), ("Grants the service's process root-level file permissions", False)],
                     explanation="Enabling a unit wires it into the appropriate systemd target via symlinks — it doesn't touch the binary or package at all. (Source: Red Hat/SUSE systemd documentation)",
                     difficulty=3),
                dict(prompt="What init system does the `systemctl` command control on most modern Linux distributions?",
                     choices=[("systemd", True), ("SysVinit", False),
                              ("Upstart", False), ("OpenRC", False)],
                     explanation="systemctl is systemd's own control tool; SysVinit, Upstart, and OpenRC are older or alternative init systems that systemd has largely replaced on major distros. (Source: systemd documentation)",
                     difficulty=1),
                dict(prompt="Which command stops a running systemd-managed service immediately, without changing its boot-time behavior?",
                     choices=[("`systemctl stop <service>`", True), ("`systemctl disable <service>`", False),
                              ("`systemctl mask <service>`", False), ("`systemctl daemon-reload`", False)],
                     explanation="`stop` only affects the currently running instance; `disable` instead changes whether it starts at the next boot, without stopping it now. (Source: systemd service management documentation)",
                     difficulty=2),

                # SSH keys
                dict(prompt="In SSH key-based authentication, where does the private key need to live?",
                     choices=[("Only on the client machine, kept secret and never shared", True), ("On the server, inside the authorized_keys file", False),
                              ("On both the client and the server equally", False), ("On a public key server accessible to anyone", False)],
                     explanation="Only the public key goes to the server; the private key must stay secret on the client, since possessing it is what proves identity. (Source: OpenSSH ssh-keygen documentation)",
                     difficulty=1),
                dict(prompt="What file on the server holds the public keys allowed to authenticate as a given user?",
                     choices=[("`~/.ssh/authorized_keys`", True), ("`~/.ssh/known_hosts`", False),
                              ("`/etc/passwd`", False), ("`~/.ssh/id_rsa`", False)],
                     explanation="authorized_keys lists which public keys are accepted for that account; known_hosts instead records which servers the client already trusts. (Source: OpenSSH documentation)",
                     difficulty=1),
                dict(prompt="What tool is used to generate a new SSH key pair?",
                     choices=[("`ssh-keygen`", True), ("`ssh-copy-id`", False),
                              ("`ssh-agent`", False), ("`scp`", False)],
                     explanation="ssh-keygen is the OpenSSH utility that creates a new public/private key pair, typically stored under ~/.ssh/. (Source: ssh-keygen(1) manual page)",
                     difficulty=1),
                dict(prompt="What does the `ssh-copy-id` command do?",
                     choices=[("Copies your public key to a remote server's authorized_keys file automatically", True), ("Copies your private key to a remote server as a backup", False),
                              ("Downloads the remote server's own public key onto your machine", False), ("Generates a brand-new SSH key pair directly on the remote server", False)],
                     explanation="ssh-copy-id automates what would otherwise be manually appending your public key to the remote authorized_keys file. (Source: OpenSSH key deployment documentation)",
                     difficulty=2),
                dict(prompt="Why might you add a passphrase when generating an SSH key with `ssh-keygen`?",
                     choices=[("To add a layer of protection so a stolen private key file alone isn't enough to authenticate", True), ("Because SSH key pairs are completely unusable without a passphrase set", False),
                              ("To make the generated key pair automatically expire after 30 days", False), ("To allow the private key to be safely shared with other people", False)],
                     explanation="A passphrase encrypts the private key at rest, so simply copying the key file isn't enough for an attacker to use it. (Source: OpenSSH/DigitalOcean SSH key documentation)",
                     difficulty=2),

                # Text processing
                dict(prompt="What is `grep` primarily used for?",
                     choices=[("Searching text for lines matching a pattern and printing them", True), ("Replacing matched text in place within a file", False),
                              ("Sorting the lines of a file into alphabetical order", False), ("Counting the number of files inside a directory", False)],
                     explanation="grep's whole job is pattern matching and printing matching lines — editing and sorting are what sed and sort are for. (Source: GNU Coreutils manual / grep documentation)",
                     difficulty=1),
                dict(prompt="What is `sed` primarily used for?",
                     choices=[("Editing a stream of text according to a script of commands, e.g. find-and-replace", True), ("Searching for and listing only the lines that match a pattern", False),
                              ("Compressing one or more files to save disk space", False), ("Displaying real-time CPU and memory usage statistics", False)],
                     explanation="sed is a 'stream editor' — it transforms text as it flows through, most commonly for substitution, rather than just searching or reporting on it. (Source: GNU sed documentation)",
                     difficulty=1),
                dict(prompt="What is `awk` primarily designed for?",
                     choices=[("Pattern scanning and processing text, especially column/field-based data", True), ("Managing user accounts and their file permissions", False),
                              ("Scheduling recurring background tasks at fixed times", False), ("Establishing encrypted network connections between hosts", False)],
                     explanation="awk is a full pattern-scanning and text-processing language built around splitting each line into fields, which grep and sed don't natively do. (Source: awk/sed/grep text processing documentation)",
                     difficulty=2),
                dict(prompt="What does the `cut` command do?",
                     choices=[("Extracts selected columns or fields from each line of input", True), ("Deletes selected files from the current working directory", False),
                              ("Splits one large file into several smaller output files", False), ("Removes trailing whitespace from the end of every line", False)],
                     explanation="cut slices out specific character positions or delimiter-separated fields from each input line, commonly used after grep to isolate one column. (Source: GNU Coreutils manual)",
                     difficulty=2),
                dict(prompt="What does `wc -l` report about a file?",
                     choices=[("The total number of lines in the file", True), ("The total number of words contained in the file", False),
                              ("The file's total size measured in bytes", False), ("The number of distinct, non-duplicate lines in the file", False)],
                     explanation="wc counts words, lines, and bytes by default; the -l flag narrows that down to just the line count. (Source: GNU Coreutils wc documentation)",
                     difficulty=1),
                dict(prompt="In the pipeline `cmd1 | cmd2`, what does the pipe character (`|`) actually do?",
                     choices=[("Feeds cmd1's standard output directly into cmd2's standard input", True), ("Runs cmd1 and cmd2 at the same time with no data shared between them", False),
                              ("Saves cmd1's output to a temporary file for cmd2 to read later", False), ("Runs cmd2 to completion first, then runs cmd1 afterward", False)],
                     explanation="A pipe connects one process's stdout directly to the next process's stdin, without ever touching disk. (Source: shell pipeline documentation)",
                     difficulty=1),
                dict(prompt="Which of these are among the standard GNU coreutils text-processing tools? (select all that apply)",
                     kind='multi',
                     choices=[("`cut`", True), ("`wc`", True),
                              ("`systemctl`", False), ("`ssh-keygen`", False)],
                     explanation="cut and wc ship as part of GNU coreutils; systemctl belongs to systemd and ssh-keygen belongs to OpenSSH — different projects entirely. (Source: GNU Coreutils manual)",
                     difficulty=2),

                # Shell fundamentals: exit codes and redirection
                dict(prompt="What range of numeric values can a Unix/Linux command's exit status take?",
                     choices=[("0 to 255", True), ("-128 to 127", False),
                              ("0 to 1 only", False), ("1 to 100", False)],
                     explanation="Exit statuses are stored in a single byte's worth of range, 0 through 255, by shell convention. (Source: Bash exit codes documentation)",
                     difficulty=2),
                dict(prompt="What does an exit status of 0 conventionally mean for a shell command?",
                     choices=[("The command completed successfully, with no error", True), ("The command is still running in the background", False),
                              ("The command was forcibly killed by a signal", False), ("The command needs elevated permissions to proceed", False)],
                     explanation="By near-universal shell convention, 0 means success and any nonzero value signals some kind of failure. (Source: Bash exit codes documentation)",
                     difficulty=1),
                dict(prompt="Which special shell variable holds the exit status of the most recently run command?",
                     choices=[("`$?`", True), ("`$!`", False),
                              ("`$#`", False), ("`$0`", False)],
                     explanation="`$?` always expands to the previous command's exit status, which is how scripts check success/failure after each step. (Source: Bash documentation)",
                     difficulty=1),
                dict(prompt="What are the three standard file descriptors every process starts with, and their numbers?",
                     choices=[("stdin (0), stdout (1), stderr (2)", True), ("stdin (1), stdout (2), stderr (3)", False),
                              ("input (0), output (1), log (2)", False), ("stdin (0), stdout (0), stderr (0)", False)],
                     explanation="File descriptor 0 is always stdin, 1 is stdout, and 2 is stderr — this numbering is what makes redirections like `2>&1` meaningful. (Source: shell redirection documentation)",
                     difficulty=1),
                dict(prompt="In `cmd > file.txt 2>&1`, what does the trailing `2>&1` do?",
                     choices=[("Sends stderr to wherever stdout currently points, so both end up in file.txt", True), ("Sends stdout to wherever stderr currently points instead", False),
                              ("Discards stderr entirely, keeping only stdout in the file", False), ("Merges stdin and stdout into a single combined stream", False)],
                     explanation="Since stdout was just redirected to file.txt, `2>&1` afterward makes stderr follow it into the same file. (Source: Linuxize stderr redirection documentation)",
                     difficulty=2),
                dict(prompt="Why does the order of redirections matter, e.g. `cmd 2>&1 > file.txt` versus `cmd > file.txt 2>&1`?",
                     choices=[("Redirections apply left to right, so `2>&1` before `> file.txt` sends stderr to the old stdout, not the file", True), ("Order never matters at all — both forms behave completely identically in every shell", False),
                              ("The first form is always rejected outright as a syntax error and will never run", False), ("Only the very last redirection listed anywhere in a command has any real effect", False)],
                     explanation="At the moment `2>&1` executes in the first form, stdout still points at the terminal, so stderr gets pinned there before stdout is later redirected to the file. (Source: shell redirection documentation)",
                     difficulty=3),
             ]),
    ),

    # =========================================================================
    # --- Book 6: Python: Advanced Concepts (compiled reference notes) ---
    # =========================================================================

    dict(book='python-advanced-concepts', slug='python-dicts-concurrency-internals', title='Python Advanced Concepts: Dictionaries, Concurrency & the Data Model',
         topic=TOPIC_PYTHON, difficulty=2,
         order=1, unlock_level=1,
         summary='How CPython dicts actually store data under the hood, subprocess vs. multiprocessing vs. threading, and the rest of the language’s advanced machinery (GC, generators, decorators, descriptors, metaclasses, asyncio).',
         concept=dict(
            slug='python-advanced-internals', title='Dict Internals, Process/Thread Management & the Data Model',
            source_note='Compiled reference notes: CPython dict internals (PEP 412); subprocess/multiprocessing/threading and the GIL; generators, decorators, context managers, descriptors, metaclasses, asyncio',
            summary=(
                "What a dict actually is under the hood, the three tiers of Python concurrency and when to reach "
                "for each one, and the rest of the language's advanced data model."
            ),
            notes=[
                dict(heading="Dictionaries: Storage Layout",
                     body=(
                        "A Python dict is a hash table, but since the CPython 3.6 'compact dict' redesign it's "
                        "really two arrays working together: a sparse index array (a power-of-2-sized array of "
                        "small integers, kept at roughly 1/3-2/3 load factor) and a dense entries array holding "
                        "(hash, key, value) triples in strict insertion order with no gaps. Looking up d[key] "
                        "hashes the key, uses the hash to pick a starting slot in the sparse array (index & mask), "
                        "reads the dense-array index stored there, and compares the cached hash then the key "
                        "itself. A mismatch triggers CPython's open-addressing probe sequence (not simple linear "
                        "probing) until it finds either a match or an empty slot. Splitting storage this way is "
                        "what makes iteration order match insertion order for free — you just walk the dense "
                        "array — and it shrank per-entry memory overhead by roughly 20-25% versus the pre-3.6 "
                        "design."
                     ),
                     deep_dive=dict(
                        title="Key-sharing dicts (PEP 412) and why __slots__ saves even more",
                        body=(
                            "When many instances of the same class have identical attribute names, CPython can "
                            "share one keys array across all of them and store only a per-instance values array — "
                            "a major memory win for ordinary __dict__-based instances. __slots__ goes further: it "
                            "removes the per-instance dict entirely in favor of a fixed-size C-level array, saving "
                            "even more memory at the cost of dynamic attribute assignment."
                        ),
                     )),
                dict(heading="Dictionaries: Resizing, Hashing & Memory",
                     body=(
                        "Resizes happen when the load factor crosses a threshold; CPython allocates a new sparse "
                        "array and re-places entries from the dense array using their already-cached hashes (no "
                        "rehashing needed). Because growth is geometric, not +1 each time, a single insertion is "
                        "O(1) on average even though any individual insertion might trigger an O(n) rebuild. Only "
                        "hashable objects can be keys — a stable __hash__ plus an __eq__ that agrees with it — "
                        "which is exactly why mutable builtins like list and dict can't be keys: a key's hash "
                        "changing after insertion would corrupt its own slot invariant. String and bytes hashes "
                        "are salted per-process by default (SipHash, since Python 3.3) specifically to prevent "
                        "hash-flooding attacks that degrade lookups toward O(n); this is also why dict iteration "
                        "order with string keys can differ across separate process runs despite being stable "
                        "within one run."
                     )),
                dict(heading="Dictionary Variants",
                     body=(
                        "collections.defaultdict supplies a factory function on missing-key access; "
                        "collections.Counter specializes in counting hashables with arithmetic operators defined "
                        "on the counts; collections.ChainMap layers several dicts as one logical view without "
                        "copying; collections.OrderedDict predates 3.7's guaranteed ordering and is still useful "
                        "for move_to_end() and order-sensitive equality; types.MappingProxyType wraps an existing "
                        "dict as a read-only live view, which is how cls.__dict__ is exposed externally."
                     )),
                dict(heading="subprocess: Running External Programs",
                     body=(
                        "subprocess.run() is the modern blocking entry point, built on the lower-level Popen, "
                        "which exposes .pid, .stdin/.stdout/.stderr as pipes, and .terminate()/.kill(). "
                        "shell=False (the default) executes the program directly via an execve-family syscall "
                        "with an argument list, avoiding shell parsing; shell=True runs the string through "
                        "/bin/sh -c, which is a command-injection risk if any part of it comes from untrusted "
                        "input. Writing to a Popen's pipes without using .communicate() risks a classic deadlock: "
                        "the OS pipe buffer (commonly 64KB on Linux) fills, the child blocks writing more, and "
                        "the parent blocks reading/writing in the wrong order — .communicate() avoids this with "
                        "internal reader threads. A child that exits before its parent calls wait()/communicate() "
                        "becomes a zombie process table entry until reaped."
                     )),
                dict(heading="multiprocessing: True Parallelism",
                     body=(
                        "The GIL lets only one thread execute Python bytecode at a time per process, so "
                        "multiprocessing sidesteps it entirely with separate OS processes, each its own "
                        "interpreter and memory space. The start method matters: fork (Linux/macOS default "
                        "historically) copy-on-write clones the parent's memory instantly but can be unsafe with "
                        "inherited threads/file descriptors; spawn (Windows and modern macOS default) boots a "
                        "clean new interpreter and re-imports the target module, which is why Windows/spawn code "
                        "needs an `if __name__ == \"__main__\":` guard; forkserver forks children from one clean "
                        "server process forked early, as a safer middle ground. Since processes don't share "
                        "memory, data crosses via Queue/Pipe (pickled through an OS pipe), Value/Array (shared "
                        "ctypes memory with an optional Lock), Manager() (a separate process proxying Python "
                        "objects), or multiprocessing.shared_memory for true unpickled shared buffers. Everything "
                        "sent between processes must be picklable — lambdas and open file handles are common "
                        "failure points."
                     )),
                dict(heading="threading: Concurrency Within One Process",
                     body=(
                        "Threads share memory and the GIL, so only one runs Python bytecode at an instant, but "
                        "I/O operations (network calls, disk reads, time.sleep, many C-extension internals) "
                        "release the GIL while waiting — which is why threading still helps I/O-bound workloads "
                        "even though it can't parallelize CPU-bound ones. Even simple-looking operations like "
                        "x += 1 aren't atomic at the bytecode level, so unsynchronized concurrent updates can "
                        "still lose data despite the GIL preventing outright memory corruption; Lock/RLock, "
                        "Condition, Event, Semaphore, and Barrier coordinate this. concurrent.futures."
                        "ThreadPoolExecutor is the modern high-level layer over raw threading. PEP 703 introduced "
                        "an experimental free-threaded (no-GIL) CPython build starting around 3.13, an active "
                        "area of change."
                     )),
                dict(heading="Memory Management & the Garbage Collector",
                     body=(
                        "Every object is reference-counted and deallocated immediately, deterministically, once "
                        "its count hits zero. Reference cycles (two objects referencing each other) can't be "
                        "freed by refcounting alone, so a separate generational garbage collector (3 generations, "
                        "young objects collected most often) handles those; gc.collect() forces a pass. CPython's "
                        "own small-object allocator, pymalloc, handles allocations under roughly 512 bytes in "
                        "arenas/pools/blocks to avoid calling the system malloc for every tiny object."
                     )),
                dict(heading="Generators, Decorators & Context Managers",
                     body=(
                        "A generator function (using yield) implements the iterator protocol (__iter__/__next__) "
                        "automatically, suspending and resuming a saved frame at each yield for lazy, on-demand "
                        "evaluation — critical for memory usage on large or infinite sequences. yield from "
                        "delegates to a sub-generator and enables .send()/.throw() two-way communication, the "
                        "mechanism early asyncio built coroutines on before async/await syntax existed. A "
                        "decorator is a higher-order function wrapping another function/class for cross-cutting "
                        "concerns like logging or caching (functools.wraps preserves the original's metadata); "
                        "functools.lru_cache is a decorator-based memoization cache using a doubly linked list "
                        "plus a dict for O(1) LRU eviction. The `with` statement relies on the context manager "
                        "protocol (__enter__/__exit__, the latter able to suppress an exception by returning "
                        "truthy); contextlib.contextmanager lets you write one as a single-yield generator "
                        "instead of a full class."
                     )),
                dict(heading="Descriptors, Metaclasses & asyncio",
                     body=(
                        "A descriptor implements __get__/__set__/__delete__ to customize attribute access when "
                        "placed as a class attribute — property, staticmethod, and classmethod are all built on "
                        "this. A metaclass (default: type) is 'the class of a class'; defining a class with "
                        "metaclass=Meta lets Meta intercept class creation itself, which is how Django's ORM and "
                        "abc.ABCMeta work under the hood. asyncio runs a single-threaded event loop that "
                        "schedules coroutines cooperatively yielding at await points (usually I/O), scaling to "
                        "thousands of concurrent connections without per-thread OS overhead — but calling a "
                        "blocking synchronous function inside a coroutine blocks the entire event loop, a common "
                        "correctness pitfall best fixed with async-native libraries or loop.run_in_executor()."
                     )),
            ],
            questions=[
                dict(prompt="Since the CPython 3.6 'compact dict' redesign, what two structures does a dict's internal storage split into?",
                     choices=[("A sparse index array of small integers, and a dense array of (hash, key, value) triples in insertion order", True),
                              ("Two identical hash tables kept in sync for redundancy", False),
                              ("A B-tree of keys and a separate linked list of values", False),
                              ("A single flat array of key-value pairs sorted by hash", False)],
                     explanation="The sparse array maps hash slots to positions in the dense array, which is what lets iteration order match insertion order for free.",
                     difficulty=2),
                dict(prompt="Why does splitting a dict into a sparse index array and a dense entries array make iteration order match insertion order?",
                     choices=[("Iterating just walks the dense array, which is already in insertion order since entries are appended there directly", True),
                              ("Python re-sorts the dict alphabetically before every iteration", False),
                              ("It doesn't — dict order is still random even in modern CPython", False),
                              ("The sparse array is what gets iterated, and it happens to be insertion-ordered", False)],
                     explanation="The dense array holds entries contiguously in the order they were inserted; the sparse array is only used for hashing to a position, not for iteration.",
                     difficulty=2),
                dict(prompt="What happens on a dict lookup when the initial slot's stored hash doesn't match the key being looked up?",
                     choices=[("CPython immediately raises KeyError with no further checking", False),
                              ("CPython follows an open-addressing probe sequence to check subsequent slots until it finds a match or an empty slot", True),
                              ("The dict automatically resizes on every single mismatch", False),
                              ("CPython falls back to a linear scan of every key in the dict", False)],
                     explanation="A hash collision triggers CPython's specific probing scheme (not simple linear probing) rather than an immediate failure or full scan.",
                     difficulty=2),
                dict(prompt="Why can't a plain Python list be used as a dict key?",
                     choices=[("Lists are too large to hash efficiently", False),
                              ("Lists are mutable, so their contents (and thus their hash) could change after insertion, corrupting the key's slot invariant", True),
                              ("Only numeric types can ever be dict keys", False),
                              ("Dicts technically allow it, but silently ignore list keys", False)],
                     explanation="If a key's hash changed after it was placed in a slot, the dict would no longer be able to find it — mutability and hashability are fundamentally incompatible.",
                     difficulty=2),
                dict(prompt="Why are Python string hashes randomized (salted) per process by default since Python 3.3?",
                     choices=[("To make dicts use less memory", False),
                              ("To prevent hash-flooding denial-of-service attacks where crafted keys deliberately collide and degrade lookups toward O(n)", True),
                              ("To guarantee dict iteration order is always alphabetical", False),
                              ("It's a leftover from Python 2 with no current purpose", False)],
                     explanation="SipHash-based per-process salting means an attacker can't precompute colliding keys in advance, which is exactly the hash-flooding attack it defends against.",
                     difficulty=3),
                dict(prompt="What does the 'key-sharing dictionary' optimization (PEP 412) do?",
                     choices=[("It compresses dict values to save disk space", False),
                              ("It lets many instances of the same class share one keys array in memory, storing only a per-instance values array", True),
                              ("It shares one dict object across multiple threads for thread safety", False),
                              ("It merges two dicts into one when their keys overlap", False)],
                     explanation="When many instances of a class have the same attribute names, sharing the keys array is a substantial memory win over each instance holding a full independent dict.",
                     difficulty=3),
                dict(prompt="Which of the following are true about `collections.defaultdict`, `Counter`, and `ChainMap`? (select all that apply)",
                     kind='multi',
                     choices=[("`defaultdict` calls a factory function automatically on missing-key access", True),
                              ("`Counter` supports arithmetic operators like `+` and `-` directly on counts", True),
                              ("`ChainMap` layers multiple dicts as one view without copying or merging them", True),
                              ("All three eagerly copy and merge their source dicts into one new dict at creation time", False)],
                     explanation="All three avoid the corresponding manual boilerplate — missing-key checks, count bookkeeping, and dict merging — without extra copying (except where the dict itself is mutated).",
                     difficulty=2),
                dict(prompt="Why does the CPython GIL exist in the first place?",
                     choices=[("To make single-threaded code run faster", False),
                              ("Because CPython's reference-counting memory management isn't thread-safe by default, so a single mutex prevents concurrent refcount corruption", True),
                              ("To prevent programs from using more than one CPU core for any reason", False),
                              ("It's required by the Python language specification itself", False)],
                     explanation="Without the GIL, concurrent increments/decrements of an object's refcount from multiple threads could race and corrupt object lifetimes.",
                     difficulty=2),
                dict(prompt="Why does `threading` still help with I/O-bound workloads despite the GIL?",
                     choices=[("Threading doesn't actually help I/O-bound workloads at all", False),
                              ("I/O operations release the GIL while waiting, letting other threads run Python bytecode during that wait", True),
                              ("The GIL only applies to CPU-bound code, never to I/O", False),
                              ("Each thread gets its own separate GIL", False)],
                     explanation="A blocked network call or disk read releases the GIL, so other threads get real concurrency during that wait even though only one thread ever executes Python bytecode at a time.",
                     difficulty=2),
                dict(prompt="What is the key architectural difference between `multiprocessing` and `threading`?",
                     choices=[("They are two names for the exact same underlying mechanism", False),
                              ("multiprocessing uses separate OS processes with independent memory (bypassing the GIL); threading uses threads sharing one process's memory (subject to the GIL)", True),
                              ("threading is always faster than multiprocessing for every kind of workload", False),
                              ("multiprocessing can only be used for network I/O, never CPU-bound work", False)],
                     explanation="Separate processes mean separate interpreters and memory spaces, which is what lets multiprocessing achieve true multi-core parallelism that threading cannot for CPU-bound code.",
                     difficulty=1),
                dict(prompt="On Windows, why does `multiprocessing` code typically require an `if __name__ == \"__main__\":` guard?",
                     choices=[("It's just a stylistic convention with no functional effect", False),
                              ("The default 'spawn' start method boots a fresh interpreter and re-imports the target module, so top-level code would otherwise re-run in every child process", True),
                              ("Windows doesn't support multiprocessing without this guard", False),
                              ("The guard is only needed when using threading, not multiprocessing", False)],
                     explanation="Without the guard, re-importing the module in each spawned child would re-execute any top-level process-creation code, potentially spawning processes recursively.",
                     difficulty=3),
                dict(prompt="Why must objects passed between processes in `multiprocessing` (via Queue, Pool, etc.) be picklable?",
                     choices=[("Because separate processes don't share memory, so data must be serialized to cross between them", True),
                              ("Pickling is only a performance optimization, not a requirement", False),
                              ("Only numeric data can ever be sent between processes", False),
                              ("Picklability is required for threading too, not just multiprocessing", False)],
                     explanation="Unlike threads, processes have independent memory spaces, so any data crossing between them (arguments, return values, queue items) must be serialized and deserialized.",
                     difficulty=2),
                dict(prompt="What is the risk of writing to a `subprocess.Popen`'s stdout/stderr pipes without using `.communicate()`?",
                     choices=[("There is no risk — pipes have unlimited buffer size", False),
                              ("A deadlock: the OS pipe buffer can fill, blocking the child, while the parent is also blocked reading/writing in the wrong order", True),
                              ("The subprocess module will raise an ImportError", False),
                              ("The child process will silently ignore all output", False)],
                     explanation="`.communicate()` uses internal reader threads specifically to avoid this classic deadlock pattern around fixed-size OS pipe buffers.",
                     difficulty=3),
                dict(prompt="What does a Python generator function (using `yield`) provide that a regular function returning a list does not?",
                     choices=[("Faster execution in every case, with no other difference", False),
                              ("Lazy, on-demand evaluation — values are computed one at a time instead of all being materialized in memory upfront", True),
                              ("Automatic parallel execution across multiple CPU cores", False),
                              ("Guaranteed thread-safety with no locking needed", False)],
                     explanation="A generator suspends execution at each `yield` and resumes on the next `next()` call, which is what enables streaming large or infinite sequences without holding them all in memory.",
                     difficulty=1),
                dict(prompt="What is a Python descriptor?",
                     choices=[("A type hint used only for static analysis, with no runtime effect", False),
                              ("Any object implementing `__get__`, `__set__`, or `__delete__`, used to customize attribute access when placed as a class attribute", True),
                              ("A special kind of comment describing what a function does", False),
                              ("A synonym for a Python decorator", False)],
                     explanation="`property`, `staticmethod`, and `classmethod` are all built on the descriptor protocol — it's the general mechanism behind customized attribute access.",
                     difficulty=3),
                dict(prompt="What does a Python metaclass do?",
                     choices=[("It defines default values for a class's instance attributes", False),
                              ("It is 'the class of a class' — it intercepts and can customize how the class object itself is constructed", True),
                              ("It is just another name for a base class in inheritance", False),
                              ("It controls only how instances are printed with `repr()`", False)],
                     explanation="By default a class's metaclass is `type`; supplying a custom metaclass lets you hook into class creation itself, which is how frameworks like Django's ORM and `abc.ABCMeta` work.",
                     difficulty=3),
                dict(prompt="Why does calling a blocking, synchronous function inside an `async def` coroutine cause problems in `asyncio`?",
                     choices=[("It raises a SyntaxError immediately", False),
                              ("It blocks the entire single-threaded event loop, preventing every other coroutine from making progress until it returns", True),
                              ("asyncio automatically runs it in a background thread with no code changes needed", False),
                              ("It has no effect since `async def` functions ignore blocking calls", False)],
                     explanation="asyncio's concurrency model depends on coroutines voluntarily yielding at `await` points; a blocking call never yields, so it stalls the whole loop until it finishes.",
                     difficulty=2),
            ]),
    ),

    # =========================================================================
    # --- Book 7: Operating Systems: File Handling & Systems Programming ---
    # =========================================================================

    dict(book='os-file-handling-systems', slug='os-file-handling-access-storage', title='File Handling: Access Management, Permissions & Storage',
         topic=TOPIC_OS, difficulty=2,
         order=2, unlock_level=1,
         summary='How files are actually represented (inodes, file descriptors), how chmod/octal permissions and special bits work, how PIDs and open files relate, and how filesystem storage is organized underneath.',
         concept=dict(
            slug='os-file-handling-permissions-storage', title='Inodes, Permissions, PIDs & Filesystem Storage',
            source_note='Compiled reference notes: inodes & file descriptors; chmod octal permission math and special bits; PIDs and process/file relationships; filesystem storage internals',
            summary=(
                "What a file actually is beneath its name, exactly how a chmod digit like 754 is built from "
                "r/w/x bits, how PIDs and open files relate, and how filesystems organize storage underneath."
            ),
            notes=[
                dict(heading="Inodes: What a File Actually Is",
                     body=(
                        "Every file and directory on a Unix-like system is represented by an inode — a fixed-"
                        "size metadata record holding the file type, owner UID/GID, permission bits, size, "
                        "timestamps (atime/mtime/ctime — ctime is last metadata change, not creation time), a "
                        "link count, and pointers to the actual data blocks. Critically, the inode does not "
                        "store the filename — that lives in a directory entry mapping name to inode number. "
                        "This is why multiple names (hard links) can point at the same inode with no 'original' "
                        "vs 'copy' distinction, and why renaming within the same filesystem is a cheap directory-"
                        "only operation while moving across filesystems requires a real copy (inode numbers are "
                        "only unique within one filesystem)."
                     ),
                     deep_dive=dict(
                        title="Why a 'deleted' file a process still has open doesn't free its space yet",
                        body=(
                            "`unlink()` (what `rm` does) only removes the directory entry and decrements the "
                            "inode's link count. If a process still has the file open, the inode and its data "
                            "blocks aren't actually freed until that last file descriptor closes — which is why "
                            "a program can keep writing to a file that `ls` no longer shows, and why disk space "
                            "isn't reclaimed until the process exits (`lsof | grep deleted` finds this situation)."
                        ),
                     )),
                dict(heading="File Descriptors and the Open File Table",
                     body=(
                        "Opening a file involves three layers: a small per-process integer, the file descriptor "
                        "(0/1/2 are stdin/stdout/stderr by convention), indexing into a table private to that "
                        "process; a system-wide open file description tracking the current read/write offset and "
                        "access mode; and the inode itself, shared by every open file description referencing it. "
                        "After fork(), parent and child share open file descriptions (and thus offsets) for FDs "
                        "that existed at fork time, while two independent open() calls on the same path get "
                        "separate offsets even though they reference the same inode. dup()/dup2() create a new "
                        "FD pointing at the same open file description, sharing its offset — different from "
                        "opening the same path twice."
                     )),
                dict(heading="Permissions: Classes, Types & the Octal Digit",
                     body=(
                        "Every file has three permission classes — owner, group, others — each with read (r), "
                        "write (w), and execute (x). Treating r/w/x as a 3-bit binary number gives each class a "
                        "single octal digit: read=4, write=2, execute=1, summed for whichever bits are set. So "
                        "rwxr-xr-- becomes owner=7 (4+2+1), group=5 (4+0+1), other=4 (4+0+0), combined as chmod "
                        "754. Every chmod digit is built exactly this way — 6 is read+write, 5 is read+execute, "
                        "3 is write+execute, and so on — which is why chmod numbers are always the same 3-digit "
                        "pattern regardless of which permissions are actually being set. For a directory, read "
                        "means listing its entries and execute means being able to cd into it or traverse to a "
                        "file inside by exact path — distinct capabilities, not synonyms."
                     )),
                dict(heading="Special Permission Bits: setuid, setgid, sticky",
                     body=(
                        "A 4th, leading chmod digit (e.g. chmod 4755) encodes special bits, also bit-weighted: "
                        "4 is setuid — an executable runs with the file owner's privileges rather than the "
                        "invoking user's (classic example: /usr/bin/passwd running as root so any user can "
                        "update /etc/shadow); 2 is setgid — on an executable it runs with the file's group "
                        "privileges, and on a directory new files inside inherit that directory's group instead "
                        "of the creator's; 1 is the sticky bit — on a directory it restricts deletion of files "
                        "inside to their owner (or root) even if others have write access, which is exactly how "
                        "/tmp (mode 1777) lets anyone create files but not delete each other's. `ls -l` shows "
                        "these as a lowercase s/t in the execute position when execute is also set, uppercase "
                        "S/T when it isn't."
                     )),
                dict(heading="chmod, chown & umask in Practice",
                     body=(
                        "chmod 644 file.txt sets exact bits (rw-r--r--), discarding whatever was there; symbolic "
                        "mode (chmod u+x,g-w,o=r) makes relative changes without needing to know the full current "
                        "mode. chown user:group file changes owner and group together (typically root-only); "
                        "chgrp changes only the group, allowed to the owner if they belong to the target group. "
                        "umask sets the default permissions stripped from every newly created file/directory — a "
                        "umask of 022 yields 644 for new files and 755 for new directories, since 022 clears the "
                        "group/other write bit from a base of 666/777."
                     )),
                dict(heading="PIDs, Process Trees & the /proc Filesystem",
                     body=(
                        "Every running process gets a unique PID from the kernel, reused after the process exits "
                        "and the value cycles around, drawn from a range capped by /proc/sys/kernel/pid_max. PID "
                        "1 (traditionally init, now usually systemd) bootstraps userspace and reaps orphaned "
                        "processes whose original parent exited before they did. On Linux, /proc/<pid>/fd/ is a "
                        "directory of symlinks, one per open file descriptor, showing exactly what that running "
                        "process has open — a regular file, socket, pipe, or /dev/null — which is how tools like "
                        "lsof inspect a live process's open files without special syscalls. A zombie is a "
                        "terminated process whose exit status hasn't been collected via wait() yet; it still "
                        "occupies a process table slot (with a PID) until reaped."
                     ),
                     deep_dive=dict(
                        title="File descriptor inheritance across fork() and exec()",
                        body=(
                            "fork() duplicates the entire file descriptor table, so child FDs point at the same "
                            "open file descriptions (and offsets) as the parent. exec() replaces a process's "
                            "program image in place, by default preserving open FDs unless they're marked "
                            "close-on-exec (FD_CLOEXEC). This combination is exactly how a shell implements "
                            "`command > file.txt`: it opens the file, dup2()s it onto FD 1, then execs the "
                            "target command, which transparently inherits the redirected stdout."
                        ),
                     )),
                dict(heading="Filesystem Storage: Blocks, Superblocks & Journaling",
                     body=(
                        "Storage devices expose fixed-size sectors, and the filesystem groups these into blocks "
                        "(commonly 4KB on ext4) — the true allocation unit, so even a 1-byte file consumes a "
                        "full block. A superblock holds filesystem-wide metadata (block/inode counts, block "
                        "size, clean/dirty state); the inode table holds every inode (pre-allocated in older "
                        "designs, which is why a filesystem can run out of inodes despite having free bytes); "
                        "and modern filesystems (ext4, XFS, Btrfs) use extents — a (start_block, length) pair — "
                        "instead of per-block pointer lists, cutting metadata size and fragmentation for large "
                        "files. Journaling logs pending metadata changes so a crash mid-write can be replayed or "
                        "rolled back on reboot instead of requiring a full filesystem scan."
                     )),
                dict(heading="Page Cache, fsync() & Advisory File Locking",
                     body=(
                        "Writes typically land in the kernel's page cache (memory) first, not immediately on "
                        "physical storage — a completed write() only guarantees the data is in kernel memory "
                        "unless the application calls fsync() (flush data+metadata, wait for confirmation) or "
                        "the lighter fdatasync(). This is why an application can 'successfully' write data that "
                        "is then lost on sudden power loss if it never calls fsync(). Because multiple processes "
                        "can open the same inode concurrently, flock() (whole-file, tied to the open file "
                        "description) and fcntl() record locks (byte-range, tied to process+inode) coordinate "
                        "access — both are advisory, meaning the kernel doesn't force an uncooperative process "
                        "to respect them, unlike rarely-used mandatory locking."
                     )),
            ],
            questions=[
                dict(prompt="Where does a file's name actually live, given that the inode doesn't store it?",
                     choices=[("In a directory entry that maps a name to an inode number", True),
                              ("Inside the inode's data blocks alongside the file's content", False),
                              ("In the filesystem's superblock", False),
                              ("Filenames aren't stored anywhere — they're computed from the inode number", False)],
                     explanation="The inode holds metadata and data-block pointers, but the name-to-inode mapping lives in the directory that contains the file — which is exactly what makes hard links possible.",
                     difficulty=2),
                dict(prompt="Why does deleting one hard link to a file not necessarily free its disk space?",
                     choices=[("Hard links can't actually be deleted at all", False),
                              ("The underlying inode is only freed once its link count reaches zero AND no process still has it open", True),
                              ("Deleting a hard link always corrupts the filesystem", False),
                              ("Hard links each have their own separate copy of the data", False)],
                     explanation="Multiple directory entries (hard links) can reference the same inode; the data is only reclaimed when the last reference — link or open file descriptor — goes away.",
                     difficulty=2),
                dict(prompt="A file is `rm`'d while a process still has it open. What happens to that process's ability to keep using the file?",
                     choices=[("The process immediately gets an error on its next read/write", False),
                              ("The process can keep reading/writing normally — the inode and data blocks stay allocated until the last open file descriptor closes", True),
                              ("The file is instantly and irrecoverably destroyed for all processes", False),
                              ("The OS automatically renames the file to prevent this from happening", False)],
                     explanation="`unlink()` only removes the directory entry; a process with the file already open retains access via its file descriptor until it closes it.",
                     difficulty=3),
                dict(prompt="What permission does the numeric mode `754` grant?",
                     choices=[("Owner: read+write+execute; Group: read+execute; Other: read-only", True),
                              ("Owner: read-only; Group: read+write+execute; Other: read+execute", False),
                              ("Owner: read+write; Group: read+write; Other: execute-only", False),
                              ("Full access for everyone", False)],
                     explanation="7 = 4(r)+2(w)+1(x) for the owner, 5 = 4(r)+0+1(x) for the group, 4 = 4(r)+0+0 for others.",
                     difficulty=1),
                dict(prompt="Which single sum of weights produces the octal digit 6 in a chmod permission?",
                     choices=[("read (4) + write (2), with no execute", True),
                              ("write (2) + execute (1), with no read", False),
                              ("read (4) + execute (1), with no write", False),
                              ("read (4) + write (2) + execute (1)", False)],
                     explanation="Each permission type has a fixed weight — read=4, write=2, execute=1 — and the digit is just the sum of whichever are present; 4+2=6 is read+write with no execute.",
                     difficulty=1),
                dict(prompt="What does `chmod u+x,g-w,o=r file.txt` do, compared to `chmod 644 file.txt`?",
                     choices=[("They are exactly equivalent in every case", False),
                              ("The symbolic form makes relative changes to whatever mode already existed; the numeric form sets an exact, absolute mode regardless of what was there before", True),
                              ("The symbolic form only works on directories, never on files", False),
                              ("The numeric form can only remove permissions, never add them", False)],
                     explanation="Symbolic mode (`+`/`-`/`=` with `u`/`g`/`o`) adjusts relative to the current permissions; a numeric mode like `644` always sets the exact final bits, discarding the prior mode entirely.",
                     difficulty=2),
                dict(prompt="What does the setuid bit do when set on an executable file?",
                     choices=[("It prevents the file from ever being executed", False),
                              ("The process runs with the privileges of the file's owner, rather than the user who invoked it", True),
                              ("It makes the file read-only for everyone including the owner", False),
                              ("It automatically encrypts the file's contents", False)],
                     explanation="The classic example is /usr/bin/passwd, owned by root with setuid set, so an unprivileged user running it can still update the privileged /etc/shadow file.",
                     difficulty=2),
                dict(prompt="Why is the sticky bit set on `/tmp` (mode 1777)?",
                     choices=[("So that no one, including root, can ever delete files there", False),
                              ("So that any user can create files in /tmp, but only that file's owner (or root) can delete or rename it, even though /tmp is world-writable", True),
                              ("So that /tmp automatically empties itself every reboot", False),
                              ("So that files in /tmp always run with root privileges", False)],
                     explanation="Without the sticky bit, world-writable would also mean anyone could delete or rename anyone else's files in that directory — the sticky bit specifically closes that gap.",
                     difficulty=2),
                dict(prompt="Which of the following are true about the special (4th) chmod digit? (select all that apply)",
                     kind='multi',
                     choices=[("setuid has weight 4", True),
                              ("setgid has weight 2", True),
                              ("the sticky bit has weight 1", True),
                              ("the special digit replaces the need for the other 3 permission digits entirely", False)],
                     explanation="setuid=4, setgid=2, sticky=1 — the same bit-weighted-sum pattern as the r/w/x digits, but it's an additional leading digit, not a replacement for the owner/group/other digits.",
                     difficulty=2),
                dict(prompt="What is the difference between `chmod` and `chown`?",
                     choices=[("They are two names for the same command", False),
                              ("`chmod` changes what actions (read/write/execute) are permitted; `chown` changes who the owner and/or group are", True),
                              ("`chown` only works on directories, never on files", False),
                              ("`chmod` changes ownership; `chown` changes permission bits", False)],
                     explanation="`chmod` controls the permission bits themselves; `chown` controls the UID/GID that those bits are evaluated against.",
                     difficulty=1),
                dict(prompt="With a umask of `022`, what default permissions do newly created files and directories get?",
                     choices=[("Files: 644, Directories: 755", True),
                              ("Files: 666, Directories: 777 (umask has no effect)", False),
                              ("Files: 022, Directories: 022", False),
                              ("Files: 755, Directories: 644", False)],
                     explanation="umask is subtracted from the base 666 (files) / 777 (directories); 022 strips the group/other write bit, giving 644 for files and 755 for directories.",
                     difficulty=3),
                dict(prompt="What is a zombie process?",
                     choices=[("A process that is consuming excessive CPU in an infinite loop", False),
                              ("A terminated process whose exit status hasn't yet been collected by its parent via wait(), so it still occupies a process table slot", True),
                              ("A process that has been forcibly killed with SIGKILL", False),
                              ("A process running with no assigned PID", False)],
                     explanation="A zombie has already finished executing — it consumes no CPU or memory beyond its process table entry — and is cleared once the parent reaps its exit status.",
                     difficulty=2),
                dict(prompt="What does `/proc/<pid>/fd/` show on a Linux system?",
                     choices=[("The source code of the running process", False),
                              ("Symlinks, one per open file descriptor, showing exactly what that process currently has open", True),
                              ("A list of every process that PID has ever spawned", False),
                              ("The process's CPU and memory usage history", False)],
                     explanation="This is the live, inspectable link between a running process and the files/sockets/pipes it has open, which is how tools like `lsof` work.",
                     difficulty=2),
                dict(prompt="After `fork()`, what do the parent and child processes share with respect to file descriptors that existed before the fork?",
                     choices=[("Nothing — the child starts with a completely empty file descriptor table", False),
                              ("The same open file descriptions, including the current read/write offset", True),
                              ("Only the file descriptor numbers, but with entirely independent offsets", False),
                              ("File descriptors are automatically closed in the child after fork()", False)],
                     explanation="fork() duplicates the FD table itself, but the duplicated FDs still point at the same underlying open file descriptions as the parent, so they share offsets.",
                     difficulty=3),
                dict(prompt="Why can a filesystem run out of usable space for new files even while `df` shows free bytes available?",
                     choices=[("This can never actually happen", False),
                              ("The filesystem's pre-allocated inode table can be exhausted by a huge number of tiny files, even with free data blocks remaining", True),
                              ("Free bytes shown by `df` always includes reserved space that can never be used", False),
                              ("Only Windows filesystems have this limitation", False)],
                     explanation="Traditional filesystem designs pre-allocate a fixed number of inodes at creation time; running out of inodes (`df -i`) is a distinct failure mode from running out of data blocks.",
                     difficulty=3),
                dict(prompt="Why might a program's `write()` call succeed, yet the data still be lost after a sudden power failure?",
                     choices=[("write() always writes directly to physical storage with no exceptions", False),
                              ("The write was buffered in the kernel's page cache and never flushed to durable storage with fsync() before the power loss", True),
                              ("This can only happen with network filesystems, never local disks", False),
                              ("write() calls are purely cosmetic and never actually persist data", False)],
                     explanation="A successful write() only guarantees the data reached kernel memory (the page cache); durability requires an explicit fsync()/fdatasync() to force it to the physical device.",
                     difficulty=2),
                dict(prompt="What does it mean that `flock()` and `fcntl()` record locks are 'advisory'?",
                     choices=[("They are enforced automatically by the filesystem for every process, no exceptions", False),
                              ("The kernel does not stop an uncooperative process from ignoring the lock and accessing the file anyway — it's a cooperative protocol", True),
                              ("They only work on network filesystems", False),
                              ("They are deprecated and no longer functional on modern Linux", False)],
                     explanation="Advisory locking relies on every participating process choosing to check the lock; a process that ignores the API entirely can still read/write the file, unlike (rarely used) mandatory locking.",
                     difficulty=3),
            ]),
    ),
]


class Command(BaseCommand):
    help = 'Seed the database with System Design book content, chapters, concepts, and quiz questions.'

    @transaction.atomic
    def handle(self, *args, **options):
        book1, _ = Book.objects.update_or_create(slug=BOOK1['slug'], defaults=BOOK1)
        book2, _ = Book.objects.update_or_create(slug=BOOK2['slug'], defaults=BOOK2)
        book3, _ = Book.objects.update_or_create(slug=BOOK3['slug'], defaults=BOOK3)
        book4, _ = Book.objects.update_or_create(slug=BOOK4['slug'], defaults=BOOK4)
        book5, _ = Book.objects.update_or_create(slug=BOOK5['slug'], defaults=BOOK5)
        book6, _ = Book.objects.update_or_create(slug=BOOK6['slug'], defaults=BOOK6)
        book7, _ = Book.objects.update_or_create(slug=BOOK7['slug'], defaults=BOOK7)
        books = {
            'system-design-interview-xu': book1, 'grokking-system-design': book2,
            'database-internals': book3, 'designing-data-intensive-apps': book4,
            'linux-pocket-guide': book5, 'python-advanced-concepts': book6,
            'os-file-handling-systems': book7,
        }

        topics = {}
        for t_data in TOPICS:
            topic, _ = Topic.objects.update_or_create(slug=t_data['slug'], defaults=t_data)
            topics[t_data['slug']] = topic

        chapter_count = 0
        concept_count = 0
        question_count = 0
        seen_chapter_ids = set()
        seen_concept_ids = set()

        for ch_data in CHAPTERS:
            book = books[ch_data['book']]
            topic = topics[ch_data['topic']]
            chapter, _ = Chapter.objects.update_or_create(
                book=book, slug=ch_data['slug'],
                defaults=dict(
                    title=ch_data['title'], order=ch_data['order'],
                    unlock_level=ch_data['unlock_level'], summary=ch_data['summary'],
                    topic=topic, difficulty=ch_data['difficulty'],
                ),
            )
            chapter_count += 1
            seen_chapter_ids.add(chapter.id)

            c_data = ch_data['concept']
            concept, _ = Concept.objects.update_or_create(
                chapter=chapter, slug=c_data['slug'],
                defaults=dict(
                    title=c_data['title'], order=1,
                    summary=c_data['summary'], source_note=c_data['source_note'],
                    notes_sections=c_data.get('notes', []),
                ),
            )
            concept_count += 1
            seen_concept_ids.add(concept.id)

            # Wipe and re-create questions for idempotent re-seeding.
            concept.questions.all().delete()
            for q_data in c_data['questions']:
                question = Question.objects.create(
                    concept=concept, kind=q_data.get('kind', Question.MCQ), prompt=q_data['prompt'],
                    explanation=q_data.get('explanation', ''),
                    difficulty=q_data.get('difficulty', 1),
                )
                for i, (text, is_correct) in enumerate(q_data['choices']):
                    Choice.objects.create(question=question, text=text, is_correct=is_correct, order=i)
                question_count += 1

        # Content restructuring (merging several chapters into one bigger
        # "domain" chapter/concept) leaves the old chapter/concept rows
        # behind under slugs that no longer appear above. Clean those up so
        # the dashboard/chapter list doesn't show stale duplicates. Any
        # matching/ordering/design challenges still pointing at a removed
        # concept get cascade-deleted here, but seed_games.py always
        # recreates them (by slug) pointed at the surviving/merged concept,
        # so run seed_games right after this command.
        stale_chapters = Chapter.objects.exclude(id__in=seen_chapter_ids)
        stale_chapter_count = stale_chapters.count()
        stale_chapters.delete()

        stale_concepts = Concept.objects.exclude(id__in=seen_concept_ids)
        stale_concept_count = stale_concepts.count()
        stale_concepts.delete()

        ensure_badges_exist()

        self.stdout.write(self.style.SUCCESS(
            f'Seeded {len(books)} books, {len(topics)} topics, {chapter_count} chapters, '
            f'{concept_count} concepts, {question_count} questions. '
            f'Removed {stale_chapter_count} stale chapters, {stale_concept_count} stale concepts.'
        ))
