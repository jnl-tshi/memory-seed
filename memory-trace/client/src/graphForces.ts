// The four forces the graph runs on, and how a slider position becomes one.
//
// Pure so the mapping can be tested without a simulation, and so the defaults
// live in one place rather than being scattered through the mount effect as
// magic numbers - which is what they were when the layout could only settle
// once and nobody could tune anything.
//
// Slider positions are 0..1 throughout. The UI never deals in force units, and
// the simulation never deals in slider units.

/**
 * Three forces, which is all a graph like this needs: things push apart, links
 * pull together, and the whole is held to a centre.
 *
 * Link DISTANCE was a fourth slider briefly. It is now a constant, because it
 * and link force are two ways of saying the same thing to a reader — both make
 * connected nodes sit closer or further apart — and offering both invites
 * fiddling with two dials that fight each other.
 */
export type ForceSettings = {
  /** Pull toward the centre. Higher packs the graph tighter. */
  centre: number;
  /** Node-to-node repulsion. Higher spreads them apart. */
  repel: number;
  /** How hard an edge pulls its endpoints together. */
  linkForce: number;
};

/** The distance an edge tries to hold. Matches the old cose idealEdgeLength. */
export const LINK_DISTANCE = 150;

/**
 * Defaults chosen to reproduce the layout the settle-only cose configuration
 * produced, so turning physics on does not rearrange a familiar graph:
 * cose ran nodeRepulsion 12_000, idealEdgeLength 150, gravity 0.3.
 */
export const DEFAULT_FORCES: ForceSettings = {
  centre: 0.35,
  repel: 0.5,
  linkForce: 0.35,
};

const clamp01 = (value: unknown, fallback: number): number =>
  typeof value === "number" && Number.isFinite(value) ? Math.min(1, Math.max(0, value)) : fallback;

export function readForceSettings(stored: unknown): ForceSettings {
  const source = (stored ?? {}) as Partial<Record<keyof ForceSettings, unknown>>;
  return {
    centre: clamp01(source.centre, DEFAULT_FORCES.centre),
    repel: clamp01(source.repel, DEFAULT_FORCES.repel),
    linkForce: clamp01(source.linkForce, DEFAULT_FORCES.linkForce),
  };
}

export type ForceParameters = {
  /** forceX/forceY strength. */
  centreStrength: number;
  /** forceManyBody strength - negative is repulsion. */
  chargeStrength: number;
  /** forceLink strength. */
  linkStrength: number;
  /** forceLink distance, in graph units. */
  linkDistance: number;
};

/**
 * Slider positions to simulation parameters.
 *
 * Repulsion is mapped on a CURVE rather than linearly: the interesting range
 * sits at the low end, and a linear map spends most of the slider's travel in
 * territory where everything is already flung apart. Squaring gives fine
 * control where the layout actually changes.
 *
 * Every range is bounded so no slider position can produce a simulation that
 * will not settle - the far ends are strong, not unstable.
 */
export function forceParameters(settings: ForceSettings): ForceParameters {
  return {
    // 0 lets the graph drift apart; the top end pulls it into a tight ball.
    centreStrength: 0.005 + settings.centre * 0.145,
    chargeStrength: -(60 + settings.repel * settings.repel * 1740),
    linkStrength: 0.02 + settings.linkForce * 0.78,
    linkDistance: LINK_DISTANCE,
  };
}
