
> Status: SOURCE RESOLVED 2026-07-08. Actionable recommendations were folded into the canonical
> reference:
> `docs/4_Reference/graph-architecture-lessons.md`. Canonical active plan:
> `docs/2_Todo/memory-trace-topic-neighbourhoods-plan.md`.

### Lessons Learned: Graph Architectures & Implementation

Based on the mechanics of both enterprise graph databases and Obsidian’s lightweight local approach, here are the core engineering and design lessons learned:

* **Separate the Data Structure from the Visualization:** Obsidian proves that a compelling visual graph does not require a complex database backend. You can build highly interactive, graph-based user experiences using cheap, in-memory data structures (like adjacency lists) and offload the heavy lifting to frontend rendering engines (WebGL/Canvas).
* **Match Engine Complexity to Query Depth:**
* If your system only needs to know immediate connections (1-hop "links" and "backlinks"), a heavy database engine is overkill. A simple memory map or relational index is faster, cheaper, and easier to maintain.
* Reserve native graph databases (e.g., Neo4j) for scenarios requiring deep traversals ($3+$ hops), variable-length pathfinding, or complex network analytics where relational joins fail.


* **Pragmatism Wins Over Rigidity:** Obsidian’s choice to use plain-text Markdown files as the source of truth—rather than a proprietary database file—ensures absolute data portability, user trust, and system resilience. The graph is treated as a disposable, easily rebuilt index rather than a fragile dependency.
* **Memory is the Primary Bottleneck:** Whether scaling to millions of enterprise nodes or thousands of local Markdown notes, graph performance is bound by RAM. Because traversals require jumping between pointers, keeping the graph topology in-memory is the single most critical factor for maintaining speed.
* **Acknowledge Scaling Trade-offs Early:** Enterprise graphs struggle with horizontal scaling (sharding across servers) due to network latency during traversals. Conversely, client-side graphs (like Obsidian's) scale beautifully for individual users but are fundamentally limited by the host machine's hardware capabilities once the dataset grows significantly.
