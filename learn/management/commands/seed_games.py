from django.core.management.base import BaseCommand
from django.db import transaction

from learn.models import (
    ComponentType, Concept, DesignChallenge, DesignChallengeComponent,
    DesignChallengeConnection, MatchingChallenge, MatchingPair,
    OrderingChallenge, OrderingStep,
)

COMPONENT_TYPES = [
    ('client', 'Client', '📱'),
    ('load-balancer', 'Load Balancer', '⚖️'),
    ('web-server', 'Web / App Server', '🖥️'),
    ('cache', 'Cache (Redis)', '⚡'),
    ('key-value-store', 'Key-Value Store', '🗄️'),
    ('id-generator', 'ID Generator Service', '🔢'),
    ('api-gateway', 'API Gateway', '🚪'),
    ('rate-limiter-component', 'Rate Limiter', '🚦'),
    ('websocket-gateway', 'WebSocket Gateway', '🔌'),
    ('presence-service', 'Presence Service', '🟢'),
    ('chat-server', 'Chat Server', '💬'),
    ('message-store', 'Message Store (DB)', '🗂️'),
    ('push-notification-service', 'Push Notification Service', '🔔'),
    ('cdn', 'CDN', '🌐'),
    ('video-transcoder', 'Video Transcoder', '🎞️'),
    ('gpu-cluster', 'GPU Cluster', '💻'),
    ('message-queue', 'Message Queue', '📬'),
    ('url-frontier', 'URL Frontier (Queue)', '📋'),
    ('fetcher-worker', 'Fetcher Worker', '🕷️'),
    ('dns-resolver', 'DNS Resolver', '🧭'),
    ('dedup-filter', 'Dedup Filter (Bloom)', '🧹'),
    ('content-store', 'Content Store', '🗃️'),
    ('sync-service', 'Sync Service', '🔄'),
    ('metadata-db', 'Metadata DB', '🗒️'),
    ('blob-storage', 'Blob / Object Storage', '📦'),
    ('leader-db', 'Leader Database', '👑'),
    ('follower-db', 'Follower Database', '🧬'),
    ('hash-ring-router', 'Consistent Hash Router', '🎡'),
    ('quorum-replica', 'Quorum Replica Node', '🧊'),
]

# (challenge_slug, title, concept_slug, prompt, difficulty,
#  required[], distractors[], connections[(a,b), ...])
DESIGN_CHALLENGES = [
    (
        'build-url-shortener', 'Design a URL Shortener', 'url-shortener-design',
        'Build the minimum architecture that turns a long URL into a short code and redirects '
        'visitors back to the original — optimized for extremely read-heavy traffic.',
        2,
        ['client', 'load-balancer', 'web-server', 'cache', 'key-value-store', 'id-generator'],
        ['video-transcoder', 'gpu-cluster', 'message-queue'],
        [
            ('client', 'load-balancer'), ('load-balancer', 'web-server'),
            ('web-server', 'cache'), ('cache', 'key-value-store'),
            ('web-server', 'id-generator'),
        ],
    ),
    (
        'build-rate-limiter', 'Design a Rate Limiter', 'rate-limiting-algorithms',
        'Build the components needed to throttle clients before their requests hit your '
        'application servers.',
        2,
        ['client', 'api-gateway', 'rate-limiter-component', 'cache', 'web-server'],
        ['cdn', 'video-transcoder', 'message-queue'],
        [
            ('client', 'api-gateway'), ('api-gateway', 'rate-limiter-component'),
            ('rate-limiter-component', 'cache'), ('rate-limiter-component', 'web-server'),
        ],
    ),
    (
        'build-chat-system', 'Design a Chat System', 'chat-system-realtime',
        'Build the architecture for real-time one-on-one messaging, including presence and '
        'offline delivery.',
        3,
        ['client', 'websocket-gateway', 'chat-server', 'presence-service',
         'message-store', 'push-notification-service'],
        ['cdn', 'video-transcoder', 'gpu-cluster'],
        [
            ('client', 'websocket-gateway'), ('websocket-gateway', 'chat-server'),
            ('chat-server', 'presence-service'), ('chat-server', 'message-store'),
            ('chat-server', 'push-notification-service'),
        ],
    ),
    (
        'build-web-crawler', 'Design a Web Crawler', 'crawler-architecture',
        'Build the pipeline that takes seed URLs, fetches pages at scale, and avoids '
        're-crawling or hammering the same host.',
        3,
        ['client', 'url-frontier', 'fetcher-worker', 'dns-resolver', 'dedup-filter', 'content-store'],
        ['gpu-cluster', 'video-transcoder', 'push-notification-service'],
        [
            ('client', 'url-frontier'), ('url-frontier', 'fetcher-worker'),
            ('fetcher-worker', 'dns-resolver'), ('fetcher-worker', 'dedup-filter'),
            ('fetcher-worker', 'content-store'),
        ],
    ),
    (
        'build-notification-system', 'Design a Notification System', 'notification-architecture',
        'Build the architecture that fans a single event out to push notifications, decoupling '
        'your app from slow third-party providers.',
        2,
        ['web-server', 'message-queue', 'cache', 'push-notification-service'],
        ['video-transcoder', 'gpu-cluster', 'cdn'],
        [
            ('web-server', 'message-queue'), ('message-queue', 'cache'),
            ('cache', 'push-notification-service'),
        ],
    ),
    (
        'build-instagram-feed', 'Design Instagram’s News Feed', 'newsfeed-fanout',
        'Build the fan-out-on-write pipeline that pre-computes each follower’s feed the '
        'moment a new photo is posted.',
        3,
        ['client', 'load-balancer', 'web-server', 'message-queue', 'cache', 'key-value-store'],
        ['video-transcoder', 'gpu-cluster', 'websocket-gateway'],
        [
            ('client', 'load-balancer'), ('load-balancer', 'web-server'),
            ('web-server', 'message-queue'), ('message-queue', 'cache'),
            ('cache', 'key-value-store'),
        ],
    ),
    (
        'build-dropbox-sync', 'Design Dropbox’s File Sync', 'sync-dedup',
        'Build the pipeline that syncs a changed file to a user’s other devices, deduplicating '
        'identical chunks along the way.',
        3,
        ['client', 'sync-service', 'message-queue', 'metadata-db', 'blob-storage'],
        ['gpu-cluster', 'video-transcoder', 'presence-service'],
        [
            ('client', 'sync-service'), ('sync-service', 'message-queue'),
            ('message-queue', 'metadata-db'), ('sync-service', 'blob-storage'),
        ],
    ),
    (
        'build-video-platform', 'Design YouTube’s Upload & Delivery Pipeline', 'video-cdn-delivery',
        'Build the pipeline that takes an uploaded video, transcodes it, and streams it back to '
        'viewers worldwide with low latency.',
        3,
        ['client', 'video-transcoder', 'blob-storage', 'metadata-db', 'cdn'],
        ['rate-limiter-component', 'websocket-gateway', 'presence-service'],
        [
            ('client', 'video-transcoder'), ('video-transcoder', 'blob-storage'),
            ('client', 'metadata-db'), ('blob-storage', 'cdn'),
        ],
    ),
    (
        'build-leader-replication', 'Design Leader-Based Replication', 'leader-based-replication',
        'Build the topology where a client writes to a single leader, which propagates the '
        'change to a follower that can serve reads.',
        1,
        ['client', 'leader-db', 'follower-db'],
        ['cdn', 'gpu-cluster', 'video-transcoder'],
        [
            ('client', 'leader-db'), ('leader-db', 'follower-db'),
        ],
    ),
    # Every concrete "design a system" item gets a builder challenge, even
    # if it already has a matching/ordering game — the builder is additive,
    # not a replacement.
    (
        'build-consistent-hashing', 'Design Consistent Hashing', 'consistent-hashing-core',
        'Build the routing layer that maps keys to storage nodes on a hash ring, so adding or '
        'removing a node only remaps its immediate neighborhood.',
        2,
        ['client', 'hash-ring-router', 'key-value-store'],
        ['cdn', 'video-transcoder', 'gpu-cluster'],
        [
            ('client', 'hash-ring-router'), ('hash-ring-router', 'key-value-store'),
        ],
    ),
    (
        'build-key-value-store', 'Design a Key-Value Store', 'cap-theorem-quorum',
        'Build a distributed key-value store where writes and reads go through a quorum of '
        'replica nodes to balance consistency and availability.',
        3,
        ['client', 'api-gateway', 'key-value-store', 'quorum-replica'],
        ['cdn', 'video-transcoder', 'gpu-cluster'],
        [
            ('client', 'api-gateway'), ('api-gateway', 'key-value-store'),
            ('key-value-store', 'quorum-replica'),
        ],
    ),
    (
        'build-id-generator', 'Design a Unique ID Generator', 'snowflake-ids',
        'Build the minimal pipeline that lets any app server mint a globally unique, roughly '
        'sortable ID with no central coordination.',
        1,
        ['client', 'web-server', 'id-generator'],
        ['cdn', 'video-transcoder', 'gpu-cluster'],
        [
            ('client', 'web-server'), ('web-server', 'id-generator'),
        ],
    ),
    (
        'build-twitter-timeline', 'Design Twitter’s Timeline', 'twitter-timeline',
        'Build the pipeline that fans a new tweet out to followers’ cached timelines while '
        'keeping sharded tweet storage underneath.',
        3,
        ['client', 'load-balancer', 'web-server', 'message-queue', 'cache', 'key-value-store'],
        ['video-transcoder', 'gpu-cluster', 'websocket-gateway'],
        [
            ('client', 'load-balancer'), ('load-balancer', 'web-server'),
            ('web-server', 'message-queue'), ('message-queue', 'cache'),
            ('web-server', 'key-value-store'),
        ],
    ),
    (
        'build-messenger', 'Design Facebook Messenger', 'messenger-delivery',
        'Build the path a message takes to an offline recipient: persist first, then attempt '
        'live delivery, then fall back to a queued push notification.',
        3,
        ['client', 'websocket-gateway', 'chat-server', 'message-store', 'message-queue', 'push-notification-service'],
        ['cdn', 'video-transcoder', 'gpu-cluster'],
        [
            ('client', 'websocket-gateway'), ('websocket-gateway', 'chat-server'),
            ('chat-server', 'message-store'), ('chat-server', 'message-queue'),
            ('message-queue', 'push-notification-service'),
        ],
    ),
]

MATCHING_CHALLENGES = [
    (
        'match-cap-theorem', 'CAP Theorem Terms', 'cap-theorem-quorum',
        [
            ('Consistency', 'Every read receives the most recent write, or an error.'),
            ('Availability', 'Every request receives a non-error response, with no guarantee it reflects the latest write.'),
            ('Partition Tolerance', 'The system keeps operating despite network communication breaking down between nodes.'),
            ('Quorum', 'The minimum number of replicas that must agree before a read or write counts as successful.'),
            ('Vector Clock', 'A mechanism for tracking causality between events across distributed replicas.'),
        ],
    ),
    (
        'match-rate-limit-algorithms', 'Rate Limiting Algorithms', 'rate-limiting-algorithms',
        [
            ('Token Bucket', 'Refills tokens at a fixed rate; requests consume tokens, allowing short bursts up to the bucket size.'),
            ('Leaky Bucket', 'Requests queue up and are processed at a constant rate, smoothing out bursts.'),
            ('Fixed Window Counter', 'Counts requests in fixed time windows; simple, but can allow spikes at window boundaries.'),
            ('Sliding Window Log', 'Tracks the exact timestamp of every request for precise limiting, at the cost of more memory.'),
        ],
    ),
    (
        'match-consistent-hashing', 'Consistent Hashing Vocabulary', 'consistent-hashing-core',
        [
            ('Hash Ring', 'A circular keyspace where servers and keys are both placed by hashing; a key belongs to the first server found clockwise.'),
            ('Virtual Nodes', 'Multiple points per physical server on the ring, used to smooth out uneven key distribution.'),
            ('Hot Spot', 'A server that receives disproportionately more keys or traffic because of uneven ring placement.'),
            ('Naive Hash % N', 'A sharding scheme where changing the server count remaps almost every key — the problem consistent hashing solves.'),
        ],
    ),
    (
        'match-twitter-timeline', 'Twitter Timeline Strategies', 'twitter-timeline',
        [
            ('Fan-out on Write', 'Pre-computes every follower’s feed at post time; fast reads, expensive for accounts with huge followings.'),
            ('Fan-out on Read', 'Builds the timeline at request time by pulling recent posts from followees; cheap writes, slower reads.'),
            ('Hybrid Fan-out', 'Uses fan-out on write for most users and merges in celebrity posts at read time.'),
            ('Tweet ID Sharding', 'Sharding by an ID that embeds a timestamp, keeping ordering roughly chronological across shards.'),
        ],
    ),
    (
        'match-btree-vocab', 'B-Tree Vocabulary', 'storage-engines-btree-lsm-wal',
        [
            ('Leaf Node', 'A node at the bottom of the tree holding the actual key-value pairs or pointers to them.'),
            ('Internal Node', 'A node holding separator keys and pointers to child nodes, used to route a search down the tree.'),
            ('Node Split', 'What happens when a full node receives another entry: it divides in two and pushes a separator key up to the parent.'),
            ('Page', 'The fixed-size unit of disk storage a B-tree node is typically stored in.'),
        ],
    ),
    (
        'match-failure-detection', 'Failure Detection & Leader Election Vocabulary', 'failure-replication-consensus',
        [
            ('Heartbeat', 'A periodic signal a node sends to show it is still alive and responsive.'),
            ('Phi Accrual Failure Detector', 'Outputs an adaptive suspicion level instead of a hard alive/dead verdict, tolerating network jitter.'),
            ('Split Brain', 'A network partition causing two sides to each elect their own leader, risking conflicting writes.'),
            ('Bully Algorithm', 'A leader election scheme where the node with the highest ID wins.'),
        ],
    ),
    (
        'match-replication-tradeoffs', 'Replication Trade-offs', 'failure-replication-consensus',
        [
            ('Synchronous Replication', 'Waits for a replica (or quorum) to acknowledge a write before confirming it to the client.'),
            ('Asynchronous Replication', 'Confirms a write as soon as the leader applies it, propagating to replicas in the background.'),
            ('Anti-Entropy', 'A background process that detects and reconciles replicas that have drifted out of sync.'),
            ('Read Repair', 'Fixing stale data on a replica opportunistically while serving a read request.'),
        ],
    ),
    (
        'match-three-pillars', 'Reliability, Scalability, Maintainability', 'data-systems-models-partitioning-transactions',
        [
            ('Fault', 'One component of the system deviating from its specification.'),
            ('Failure', 'The system as a whole ceasing to provide the required service to the user.'),
            ('Load Parameter', 'A number describing system load, like requests per second or the read/write ratio.'),
            ('p99 Latency', 'The response time below which 99% of requests complete — reveals tail latency an average would hide.'),
        ],
    ),
    (
        'match-data-models', 'Data Models', 'data-systems-models-partitioning-transactions',
        [
            ('Relational Model', 'Organizes data into tables of rows with a fixed schema; excels at many-to-many relationships via joins.'),
            ('Document Model', 'Stores nested, self-contained records that map naturally to application objects.'),
            ('Graph Model', 'Represents data as nodes and edges; ideal when relationships matter as much as the records themselves.'),
            ('Declarative Query', 'States the desired result and lets the database choose how to execute it, e.g. SQL.'),
        ],
    ),
    (
        'match-partitioning', 'Partitioning Strategies', 'data-systems-models-partitioning-transactions',
        [
            ('Key-Range Partitioning', 'Assigns contiguous ranges of keys to each partition; keeps range queries fast but risks hot spots.'),
            ('Hash Partitioning', 'Distributes keys evenly by hashing them first, avoiding hot spots but losing efficient range queries.'),
            ('Rebalancing', 'Moving data between partitions as the dataset grows, ideally without stopping reads or writes.'),
            ('Hot Spot', 'A single partition receiving disproportionate load because access patterns cluster around its keys.'),
        ],
    ),
    (
        'match-isolation-levels', 'Transaction Isolation Levels', 'data-systems-models-partitioning-transactions',
        [
            ('Read Committed', 'Prevents dirty reads (seeing uncommitted data) but still allows non-repeatable reads.'),
            ('Snapshot Isolation', 'Gives each transaction a consistent snapshot as of its start; prevents most anomalies but still allows write skew.'),
            ('Write Skew', 'Two transactions each read overlapping data and make disjoint writes that together violate an invariant.'),
            ('Serializability', 'The result is equivalent to running all transactions one at a time, even if they ran concurrently.'),
        ],
    ),
    (
        'match-consistency-consensus', 'Consistency & Consensus', 'failure-replication-consensus',
        [
            ('Linearizability', 'The strongest single-object guarantee: every read after a write sees that write or a later one, as if there were one copy of the data.'),
            ('Total Order Broadcast', 'A guarantee that all nodes deliver the same messages in the same order.'),
            ('Consensus', 'Getting a group of nodes to agree on a single value despite failures, as long as a majority are reachable.'),
            ('Quorum', 'The minimum number of nodes that must agree for an operation to be considered successful.'),
        ],
    ),
    (
        'match-linux-navigation', 'Filesystem Navigation Commands', 'linux-cli-essentials',
        [
            ('pwd', 'Prints the full path of the current working directory.'),
            ('cd -', 'Switches back to the previous working directory.'),
            ('ls -la', 'Lists all files, including hidden ones, with full details.'),
            ('find', 'Recursively searches a directory tree by name, type, size, or modification time.'),
        ],
    ),
    (
        'match-linux-permissions', 'Linux Permissions Commands', 'linux-cli-essentials',
        [
            ('chmod 755', 'Grants the owner read/write/execute and group/others read/execute.'),
            ('chmod u+x', 'Adds execute permission for the file’s owner only.'),
            ('chown', 'Changes a file’s owner and/or group.'),
            ('umask', 'Sets the default permissions removed from newly created files.'),
        ],
    ),
    (
        'match-linux-packages', 'Package Management Commands', 'linux-cli-essentials',
        [
            ('apt update', 'Refreshes the local list of available packages and versions from configured repositories.'),
            ('apt install', 'Installs a package and automatically resolves and installs its dependencies.'),
            ('dpkg -i', 'Installs a .deb file directly, without resolving dependencies.'),
            ('apt remove', 'Uninstalls a package.'),
        ],
    ),
    (
        'match-linux-networking', 'Networking Commands', 'linux-cli-essentials',
        [
            ('ping', 'Sends ICMP echo requests to check whether a host is reachable and measure round-trip latency.'),
            ('curl', 'Fetches a URL’s content directly from the command line, useful for testing APIs.'),
            ('ssh', 'Opens a secure, encrypted remote shell session on another machine.'),
            ('scp', 'Copies files to or from a remote machine over an SSH connection.'),
        ],
    ),
]

ORDERING_CHALLENGES = [
    (
        'order-seven-steps', 'The 7-Step Framework', 'fundamentals-framework-scaling-estimation',
        [
            'Requirements clarification',
            'System interface definition',
            'Back-of-the-envelope estimation',
            'Defining the data model',
            'High-level design',
            'Detailed design',
            'Identifying and resolving bottlenecks',
        ],
    ),
    (
        'order-scale-to-millions', 'Scaling From One Server to Millions of Users', 'fundamentals-framework-scaling-estimation',
        [
            'Start with everything on a single server',
            'Separate the web/app tier from the database tier',
            'Add a load balancer and multiple web servers',
            'Add database replication (master-slave)',
            'Introduce a cache to reduce database load',
            'Add a CDN for static assets',
            'Shard the database for further scale',
        ],
    ),
    (
        'order-latency-numbers', 'Latency Numbers: Fastest to Slowest', 'fundamentals-framework-scaling-estimation',
        [
            'L1/L2 cache reference',
            'Main memory (RAM) access',
            'SSD random read',
            'Round trip within the same data center',
            'Disk seek (spinning HDD)',
            'Round trip between the US and Europe',
        ],
    ),
    (
        'order-snowflake-bits', 'Snowflake ID: Most to Least Significant', 'snowflake-ids',
        [
            'Sign bit (unused, always 0)',
            'Timestamp (milliseconds since a custom epoch)',
            'Datacenter ID',
            'Machine ID',
            'Per-millisecond sequence number',
        ],
    ),
    (
        'order-messenger-delivery', 'Messenger: Sending to an Offline User', 'messenger-delivery',
        [
            'Alice’s client sends the message to the chat server',
            'The chat server persists the message to the message store',
            'The server attempts live delivery to Bob’s connection and finds him offline',
            'The server triggers a push notification to Bob’s device',
            'Bob reconnects and the server delivers the queued messages',
            'Bob’s client sends a read receipt back',
        ],
    ),
    (
        'order-lsm-write-path', 'LSM-Tree Write Path', 'storage-engines-btree-lsm-wal',
        [
            'Write is appended to the write-ahead log (WAL) for durability',
            'Write is inserted into the in-memory memtable',
            'Memtable reaches its size threshold and is flushed to disk as an immutable SSTable',
            'Multiple SSTables accumulate on disk over time',
            'A background compaction process merges SSTables and discards overwritten/deleted data',
        ],
    ),
    (
        'order-aries-recovery', 'ARIES Crash Recovery Phases', 'storage-engines-btree-lsm-wal',
        [
            'Analysis: scan the log to find in-progress transactions and possibly-dirty pages',
            'Redo: replay every logged change, committed or not, to reach the exact pre-crash state',
            'Undo: roll back the changes made by transactions that never committed',
        ],
    ),
    (
        'order-raft-election', 'Raft Leader Election', 'failure-replication-consensus',
        [
            'A follower’s election timeout expires without hearing from a leader',
            'The follower becomes a candidate and requests votes from other nodes',
            'Other nodes grant their vote if they haven’t already voted this term',
            'The candidate receives votes from a majority of nodes',
            'The candidate becomes the new leader and starts sending heartbeats',
        ],
    ),
    (
        'order-lsm-read-path', 'How a Read Traverses an LSM-Tree', 'storage-engines-btree-lsm-wal',
        [
            'Check the in-memory memtable for the key',
            'Check the newest on-disk SSTable’s Bloom filter',
            'If the Bloom filter says "maybe present", consult that SSTable’s sparse index',
            'Scan the located region of the SSTable for the exact key',
            'If not found, repeat the Bloom filter check on the next-oldest SSTable',
        ],
    ),
    (
        'order-gc-pause-failure', 'How a GC Pause Can Cause a False Failure Detection', 'failure-replication-consensus',
        [
            'Node A sends a heartbeat and begins a long garbage collection pause',
            'Node A stops responding while paused',
            'Other nodes miss A’s expected heartbeats',
            'The cluster suspects A has failed and reassigns its work',
            'Node A’s GC pause ends and it resumes running',
            'Node A discovers its work was reassigned while it believed it was still active',
        ],
    ),
    (
        'order-find-kill-process', 'Find and Force-Stop a Runaway Process', 'linux-cli-essentials',
        [
            'Run `ps aux | grep processname` to find the process and note its PID',
            'Run `kill PID` to request a graceful shutdown (SIGTERM)',
            'Check with `ps aux` again to see if it is still running',
            'If it is still running, run `kill -9 PID` to force-kill it (SIGKILL)',
            'Verify with `ps aux` that the process is gone',
        ],
    ),
    (
        'order-pipeline-build', 'Build the Pipeline: Count and Rank Matching Lines', 'linux-cli-essentials',
        [
            'cat access.log',
            "grep 'ERROR'",
            'sort',
            'uniq -c',
            'sort -rn',
        ],
    ),
]


class Command(BaseCommand):
    help = 'Seed drag-and-drop architecture builder, matching, and ordering mini-games.'

    @transaction.atomic
    def handle(self, *args, **options):
        types = {}
        for slug, name, icon in COMPONENT_TYPES:
            ct, _ = ComponentType.objects.update_or_create(
                slug=slug, defaults={'name': name, 'icon': icon},
            )
            types[slug] = ct

        design_count = 0
        all_slugs = [slug for slug, _, _ in COMPONENT_TYPES]
        for slug, title, concept_slug, prompt, difficulty, required, _hand_picked_distractors, conns in DESIGN_CHALLENGES:
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
            # Every component NOT required for this scenario is a distractor — the player
            # chooses from the full ~27-component catalog, gaining points for the right
            # pieces and losing points for anything that doesn't belong in this design.
            full_distractors = [s for s in all_slugs if s not in required]
            for i, s in enumerate(full_distractors):
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

        self.stdout.write(self.style.SUCCESS(
            f'Seeded {len(types)} component types, {design_count} design challenges, '
            f'{matching_count} matching challenges, {ordering_count} ordering challenges.'
        ))
