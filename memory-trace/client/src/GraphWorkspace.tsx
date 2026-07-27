import { useEffect, useMemo, useRef } from "react";
import type { Core, NodeSingular } from "cytoscape";
import type { Simulation, SimulationLinkDatum, SimulationNodeDatum } from "d3-force";
import { Maximize2, Minus, Plus } from "lucide-react";
import { type RendererGraphEdge, type RendererGraphNode, type RendererGraphResponse } from "./api";
import { nodeSetSignature, seedPositions, type Point } from "./graphLayout";
import { anchorEntryIdFor, connectedIdsWithDecisionAnchors, decisionGroups, decisionHaloId, haloDiameter, isDecisionRowId, parentIdsFor, satellitePositions, simulationLinks, visibilityIdFor } from "./graphDecisionRows";
import { forceParameters, ticksPerPaint, type ForceSettings } from "./graphForces";
import { outrankedEdgeIds } from "./graphEdges";
import { authoredBorderColour, authoredNodeColour, communityColourScale, communityLegend, inferredCommunityColours, wearsAuthoredRim, type TopicRoots } from "./graphCommunities";

type GraphWorkspaceProps = {
  graph: RendererGraphResponse;
  selectedId: string | null;
  onSelect: (node: RendererGraphNode) => void;
  labelMode: "focus" | "minimal" | "all";
  theme: "light" | "dark";
  // Motion settings (proposal §6.5). dragResponse is read through a ref at
  // event time so changing it never remounts the instance or moves the map.
  dragResponse: "fixed" | "reheat";
  /** The four live force parameters. Retunes the running simulation. */
  forces: ForceSettings;
  /** Whether entries with no authored edge are drawn at all. */
  showOrphans: boolean;
  /**
   * Hide machine-suggested edges scored below this (0 shows everything).
   * Human-authored edges carry NO confidence and are never hidden by it —
   * absence means "authored, not scored", never "confidence zero".
   */
  minConfidence: number;
  // Corpus-wide topic counts, so community colours are assigned from the whole
  // corpus rather than from whatever subset is currently loaded.
  corpusTopics: Readonly<Record<string, number>> | null;
  // Server-computed colour-wheel order (co-occurring topics adjacent), so hues
  // form coherent neighbourhoods and multi-topic mixtures stay in-family.
  topicWheel: readonly string[] | null;
  // slug -> root of its topic hierarchy. Colour is assigned at the root so the
  // palette stays bounded by roots as children populate; grouping, filtering
  // and every label keep reading the child slug.
  topicRoots: TopicRoots | null;
  /**
   * The topic the view is filtered to, or null for the whole corpus.
   *
   * Colour only. With nothing focused a node takes its topic FAMILY's colour, so
   * the map splits by family at a glance; filtered to a family, that rule paints
   * everything one colour, so inside the focus each node reverts to its own
   * child slug's colour (JNL, 2026-07-27). Membership, grouping and every label
   * keep reading the child either way — this changes no node set and no layout.
   */
  focusTopic: string | null;
  /** slug -> canonical slug, so an alias never splits from what it denotes. */
  topicCanonical: TopicRoots | null;
  // Which edge types are switched on in the "Edges" filter row. Obsidian-style:
  // this only toggles line visibility on the graph already in memory — it must
  // never drive which nodes are rendered or trigger a re-layout.
  visibleEdgeTypes: RendererGraphEdge["edge_type"][];
};

// Cytoscape styles can't consume CSS custom properties, so resolve the theme
// tokens at mount time; the mount effect re-runs on theme change (safe — the
// deterministic layout reproduces identical positions).
function themeToken(name: string, fallback: string) {
  const value = getComputedStyle(document.documentElement).getPropertyValue(name).trim();
  return value || fallback;
}

// colourForCommunity moved to graphCommunities.ts so the legend and the nodes
// share one derivation. Two copies of the hash is exactly how a legend swatch
// ends up disagreeing with the node it claims to describe.

/** A node in the simulation. fx/fy pin it while it is dragged. */
type ReheatNode = SimulationNodeDatum & { id: string; x: number; y: number };
type ReheatLink = SimulationLinkDatum<ReheatNode>;

type SimulationHandle = {
  /** Warm the simulation back up — after a drag, or a force change. */
  reheat: (alpha?: number) => void;
  /** Hold a node at a position (drag), or release it (null). */
  pin: (id: string, position: { x: number; y: number } | null) => void;
  /** Re-read the force settings and apply them without restarting. */
  retune: () => void;
  /** Save current positions without stopping — for a drag that woke nothing. */
  persistNow: () => void;
  stop: () => void;
};

// One button press or key press worth of zoom. 1.22 took five presses to
// double; this takes two, which is what "navigate" needs when the fit sits near
// 0.06 and a readable node is up around 1.
const ZOOM_STEP = 1.45;

/** How long one newly loaded node takes to grow into place. */
const SPAWN_MS = 380;

/**
 * Gap between one arriving entry and the next.
 *
 * The whole page appearing together reads as a single flash; entries arriving
 * back to back read as the graph GROWING. Small enough that a 60-entry page
 * finishes in about a second, so it never becomes a wait.
 */
const SPAWN_STAGGER_MS = 14;

/** No page should take longer than this to finish arriving, however large. */
const SPAWN_TOTAL_CAP_MS = 1100;

/**
 * How often the camera may re-measure a growing graph, in ms.
 *
 * `scaleToFitGrowth` used to run on EVERY tick, and its `boundingBox()` over the
 * whole element set is not cheap: measured on the real corpus 8.65ms at 294
 * nodes and 11.26ms at 453, against a 16.7ms frame — before the fit it may then
 * trigger, another 10ms. That is a sixth of the settle's whole frame budget
 * spent asking a question whose answer changes slowly, and it was a measurable
 * part of why paging the Overview froze the page (2026-07-27: ~365 long tasks
 * averaging 74ms, 27 of 37 seconds with the main thread blocked).
 *
 * 4Hz is far faster than a graph's bounding box actually grows while settling,
 * so the camera behaves the same and the cost drops by ~93%.
 */
const AUTO_SCALE_INTERVAL_MS = 250;

/**
 * Where a WARM (grown) mount starts and stops its settle.
 *
 * Node count is not what makes paging expensive — the number of TICKS is. From
 * alpha 1 to the d3 default alphaMin of 0.001 is ~300 ticks, and at ~450 nodes
 * each tick costs tens of milliseconds of canvas redraw, so one "Show more" held
 * the main thread for ~20s and three of them for a minute.
 *
 * A warm mount does not need that budget: every incumbent came back from a
 * settled layout and only the arriving page has to travel. Starting lower keeps
 * the incumbents from being thrown around, and stopping at a higher floor ends
 * the run once motion is no longer visible — together ~130 ticks rather than
 * ~300. Lowering the START alone would not have worked: ticks scale with
 * log(alpha0 / alphaMin), so alpha 0.4 buys only 14%.
 *
 * A COLD mount keeps the full budget: it has no good positions to preserve, and
 * a first load is small enough that the cost does not bite.
 */
const WARM_ALPHA_START = 0.6;
const WARM_ALPHA_MIN = 0.03;

/**
 * Diameter of a decision row, in graph units.
 *
 * Comfortably under the smallest entry (22 at degree 0) and under twice the
 * satellite radius, so a full fan of rows around one anchor stays inside the
 * group box without touching.
 */
const DECISION_ROW_SIZE = 15;

/** True when the reader has asked the system for less animation. */
function prefersReducedMotion(): boolean {
  return typeof window !== "undefined" && window.matchMedia?.("(prefers-reduced-motion: reduce)").matches === true;
}

/**
 * The graph's one simulation: continuous, whole-graph, alpha-driven.
 *
 * d3-force rather than a cytoscape layout because this must keep running and
 * stay steerable — alpha is a dial the UI can turn (a drag, a force change)
 * and which decays to rest on its own. That decay IS "Settled": when alpha
 * falls below the floor the loop stops entirely and costs nothing until
 * something disturbs it again.
 *
 * EVERY node takes part, isolates included. They have no link force, so what
 * holds them is repulsion against their neighbours and the pull to centre —
 * precisely the "force-packed" arrangement that puts them in the body of the
 * graph rather than on a ring outside it.
 *
 * Cheap enough to be honest about: 1.60ms median per tick at 570 nodes / 674
 * links, against a 16.7ms frame at 60fps. The old 150-node bound measured
 * cose's cost to SETTLE, which is a different quantity — see the 2026-07-22
 * amendment to proposal §6.5.
 */
function startSimulation(options: {
  cy: Core;
  nodes: readonly RendererGraphNode[];
  edges: readonly RendererGraphEdge[];
  forces: { current: ForceSettings };
  settled: boolean;
  /**
   * Some nodes came back from a previous layout — a "Show more" page, typically.
   * Those are already where they belong, so only the newcomers have to travel
   * and the settle can stop far earlier. See `WARM_ALPHA_*`.
   */
  warmSeeded: boolean;
  onRest: () => void;
  onFirstSettle: () => void;
  /** Keeps a growing graph in frame. Throttled — see `AUTO_SCALE_INTERVAL_MS`. */
  autoScale?: () => void;
  /**
   * Run after every position write. Decision rows are NOT simulation
   * participants - their position is derived from their anchor's, which is what
   * makes containment true by construction and why turning rows on moves no
   * anchor. So they must be re-derived after each paint, including the paints
   * that happen while a node is being dragged.
   */
  afterPaint?: () => void;
  disposed: () => boolean;
  reducedMotion: boolean;
}): SimulationHandle {
  const { cy, nodes: graphNodes, edges: graphEdges, forces, settled, warmSeeded, onRest, onFirstSettle, autoScale, afterPaint, disposed, reducedMotion } = options;
  let frame = 0;
  let cancelled = false;
  let fitted = settled;
  let sim: Simulation<ReheatNode, ReheatLink> | null = null;
  let applyForces: (() => void) | null = null;

  const simNodes: ReheatNode[] = graphNodes.map((node) => {
    const position = cy.getElementById(node.id).position();
    return { id: node.id, x: position.x, y: position.y };
  });
  const byId = new Map(simNodes.map((node) => [node.id, node]));

  // Decision-level edges are transferred to the entries their rows belong to,
  // rather than dropped for matching no simulation node. See `simulationLinks`
  // for why - the short version is that a decision is part of its entry, so a
  // pull on the part is a pull on the whole.
  const links: ReheatLink[] = simulationLinks(graphEdges, new Set(byId.keys()));

  // Nodes the pointer is currently holding. The simulation reads their position
  // and never writes it: while a node is grabbed, Cytoscape owns where it is.
  // Painting over a grabbed node makes it snap back to the last tick's position
  // every frame, which feels exactly like the node being locked in place.
  const grabbed = new Set<string>();

  const paint = () => {
    cy.batch(() => {
      for (const node of simNodes) {
        if (grabbed.has(node.id)) continue;
        cy.getElementById(node.id).position({ x: node.x, y: node.y });
      }
      // Inside the same batch: rows follow their anchor in the frame the anchor
      // moved, so a group never renders mid-stride with its rows a tick behind.
      afterPaint?.();
    });
  };

  const persist = () => {
    for (const node of simNodes) settledPositions.set(node.id, { x: node.x, y: node.y });
  };

  const halt = () => {
    cancelled = true;
    if (frame) cancelAnimationFrame(frame);
    frame = 0;
    sim?.stop();
    sim = null;
  };

  // Last time the camera re-measured the graph. Starts at 0 so the first tick
  // after a mount always scales — a newly grown set is exactly when it matters.
  let lastAutoScale = 0;

  // Fixed for the life of this simulation: the element set does not change
  // without a remount, and re-deriving it per frame would be the kind of
  // per-tick work this exists to remove. Edges are counted because they are
  // drawn — at corpus scale there are as many of them as nodes.
  const ticksPerFrame = ticksPerPaint(graphNodes.length + graphEdges.length);

  const run = () => {
    if (frame || cancelled) return;
    const step = () => {
      frame = 0;
      if (cancelled || disposed() || !sim) return;
      // Several physics steps per painted frame once the canvas is large enough
      // for the repaint to dominate — see ticksPerPaint. Alpha decays per TICK,
      // so this reaches rest after the same number of ticks in a fraction of the
      // frames: the settle is cheaper AND shorter, not stretched out.
      for (let tick = 0; tick < ticksPerFrame; tick += 1) {
        sim.tick();
        if (sim.alpha() < sim.alphaMin()) break;
      }
      paint();
      // Keep the growing graph in view while it expands. A page of new entries
      // pushes the bounding box outward as the simulation makes room for them,
      // and without this they simply grow off-screen. Only ever zooms OUT, and
      // only while settling — panning or zooming by hand after that is never
      // overridden.
      //
      // Throttled rather than per-tick: measuring the bounding box costs more
      // than the physics and the paint put together at corpus scale, and the
      // answer moves far slower than 60Hz. See AUTO_SCALE_INTERVAL_MS.
      const now = performance.now();
      if (!fitted && autoScale && now - lastAutoScale >= AUTO_SCALE_INTERVAL_MS) {
        lastAutoScale = now;
        autoScale();
      }
      if (sim.alpha() < sim.alphaMin()) {
        // At rest: persist, fit once more so the final shape is framed, and
        // stop burning frames.
        onRest();
        if (!fitted) {
          fitted = true;
          onFirstSettle();
        }
        return;
      }
      frame = requestAnimationFrame(step);
    };
    frame = requestAnimationFrame(step);
  };

  void (async () => {
    const d3 = await import("d3-force");
    if (cancelled || disposed()) return;
    const simulation = d3
      .forceSimulation<ReheatNode, ReheatLink>(simNodes)
      .force("link", d3.forceLink<ReheatNode, ReheatLink>(links).id((node) => node.id))
      .force("charge", d3.forceManyBody<ReheatNode>())
      .force("x", d3.forceX<ReheatNode>(0))
      .force("y", d3.forceY<ReheatNode>(0))
      .stop();
    applyForces = () => {
      const params = forceParameters(forces.current);
      simulation.force<ReturnType<typeof d3.forceLink<ReheatNode, ReheatLink>>>("link")
        ?.distance(params.linkDistance)
        .strength(params.linkStrength);
      simulation.force<ReturnType<typeof d3.forceManyBody<ReheatNode>>>("charge")?.strength(params.chargeStrength);
      simulation.force<ReturnType<typeof d3.forceX<ReheatNode>>>("x")?.strength(params.centreStrength);
      simulation.force<ReturnType<typeof d3.forceY<ReheatNode>>>("y")?.strength(params.centreStrength);
    };
    applyForces();
    sim = simulation;

    // A grown set stops sooner: the incumbents are already settled, so the run
    // exists only to place the arriving page. Set before the branches below so
    // the reduced-motion block and every later reheat honour the same floor.
    if (warmSeeded) simulation.alphaMin(WARM_ALPHA_MIN);

    if (settled) {
      // Cached positions are already a resting state — fit and idle. Nothing
      // ticks until a drag or a force change asks for it, which is what keeps
      // theme toggles and view round-trips instant at any graph size.
      simulation.alpha(0);
      onFirstSettle();
      return;
    }
    if (reducedMotion) {
      // Converge without painting the journey: tick to rest in one block, then
      // show the end state. Same destination, no animation.
      for (let i = 0; i < 400 && simulation.alpha() > simulation.alphaMin(); i += 1) simulation.tick();
      paint();
      persist();
      onRest();
      onFirstSettle();
      fitted = true;
      return;
    }
    simulation.alpha(warmSeeded ? WARM_ALPHA_START : 1);
    run();
  })();

  return {
    reheat: (alpha = 0.35) => {
      if (cancelled || reducedMotion || !sim) return;
      sim.alpha(Math.max(sim.alpha(), alpha));
      run();
    },
    pin: (id, position) => {
      const node = byId.get(id);
      if (!node) return;
      if (position) {
        grabbed.add(id);
        // Anchor the simulation's copy to where the pointer has it, so the pull
        // travels outward through the links from the node's REAL position.
        node.fx = position.x;
        node.fy = position.y;
        node.x = position.x;
        node.y = position.y;
      } else {
        grabbed.delete(id);
        delete node.fx;
        delete node.fy;
      }
    },
    retune: () => applyForces?.(),
    // Fixed-mode drags never wake the loop, so nothing would otherwise write
    // the new position into the cache and a remount would undo the arrangement.
    persistNow: () => {
      for (const node of simNodes) {
        const live = cy.getElementById(node.id).position();
        node.x = live.x;
        node.y = live.y;
      }
      persist();
    },
    stop: () => {
      // Persist wherever it got to, so a mid-flight unmount does not discard
      // the arrangement the reader was looking at.
      persist();
      halt();
    },
  };
}

/**
 * Fit the whole graph, then set the zoom floor from what the fit needed.
 *
 * A fixed minZoom silently caps cy.fit: at full corpus size the fit wanted to
 * zoom further out than 0.35, got clamped, and drew the graph larger than the
 * viewport with no way to reach the rest. Deriving the floor from the achieved
 * fit means fit always succeeds, while still stopping a user zooming out into
 * an unreadable dot-cloud.
 */
function fitAndClamp(cy: Core) {
  cy.minZoom(0.02);
  cy.fit(cy.elements(), 52);
  cy.minZoom(Math.min(0.35, cy.zoom() * 0.75));
}

/**
 * Keep a graph that is still growing inside the viewport.
 *
 * Called every tick while the simulation settles. Zooms OUT only: as a page of
 * new entries is absorbed the layout pushes outward, and without this the graph
 * simply expands past the edges. Zooming back IN is left to the final fit, so
 * the view does not pump in and out on every tick.
 *
 * The 2% deadband stops it reacting to the constant small jitter of a settling
 * simulation — without it the camera never stops adjusting.
 */
function scaleToFitGrowth(cy: Core) {
  const box = cy.elements().boundingBox();
  const width = box.x2 - box.x1;
  const height = box.y2 - box.y1;
  if (width <= 0 || height <= 0) return;
  const padding = 52;
  const needed = Math.min((cy.width() - padding * 2) / width, (cy.height() - padding * 2) / height);
  if (needed < cy.zoom() * 0.98) {
    cy.minZoom(0.02);
    cy.fit(cy.elements(), padding);
    cy.minZoom(Math.min(0.35, cy.zoom() * 0.75));
  }
}

function labelIdsFor(graph: RendererGraphResponse, selectedId: string | null, labelMode: GraphWorkspaceProps["labelMode"]) {
  if (labelMode === "all") return new Set(graph.nodes.map((node) => node.id));
  if (labelMode === "minimal") return new Set(selectedId ? [selectedId] : []);
  return new Set(
    [...graph.nodes]
      .sort((left, right) => right.connectivity - left.connectivity || right.importance_score - left.importance_score)
      .slice(0, 12)
      .map((node) => node.id),
  );
}

// Settled positions from the last completed layout, keyed by the node-id set
// they were computed for. Module-level so a remount (theme change, view
// round-trip) with the SAME node set restores positions instantly via a
// preset layout instead of re-running the simulation, and a GROWN node set
// ("Show more") seeds its old nodes where they already settled so only the
// additions need real layout work. The seeding rules themselves live in
// graphLayout.ts so they can be unit tested.
let settledSignature = "";
const settledPositions = new Map<string, Point>();

export function GraphWorkspace({ graph, selectedId, onSelect, labelMode, theme, visibleEdgeTypes, corpusTopics, topicWheel, topicRoots, focusTopic, topicCanonical, dragResponse, forces, showOrphans, minConfidence }: GraphWorkspaceProps) {
  const container = useRef<HTMLDivElement>(null);
  const cytoscape = useRef<Core | null>(null);
  // Refs so the tap handler and selection effect never force an instance remount.
  const onSelectRef = useRef(onSelect);
  onSelectRef.current = onSelect;
  const graphRef = useRef(graph);
  graphRef.current = graph;
  const selectedIdRef = useRef(selectedId);
  selectedIdRef.current = selectedId;
  const labelIdsRef = useRef<Set<string>>(new Set());
  const visibleEdgeTypesRef = useRef(visibleEdgeTypes);
  visibleEdgeTypesRef.current = visibleEdgeTypes;
  const minConfidenceRef = useRef(minConfidence);
  minConfidenceRef.current = minConfidence;
  const dragResponseRef = useRef(dragResponse);
  dragResponseRef.current = dragResponse;
  // The graph's simulation. A ref because it must be reachable from the mount
  // cleanup: ticks that outlive the instance would write positions into a
  // destroyed Cytoscape.
  const simulation = useRef<SimulationHandle | null>(null);
  // Staggered spawn timers, cancelled on unmount so a page that is still
  // arriving cannot keep touching a destroyed instance.
  const spawnTimers = useRef<number[]>([]);
  // Force settings by ref so moving a slider retunes the RUNNING simulation
  // rather than remounting the graph — the whole point of continuous physics.
  const forcesRef = useRef(forces);
  forcesRef.current = forces;
  // Selection restyle was the one metric that grew with corpus size: 5-13ms
  // below ~400 nodes but 47-102ms at 1000 edges, because every selection swept
  // the whole edge set. The sweep's result depends only on the edge set and the
  // visible-type filter - never on which node is selected - so it is memoized
  // on exactly those two inputs and drops out of the selection path entirely.
  const outrankedMemo = useRef<{ edges: unknown; typesKey: string; value: Set<string> } | null>(null);

  // In-place presentation pass — selection ring, labels, edge filter. Reads
  // current state from refs so both the mount (async) and the update effect
  // can apply it without racing each other.
  const applyPresentation = (cy: Core) => {
    const currentSelected = selectedIdRef.current;
    const currentLabels = labelIdsRef.current;
    const currentVisibleTypes = visibleEdgeTypesRef.current;
    cy.batch(() => {
      cy.nodes().forEach((node) => {
        const id = node.id();
        node.data("selected", id === currentSelected ? "yes" : "no");
        node.data("label", id === currentSelected || currentLabels.has(id) ? node.data("title") : "");
      });
      // Edge visibility is the "Edges" filter row's business ALONE: a type
      // that is switched on is drawn for every node pair that has it, always.
      // Evolves edges used to additionally hide unless they touched the
      // selection, which contradicted their own chip reading as ON and made
      // the map's lineage invisible until you happened to click the right
      // node. Turning a chip off still hides that type outright, Obsidian
      // style, and never touches which nodes exist or where they sit.
      //
      // One line per PAIR: two entries often carry several relationships at
      // once, which drew coincident lines and let the weakest one (a topic
      // tag) paint over the strongest (a supersession). Only the most
      // consequential relationship survives - see EDGE_PRIORITY. The winner is
      // chosen among the types currently switched ON, so switching a type off
      // promotes whatever it was covering rather than blanking the pair.
      // Keyed on the graph's edge ARRAY IDENTITY, which changes only when a new
      // graph is fetched, so a stale set can never survive a reload.
      // A confidence-filtered edge is hidden for the same reason a
      // switched-off type is, so it must also be excluded from the
      // outranking input below. Otherwise a hidden low-confidence edge could
      // win its pair and blank the visible relationship underneath it.
      const currentMinConfidence = minConfidenceRef.current;
      const passesConfidence = (confidence: unknown) =>
        currentMinConfidence <= 0 || typeof confidence !== "number" || confidence >= currentMinConfidence;
      const typesKey = `${currentVisibleTypes.join(",")}|${currentMinConfidence}`;
      const memo = outrankedMemo.current;
      let outranked: Set<string>;
      if (memo && memo.edges === graphRef.current.edges && memo.typesKey === typesKey) {
        outranked = memo.value;
      } else {
        outranked = outrankedEdgeIds(
          cy
            .edges()
            .filter((edge) => passesConfidence(edge.data("confidence")))
            .map((edge) => ({
              id: edge.id(),
              source: edge.data("source"),
              target: edge.data("target"),
              type: edge.data("type"),
            })),
          currentVisibleTypes,
        );
        outrankedMemo.current = { edges: graphRef.current.edges, typesKey, value: outranked };
      }
      cy.edges().forEach((edge) => {
        const hidden =
          !currentVisibleTypes.includes(edge.data("type")) || !passesConfidence(edge.data("confidence"));
        edge.toggleClass("edge-filtered", hidden);
        edge.toggleClass("edge-outranked", outranked.has(edge.id()));
      });
    });
  };

  // The rendered element set is SELECTION-INDEPENDENT: EVERY payload node
  // renders, always. Selecting must never add/remove elements or move the map —
  // selection only restyles (ring, labels).
  //
  // Edgeless entries used to be filtered out here unconditionally, on the
  // reasoning that an entry with no authored link is noise. That made the
  // coverage readout look like a hard cap ("462 of 603") when it was really a
  // rendering choice, and it hid a fifth of the corpus. Showing them is now a
  // VIEWING PREFERENCE (the Orphans toggle) rather than a structural decision,
  // and when shown they take part in the simulation like anything else.
  //
  // Endpoints credit their ANCHOR as well as themselves, so an entry whose only
  // relationships are decision-level counts as connected once its rows are on
  // screen. Without that rule the Orphans filter would hide the anchor and keep
  // its own decision rows, which is both untrue (the tie exists, it just names a
  // decision) and structurally broken - a group with no anchor.
  const connected = useMemo(() => connectedIdsWithDecisionAnchors(graph.edges), [graph.edges]);
  // Degree centrality over the PAYLOAD's edges, which drives node size below.
  // Two deliberate choices. It counts every edge kind in the payload, not just
  // `related` — the node's server-computed `connectivity` is a related-only
  // weight, so an entry whose ties are mostly `evolves` drew small while a
  // chattier but less consequential one drew large. And it reads the payload
  // rather than the VISIBLE edge set, so toggling an edge filter re-styles
  // lines without resizing every node underneath them.
  const degree = useMemo(() => {
    const counts = new Map<string, number>();
    for (const edge of graph.edges) {
      if (edge.source === edge.target) continue;
      counts.set(edge.source, (counts.get(edge.source) ?? 0) + 1);
      counts.set(edge.target, (counts.get(edge.target) ?? 0) + 1);
    }
    return counts;
  }, [graph.edges]);
  // A decision row is kept or dropped with its ANCHOR, never on its own degree —
  // see visibilityIdFor. Otherwise the Orphans filter takes a group apart and
  // leaves it claiming fewer decisions than the entry has.
  const renderedNodes = useMemo(
    () => (showOrphans ? graph.nodes : graph.nodes.filter((node) => connected.has(visibilityIdFor(node.id)))),
    [graph.nodes, connected, showOrphans],
  );
  // Decision-row containment. Each entry that has rendered rows gets a synthetic
  // `dgroup:` compound node holding BOTH the anchor and its rows as children —
  // never the anchor as parent, because a Cytoscape parent is auto-positioned
  // (and this simulation writes every participant's position every tick) and
  // auto-sized (so the entry would lose the circle/fill/rim vocabulary the rest
  // of the map reads). This is the non-edge structural channel: no fifth edge
  // kind, nothing entry-level emitted, and the four-kind contract untouched.
  const decisionRowGroups = useMemo(() => decisionGroups(renderedNodes), [renderedNodes]);
  const rowParentIds = useMemo(() => parentIdsFor(decisionRowGroups), [decisionRowGroups]);
  // What each decision row is tied to, so its ring can rotate to face its own
  // relatives. Recorded as the counterpart's ANCHOR, never the counterpart row:
  // anchors are the simulation's participants, so the position read is settled
  // for the frame rather than being derived in the same pass — which is what
  // keeps the rotation deterministic instead of order-dependent.
  const rowCounterparts = useMemo(() => {
    const map = new Map<string, string[]>();
    const add = (rowId: string, otherId: string) => {
      const anchor = anchorEntryIdFor(otherId);
      if (anchor === anchorEntryIdFor(rowId)) return;
      map.set(rowId, [...(map.get(rowId) ?? []), anchor]);
    };
    for (const edge of graph.edges) {
      if (isDecisionRowId(edge.source)) add(edge.source, edge.target);
      if (isDecisionRowId(edge.target)) add(edge.target, edge.source);
    }
    return map;
  }, [graph.edges]);
  // `focusTopic` is in every dependency array below on purpose: it changes the
  // colour KEY (root when nothing is focused, the child's own slug inside the
  // focus), so a memo that omitted it would keep handing back root colours after
  // a filter — the same class of silent no-op as the confidence threshold that
  // was read from a ref but missing from its effect's deps.
  const legend = useMemo(() => communityLegend(renderedNodes, corpusTopics, topicWheel, topicRoots, focusTopic, topicCanonical), [renderedNodes, corpusTopics, topicWheel, topicRoots, focusTopic, topicCanonical]);
  const colourOf = useMemo(() => communityColourScale(corpusTopics, topicWheel, topicRoots, focusTopic, topicCanonical), [corpusTopics, topicWheel, topicRoots, focusTopic, topicCanonical]);
  // Authored fill is the MIXTURE of a node's qualifying topics; falls back to
  // the pure community colour when the mixture cannot be built.
  // The authored mixture, or null when the node authored nothing that clears
  // the floor. Kept as null rather than pre-resolved to a fallback because the
  // caller needs to know WHETHER a node authored a colour - that is what
  // decides the rim, and what stops an inferred pastel overriding a real one.
  const authoredOf = useMemo(
    () => (node: RendererGraphNode) => authoredNodeColour(node, corpusTopics, topicWheel, topicRoots, focusTopic, topicCanonical),
    [corpusTopics, topicWheel, topicRoots, focusTopic, topicCanonical],
  );
  // Topicless nodes take a pastel blend of the communities that reach them
  // (directly, or as decaying residue down a topicless chain). Pastel is a
  // property of the community colour alone, so no theme dependency here.
  const inferredColours = useMemo(
    () => inferredCommunityColours(renderedNodes, graph.edges, colourOf),
    [renderedNodes, graph.edges, colourOf],
  );
  const labelIds = useMemo(() => labelIdsFor(graph, selectedId, labelMode), [graph, labelMode, selectedId]);
  labelIdsRef.current = labelIds;

  const fit = () => {
    const cy = cytoscape.current;
    if (cy) fitAndClamp(cy);
  };
  const zoom = (factor: number) => {
    const cy = cytoscape.current;
    if (!cy) return;
    cy.zoom({ level: Math.max(cy.minZoom(), Math.min(cy.maxZoom(), cy.zoom() * factor)), renderedPosition: { x: cy.width() / 2, y: cy.height() / 2 } });
  };

  const selectAdjacent = (direction: 1 | -1) => {
    if (!graph.nodes.length) return;
    const ordered = [...graph.nodes].sort((left, right) => left.temporal.value.localeCompare(right.temporal.value) || left.label.localeCompare(right.label));
    const currentIndex = Math.max(0, ordered.findIndex((node) => node.id === selectedId));
    onSelect(ordered[(currentIndex + direction + ordered.length) % ordered.length]);
  };

  // Mount ONCE per graph payload. Selection, label mode, and evolves visibility
  // are applied in place by the effect below — never by rebuilding the instance,
  // never by re-running layout. The map only moves when the data changes.
  useEffect(() => {
    let disposed = false;

    async function mount() {
      const { default: createCytoscape } = await import("cytoscape");
      if (disposed || !container.current) return;
      const signature = nodeSetSignature(renderedNodes);
      // Which entries this mount is ADDING. settledPositions still holds the
      // previous set at this point, so anything missing from it is arriving
      // now — a "Show more" page, typically. Captured before seeding, which is
      // what writes the newcomers in.
      const arriving = new Set(renderedNodes.filter((node) => !settledPositions.has(node.id)).map((node) => node.id));
      const { positions, settled, warmSeeded } = seedPositions(renderedNodes, graph.edges, settledPositions, settledSignature);
      const nodeBorder = themeToken("--panel", "#142a26");
      const nodeText = themeToken("--text-bright", "#e9f3f0");
      const nodeOutline = themeToken("--bg", "#10201e");
      const selectedRing = themeToken("--accent-strong", "#efb345");
      const edgeRelated = themeToken("--edge-related", "#74a6ce");
      const edgeReplaces = themeToken("--edge-replaces", "#e18494");
      const edgeEvolves = themeToken("--edge-evolves", "#7cc6e8");
      const edgeTopic = themeToken("--edge-topic", "#a88acc");
      const groupFill = themeToken("--muted", "#8b9a93");
      const cy = createCytoscape({
        container: container.current,
        elements: [
          // Containers first: Cytoscape requires a parent to exist before a
          // child names it.
          ...[...decisionRowGroups.values()].map((group) => ({
            data: { id: group.groupId, isGroup: "yes" },
            // Neither selectable nor draggable: a container is scaffolding, and
            // dragging a compound parent in Cytoscape drags every child with it,
            // which would move an anchor the simulation owns.
            selectable: false,
            grabbable: false,
          })),
          // The visible circle. A child of the container rather than the
          // container itself, because Cytoscape draws a compound parent as a
          // rectangle whatever its shape says. Sized to enclose the ring and
          // positioned on the anchor by the same pass that places the rows.
          ...[...decisionRowGroups.values()].map((group) => ({
            data: {
              id: decisionHaloId(group.anchorId),
              parent: group.groupId,
              isHalo: "yes",
              size: haloDiameter(group.rowIds.length),
            },
            selectable: false,
            grabbable: false,
          })),
          ...renderedNodes.map((node) => {
            // AUTHORED COLOUR WINS, and the test is whether the node has one -
            // not whether its COMMUNITY qualifies. The two came apart when
            // colour started climbing to the root: an entry tagged only with
            // child slugs (four children of `control-plane`, say) is named
            // `unassigned` by the server, because grouping still applies the
            // floor per slug, yet it plainly authored a topic and now has a
            // root colour to show for it. Gating on the community handed those
            // entries a borrowed pastel instead - the entry said what it was
            // about and the graph answered with a guess from its neighbours.
            //
            // Known edge, deliberately left: such a node still RELAYS residue
            // as a topicless waypoint, because the inference walk decides
            // membership from the community too. That only affects who receives
            // a faded tint, never what colour this node shows, and rewriting
            // the walk's seeding rules is not worth it for the handful of
            // entries involved.
            const authored = authoredOf(node);
            const colour = authored ?? inferredColours.get(node.id) ?? colourOf(node);
            return {
              data: {
                parent: rowParentIds.get(node.id),
                id: node.id,
                label: "",
                title: node.label,
                agent: node.source.agent,
                selected: "no",
                colour,
                // Authored membership wears a rim of its own colour, darkened;
                // inferred and unassigned nodes keep the invisible cutout
                // border, so the rim alone says "this entry declared a topic".
                // Either an authored mixture or an authored community earns it -
                // see wearsAuthoredRim. A full-strength authored colour with no
                // rim would be indistinguishable from a saturated inferred tint,
                // which is the confusion the rim exists to prevent.
                borderColour: wearsAuthoredRim(node, authored) ? authoredBorderColour(colour) : nodeBorder,
                // Square-root scaling, not linear: degree is heavy-tailed, so a
                // linear ramp spends its whole range on the few hubs and leaves
                // everything else indistinguishable. sqrt keeps the low end
                // legible while still ranking the hubs, and the cap stops one
                // outlier dominating the canvas.
                // A decision row is a SUBDIVISION of its anchor, not a peer, so
                // it takes a fixed small size instead of a degree-derived one.
                // Two reasons: degree centrality is a claim about how connected
                // an ENTRY is, and a row must never out-size the entry that
                // contains it or the containment reads backwards.
                size: isDecisionRowId(node.id)
                  ? DECISION_ROW_SIZE
                  : 22 + Math.min(20, Math.sqrt(degree.get(node.id) ?? 0) * 5),
                kind: isDecisionRowId(node.id) ? "decision" : "entry",
              },
              // A row's position is derived, so letting the pointer move it
              // would just be a fight the next paint wins. Still tappable —
              // clicking a decision is how the Inspector reaches it.
              grabbable: !isDecisionRowId(node.id),
              position: positions.get(node.id),
            };
          }),
          ...graph.edges.map((edge, index) => ({
            // Machine-suggested edges carry a 0..1 confidence; human-authored
            // edges have none. The attribute is OMITTED (not null) when unscored
            // so a `[confidence < x]` selector never matches them - cytoscape
            // coerces a null attr to 0, which would fade every authored edge.
            data:
              edge.confidence == null
                ? { id: edge.id || `${edge.source}-${edge.target}-${index}`, source: edge.source, target: edge.target, type: edge.edge_type }
                : { id: edge.id || `${edge.source}-${edge.target}-${index}`, source: edge.source, target: edge.target, type: edge.edge_type, confidence: edge.confidence },
          })),
        ],
        style: [
          {
            selector: "node",
            style: {
              "background-color": "data(colour)",
              "border-color": "data(borderColour)",
              "border-width": 2.5,
              "label": "data(label)",
              "font-family": "Inter, sans-serif",
              "font-size": 11,
              // Now that the zoom floor follows the fit, a full-corpus view can
              // sit far enough out that labels would smear into illegible
              // pixels; below this they drop out cleanly instead.
              "min-zoomed-font-size": 9,
              "font-weight": 600,
              "color": nodeText,
              "text-wrap": "ellipsis",
              "text-max-width": "132px",
              "text-outline-color": nodeOutline,
              "text-outline-width": 3,
              "text-valign": "bottom",
              "text-margin-y": 8,
              "width": "data(size)",
              "height": "data(size)",
              // Above the decision-group halo, which asks for 0. Every real node
              // has to sit on top of the disc that frames it.
              "z-index": 10,
              // Newly loaded entries grow into place rather than blinking in —
              // see the .spawning rules below.
              "transition-property": "width, height, opacity",
              "transition-duration": SPAWN_MS,
              "transition-timing-function": "ease-out",
            },
          },
          // The decision group's container. Deliberately faint: it exists to
          // say "these belong to that entry", and a heavy box would compete
          // with the relationships it surrounds. `events: "no"` keeps it out of
          // the tap path — a synthetic container is not a selectable memory —
          // and bottom compound depth keeps it behind its own children.
          //
          // Invisible: the shape a reader sees is the halo below, because
          // Cytoscape draws a compound parent as a rectangle whatever `shape`
          // says. This element's whole job is the `parent` relationship.
          {
            selector: 'node[isGroup = "yes"]',
            style: {
              "background-opacity": 0,
              "border-width": 0,
              "padding": "0px",
              "label": "",
              "events": "no",
              "z-compound-depth": "bottom",
            },
          },
          // The group's visible CIRCLE (JNL, 2026-07-27), not a box: the rows sit
          // on a ring at equal angles, so a circle is the shape that arrangement
          // actually has. A rectangle drew corners the content never reached and
          // read as a container of records rather than one memory with its
          // decisions. Faint, and behind its siblings, so it frames the group
          // without competing with the relationships crossing it.
          {
            selector: 'node[isHalo = "yes"]',
            style: {
              "shape": "ellipse",
              "width": "data(size)",
              "height": "data(size)",
              "background-color": groupFill,
              "background-opacity": 0.09,
              "border-width": 1,
              "border-color": groupFill,
              "border-opacity": 0.34,
              "label": "",
              "events": "no",
              "z-index": 0,
            },
          },
          // A decision row: same fill vocabulary as its anchor (it inherits the
          // entry's topics), squared off so the shape alone says "part of an
          // entry" rather than "an entry".
          { selector: 'node[kind = "decision"]', style: { "shape": "round-diamond", "border-width": 1.5, "font-size": 9 } },
          // A node that has just arrived: no size, no opacity. Removing the
          // class lets the transition above carry it to full, so what a reader
          // sees is the entry expanding into existence at the position the
          // simulation is already pulling it toward.
          { selector: "node.spawning", style: { width: 1, height: 1, opacity: 0 } },
          // Its links follow a beat later, so the node appears and THEN attaches
          // — the order the graph actually grew in.
          {
            selector: "edge.spawning",
            style: { opacity: 0, "transition-property": "opacity", "transition-duration": SPAWN_MS },
          },
          {
            selector: 'node[selected = "yes"]',
            style: { "border-color": selectedRing, "border-width": 5, "overlay-color": selectedRing, "overlay-opacity": 0.26, "overlay-padding": 5 },
          },
          // Straight edges: curvature carried no information and read as noise.
          { selector: "edge", style: { "curve-style": "straight", "line-color": edgeRelated, "target-arrow-color": edgeRelated, "target-arrow-shape": "triangle", "width": 2, "opacity": 0.85 } },
          { selector: 'edge[type = "related"]', style: { "line-color": edgeRelated, "target-arrow-color": edgeRelated } },
          { selector: 'edge[type = "replaces"]', style: { "line-style": "dashed", "line-color": edgeReplaces, "target-arrow-color": edgeReplaces } },
          { selector: 'edge[type = "evolves"]', style: { "line-style": "dotted", "line-color": edgeEvolves, "target-arrow-color": edgeEvolves, "width": 2.5 } },
          { selector: 'edge[type = "topic"]', style: { "line-style": "dotted", "line-color": edgeTopic, "target-arrow-color": edgeTopic, "opacity": 0.58 } },
          // Confidence weighting (machine-suggested edges only; authored edges
          // omit the attribute and keep full strength). Mid fades; low fades
          // more and thins - an unverified suggestion never looks settled. The
          // existence guard `edge[confidence]` keeps the numeric compares off
          // authored edges even if a future value is exactly 0.
          { selector: "edge[confidence][confidence >= 0.7][confidence < 0.9]", style: { opacity: 0.5 } },
          { selector: "edge[confidence][confidence < 0.7]", style: { opacity: 0.28, width: 1 } },
          { selector: "edge.edge-filtered", style: { display: "none" } },
          { selector: "edge.edge-outranked", style: { display: "none" } },
        ],
        layout: { name: "preset" },
        // An absolute floor, not the working minimum. The working floor is set
        // from each successful fit (see fitAndClamp): a fixed 0.35 CLAMPED the
        // fit on large graphs, which is why the full corpus rendered larger
        // than the viewport with no way to zoom out to it.
        minZoom: 0.02,
        // 4x rather than 2.4x: the fit at full corpus size sits near 0.06, so
        // the useful range now spans two orders of magnitude and the ceiling
        // has to leave room to actually read a node.
        maxZoom: 4,
        // Cytoscape's own default. It was 0.16 — about a sixth of a normal
        // wheel notch — which made crossing that range a grind.
        wheelSensitivity: 1,
      });
      // Decision rows are DERIVED, not simulated: their position is recomputed
      // from their anchor's after every position write. That is what makes
      // containment true by construction — a row cannot drift out of its group,
      // no leash force is needed, and turning rows ON moves no anchor at all,
      // because a row exerts no force on anything. The map a reader had is the
      // map they still have, with decisions added to it.
      //
      // Called once immediately as well as on every paint: a settled mount never
      // ticks (alpha starts at 0), so without this the rows would sit wherever
      // the position cache left them until something disturbed the graph.
      const positionDecisionRows = decisionRowGroups.size
        ? () => {
            for (const group of decisionRowGroups.values()) {
              const anchor = cy.getElementById(group.anchorId);
              if (anchor.empty()) continue;
              const at = anchor.position();
              const counterparts = new Map<string, Point[]>();
              for (const rowId of group.rowIds) {
                const points: Point[] = [];
                for (const otherId of rowCounterparts.get(rowId) ?? []) {
                  const other = cy.getElementById(otherId);
                  if (!other.empty()) points.push({ ...other.position() });
                }
                if (points.length) counterparts.set(rowId, points);
              }
              const placed = satellitePositions({ rowIds: group.rowIds, anchor: at, counterparts });
              for (const [rowId, point] of placed) cy.getElementById(rowId).position(point);
              // The circle is centred on the anchor, so it stays concentric with
              // the ring it frames however the anchor moves.
              cy.getElementById(decisionHaloId(group.anchorId)).position({ x: at.x, y: at.y });
            }
          }
        : undefined;
      positionDecisionRows?.();
      cy.on("tap", "node", (event) => {
        const node = graphRef.current.nodes.find((item) => item.id === event.target.id());
        if (node) onSelectRef.current(node);
      });

      // Reheat on drag (proposal §6.5). Pulling a node transfers force to the
      // nodes it is connected to, then everything cools and stays put.
      //
      // Three properties make this exploration rather than a claim about the
      // data: it is LOCAL (a bounded neighbourhood, with a pinned ring so
      // nothing propagates past it), it is FINITE (cools to rest, hard-capped),
      // and it is LOCAL-ONLY in the storage sense - positions go to the
      // renderer's settled cache and nowhere else. No refetch, no remount, and
      // nothing is ever written back to Markdown.
      // Pinning happens in BOTH drag modes: it is what stops the simulation
      // painting over a node the pointer is holding. Only the reheat differs —
      // that is what decides whether the rest of the graph responds.
      cy.on("grab", "node", (event) => {
        simulation.current?.pin(event.target.id(), event.target.position());
        if (dragResponseRef.current === "reheat") simulation.current?.reheat(0.5);
      });
      cy.on("drag", "node", (event) => {
        // The pointer owns the grabbed node; the simulation follows it, so the
        // pull propagates outward through the links rather than fighting it.
        simulation.current?.pin(event.target.id(), event.target.position());
        if (dragResponseRef.current === "reheat") simulation.current?.reheat(0.3);
        // Fixed drags never wake the loop, so no paint would carry the rows
        // along with the anchor the pointer is moving.
        else positionDecisionRows?.();
      });
      cy.on("free", "node", (event) => {
        // Unpin and let it cool. Alpha decay does the rest — no cooling timer,
        // because rest is the simulation's own resting state now.
        simulation.current?.pin(event.target.id(), null);
        if (dragResponseRef.current === "reheat") simulation.current?.reheat(0.2);
        else simulation.current?.persistNow();
      });
      // Grow the newcomers in. Only on a GROWN set: on a cold start everything
      // is new, and 570 nodes inflating at once is a splash screen, not a
      // signal. Here the point is to show WHICH entries just arrived and what
      // they attached to.
      if (warmSeeded && arriving.size && !prefersReducedMotion()) {
        const fresh = cy.nodes().filter((node) => arriving.has(node.id()));
        fresh.addClass("spawning");
        cy.edges().filter((edge) => arriving.has(edge.data("source")) || arriving.has(edge.data("target"))).addClass("spawning");
        // OLDEST FIRST, so the page arrives in the order it was written rather
        // than in whatever order the payload happened to list.
        const order = fresh.nodes().toArray().sort((left, right) => {
          const at = (node: NodeSingular) => graphRef.current.nodes.find((item) => item.id === node.id())?.temporal.value ?? "";
          return at(left).localeCompare(at(right)) || left.id().localeCompare(right.id());
        });
        const stagger = Math.min(SPAWN_STAGGER_MS, SPAWN_TOTAL_CAP_MS / Math.max(1, order.length));
        const timers: number[] = [];
        // Two frames before the first release: one for the "before" state to
        // paint, the next to transition from it. Removing the class in the same
        // frame skips the animation, because the browser never renders it.
        requestAnimationFrame(() => requestAnimationFrame(() => {
          if (disposed) return;
          order.forEach((node, index) => {
            timers.push(window.setTimeout(() => {
              if (disposed) return;
              node.removeClass("spawning");
              // Each entry's own links follow it a beat later, so a node appears
              // and THEN reaches out — the order the graph actually grew in.
              timers.push(window.setTimeout(() => {
                if (!disposed) node.connectedEdges().removeClass("spawning");
              }, SPAWN_MS * 0.5));
            }, index * stagger));
          });
        }));
        spawnTimers.current = timers;
      }
      cytoscape.current = cy;
      // Debug/parity surface (same pattern as the Trail's memoryTraceNextDebug
      // harness): lets stability be asserted from outside — positions must not
      // move on selection.
      const debugHost = window as unknown as { memoryTraceNextDebug?: Record<string, unknown> };
      debugHost.memoryTraceNextDebug = { ...(debugHost.memoryTraceNextDebug ?? {}), graphCy: cy };
      applyPresentation(cy);
      // ONE continuous simulation over the WHOLE graph, isolates included.
      //
      // This replaced a cose layout that ran once to convergence and then froze,
      // with edgeless nodes placed on computed rings outside it because they
      // could not be simulated affordably. Both were consequences of a
      // measurement that turned out to be about the wrong thing: the 150-node
      // live-motion bound came from cose's cost to SETTLE (1177ms at 467 nodes),
      // not the cost of one tick. A d3 tick over 570 nodes measures 1.60ms
      // median, 2.81ms p99 — about a tenth of a 60fps frame. See the 2026-07-22
      // amendment to proposal §6.5.
      //
      // Settled is not a separate mode any more: it is what this simulation
      // does when left alone. Alpha decays, ticking stops, positions persist.
      // Everything §6.5 requires of motion still holds — it cools to rest, it
      // never refetches, and nothing reaches Markdown.
      simulation.current = startSimulation({
        cy,
        // Entries only. Rows follow their anchor (see positionDecisionRows) and
        // group containers are auto-positioned by Cytoscape from their children,
        // so handing either to the simulation would fight the thing that places
        // it.
        nodes: renderedNodes.filter((node) => !isDecisionRowId(node.id)),
        edges: graph.edges,
        forces: forcesRef,
        settled,
        warmSeeded,
        onRest: () => {
          if (disposed) return;
          settledSignature = signature;
          settledPositions.clear();
          cy.nodes().forEach((node) => {
            const position = node.position();
            settledPositions.set(node.id(), { x: position.x, y: position.y });
          });
        },
        onFirstSettle: () => {
          if (!disposed) fitAndClamp(cy);
        },
        autoScale: () => {
          if (!disposed) scaleToFitGrowth(cy);
        },
        afterPaint: positionDecisionRows,
        disposed: () => disposed,
        reducedMotion: prefersReducedMotion(),
      });
    }

    void mount();
    return () => {
      disposed = true;
      // Stop the simulation BEFORE destroying the instance: a tick that lands
      // after destroy writes positions into a dead Cytoscape.
      simulation.current?.stop();
      simulation.current = null;
      for (const timer of spawnTimers.current) window.clearTimeout(timer);
      spawnTimers.current = [];
      cytoscape.current?.destroy();
      cytoscape.current = null;
    };
  }, [graph, renderedNodes, theme]);

  // A force change retunes the RUNNING simulation and warms it just enough to
  // show the new shape. No remount, no refetch, no camera move — moving a
  // slider is a physics change, not a data change.
  useEffect(() => {
    simulation.current?.retune();
    simulation.current?.reheat(0.3);
  }, [forces]);

  // Presentation updates on selection/label/edge-filter changes: in place, no
  // element churn, no layout, no camera movement.
  useEffect(() => {
    const cy = cytoscape.current;
    if (!cy) return;
    applyPresentation(cy);
  }, [labelIds, selectedId, graph, visibleEdgeTypes, minConfidence]);

  return <section className="graph-workspace" aria-label="Memory graph workspace">
    {/* Overlaid on the canvas rather than added as a row: .workspace's grid
        reserves exactly three rows (bar / filters / content), so a fourth
        sibling collapses the canvas to zero height. A legend also belongs
        beside the thing it explains. */}
    {legend.length > 0 && (
      <div className="graph-legend" aria-label="Topic community legend">
        <span className="graph-legend-title">Topics</span>
        {legend.map((entry) => (
          <span key={entry.id} className={`graph-legend-item${entry.topic ? "" : " graph-legend-item-none"}`}>
            {/* Same rim rule as the nodes, so the key teaches it: authored
                communities are outlined, absence is not. */}
            <span className="graph-legend-key" style={{ background: entry.colour, border: entry.topic ? `1.5px solid ${authoredBorderColour(entry.colour)}` : "none" }} aria-hidden="true" />
            {entry.label}
            {/* Colour comes from the root, so sibling communities share a
                swatch. Naming the parent is what stops that reading as the
                legend having lost track of which row is which. */}
            {entry.rootLabel && <i className="graph-legend-parent">{entry.rootLabel}</i>}
            <b>{entry.count}</b>
          </span>
        ))}
      </div>
    )}
    <div className="graph-controls" aria-label="Graph view controls">
      <button className="icon-button" type="button" onClick={() => zoom(1 / ZOOM_STEP)} aria-label="Zoom out" title="Zoom out"><Minus size={16} /></button>
      <button className="icon-button" type="button" onClick={fit} aria-label="Fit graph" title="Fit graph"><Maximize2 size={16} /></button>
      <button className="icon-button" type="button" onClick={() => zoom(ZOOM_STEP)} aria-label="Zoom in" title="Zoom in"><Plus size={16} /></button>
    </div>
    <div className="graph-canvas" ref={container} aria-label="Memory graph" role="application" tabIndex={0} aria-keyshortcuts="+ - 0 ArrowLeft ArrowRight" onKeyDown={(event) => {
      if (event.key === "+" || event.key === "=") { event.preventDefault(); zoom(ZOOM_STEP); }
      if (event.key === "-") { event.preventDefault(); zoom(1 / ZOOM_STEP); }
      if (event.key === "0" || event.key === "Home") { event.preventDefault(); fit(); }
      if (event.key === "ArrowLeft" || event.key === "ArrowUp") { event.preventDefault(); selectAdjacent(-1); }
      if (event.key === "ArrowRight" || event.key === "ArrowDown") { event.preventDefault(); selectAdjacent(1); }
    }} />
  </section>;
}
