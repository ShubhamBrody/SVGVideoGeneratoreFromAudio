"""A corpus of 110+ sample "speeches" (short technical narrations) spanning many
domains, used to evaluate how well the Scene Director molds to arbitrary text.

Each entry: {"domain": str, "text": str}. Texts are multi-sentence so the
speech-paced director produces several beats.
"""
from __future__ import annotations

SPEECHES: list[dict[str, str]] = [
    # ---------------- Kubernetes ----------------
    {"domain": "kubernetes", "text": "A Kubernetes service load-balances traffic across three pods. Each pod runs a copy of the app. When a pod fails its health check, the service stops routing to it. Kubernetes then schedules a replacement pod and traffic resumes."},
    {"domain": "kubernetes", "text": "A deployment declares three replicas. The controller notices only two pods are running. It creates a new pod to match the desired state. Once the pod is ready, the deployment is healthy again."},
    {"domain": "kubernetes", "text": "The horizontal pod autoscaler watches CPU usage. When load rises above the target, it adds more pods. As traffic falls, it scales the pods back down. This keeps the service responsive while saving resources."},
    {"domain": "kubernetes", "text": "During a rolling update, Kubernetes starts a new pod with the new version. It waits for the pod to become ready, then terminates an old pod. This repeats until every pod runs the new version with no downtime."},
    {"domain": "kubernetes", "text": "An ingress receives external requests. It routes each request to the correct service based on the host and path. The service then forwards traffic to a healthy pod."},
    {"domain": "kubernetes", "text": "A node becomes unreachable and stops sending heartbeats. The control plane marks the node as not ready. Pods on that node are rescheduled onto healthy nodes to restore capacity."},
    {"domain": "kubernetes", "text": "A kubelet on each node reports pod status to the API server. The scheduler places new pods on nodes with enough resources. The controller manager keeps the actual state matching the desired state."},
    {"domain": "kubernetes", "text": "A statefulset gives each pod a stable identity and its own storage. When a pod restarts, it keeps the same name and volume. This is important for databases that need consistent state."},
    {"domain": "kubernetes", "text": "A config map holds application settings. The pod mounts the config map as environment variables. When the config changes, a rolling restart picks up the new values."},
    {"domain": "kubernetes", "text": "A service mesh injects a sidecar proxy next to each pod. All traffic flows through the proxies. This gives you retries, timeouts, and metrics without changing the application code."},

    # ---------------- Kafka / streaming ----------------
    {"domain": "kafka", "text": "A producer publishes events to a Kafka topic. The topic is split into partitions for parallelism. Each consumer in a group reads from its own partition. This lets throughput scale with the number of consumers."},
    {"domain": "kafka", "text": "Kafka replicates each partition across several brokers. One broker is the leader and the others are followers. If the leader fails, a follower is promoted so no data is lost."},
    {"domain": "kafka", "text": "A consumer commits its offset after processing messages. If the consumer restarts, it resumes from the last committed offset. This gives at-least-once delivery."},
    {"domain": "kafka", "text": "When a new consumer joins the group, Kafka triggers a rebalance. Partitions are redistributed across the consumers. Each consumer then continues reading from its newly assigned partitions."},
    {"domain": "kafka", "text": "A producer waits for acknowledgement from the broker. With acks set to all, the broker confirms only after the followers replicate the message. This trades latency for durability."},
    {"domain": "kafka", "text": "Log compaction keeps only the latest value for each key. Old duplicate records are removed during cleanup. This keeps the topic small while preserving the current state."},
    {"domain": "kafka", "text": "A stream processor reads from an input topic, transforms the events, and writes to an output topic. State is stored locally and backed up to Kafka. If the processor crashes, it restores its state and resumes."},
    {"domain": "kafka", "text": "A dead letter queue captures messages that fail processing. The consumer retries a few times, then routes the bad message to the dead letter topic. Engineers inspect it later without blocking the main flow."},
    {"domain": "kafka", "text": "A message queue decouples the producer from the consumer. The producer drops a task on the queue and moves on. A worker picks up the task later and processes it at its own pace."},

    # ---------------- Caching ----------------
    {"domain": "caching", "text": "With cache-aside, the app first checks Redis. On a cache miss it reads from the database, stores the result in Redis, and returns it. The next request is served straight from the cache."},
    {"domain": "caching", "text": "A write-through cache updates the cache and the database together. Reads are always fresh because the cache is written on every update. This simplifies consistency at the cost of slower writes."},
    {"domain": "caching", "text": "When the cache fills up, an eviction policy removes entries. Least-recently-used keeps hot data and drops cold data. This maximizes the hit rate for a fixed cache size."},
    {"domain": "caching", "text": "A CDN caches static assets close to users. When a user requests an image, the nearest edge server responds. If the edge lacks the file, it fetches it from the origin and caches it."},
    {"domain": "caching", "text": "Cache invalidation removes stale entries after an update. The app writes to the database and then deletes the cached key. The next read repopulates the cache with fresh data."},
    {"domain": "caching", "text": "A read replica serves heavy read traffic. The application sends writes to the primary and reads to the replica. This spreads load and keeps the primary responsive."},
    {"domain": "caching", "text": "Redis stores session data in memory. Every request looks up the session by its token. Because memory is fast, authentication adds almost no latency."},
    {"domain": "caching", "text": "A thundering herd happens when a popular key expires. Many requests miss at once and hit the database. A lock lets one request rebuild the cache while the others wait."},
    {"domain": "caching", "text": "Two levels of cache work together. A local in-process cache handles the hottest keys, and a shared Redis cache handles the rest. Misses fall through to the database."},

    # ---------------- Scaling / system design ----------------
    {"domain": "scaling", "text": "A load balancer sits in front of several servers. It spreads incoming requests evenly across them. If one server goes down, the load balancer routes around it."},
    {"domain": "scaling", "text": "Horizontal scaling adds more servers behind the load balancer. Each server handles a share of the traffic. This lets the system grow with demand instead of relying on one big machine."},
    {"domain": "scaling", "text": "Database sharding splits data across several databases by key. Each shard holds a subset of the users. A request is routed to the shard that owns its data."},
    {"domain": "scaling", "text": "A rate limiter protects the service from abuse. Each client gets a bucket of tokens that refills over time. When the bucket is empty, extra requests are rejected."},
    {"domain": "scaling", "text": "An API gateway is the single entry point for clients. It authenticates requests, applies rate limits, and routes to the right microservice. The services stay simple behind it."},
    {"domain": "scaling", "text": "A queue smooths out traffic spikes. Requests are accepted quickly and placed on the queue. Workers drain the queue at a steady rate so the database is never overwhelmed."},
    {"domain": "scaling", "text": "A read-heavy service adds replicas to scale reads. Writes go to the primary and replicate to the followers. Clients read from the nearest replica for low latency."},
    {"domain": "scaling", "text": "Consistent hashing maps keys to nodes on a ring. When a node is added, only a small slice of keys move. This avoids reshuffling the entire dataset."},
    {"domain": "scaling", "text": "A circuit breaker watches calls to a downstream service. After too many failures it opens and fails fast. After a cool-down it lets a test request through to check recovery."},

    # ---------------- Databases ----------------
    {"domain": "databases", "text": "A primary database replicates its writes to follower replicas. Reads can be served by any follower. If the primary fails, a follower is promoted to take its place."},
    {"domain": "databases", "text": "An index speeds up queries by pointing directly to matching rows. Without it, the database scans the whole table. The index trades extra storage and slower writes for much faster reads."},
    {"domain": "databases", "text": "A transaction groups several writes into one atomic unit. Either all of them commit or none of them do. This keeps the data consistent even if a failure happens midway."},
    {"domain": "databases", "text": "A write-ahead log records changes before applying them. If the database crashes, it replays the log to recover. This guarantees durability of committed transactions."},
    {"domain": "databases", "text": "Two-phase commit coordinates a transaction across services. The coordinator asks each participant to prepare, then tells them all to commit. If any participant cannot prepare, everyone aborts."},
    {"domain": "databases", "text": "A connection pool reuses open database connections. Requests borrow a connection, run a query, and return it. This avoids the cost of opening a new connection every time."},
    {"domain": "databases", "text": "Optimistic locking uses a version number on each row. A write succeeds only if the version still matches. If another update slipped in, the write retries with fresh data."},
    {"domain": "databases", "text": "A materialized view precomputes an expensive query. Reads hit the view instead of recomputing. A background job refreshes the view as the underlying data changes."},
    {"domain": "databases", "text": "MongoDB stores documents in collections. A query filters documents by their fields. An index on a field makes those lookups fast."},
    {"domain": "databases", "text": "PostgreSQL runs each query through a planner. The planner picks the cheapest way to fetch the rows. Statistics about the data guide that decision."},

    # ---------------- Networking ----------------
    {"domain": "networking", "text": "A TCP connection begins with a three-way handshake. The client sends a SYN, the server replies with SYN-ACK, and the client answers with ACK. Now both sides can exchange data reliably."},
    {"domain": "networking", "text": "A browser resolves a domain through DNS. It asks a resolver, which walks the root, top-level, and authoritative servers. The resolver returns the IP address and caches it for next time."},
    {"domain": "networking", "text": "An HTTP request travels from the client to the server. The server processes it and sends back a response. The status code tells the client whether it succeeded."},
    {"domain": "networking", "text": "A TLS handshake secures the connection. The client and server agree on a cipher and exchange keys. All traffic after that is encrypted."},
    {"domain": "networking", "text": "A reverse proxy sits in front of the servers. It terminates TLS, caches responses, and forwards requests. Clients only ever talk to the proxy."},
    {"domain": "networking", "text": "A firewall inspects incoming packets. It allows traffic that matches its rules and drops the rest. This shields the internal servers from the public internet."},
    {"domain": "networking", "text": "A CDN routes each user to the nearest edge location. Static content is served from the edge. Only cache misses travel back to the origin server."},
    {"domain": "networking", "text": "A client sends a request through an API gateway. The gateway checks the token and forwards the call to a backend service. The service returns data through the gateway."},
    {"domain": "networking", "text": "A load balancer performs health checks on each server. Healthy servers stay in the pool. When a check fails, the server is removed until it recovers."},

    # ---------------- AI / ML ----------------
    {"domain": "ai_ml", "text": "A neural network trains on a labeled dataset. It makes a prediction, measures the error, and adjusts its weights. Over many passes the model gets more accurate."},
    {"domain": "ai_ml", "text": "During backpropagation, the loss flows backward through the layers. Each layer computes how much it contributed to the error. The optimizer then nudges the weights to reduce it."},
    {"domain": "ai_ml", "text": "A model is trained on a GPU for speed. The dataset is split into batches. Each batch runs a forward and backward pass, and the weights update after every batch."},
    {"domain": "ai_ml", "text": "A transformer uses attention to weigh every token against the others. This lets it capture long-range context. Stacked attention layers build a rich representation of the input."},
    {"domain": "ai_ml", "text": "After training, the model is deployed for inference. A request sends input features to the model server. The model returns a prediction in milliseconds."},
    {"domain": "ai_ml", "text": "A dataset is split into training, validation, and test sets. The model learns on the training set. The validation set tunes it, and the test set gives an honest final score."},
    {"domain": "ai_ml", "text": "Gradient descent walks the loss surface downhill. It computes the gradient and takes a small step against it. The learning rate controls how big each step is."},
    {"domain": "ai_ml", "text": "A feature pipeline transforms raw data into model inputs. It cleans, encodes, and scales the features. The same pipeline runs at training and at serving time."},
    {"domain": "ai_ml", "text": "An ensemble combines several models. Each model votes on the answer. The combined prediction is usually more accurate than any single model."},
    {"domain": "ai_ml", "text": "A recommendation system embeds users and items as vectors. It scores items by similarity to the user. The top-scoring items become the recommendations."},

    # ---------------- RAG / LLM ----------------
    {"domain": "rag_llm", "text": "A RAG pipeline starts by splitting documents into chunks. Each chunk is embedded into a vector and stored in a vector database. At query time the question is embedded and the nearest chunks are retrieved."},
    {"domain": "rag_llm", "text": "A user asks a question. The retriever finds relevant passages from the vector store. Those passages are added to the prompt so the language model answers with grounded context."},
    {"domain": "rag_llm", "text": "Embeddings turn text into vectors that capture meaning. Similar sentences land close together in the vector space. A nearest-neighbor search then finds related content."},
    {"domain": "rag_llm", "text": "A reranker refines the retrieved results. It scores each candidate passage against the query more precisely. Only the best passages are passed to the language model."},
    {"domain": "rag_llm", "text": "An agent plans a task and calls tools to complete it. It may search the web, query a database, or run code. It observes each result and decides the next step."},
    {"domain": "rag_llm", "text": "A language model receives a prompt and generates tokens one at a time. Each new token depends on the ones before it. The stream continues until the model emits a stop token."},
    {"domain": "rag_llm", "text": "Documents are ingested into a knowledge base. A loader reads the files, a splitter chunks them, and an embedder stores the vectors. The index is now ready to answer questions."},
    {"domain": "rag_llm", "text": "A chatbot keeps a memory of the conversation. Each turn is stored and summarized. Relevant history is retrieved and added to the prompt for the next reply."},
    {"domain": "rag_llm", "text": "An LLM gateway routes a request to the best model. Simple prompts go to a small fast model, and hard ones go to a large model. This balances cost against quality."},
    {"domain": "rag_llm", "text": "A guardrail checks the model output before it reaches the user. It filters unsafe content and validates the format. If the output fails, the system retries or falls back."},

    # ---------------- Cloud / serverless ----------------
    {"domain": "cloud", "text": "A serverless function runs only when triggered. An event invokes the function, which processes it and returns. You pay just for the time it runs."},
    {"domain": "cloud", "text": "A cold start happens when no warm instance is available. The platform spins up a new container and loads the code. Later requests reuse the warm instance and respond faster."},
    {"domain": "cloud", "text": "A file uploaded to object storage triggers a function. The function generates a thumbnail and writes it back. This event-driven flow needs no servers to manage."},
    {"domain": "cloud", "text": "An autoscaling group watches demand. When traffic rises it launches more instances behind the load balancer. When traffic falls it terminates the extra instances."},
    {"domain": "cloud", "text": "A queue connects a producer to a fleet of workers. Messages pile up during a spike. Workers scale out to drain the queue and scale back in when it empties."},
    {"domain": "cloud", "text": "A managed database handles backups and failover. The application connects through an endpoint. If the primary fails, the endpoint points to a standby with no code changes."},
    {"domain": "cloud", "text": "Static files live in object storage behind a CDN. Users download assets from the edge. The origin bucket only serves cache misses."},
    {"domain": "cloud", "text": "An event bus fans out one event to many consumers. A single order event notifies billing, shipping, and analytics. Each consumer reacts independently."},
    {"domain": "cloud", "text": "Infrastructure is described as code. A deploy applies the template to create the resources. The same template rebuilds an identical environment anywhere."},

    # ---------------- Security / auth ----------------
    {"domain": "security", "text": "In OAuth, the user logs in at the authorization server. The app receives an authorization code and exchanges it for an access token. The app then calls the API with that token."},
    {"domain": "security", "text": "A JWT carries claims signed by the server. The client sends the token with each request. The server verifies the signature and trusts the claims without a database lookup."},
    {"domain": "security", "text": "A password is never stored directly. The server hashes it with a salt and saves the hash. At login it hashes the input and compares it to the stored value."},
    {"domain": "security", "text": "TLS encrypts data between the client and server. They exchange keys during the handshake. An attacker on the wire sees only ciphertext."},
    {"domain": "security", "text": "Zero-trust assumes no request is safe by default. Every call is authenticated and authorized. Access is granted only for the specific resource requested."},
    {"domain": "security", "text": "An API key identifies the calling application. The gateway checks the key and its rate limit. Requests without a valid key are rejected."},
    {"domain": "security", "text": "Multi-factor authentication adds a second check. After the password, the user confirms a one-time code. Even a stolen password is not enough to log in."},
    {"domain": "security", "text": "A secret manager stores credentials securely. The application requests a secret at runtime. The secret is never baked into the code or the image."},
    {"domain": "security", "text": "A firewall and a web application firewall guard the perimeter. They block malicious traffic and known attack patterns. Clean requests continue to the application."},

    # ---------------- Distributed systems ----------------
    {"domain": "distributed", "text": "In Raft, one node is elected leader. The leader accepts writes and replicates them to the followers. If the leader fails, the followers elect a new one."},
    {"domain": "distributed", "text": "A quorum requires a majority of nodes to agree. A write is committed once enough replicas acknowledge it. This tolerates the failure of a minority of nodes."},
    {"domain": "distributed", "text": "Leader election picks a single coordinator. Nodes vote, and the candidate with a majority wins. The others become followers and replicate its decisions."},
    {"domain": "distributed", "text": "A gossip protocol spreads state between nodes. Each node shares what it knows with a few random peers. Over time every node converges on the same view."},
    {"domain": "distributed", "text": "The CAP theorem says you cannot have consistency, availability, and partition tolerance all at once. During a network partition you must choose. Many systems favor availability and accept eventual consistency."},
    {"domain": "distributed", "text": "A distributed lock coordinates access to a shared resource. One node acquires the lock and does the work. The others wait until the lock is released."},
    {"domain": "distributed", "text": "Vector clocks track causality between events. Each node increments its own counter. Comparing clocks tells you which event happened before another."},
    {"domain": "distributed", "text": "A heartbeat detects failures. Each node periodically pings the others. When the heartbeats stop, the node is presumed down and its work is reassigned."},
    {"domain": "distributed", "text": "Sharding with replication combines scale and safety. Data is split into shards, and each shard is replicated. A request reaches the right shard and reads from a healthy replica."},

    # ---------------- Web / microservices ----------------
    {"domain": "web_micro", "text": "A browser requests a page from the server. The server renders HTML and sends it back. The browser paints the page and then loads scripts and styles."},
    {"domain": "web_micro", "text": "A single-page app loads once and then fetches data as JSON. The client updates the view without full reloads. The server becomes a pure API."},
    {"domain": "web_micro", "text": "A CI pipeline builds and tests every commit. If the tests pass, it produces an artifact. A deploy step then ships that artifact to production."},
    {"domain": "web_micro", "text": "In the saga pattern, a workflow spans several services. Each service does its step and emits an event. If a step fails, compensating actions undo the earlier ones."},
    {"domain": "web_micro", "text": "Service discovery lets services find each other. Each service registers its address on startup. A caller looks up a healthy instance before making a request."},
    {"domain": "web_micro", "text": "A gateway aggregates several microservices. It calls each service and combines the responses. The client gets one clean payload instead of many round trips."},
    {"domain": "web_micro", "text": "An order service publishes an order-created event. The payment and inventory services react to it. Each updates its own data independently."},
    {"domain": "web_micro", "text": "A health endpoint reports whether a service is ready. The load balancer polls it regularly. Unhealthy instances are pulled out of rotation."},
    {"domain": "web_micro", "text": "A background worker processes jobs from a queue. The web server enqueues slow tasks and responds immediately. The worker finishes the task out of band."},
]
