from django.core.management.base import BaseCommand
from django.db import transaction

from learn.models import (
    ComponentType, Concept, DesignChallenge, DesignChallengeComponent,
    DesignChallengeConnection, FlawChallenge, FlawPart, FlawReason,
    MatchingChallenge, MatchingPair, OrderingChallenge, OrderingStep, QuorumChallenge, RingChallenge, TrafficChallenge,
)

COMPONENT_TYPES = [
    # cs-01 ticket booking
    ('buyer', 'Buyer', '🧑'),
    ('reservation-api', 'Reservation API', '🚪'),
    ('seat-map-cache', 'Seat-map Cache', '⚡'),
    ('reservation-db', 'Reservation Database', '🗄️'),
    ('payment-adapter', 'Payment Adapter', '🔌'),
    ('payment-provider', 'Payment Provider', '💳'),
    ('outbox-relay', 'Outbox Relay', '📤'),
    ('notification-worker', 'Notification Worker', '🔔'),
    ('cache-seat-lock', 'Cache-only Seat Lock', '🔒'),
    ('in-process-seat-mutex', 'In-process Seat Mutex', '🧷'),
    ('inline-email-sender', 'Inline Email Sender', '✉️'),
    # cs-02 payment processing
    ('merchant-client', 'Merchant Client', '🏪'),
    ('payments-api', 'Payments API', '🚪'),
    ('workflow-journal-store', 'Workflow & Journal Store', '📒'),
    ('provider-adapter', 'Provider Adapter', '🔌'),
    ('webhook-ingress', 'Verified Webhook Ingress', '📨'),
    ('event-worker', 'Event Worker', '⚙️'),
    ('reconciler', 'Reconciler', '⚖️'),
    ('timeout-auto-fail', 'Timeout Auto-fail Job', '⏲️'),
    ('arrival-order-sequencer', 'Arrival-order Sequencer', '🔢'),
    ('unverified-webhook', 'Unverified Webhook Endpoint', '🕳️'),
    # cs-03 job scheduling
    ('scheduling-api', 'Scheduling API', '🚪'),
    ('job-store', 'Job & Attempt Store', '🗄️'),
    ('due-job-scheduler', 'Due-job Scheduler', '⏰'),
    ('work-broker', 'Work Broker', '📬'),
    ('bounded-workers', 'Bounded Workers', '👷'),
    ('result-authority', 'Result Authority', '🏁'),
    ('recovery-loop', 'Recovery Loop', '♻️'),
    ('local-clock-lease', 'Worker Local-clock Lease Check', '🕰️'),
    ('single-server-cron', 'In-memory Cron on One Server', '🗓️'),
    ('exactly-once-executor', 'Exactly-once Executor', '🎯'),
    # cs-04 search and autocomplete
    ('search-client', 'Search Client', '🔎'),
    ('query-api', 'Query API', '🚪'),
    ('authorization-service', 'Authorization', '🛡️'),
    ('search-index', 'Search Index', '📚'),
    ('suggestion-index', 'Suggestion Index', '💡'),
    ('content-authority', 'Content Authority', '🗄️'),
    ('change-stream', 'Change Stream', '📤'),
    ('version-aware-indexer', 'Version-aware Indexer', '🏷️'),
    ('public-title-prefix-list', 'Public Prefix List of All Titles', '🗒️'),
    ('index-only-visibility', 'Index-only Visibility Check', '🙈'),
    ('api-dual-write', 'API Dual Write to DB and Index', '✍️'),
    # cs-05 feature flags
    ('flag-administrator', 'Authorized Administrator', '🛠️'),
    ('control-api', 'Control API', '🎛️'),
    ('config-audit-store', 'Versioned Config & Audit', '🗄️'),
    ('distribution-service', 'Distribution Service', '📡'),
    ('sdk-snapshot', 'Local SDK Snapshot', '💾'),
    ('flag-application', 'Application', '🖥️'),
    ('evaluation-telemetry', 'Evaluation Telemetry', '📈'),
    ('per-evaluation-fetch', 'Per-evaluation Remote Fetch', '🐢'),
    ('flag-as-permission', 'Flag-based API Permission', '🔓'),
    ('client-side-secret-rules', 'Client-side Secret Rules', '🗝️'),
    # cs-06 multi-region SaaS
    ('tenant-clients', 'Tenant Clients', '👥'),
    ('global-routing', 'Global Routing', '🌐'),
    ('tenant-directory', 'Tenant Directory & Authority', '📇'),
    ('region-a-app', 'Region A Application', '🅰️'),
    ('region-b-app', 'Region B Application', '🅱️'),
    ('region-a-data', 'Region A Data', '🗄️'),
    ('region-b-data', 'Region B Data', '💽'),
    ('recovery-backups', 'Recovery Backups', '🧯'),
    ('dns-only-failover', 'DNS-only Failover Switch', '🔀'),
    ('lww-billing-merge', 'Last-writer-wins Billing Merge', '✏️'),
    ('shared-global-database', 'Shared Global Database', '🌍'),
]

# One builder per case study, from the reference architecture in
# docs/learning/catalogue.json. Connections are undirected pairs, so a
# two-way edge in the reference graph is one wire here. The distractors are
# the wrong turns each case study's builder brief warns about; the pool is
# the required parts plus these, shuffled.
#
# (challenge_slug, title, concept_slug, prompt, difficulty,
#  required[], distractors[], connections[(a,b), ...])
DESIGN_CHALLENGES = [
    (
        'build-ticket-booking', 'Build the Ticket-booking Flow', 'ticket-booking',
        'Build a seat reservation system that never confirms two bookings for one seat. Browsing may '
        'show a stale seat map, payment happens outside the claim transaction, and confirmations are '
        'sent after the booking commits.',
        3,
        ['buyer', 'reservation-api', 'seat-map-cache', 'reservation-db', 'payment-adapter',
         'payment-provider', 'outbox-relay', 'notification-worker'],
        ['cache-seat-lock', 'in-process-seat-mutex', 'inline-email-sender'],
        [
            ('buyer', 'reservation-api'), ('reservation-api', 'seat-map-cache'),
            ('reservation-api', 'reservation-db'), ('reservation-api', 'payment-adapter'),
            ('payment-adapter', 'payment-provider'), ('payment-adapter', 'reservation-db'),
            ('reservation-db', 'outbox-relay'), ('outbox-relay', 'notification-worker'),
        ],
    ),
    (
        'build-payment-workflow', 'Build the Payment Workflow', 'payment-processing',
        'Build the application side of a payment service: durable commands, provider calls that reuse '
        'one operation key, verified webhooks, an append-only journal, and a reconciler for outcomes '
        'nobody is sure about.',
        3,
        ['merchant-client', 'payments-api', 'workflow-journal-store', 'provider-adapter',
         'payment-provider', 'webhook-ingress', 'event-worker', 'reconciler'],
        ['timeout-auto-fail', 'arrival-order-sequencer', 'unverified-webhook'],
        [
            ('merchant-client', 'payments-api'), ('payments-api', 'workflow-journal-store'),
            ('provider-adapter', 'workflow-journal-store'), ('provider-adapter', 'payment-provider'),
            ('payment-provider', 'webhook-ingress'), ('webhook-ingress', 'workflow-journal-store'),
            ('workflow-journal-store', 'event-worker'), ('reconciler', 'payment-provider'),
            ('reconciler', 'workflow-journal-store'),
        ],
    ),
    (
        'build-job-scheduler', 'Build a Durable Job Scheduler', 'job-scheduling',
        'Build a scheduler that can account for every accepted job through crashes, retries and stale '
        'workers. Delivery is at least once; a result is published only by the attempt that currently '
        'owns the run.',
        3,
        ['scheduling-api', 'job-store', 'due-job-scheduler', 'outbox-relay', 'work-broker',
         'bounded-workers', 'result-authority', 'recovery-loop'],
        ['local-clock-lease', 'single-server-cron', 'exactly-once-executor'],
        [
            ('scheduling-api', 'job-store'), ('due-job-scheduler', 'job-store'),
            ('job-store', 'outbox-relay'), ('outbox-relay', 'work-broker'),
            ('work-broker', 'bounded-workers'), ('bounded-workers', 'job-store'),
            ('bounded-workers', 'result-authority'), ('recovery-loop', 'job-store'),
            ('recovery-loop', 'work-broker'),
        ],
    ),
    (
        'build-search-autocomplete', 'Build Search and Autocomplete', 'search-autocomplete',
        'Build search over a content database as a rebuildable projection: committed changes flow to a '
        'version-aware indexer, and every query passes an authorization check even while the index lags.',
        3,
        ['search-client', 'query-api', 'authorization-service', 'search-index', 'suggestion-index',
         'content-authority', 'change-stream', 'version-aware-indexer'],
        ['public-title-prefix-list', 'index-only-visibility', 'api-dual-write'],
        [
            ('search-client', 'query-api'), ('query-api', 'authorization-service'),
            ('query-api', 'search-index'), ('query-api', 'suggestion-index'),
            ('content-authority', 'change-stream'), ('change-stream', 'version-aware-indexer'),
            ('version-aware-indexer', 'search-index'), ('version-aware-indexer', 'suggestion-index'),
        ],
    ),
    (
        'build-feature-flags', 'Build a Feature-flag Service', 'feature-flags',
        'Build a flag service whose control plane is separate from evaluation: applications evaluate '
        'flags locally from a validated snapshot, fall back to typed defaults, and report bounded '
        'diagnostics.',
        3,
        ['flag-administrator', 'control-api', 'config-audit-store', 'distribution-service',
         'sdk-snapshot', 'flag-application', 'evaluation-telemetry'],
        ['per-evaluation-fetch', 'flag-as-permission', 'client-side-secret-rules'],
        [
            ('flag-administrator', 'control-api'), ('control-api', 'config-audit-store'),
            ('config-audit-store', 'distribution-service'), ('distribution-service', 'sdk-snapshot'),
            ('flag-application', 'sdk-snapshot'), ('sdk-snapshot', 'evaluation-telemetry'),
        ],
    ),
    (
        'build-multi-region-saas', 'Build Home-region Failover', 'multi-region-saas',
        'Build the path for a tenant whose home is Region A, with Region B as its failover target. '
        'Routing asks the tenant directory which region holds write authority, Region A replicates '
        'to Region B, and recoverable history goes to backups.',
        3,
        ['tenant-clients', 'global-routing', 'tenant-directory', 'region-a-app', 'region-b-app',
         'region-a-data', 'region-b-data', 'recovery-backups'],
        ['dns-only-failover', 'lww-billing-merge', 'shared-global-database'],
        [
            ('tenant-clients', 'global-routing'), ('global-routing', 'tenant-directory'),
            ('global-routing', 'region-a-app'), ('global-routing', 'region-b-app'),
            ('region-a-app', 'region-a-data'), ('region-b-app', 'region-b-data'),
            ('region-a-data', 'region-b-data'), ('region-a-data', 'recovery-backups'),
        ],
    ),
]

MATCHING_CHALLENGES = [
    (
        'match-request-layers', 'What Each Layer Guarantees', 'dns-tcp-tls',
        [
            ('DNS', 'Maps a hostname to records, answering from cache or by following the hierarchy to an authoritative server.'),
            ('TCP', 'Carries an ordered byte stream with retransmission and flow and congestion control.'),
            ('TLS', 'Authenticates the server and protects the connection with encryption and integrity.'),
            ('HTTP', 'Defines the application request and response.'),
            ('TTL', 'Limits how long a cached DNS answer may be reused.'),
        ],
    ),
    (
        'match-http-contract', 'HTTP Contract Vocabulary', 'http-api-design',
        [
            ('Safe method', 'The client does not request a state-changing action, as with GET.'),
            ('Idempotent operation', 'Repeating it has the same intended effect on state as doing it once, as with PUT and DELETE.'),
            ('202 Accepted', 'The work was accepted for processing; completion needs a separate observation.'),
            ('ETag', 'Identifies one version of a representation.'),
            ('412 Precondition Failed', 'A conditional write was rejected because the client’s If-Match version is stale.'),
        ],
    ),
    (
        'match-latency-terms', 'Latency and Throughput Terms', 'latency-throughput',
        [
            ('Throughput', 'Completed work per unit of time.'),
            ('Latency', 'Elapsed time of one operation, including any waiting.'),
            ('Service time', 'Time a resource spends actually doing the work.'),
            ("Little's Law", 'Average work in the system equals throughput times average time in the system.'),
            ('Tail percentile', 'Describes the slow requests an average can hide.'),
        ],
    ),
    (
        'match-concurrency-terms', 'Concurrency Vocabulary', 'concurrency-basics',
        [
            ('Concurrency', 'Several tasks in progress during overlapping periods.'),
            ('Parallelism', 'Work running at the same instant on separate resources.'),
            ('Lost update', 'Two read-modify-write sequences interleave and one change disappears.'),
            ('Atomicity', 'A group of related writes commits together or has no effect.'),
            ('Optimistic version check', 'A write succeeds only if the version is unchanged since it was read, retrying on conflict.'),
        ],
    ),
    (
        'match-query-plans', 'Reading Query Plans', 'indexes-query-plans',
        [
            ('EXPLAIN', 'Shows the strategy the planner intends to use, from estimates.'),
            ('EXPLAIN ANALYZE', 'Executes the statement and reports measured behavior.'),
            ('Sequential scan', 'Reads the whole table in order; can win when a query needs much of it.'),
            ('Covering index', 'Holds every column a query needs, saving table reads at extra storage cost.'),
            ('N+1 queries', 'One query for a list, then one more for each item in it.'),
        ],
    ),
    (
        'match-probes-routing', 'Health Checks and Routing', 'load-balancing-health',
        [
            ('Readiness probe', 'Decides whether a pod receives Service traffic.'),
            ('Liveness probe', 'Can restart a container that has stopped making progress.'),
            ('Startup probe', 'Protects slow initialization from the other checks.'),
            ('Least outstanding requests', 'Routes to the instance with the fewest requests in progress, helping when durations vary.'),
            ('Sticky sessions', 'Pins a client to one instance, simplifying state access but concentrating work.'),
        ],
    ),
    (
        'match-cache-terms', 'Caching Vocabulary', 'caching-invalidation',
        [
            ('Cache-aside', 'The application checks the cache, reads the authority on a miss, and fills the cache.'),
            ('TTL', 'Limits how long a cached copy may live.'),
            ('Eviction', 'Removes entries under capacity pressure.'),
            ('no-cache', 'A stored response must be validated before reuse.'),
            ('no-store', 'Caches subject to the directive must not store the response.'),
            ('Request coalescing', 'One request refreshes a key while the others wait or use a permitted stale value.'),
        ],
    ),
    (
        'match-pool-settings', 'Connection Pool Settings', 'connection-pooling',
        [
            ('Pool size', 'The most connections one pool keeps open at once.'),
            ('Acquire timeout', 'How long a request waits for a free connection before failing.'),
            ('Connection lifetime', 'How long a connection is kept before it is replaced.'),
            ('Session pooling', 'Reserves a server connection for a client’s whole session.'),
            ('Transaction pooling', 'Releases the server connection after each transaction.'),
        ],
    ),
    (
        'match-pagination', 'Pagination Contracts', 'pagination-access-patterns',
        [
            ('Offset pagination', 'Skips a count of rows: easy page numbers, but items repeat or vanish as the collection changes.'),
            ('Keyset pagination', 'Continues after the last ordered key seen.'),
            ('Tiebreaker', 'A unique column added to the sort so equal timestamps stay unambiguous.'),
            ('Signed cursor', 'Lets the server detect a tampered continuation token.'),
            ('Snapshot token', 'Pins traversal to a point-in-time view instead of the live collection.'),
        ],
    ),
    (
        'match-retry-controls', 'Retry Controls', 'timeouts-retries-jitter',
        [
            ('Total deadline', 'The whole time the caller will wait, across every attempt.'),
            ('Per-attempt timeout', 'How long a single try may take.'),
            ('Exponential backoff', 'Grows the wait between attempts.'),
            ('Jitter', 'Randomizes retry times so clients do not retry in step.'),
            ('Retry budget', 'Caps the extra load retries may add, often propagated across layers.'),
            ('Circuit breaker', 'Stops calling a failing dependency for a while, then probes it.'),
        ],
    ),
    (
        'match-idempotency', 'Idempotency Building Blocks', 'idempotency-deduplication',
        [
            ('Idempotency key', 'A caller-supplied identity for one intended operation.'),
            ('Request fingerprint', 'A stored summary of the input, used to reject a key reused with different parameters.'),
            ('Unique constraint', 'Makes concurrent duplicates compete for a single claim on the key.'),
            ('Retention window', 'How long identifying state is kept, which bounds duplicate suppression.'),
            ('Pending record', 'Marks an operation in progress, with ownership and recovery rules.'),
        ],
    ),
    (
        'match-delivery-guarantees', 'Delivery Guarantees', 'delivery-ordering',
        [
            ('At-most-once', 'Never retries an uncertain delivery, so work can be lost.'),
            ('At-least-once', 'Retries until acknowledged, so work can repeat.'),
            ('Exactly-once', 'Meaningful only inside a defined protocol boundary.'),
            ('Partition ordering', 'Order is kept within one partition or stream, not across the whole system.'),
            ('Processed-event record', 'A unique row, written with the effect, that lets a replay skip events already applied.'),
        ],
    ),
    (
        'match-overload-controls', 'Overload Controls', 'backpressure-load-shedding',
        [
            ('Rate limit', 'Bounds arrivals over time.'),
            ('Concurrency limit', 'Bounds work in flight.'),
            ('Queue limit', 'Bounds work waiting to start.'),
            ('Load shedding', 'Rejects some work to protect the valuable work that completes.'),
            ('Graceful degradation', 'Reduces what a successful response attempts, such as leaving out recommendations.'),
            ('Per-tenant budget', 'Stops one noisy tenant consuming the shared capacity.'),
        ],
    ),
    (
        'match-slo-terms', 'Reliability Targets', 'slos-error-budgets',
        [
            ('SLI', 'A measured indicator of user-visible behavior, such as good events over eligible events.'),
            ('SLO', 'The target fraction of good events over a stated window.'),
            ('Error budget', 'The bad events the target allows: (1 − target) × eligible events.'),
            ('Burn rate', 'The observed bad fraction divided by the allowed bad fraction.'),
            ('Eligible event', 'An event the indicator counts at all, as defined up front.'),
        ],
    ),
    (
        'match-telemetry', 'Telemetry Signals', 'logs-metrics-traces',
        [
            ('Metric', 'A numeric summary of measurements over time.'),
            ('Log', 'A record of a discrete event, with its details.'),
            ('Trace', 'Timed operations linked across one request.'),
            ('Trace Context', 'The W3C headers that carry trace identity between services.'),
            ('High-cardinality label', 'A metric dimension with nearly unbounded values, which multiplies time series.'),
            ('Sampling', 'Keeping a fraction of telemetry to cut cost, at the risk of hiding rare failures.'),
        ],
    ),
    (
        'match-load-tests', 'Load Test Models and Types', 'performance-load-testing',
        [
            ('Closed model', 'Virtual users wait for each iteration before starting the next.'),
            ('Open model', 'New work arrives on schedule, independent of completions.'),
            ('Coordinated omission', 'A slowing system reduces the load a closed test offers, hiding overload.'),
            ('Stress test', 'Raises load to find the limits.'),
            ('Soak test', 'Runs for a long time to expose leaks and slow growth.'),
            ('Recovery test', 'Measures the return to health after overload or failure.'),
        ],
    ),
    (
        'match-access-control', 'Access Control Vocabulary', 'authentication-authorization-tenants',
        [
            ('Authentication', 'Establishes who is making the request.'),
            ('Authorization', 'Decides whether this identity may do this action on this resource now.'),
            ('Object-level check', 'Verifies access each time a client-supplied ID selects a record.'),
            ('Row-level security', 'Database policies that filter rows by role; superusers bypass them.'),
            ('Tenant-scoped cache key', 'Includes the tenant so one customer never receives another’s cached answer.'),
        ],
    ),
    (
        'match-recovery-terms', 'Backup and Recovery Terms', 'backup-disaster-recovery',
        [
            ('RPO', 'How much recent data, measured in time, may be lost.'),
            ('RTO', 'How long restoration may take.'),
            ('Base backup', 'The physical copy point-in-time recovery starts from.'),
            ('Write-ahead log archive', 'The continuous sequence of changes replayed on top of a base backup.'),
            ('Logical dump', 'An export of schema and data; not a starting point for log replay.'),
        ],
    ),
    (
        'match-consistency-models', 'Consistency Models', 'consistency-histories',
        [
            ('Linearizability', 'Each operation appears to take effect at one instant between its invocation and completion.'),
            ('Serializability', 'Concurrent transactions are equivalent to some serial order.'),
            ('Strict serializability', 'Serializability that also respects real-time order.'),
            ('Read-your-writes', 'A session sees its own earlier writes.'),
            ('Monotonic reads', 'A session never sees older data after it has seen newer data.'),
            ('Eventual convergence', 'Replicas agree once updates stop, with no stated freshness bound.'),
        ],
    ),
    (
        'match-consensus-terms', 'Consensus Vocabulary', 'consensus-membership',
        [
            ('Term', 'A numbered period of leadership, used to reject stale leaders.'),
            ('Majority quorum', 'Enough voters that any two such groups overlap.'),
            ('Committed entry', 'A current-term entry replicated to a majority, which the protocol preserves.'),
            ('Joint consensus', 'A transition that needs majorities of both the old and the new configuration.'),
            ('Learner', 'A non-voting member that catches up before promotion.'),
        ],
    ),
    (
        'match-time-terms', 'Clocks and Ownership', 'clocks-leases-fencing',
        [
            ('Wall clock', 'Calendar time, which can drift or jump.'),
            ('Monotonic clock', 'Measures elapsed time locally; cannot order events across machines.'),
            ('Lamport clock', 'A logical counter consistent with causal precedence.'),
            ('Lease', 'Ownership that is valid for a bounded period under a time model.'),
            ('Fencing token', 'An increasing epoch the protected resource uses to reject stale owners.'),
        ],
    ),
    (
        'match-multi-region', 'Multi-region Write Strategies', 'multi-region-conflicts',
        [
            ('Single write owner', 'One region decides each entity’s writes, avoiding some conflicts.'),
            ('Last-writer-wins', 'Converges by picking one winner and discarding concurrent intent.'),
            ('CRDT', 'A data type whose operations and merge rule converge under stated assumptions.'),
            ('Grow-only counter merge', 'Takes the component-wise maximum of each region’s count.'),
            ('Tombstone', 'A retained marker that a value was deleted, so a merge does not bring it back.'),
        ],
    ),
    (
        'match-stream-time', 'Streaming Time and State', 'stream-processing-correctness',
        [
            ('Event time', 'When the event actually happened.'),
            ('Processing time', 'When the processor handles the event.'),
            ('Watermark', 'A progress assumption about event time, used to decide when to emit windows.'),
            ('Checkpoint', 'Saved processing state and source positions for recovery.'),
            ('Late-data policy', 'What happens to events that arrive after their window was emitted.'),
        ],
    ),
    (
        'match-python-dict-internals', 'Python Dict Internals Vocabulary', 'python-advanced-internals',
        [
            ('Sparse Index Array', 'The power-of-2-sized array of small integers a dict hashes into to find a slot.'),
            ('Dense Entries Array', 'The compact array storing (hash, key, value) triples in strict insertion order.'),
            ('Open Addressing / Probing', 'The scheme used to find the next candidate slot when a hash collision occurs.'),
            ('Key-Sharing Dict (PEP 412)', 'An optimization where instances of the same class share one keys array, storing only per-instance values.'),
            ('Hash Randomization', 'Per-process salting of string/bytes hashes (SipHash) that defends against hash-flooding attacks.'),
        ],
    ),
    (
        'match-python-concurrency-tools', 'Python Concurrency Tools', 'python-advanced-internals',
        [
            ('subprocess', 'Launches and controls an entirely separate external program, with full OS-level isolation.'),
            ('multiprocessing', 'Runs separate OS processes with independent memory to achieve true parallelism, bypassing the GIL.'),
            ('threading', 'Runs multiple threads sharing one process’s memory — good for I/O-bound work, limited for CPU-bound work by the GIL.'),
            ('GIL', 'The single mutex that lets only one thread execute Python bytecode at a time per process.'),
            ('asyncio Event Loop', 'A single-threaded scheduler that runs coroutines cooperatively, yielding at await points.'),
        ],
    ),
    (
        'match-file-permission-vocab', 'File Permission Vocabulary', 'os-file-handling-permissions-storage',
        [
            ('Octal digit 7', 'read (4) + write (2) + execute (1) — full access for that class.'),
            ('setuid', 'Special bit (weight 4) making an executable run with its owner’s privileges, not the invoking user’s.'),
            ('setgid', 'Special bit (weight 2); on a directory, new files inside inherit that directory’s group.'),
            ('Sticky bit', 'Special bit (weight 1) restricting deletion inside a world-writable directory to each file’s own owner.'),
            ('umask', 'The value subtracted from the base 666/777 permissions to set defaults for newly created files/directories.'),
        ],
    ),
    (
        'match-inode-filesystem-vocab', 'Inodes & Filesystem Vocabulary', 'os-file-handling-permissions-storage',
        [
            ('Inode', 'The metadata record (owner, permissions, timestamps, data-block pointers) representing a file, but not its name.'),
            ('Hard Link', 'A second directory entry pointing at the same inode, indistinguishable from the “original” name.'),
            ('Symbolic Link', 'Its own inode whose data is just a path string to another file, resolvable across filesystems.'),
            ('Superblock', 'Filesystem-wide metadata: block/inode counts, block size, and clean/dirty state.'),
            ('File Descriptor', 'A small per-process integer indexing into a table that points at a system-wide open file description.'),
        ],
    ),
]

ORDERING_CHALLENGES = [
    (
        'order-capacity-estimate', 'From Product Question to Capacity Estimate', 'requirements-capacity',
        [
            'Write down user actions, request sizes and active-user assumptions',
            'Multiply daily active users by actions per user for the daily volume',
            'Divide the daily volume by 86,400 seconds for the average rate',
            'Apply an assumed peak factor for the busiest period',
            'Multiply peak requests by payload size for peak bandwidth',
            'Measure what one server sustains at the target latency before choosing a server count',
        ],
    ),
    (
        'order-graceful-shutdown', 'Drain an Instance Before Shutdown', 'load-balancing-health',
        [
            'Withdraw readiness so the instance stops being chosen for new traffic',
            'Keep serving while the routing change propagates',
            'Stop admitting new work and track active requests',
            'Let short requests finish within the grace period',
            'Ask long streams to reconnect or resume elsewhere',
            'Force termination once the declared deadline passes',
        ],
    ),
    (
        'order-stale-fill-race', 'How Invalidation Still Serves Stale Data', 'caching-invalidation',
        [
            'Reader A misses the cache and reads version 4 from the database',
            'Writer B commits version 5',
            'Writer B invalidates the cache key',
            'Reader A fills the cache with version 4',
            'Later readers get version 4 until the entry expires',
        ],
    ),
    (
        'order-export-job', 'Life of an Export Job', 'queues-background-jobs',
        [
            'The API stores an operation ID as pending and arranges durable publication',
            'The API returns 202 with a status URL',
            'The broker delivers the job to a worker',
            'The worker writes the report to a versioned object key',
            'The worker marks the operation complete with a conditional update',
            'The worker acknowledges the delivery',
        ],
    ),
    (
        'order-publish-upload', 'Publish a Large Upload', 'object-storage-cdn',
        [
            'Create a pending upload record',
            'Grant a short-lived, narrowly scoped upload capability',
            'The client uploads the bytes directly to object storage',
            'A completion worker verifies the object, its size or checksum, and processing',
            'Metadata switches to the new immutable object key',
            'Readers fetch the versioned URL through the CDN',
        ],
    ),
    (
        'order-outbox-flow', 'Transactional Outbox, Step by Step', 'outbox-cdc',
        [
            'Confirm order 81 and insert event e81 into the outbox, in one local transaction',
            'Commit the transaction',
            'The relay reads the committed outbox row',
            'The relay publishes e81 to the broker',
            'The relay records its progress',
        ],
    ),
    (
        'order-rental-saga', 'Compensate a Declined Rental', 'sagas-compensation',
        [
            'The coordinator records the new workflow',
            'Reserve the bicycle',
            'Request payment authorization',
            'The provider declines the payment',
            'The coordinator records the decline',
            'Release the bicycle reservation',
            'Mark the workflow canceled',
        ],
    ),
    (
        'order-expand-contract', 'Rename a Column Safely', 'safe-releases-migrations',
        [
            'Add a nullable display_name column',
            'Deploy code that writes both full_name and display_name',
            'Backfill display_name in small, restartable batches',
            'Verify counts and semantics',
            'Switch reads to display_name',
            'Stop writing full_name',
            'Drop full_name once no version, job or rollback path needs it',
        ],
    ),
    (
        'order-two-phase-commit', 'Two-phase Commit', 'distributed-transactions',
        [
            'The coordinator asks every participant to prepare',
            'Each participant durably records its prepared state and votes',
            'The coordinator durably records the commit decision',
            'The coordinator tells each participant to commit',
            'Each participant commits and releases its locks',
        ],
    ),
    (
        'order-fenced-publish', 'A Stale Worker Meets a Fence', 'clocks-leases-fencing',
        [
            'Worker 1 acquires the lease with epoch 41',
            'Worker 1 stalls mid-job',
            'The lease expires and worker 2 acquires epoch 42',
            'Worker 2 publishes its result with epoch 42',
            'Worker 1 resumes and tries to publish with epoch 41',
            'The store compares epochs and rejects the stale write',
        ],
    ),
    (
        'order-dict-lookup-process', 'Python Dict Lookup: Step by Step', 'python-advanced-internals',
        [
            'Compute hash(key)',
            'Use the hash to select a starting slot in the sparse index array (hash & mask)',
            'Read the dense-array index stored at that slot',
            'Compare the stored hash, then the key itself, for a match',
            'If it doesn’t match, follow the probe sequence to the next candidate slot',
            'Return the value on a match, or raise KeyError on an empty slot',
        ],
    ),
    (
        'order-thread-io-gil-release', 'A Thread Releasing the GIL During I/O', 'python-advanced-internals',
        [
            'Thread A starts a blocking network read call',
            'Thread A releases the GIL while waiting on the I/O',
            'Thread B acquires the GIL and executes Python bytecode',
            'Thread A’s I/O operation completes in the background',
            'Thread A re-acquires the GIL',
            'Thread A resumes executing Python bytecode',
        ],
    ),
    (
        'order-chmod-digit-calculation', 'Building a chmod Digit From r/w/x', 'os-file-handling-permissions-storage',
        [
            'Identify which of read, write, and execute are granted for this class',
            'Assign the weight for each granted bit: read=4, write=2, execute=1',
            'Sum the weights for that class into a single digit',
            'Repeat separately for owner, group, and other',
            'Combine the three digits in owner-group-other order as the chmod argument',
        ],
    ),
    (
        'order-file-deletion-open-fd', 'Deleting a File a Process Still Has Open', 'os-file-handling-permissions-storage',
        [
            '`rm` calls unlink() on the file’s directory entry',
            'The inode’s link count is decremented and the entry disappears from `ls`',
            'A process that already had the file open keeps reading/writing via its existing file descriptor',
            'The data blocks stay allocated as long as any file descriptor on the file remains open',
            'The last open file descriptor on the file is closed',
            'The inode and its data blocks are finally freed',
        ],
    ),
]

# Spot the Flaw: an architecture diagram with design mistakes planted in it.
# Geometry is in the challenge's SVG viewBox (width x height). Boxes are
# (x, y, w, h); arrows are SVG paths, with `at` placing an optional caption.
# A part with `flaw` is a planted mistake: its first reason is the right one
# (the page shuffles them). Every other part has an `ok` note saying why
# it's fine, which the learner reads after tapping it.
FLAW_CHALLENGES = [
    dict(
        slug='flaw-notification-system', title='Review a Flawed Notification System',
        concept='queues-background-jobs', width=1000, height=430,
        prompt=(
            'This notification system has four planted design mistakes. '
            'Tap each part you think is wrong, then say why.'
        ),
        boxes=[
            dict(key='order', label='Order Service', box=(16, 60, 150, 52),
                 ok='Callers only publish a "notify this user" event and carry on. That boundary is right.'),
            dict(key='billing', label='Billing Service', box=(16, 150, 150, 52),
                 ok='Another caller publishing events. Nothing wrong here.'),
            dict(key='userdb', label='User & Device DB', box=(16, 262, 150, 52),
                 ok='The server needs device tokens, phone numbers and email addresses to reach each channel.'),
            dict(key='optout', label='Opt-out Settings', box=(16, 338, 150, 52),
                 ok="Checking each user's notification preferences before sending is part of the design."),
            dict(key='ns', label='Notification Server', sub='1 instance', box=(220, 96, 170, 68), flaw=[
                "One instance is a single point of failure and can't scale out. Run several behind a load balancer.",
                'It should render the email HTML itself instead of leaving that to the workers.',
                'It should read user data through the message queue instead of the database.',
            ]),
            dict(key='queue', label='Message Queue', sub='shared by all channels', box=(440, 96, 170, 68), flaw=[
                'With one queue for every channel, a slow SMS provider backs up push and email too. '
                'Use one queue per channel.',
                'Queues add delay. The server should call each provider directly.',
                'A message broker can only hold one type of message per queue.',
            ]),
            dict(key='push', label='Push Workers', box=(660, 40, 150, 52),
                 ok='A worker pool per channel drains its own queue at a steady rate. That is the design.'),
            dict(key='email', label='Email Workers', sub='drop a send on error', box=(660, 130, 150, 68), flaw=[
                'Provider failures are routine. Retry with exponential backoff and record each attempt '
                'in a notification log.',
                'Workers should retry instantly in a tight loop until the send succeeds.',
                'Email should be sent by the Notification Server, not by a worker.',
            ]),
            dict(key='apns', label='APNs / FCM', box=(850, 40, 134, 52),
                 ok='Apple and Google own delivery to devices. Handing push to them is correct.'),
            dict(key='sendgrid', label='SendGrid', box=(850, 138, 134, 52),
                 ok='A third-party email provider owns delivery. Correct.'),
            dict(key='twilio', label='Twilio SMS', box=(850, 356, 134, 52),
                 ok='Using an SMS provider is correct. Look at how it is being called.'),
        ],
        arrows=[
            dict(key='e-order', label='Order Service to Notification Server', d='M166 86 L220 118',
                 ok='Events flow from callers to the notification server. Fine.'),
            dict(key='e-billing', label='Billing Service to Notification Server', d='M166 176 L220 142',
                 ok='Events flow from callers to the notification server. Fine.'),
            dict(key='e-userdb', label='Notification Server to User & Device DB', d='M250 164 L166 288',
                 ok='Looking up contact details and device tokens is needed.'),
            dict(key='e-optout', label='Notification Server to Opt-out Settings', d='M284 164 L166 364',
                 ok='Checking preferences before sending is needed.'),
            dict(key='e-queue', label='Notification Server to Message Queue', d='M390 130 L440 130',
                 ok='Publishing to a queue decouples the server from delivery. Fine.'),
            dict(key='e-push', label='Message Queue to Push Workers', d='M610 116 L660 70',
                 ok='Workers pull from a queue. Fine.'),
            dict(key='e-email', label='Message Queue to Email Workers', d='M610 144 L660 160',
                 ok='Workers pull from a queue. Fine.'),
            dict(key='e-apns', label='Push Workers to APNs / FCM', d='M810 66 L850 66',
                 ok='Workers call the provider. Fine.'),
            dict(key='e-sendgrid', label='Email Workers to SendGrid', d='M810 164 L850 164',
                 ok='Workers call the provider. Fine.'),
            dict(key='e-sms', label='Notification Server calls Twilio SMS directly', d='M330 164 V382 H850',
                 caption='sync HTTP call per SMS', at=(590, 372), flaw=[
                     'If Twilio is slow or down, the server blocks with it, and a burst of events hits Twilio '
                     'all at once. Put SMS behind its own queue.',
                     'SMS has to be sent over a WebSocket.',
                     'Twilio should sit behind a CDN.',
                 ]),
        ],
    ),
]

# Traffic Day: one simulated day of traffic against a design the learner can
# change at any time. `params` feeds both copies of the load model
# (learn/traffic.py and learn/static/learn/traffic_model.js). Rates are per
# second on average across the day; prices are dollars per hour; `events` are
# ops-log lines keyed by 10-minute tick (tick 114 is 19:00).
TRAFFIC_CHALLENGES = [
    dict(
        slug='traffic-url-shortener', title='Run a URL Shortener Through a Viral Day',
        concept='caching-invalidation',
        prompt=(
            'Run a URL shortener through one day of traffic: 12,000 reads and 1,000 writes per second '
            'on average, and a viral link at 19:00. Change the design at any time, even mid-run. Any '
            'design that stays inside the SLO passes.'
        ),
        params={
            'source': 'sd-08 Caching, invalidation, and stampedes · sd-06 Requirements and capacity · '
                      'RFC 9110 (301 and 302 redirects)',
            'reads_per_sec': 12000, 'writes_per_sec': 1000,
            'app_capacity': 5000, 'db_capacity': 6000,
            'hourly_cost': {'app': 1.5, 'cache': 0.8, 'db': 2.0},
            'slo': {'p99_ms': 200, 'error_rate': 0.01},
            'spike': {'at_hour': 19, 'hours': 1.5, 'reads_per_sec': 24000},
            'score': {'start': 1000, 'per_breach': 50, 'analytics': 250},
            'limits': {'servers': [1, 14], 'replicas': [0, 4]},
            'start': {'servers': 4, 'replicas': 1, 'cache': False, 'redirect': 302},
            'briefing': 'Marketing warns you: a celebrity will post one of your links around 19:00.',
            'events': {
                '42': 'Morning traffic is picking up.',
                '102': 'The evening peak starts. It tops out around 20:00.',
                '114': 'A celebrity posts one of your short links. Reads of that one URL jump by 24,000 a second.',
                '123': 'The viral wave fades.',
                '138': 'Traffic winds down for the night.',
            },
        },
    ),
]


# Quorum Casino: replicas hold the key x while the learner steps through a
# script of writes, crashes, partitions and syncs, betting before each read.
# learn/quorum.py plays the script and documents the step shapes; replicas
# are named A, B, C... up to N. Every table needs a read, and a read needs a
# successful write before it (the bet is on returning it). The tests run
# quorum.validate_tables over these.
QUORUM_CHALLENGES = [
    dict(
        slug='quorum-casino-three-replicas', title='Bet on Quorum Reads',
        concept='consistency-histories',
        source='sd-25 Consistency and histories: quorum arithmetic alone does not prove a protocol linearizable',
        prompt=(
            'Three replicas hold the key x. Step through writes, crashes and partitions. Before each '
            'read, bet how likely it is to return the last successful write.'
        ),
        tables=[
            dict(
                name='Table 1: strict quorum', N=3, W=2, R=2,
                steps=[
                    dict(t='write', val=1, reach=['A', 'B', 'C'], say='The client writes x = 1. All three replicas store it.'),
                    dict(t='status', set={'C': 'cut'}, say='A network partition cuts C off from the client.'),
                    dict(t='write', val=2, reach=['A', 'B'], say='The client writes x = 2. Only A and B receive it.'),
                    dict(t='status', set={'C': 'up'}, say='The partition heals. C still holds the old x = 1.'),
                    dict(t='read'),
                    dict(t='status', set={'A': 'down'}, say='Replica A crashes.'),
                    dict(t='read'),
                    dict(t='write', val=3, reach=['B', 'C'], say='The client writes x = 3. B and C receive it.'),
                    dict(t='status', set={'B': 'down'}, say='Replica B crashes too.'),
                    dict(t='read'),
                ],
                outro=(
                    'With R + W > N, every set of replicas a read asks overlaps every set a successful '
                    'write reached, so reads were certain. The price is availability: with two replicas '
                    'down, the read failed.'
                ),
            ),
            dict(
                name='Table 2: fast and loose', N=3, W=1, R=1,
                steps=[
                    dict(t='write', val=1, reach=['A', 'B', 'C'], say='The client writes x = 1. All three replicas store it.'),
                    dict(t='status', set={'B': 'cut', 'C': 'cut'}, say='A network blip: only A is reachable.'),
                    dict(t='write', val=2, reach=['A'], say='The client writes x = 2. Only A receives it.'),
                    dict(t='status', set={'B': 'up', 'C': 'up'}, say='The blip ends. B and C still hold x = 1.'),
                    dict(t='read'),
                    {'t': 'sync', 'from': 'A', 'to': 'B', 'say': 'Background anti-entropy copies x = 2 from A to B.'},
                    dict(t='read'),
                    dict(t='write', val=3, reach=['C'], say='The client writes x = 3. C answers first; A and B have not applied it yet.'),
                    dict(t='read'),
                ],
                outro=(
                    'With R + W ≤ N, a read can miss the replicas a write reached. Reads were fast and '
                    'always answered, but freshness came down to which replica you happened to ask.'
                ),
            ),
            dict(
                name='Table 3: safe writes?', N=3, W=3, R=1,
                steps=[
                    dict(t='write', val=1, reach=['A', 'B', 'C'], say='The client writes x = 1. All three replicas store it.'),
                    dict(t='status', set={'C': 'down'}, say='Replica C crashes.'),
                    dict(t='write', val=2, reach=['A', 'B'], say='The client writes x = 2. Only A and B receive it.'),
                    dict(t='read'),
                    dict(t='status', set={'C': 'up'}, say='C recovers, still holding x = 1.'),
                    dict(t='read'),
                ],
                outro=(
                    'W = N makes writes fragile: one crashed replica turns every write into a failure. '
                    'Worse, a failed write is not rolled back on the replicas that applied it, so reads '
                    'can return a value the client was told never saved. Quorum sizes alone do not '
                    'define what a read may return (sd-25).'
                ),
            ),
        ],
    ),
]


# Ring Balancer: 2,000 cache keys on a consistent-hash ring. learn/ring.py
# plays the stages and documents their shape. A server's `w` is its capacity,
# so S5 (w=2) has twice the fair share. Challenge 3's tolerance is 20%, not
# 25%: at 25% an unweighted ring passes by luck at 83 and 84 virtual nodes,
# and at 20% none does, so only weighting by capacity clears it. The tests
# run ring.validate_stages over these and check that.
_FOUR = [dict(id='S1', w=1), dict(id='S2', w=1), dict(id='S3', w=1), dict(id='S4', w=1)]
RING_CHALLENGES = [
    dict(
        slug='ring-balancer-cache-cluster', title='Balance a Cache Ring',
        concept='caching-invalidation',
        source=('sd-08 Caching, invalidation, and stampedes · Karger et al., Consistent Hashing and Random '
                'Trees (STOC 1997) · DeCandia et al., Dynamo (SOSP 2007), virtual nodes sized to capacity'),
        prompt=(
            '2,000 cache keys sit on a hash ring. Each key belongs to the first server position '
            'clockwise from it. Balance the load, survive a crash, and make room for a bigger machine.'
        ),
        stages=[
            dict(
                t='balance', title='Challenge 1: Even out the load', servers=_FOUR,
                text=(
                    'Four equal cache servers, one ring position each. Add virtual nodes until the '
                    'busiest server is at most 25% over its fair share, using as few ring positions '
                    'as you can.'
                ),
                rule='busiest', within=25, weights=False,
                done='More virtual nodes smooth the load, but every position is a routing-table entry.',
            ),
            dict(
                t='predict', title='Challenge 2: Lose a server', servers=_FOUR,
                text='S3 is about to crash. Predict how many keys change server.',
                questions=[
                    dict(
                        ask='On the ring, when S3 crashes, roughly what share of all keys will move to a different server?',
                        scheme='ring', crash='S3',
                        options=['About a quarter, only the keys S3 owned', 'About three quarters', 'All of them'],
                        answer=0,
                        after=(
                            'S3 is down. Only its keys moved, each to the next position clockwise, so '
                            'they spread over its ring neighbours. Now the same crash under hash(key) % N.'
                        ),
                    ),
                    dict(
                        ask='With hash(key) % N, N drops from 4 to 3. Roughly what share of keys move?',
                        scheme='mod', crash='S3',
                        options=['About a quarter', 'About three quarters', 'All of them'],
                        answer=1,
                        after=(
                            'Under hash(key) % N, most keys moved, including keys that S3 never held. '
                            'For a cache, that means most requests miss at once and fall through to the '
                            'database at the same moment: a cache stampede.'
                        ),
                    ),
                ],
            ),
            dict(
                t='balance', title='Challenge 3: A bigger box joins',
                servers=_FOUR + [dict(id='S5', w=2)],
                text=(
                    'S3 is back and S5 has twice the memory of the others, so its fair share is twice '
                    'as big. Get every server within 20% of its fair share.'
                ),
                rule='every', within=20, weights=True,
                done='S5 got twice the virtual nodes, so it owns about twice the keys.',
                unweighted_hint='S5 has twice the memory but the same number of ring positions as everyone else.',
            ),
        ],
    ),
]


class Command(BaseCommand):
    help = 'Seed drag-and-drop architecture builder, matching, ordering, spot-the-flaw, traffic-day, quorum-casino, and ring-balancer mini-games.'

    @transaction.atomic
    def handle(self, *args, **options):
        types = {}
        for slug, name, icon in COMPONENT_TYPES:
            ct, _ = ComponentType.objects.update_or_create(
                slug=slug, defaults={'name': name, 'icon': icon},
            )
            types[slug] = ct

        design_count = 0
        for slug, title, concept_slug, prompt, difficulty, required, distractors, conns in DESIGN_CHALLENGES:
            concept = Concept.objects.get(slug=concept_slug)
            challenge, _ = DesignChallenge.objects.update_or_create(
                slug=slug, defaults=dict(concept=concept, title=title, prompt=prompt, difficulty=difficulty),
            )
            challenge.pool_components.all().delete()
            challenge.correct_connections.all().delete()
            for i, s in enumerate(required):
                DesignChallengeComponent.objects.create(
                    challenge=challenge, component_type=types[s], is_required=True, order=i,
                )
            # Each case study's parts are specific to it, so the pool is the
            # required parts plus that case's hand-picked wrong turns, not the
            # whole catalog: another case's parts can be defensible here.
            for i, s in enumerate(distractors):
                DesignChallengeComponent.objects.create(
                    challenge=challenge, component_type=types[s], is_distractor=True, order=len(required) + i,
                )
            for a, b in conns:
                DesignChallengeConnection.objects.create(
                    challenge=challenge, from_component=types[a], to_component=types[b],
                )
            design_count += 1

        matching_count = 0
        for slug, title, concept_slug, pairs in MATCHING_CHALLENGES:
            concept = Concept.objects.get(slug=concept_slug)
            challenge, _ = MatchingChallenge.objects.update_or_create(
                slug=slug, defaults=dict(concept=concept, title=title),
            )
            challenge.pairs.all().delete()
            for i, (term, definition) in enumerate(pairs):
                MatchingPair.objects.create(challenge=challenge, term=term, definition=definition, order=i)
            matching_count += 1

        ordering_count = 0
        for slug, title, concept_slug, steps in ORDERING_CHALLENGES:
            concept = Concept.objects.get(slug=concept_slug)
            challenge, _ = OrderingChallenge.objects.update_or_create(
                slug=slug, defaults=dict(concept=concept, title=title),
            )
            challenge.steps.all().delete()
            for i, text in enumerate(steps, start=1):
                OrderingStep.objects.create(challenge=challenge, text=text, correct_position=i)
            ordering_count += 1

        flaw_count = 0
        for spec in FLAW_CHALLENGES:
            concept = Concept.objects.get(slug=spec['concept'])
            challenge, _ = FlawChallenge.objects.update_or_create(
                slug=spec['slug'], defaults=dict(
                    concept=concept, title=spec['title'], prompt=spec['prompt'],
                    canvas_width=spec['width'], canvas_height=spec['height'],
                ),
            )
            challenge.parts.all().delete()
            specs = [(FlawPart.NODE, b) for b in spec['boxes']] + [(FlawPart.EDGE, a) for a in spec['arrows']]
            for i, (kind, p) in enumerate(specs):
                if kind == FlawPart.NODE:
                    x, y, w, h = p['box']
                    geometry, sublabel = {'x': x, 'y': y, 'w': w, 'h': h}, p.get('sub', '')
                else:
                    geometry, sublabel = {'d': p['d']}, p.get('caption', '')
                    if 'at' in p:
                        geometry['lx'], geometry['ly'] = p['at']
                part = FlawPart.objects.create(
                    challenge=challenge, key=p['key'], kind=kind, label=p['label'], sublabel=sublabel,
                    geometry=geometry, is_flaw='flaw' in p, explanation=p.get('ok', ''), order=i,
                )
                for j, text in enumerate(p.get('flaw', [])):
                    FlawReason.objects.create(part=part, text=text, is_correct=(j == 0), order=j)
            flaw_count += 1

        for spec in TRAFFIC_CHALLENGES:
            TrafficChallenge.objects.update_or_create(
                slug=spec['slug'], defaults=dict(
                    concept=Concept.objects.get(slug=spec['concept']), title=spec['title'],
                    prompt=spec['prompt'], params=spec['params'],
                ),
            )

        for spec in QUORUM_CHALLENGES:
            QuorumChallenge.objects.update_or_create(
                slug=spec['slug'], defaults=dict(
                    concept=Concept.objects.get(slug=spec['concept']), title=spec['title'],
                    prompt=spec['prompt'], source=spec['source'], tables=spec['tables'],
                ),
            )

        for spec in RING_CHALLENGES:
            RingChallenge.objects.update_or_create(
                slug=spec['slug'], defaults=dict(
                    concept=Concept.objects.get(slug=spec['concept']), title=spec['title'],
                    prompt=spec['prompt'], source=spec['source'], stages=spec['stages'],
                ),
            )

        # Component types no longer listed and no longer in any challenge's
        # pool (their challenges went with their concepts in seed_content).
        ComponentType.objects.exclude(slug__in=types).filter(designchallengecomponent__isnull=True).delete()

        self.stdout.write(self.style.SUCCESS(
            f'Seeded {len(types)} component types, {design_count} design challenges, '
            f'{matching_count} matching challenges, {ordering_count} ordering challenges, '
            f'{flaw_count} spot-the-flaw challenges, {len(TRAFFIC_CHALLENGES)} traffic-day challenges, '
            f'{len(QUORUM_CHALLENGES)} quorum-casino challenges, {len(RING_CHALLENGES)} ring-balancer challenges.'
        ))
