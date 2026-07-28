/**
 * A generic, arbitrarily-deep tree navigator.
 *
 * Deliberately knows NOTHING about topics, axes or the graph. It takes nodes of
 * one recursive shape and renders them; everything specific - what a node means,
 * what selecting one does, what the counts are - arrives as props. That is what
 * lets a third ontology axis (domains, systems, projects) reuse it by adding a
 * key to the data rather than a branch to this file.
 *
 * Expansion state is OWNED BY THE CALLER for the same reason: switching axis must
 * not forget where you were, and a component that held its own state would reset
 * on every remount. Keeping it outside also makes "expand this ancestor chain"
 * something the caller can do directly when a selection arrives from elsewhere.
 */

export interface OntologyNode {
  id: string;
  name: string;
  children: OntologyNode[];
  /** Attributions on this node alone. Optional: a pure hierarchy has none. */
  count?: number;
  /** Attributions including every descendant - what selecting this returns. */
  total?: number;
}

export interface TreeViewProps {
  nodes: readonly OntologyNode[];
  selectedId: string | null;
  expandedIds: ReadonlySet<string>;
  onToggle: (id: string) => void;
  onSelect: (id: string) => void;
  /** Depth of the top-level nodes. Internal; the caller leaves it alone. */
  depth?: number;
}

/**
 * Every ancestor id of `target`, so a caller can open the path to a selection
 * it did not make itself - a topic chosen from the graph, or restored from a
 * previous session. Returns an empty array when the id is absent, so an unknown
 * slug simply opens nothing rather than throwing.
 */
export function ancestorIdsOf(nodes: readonly OntologyNode[], target: string): string[] {
  const walk = (node: OntologyNode, trail: string[]): string[] | null => {
    if (node.id === target) return trail;
    for (const child of node.children) {
      const found = walk(child, [...trail, node.id]);
      if (found) return found;
    }
    return null;
  };
  for (const node of nodes) {
    const found = walk(node, []);
    if (found) return found;
  }
  return [];
}

/** Total nodes in a forest, for the caller's "expand all" affordances. */
export function allIdsOf(nodes: readonly OntologyNode[]): string[] {
  return nodes.flatMap((node) => [node.id, ...allIdsOf(node.children)]);
}

export function TreeView({ nodes, selectedId, expandedIds, onToggle, onSelect, depth = 0 }: TreeViewProps) {
  return (
    <ul className="tree" role={depth === 0 ? "tree" : "group"}>
      {nodes.map((node) => {
        const hasChildren = node.children.length > 0;
        const expanded = expandedIds.has(node.id);
        const selected = selectedId === node.id;
        return (
          <li key={node.id} className="tree-item" role="none">
            <div
              className={selected ? "tree-row selected" : "tree-row"}
              // Indent by depth rather than by nesting the padding, so a deep
              // node keeps a full-width hit area and the hover band still spans
              // the panel instead of stepping in with the text.
              style={{ paddingLeft: `${6 + depth * 13}px` }}
            >
              {hasChildren ? (
                <button
                  type="button"
                  className={expanded ? "tree-chevron open" : "tree-chevron"}
                  onClick={() => onToggle(node.id)}
                  aria-label={`${expanded ? "Collapse" : "Expand"} ${node.name}`}
                  aria-expanded={expanded}
                  tabIndex={-1}
                >
                  <svg viewBox="0 0 12 12" width="10" height="10" aria-hidden="true">
                    <path d="M4 2.5 L8 6 L4 9.5" fill="none" stroke="currentColor" strokeWidth="1.6" strokeLinecap="round" strokeLinejoin="round" />
                  </svg>
                </button>
              ) : (
                // A spacer, not a missing element: without it a leaf's label
                // would sit where its siblings' chevrons are and the column of
                // names would not line up.
                <span className="tree-chevron placeholder" aria-hidden="true" />
              )}
              <button
                type="button"
                className="tree-label"
                onClick={() => onSelect(node.id)}
                aria-pressed={selected}
                role="treeitem"
                aria-selected={selected}
                aria-expanded={hasChildren ? expanded : undefined}
              >
                <span className="tree-name">{node.name}</span>
                {typeof node.total === "number" && node.total > 0 && (
                  // The ROLLUP, because that is what selecting this returns.
                  // Showing the node's own count beside a parent whose children
                  // hold most of the corpus makes the number disagree with the
                  // result it produces.
                  <b className="tree-count">{node.total}</b>
                )}
              </button>
            </div>
            {hasChildren && (
              // Kept mounted while closed so the height transition has something
              // to animate from, and so expanding does not re-mount a deep
              // subtree on every toggle.
              <div className={expanded ? "tree-branch open" : "tree-branch"}>
                <TreeView
                  nodes={node.children}
                  selectedId={selectedId}
                  expandedIds={expandedIds}
                  onToggle={onToggle}
                  onSelect={onSelect}
                  depth={depth + 1}
                />
              </div>
            )}
          </li>
        );
      })}
    </ul>
  );
}
