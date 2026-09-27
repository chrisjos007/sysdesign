from django.core.management.base import BaseCommand
from django.db import transaction

from learn.models import (
    ComponentType, Concept, DesignChallenge, DesignChallengeComponent,
    DesignChallengeConnection, FlawChallenge, FlawPart, FlawReason,
    MatchingChallenge, MatchingPair, OrderingChallenge, OrderingStep, TrafficChallenge,
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
        concept='notification-architecture', width=1000, height=430,
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
        concept='url-shortener-design',
        prompt=(
            'Run a URL shortener through one day of traffic: 11,600 reads and 1,160 writes per second '
            'on average, and a viral link at 19:00. Change the design at any time, even mid-run. Any '
            'design that stays inside the SLO passes.'
        ),
        params={
            'source': 'Chapter 1: Scale From Zero to Millions of Users · Chapter 8: Design a URL Shortener',
            'reads_per_sec': 11600, 'writes_per_sec': 1160,
            'app_capacity': 5000, 'db_capacity': 6000,
            'hourly_cost': {'app': 1.5, 'cache': 0.8, 'db': 2.0},
            'slo': {'p99_ms': 200, 'error_rate': 0.01},
            'spike': {'at_hour': 19, 'hours': 1.5, 'reads_per_sec': 23200},
            'score': {'start': 1000, 'per_breach': 50, 'analytics': 250},
            'limits': {'servers': [1, 14], 'replicas': [0, 4]},
            'start': {'servers': 4, 'replicas': 1, 'cache': False, 'redirect': 302},
            'briefing': 'Marketing warns you: a celebrity will post one of your links around 19:00.',
            'events': {
                '42': 'Morning traffic is picking up.',
                '102': 'The evening peak starts. It tops out around 20:00.',
                '114': 'A celebrity posts one of your short links. Reads of that one URL jump by 23,000 a second.',
                '123': 'The viral wave fades.',
                '138': 'Traffic winds down for the night.',
            },
        },
    ),
]


class Command(BaseCommand):
    help = 'Seed drag-and-drop architecture builder, matching, ordering, spot-the-flaw, and traffic-day mini-games.'

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

        self.stdout.write(self.style.SUCCESS(
            f'Seeded {len(types)} component types, {design_count} design challenges, '
            f'{matching_count} matching challenges, {ordering_count} ordering challenges, '
            f'{flaw_count} spot-the-flaw challenges, {len(TRAFFIC_CHALLENGES)} traffic-day challenges.'
        ))
