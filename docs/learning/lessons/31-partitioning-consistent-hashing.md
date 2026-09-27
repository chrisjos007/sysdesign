# Partitioning, hot keys, and consistent hashing

ID: sd-31 | Stage 2: intermediate | Suggested study: 35 minutes

Prerequisites: sd-05, sd-06, sd-08

[Curriculum map](../curriculum-map.md) · [Catalogue](../catalogue.json)

## Learning objectives

- Choose hash or range partitioning from a stated access pattern.
- Calculate how many keys move when a node joins or leaves, under hash mod N and under consistent hashing.
- Explain why a hot key needs a workload change rather than rebalancing.

## Intuition

Partitioning splits one dataset across several nodes so that each node stores and serves only part of it. Every read and write must then be routed to the partition that owns its key. The partition key therefore decides two things at once: how evenly the load spreads, and which queries one node can answer without asking all the others. Here a partition is a subset of the data, often called a shard, not the network split of lesson 25.

## How it works

Range partitioning gives each partition a contiguous span of sorted keys. Bigtable, for example, keeps rows in row-key order and splits a table into tablets that each hold a contiguous row range, so a prefix or range scan touches few partitions. Its weakness is a key that only grows, such as a timestamp or an auto-increment ID: every new row lands in the last range, and no split point divides that write load. Hash partitioning places a key by a hash of its value instead. Sequential keys spread evenly, but keys that are neighbors in sort order end up on different partitions, so an ordered scan must ask every partition and merge the results. CockroachDB's hash-sharded indexes take a middle path: a small shard number computed from the hash leads the key, which spreads writes over a few shards that an ordered read must merge.

Placing a key with hash(key) mod N ties its location to the node count. When N changes, a key stays only if both remainders agree, so most keys move. Consistent hashing puts keys and nodes on one circular hash space, and a key belongs to the first node position clockwise from it. A joining node takes over only the keys on the arcs it lands on, and a departing node's keys pass to the next positions. No key moves between two nodes that both stayed. With one position per node, arcs differ widely in size and a failed node's whole load falls on one neighbor. Virtual nodes give each physical node many positions: load evens out, a departed node's keys scatter across many survivors, and a bigger machine can take proportionally more positions. More positions mean more routing metadata. Cassandra's documentation adds two costs: more ways for a few simultaneous node failures to make some data unavailable, and slower cluster-wide maintenance.

A third approach fixes many partitions in advance and moves whole partitions. Redis Cluster hashes every key into one of 16,384 slots and adds a node by moving slots to it. Dynamo moved to fixed, equal-sized partitions partly because a partition could then be transferred as a unit. Whatever the scheme, the map from key to node changes while clients still hold older copies of it. Redis Cluster answers a request sent to the wrong node with a MOVED redirection that names the current owner, so a client with a stale map can correct itself.

Technical references: [Consistent Hashing and Random Trees: Distributed Caching Protocols for Relieving Hot Spots on the World Wide Web](https://people.csail.mit.edu/karger/Papers/web.pdf); [Dynamo: Amazon's Highly Available Key-value Store](https://www.allthingsdistributed.com/files/amazon-dynamo-sosp2007.pdf); [Apache Cassandra architecture: Dynamo](https://cassandra.apache.org/doc/latest/cassandra/architecture/dynamo.html); [Redis cluster specification](https://redis.io/docs/latest/operate/oss_and_stack/reference/cluster-spec/); [Bigtable schema design best practices](https://docs.cloud.google.com/bigtable/docs/schema-design); [Index Sequential Keys with Hash-sharded Indexes](https://docs.cockroachlabs.com/docs/stable/hash-sharded-indexes); [Using write sharding to distribute workloads evenly in your DynamoDB table](https://docs.aws.amazon.com/amazondynamodb/latest/developerguide/bp-partition-key-sharding.html).

## Worked example

A fictional cache cluster holds 1,000,000 keys on four equal nodes, about 250,000 each, and a fifth node joins. Under hash(key) mod N, a key keeps its node only when its hash leaves the same remainder mod 4 and mod 5, which happens for 4 of every 20 hash values. About 200,000 keys stay and 800,000 move. For a cache, that is 800,000 near-simultaneous misses falling through to the database: the stampede from lesson 8. On a ring with many virtual nodes per server, the fifth node takes about its fair share, 200,000 keys drawn from all four old nodes, and the other 800,000 stay where they were. Now suppose one of the original four fails instead. With one ring position per node, all of its 250,000 keys move to its single clockwise neighbor, which doubles that node's load to 500,000. With many virtual nodes, the keys scatter across the three survivors, roughly 83,000 each.

## Trade-offs and failure modes

Choose the partition key from the queries that matter most. A query that names the key reaches one partition; any other query fans out to every partition and waits for the slowest, so the tail latency of lesson 3 applies to each fan-out. Range partitions suit scans but need a leading key that spreads writes. Bigtable's guidance is to put a high-cardinality field, such as a user ID, before a timestamp, and it warns that hashing a whole row key gives up the sort order that range queries rely on.

Partitioning spreads distinct keys; it cannot split one. Every request for a hot key goes to the partition that owns it, however the cluster is rebalanced. The fix changes the workload: cache the key's reads, or split its writes across sub-keys with a suffix. DynamoDB's documentation shows a date key extended with a suffix from 1 to 200. Writes spread over 200 key values, and reading the whole day then takes 200 queries that the application merges.

Rebalancing copies real data over the network and competes with foreground traffic. Dynamo's first scheme had to scan a node's store to hand off key ranges; run at low priority, bootstrapping a new node took almost a day in a busy season. Its authors also chose explicit membership changes, because most node outages are transient and should not trigger rebalancing. Moving data away from a node that is only slow adds load when the cluster can least afford it. Throttle moves, prefer moving whole partitions, and make sure routers and clients learn each new owner.

## Practice

A fictional analytics service stores page-view events. Its main query reads the last hour of events for one site, and a dashboard shows total views per minute across all sites. One site produces 40% of all writes. Choose a partition key, explain how the service adds a node, and handle the large site.

### Answer guidance

Lead the key with the site ID and follow it with the event time, so the main query reaches one partition and reads a contiguous time range. Do not lead with the timestamp: every write would land in the newest range. The cross-site total would fan out to every partition, so maintain it as a separate aggregate instead of computing it per request. The large site is a hot key: split its writes across sub-keys such as the site ID plus a bucket number, and read its last hour by querying every bucket and merging. Add nodes with many virtual nodes or many fixed partitions, move data at a throttled rate, and make sure clients follow redirections to new owners.

## Knowledge check

### 1. Does consistent hashing stop a single hot key from overloading its node?

No. It decides which node owns each key, and every request for that key still goes to that owner. Spreading one key's load needs a workload change, such as caching its reads or splitting it into sub-keys.

### 2. Why do virtual nodes help when a node fails?

Each physical node holds many small arcs of the ring, so a failed node's keys scatter across many survivors instead of all landing on one neighbor.

## Mastery checkpoint

Explain the worked example without notes, complete the practice task, and justify both knowledge-check answers. Revisit any prerequisite needed to explain your reasoning.

## Sources and scope

Sources reviewed 2026-09-27. The examples, workloads, exercises, and proposed choices are original teaching scenarios, not production measurements. Product-specific behavior belongs to the linked version or documentation checked on that date.

- [Consistent Hashing and Random Trees: Distributed Caching Protocols for Relieving Hot Spots on the World Wide Web](https://people.csail.mit.edu/karger/Papers/web.pdf)
- [Dynamo: Amazon's Highly Available Key-value Store](https://www.allthingsdistributed.com/files/amazon-dynamo-sosp2007.pdf)
- [Apache Cassandra architecture: Dynamo](https://cassandra.apache.org/doc/latest/cassandra/architecture/dynamo.html)
- [Redis cluster specification](https://redis.io/docs/latest/operate/oss_and_stack/reference/cluster-spec/)
- [Bigtable schema design best practices](https://docs.cloud.google.com/bigtable/docs/schema-design)
- [Index Sequential Keys with Hash-sharded Indexes](https://docs.cockroachlabs.com/docs/stable/hash-sharded-indexes)
- [Using write sharding to distribute workloads evenly in your DynamoDB table](https://docs.aws.amazon.com/amazondynamodb/latest/developerguide/bp-partition-key-sharding.html)
