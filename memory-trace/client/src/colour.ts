// Perceptual colour maths, used for two things the graph needs and CSS cannot
// give us: measuring that two community colours are actually distinguishable,
// and fading a colour toward a background by a perceptually even amount.
//
// OKLab rather than sRGB or HSL. Distance in sRGB is close to meaningless -
// two blues 0.04 apart in sRGB can be indistinguishable while a blue and a
// yellow the same distance apart are obvious. OKLab is near-uniform, so a
// single minimum-distance threshold means the same thing across the wheel.

export type Oklab = readonly [number, number, number];

function channelToLinear(channel: number): number {
  return channel <= 0.04045 ? channel / 12.92 : ((channel + 0.055) / 1.055) ** 2.4;
}

function linearToChannel(value: number): number {
  return value <= 0.0031308 ? 12.92 * value : 1.055 * value ** (1 / 2.4) - 0.055;
}

function hexToLinear(hex: string): [number, number, number] {
  const body = hex.replace("#", "");
  const parse = (index: number) => parseInt(body.slice(index, index + 2), 16) / 255;
  return [channelToLinear(parse(0)), channelToLinear(parse(2)), channelToLinear(parse(4))];
}

export function hexToOklab(hex: string): Oklab {
  const [r, g, b] = hexToLinear(hex);
  const l = Math.cbrt(0.4122214708 * r + 0.5363325363 * g + 0.0514459929 * b);
  const m = Math.cbrt(0.2119034982 * r + 0.6806995451 * g + 0.1073969566 * b);
  const s = Math.cbrt(0.0883024619 * r + 0.2817188376 * g + 0.6299787005 * b);
  return [
    0.2104542553 * l + 0.793617785 * m - 0.0040720468 * s,
    1.9779984951 * l - 2.428592205 * m + 0.4505937099 * s,
    0.0259040371 * l + 0.7827717662 * m - 0.808675766 * s,
  ];
}

/** Perceptual distance. Roughly: below ~0.05 two large fills read as the same colour. */
export function oklabDistance(left: string, right: string): number {
  const a = hexToOklab(left);
  const b = hexToOklab(right);
  return Math.hypot(a[0] - b[0], a[1] - b[1], a[2] - b[2]);
}

/** The smallest distance between any two colours in a set. */
export function minimumSeparation(colours: readonly string[]): number {
  let smallest = Infinity;
  for (let i = 0; i < colours.length; i += 1) {
    for (let j = i + 1; j < colours.length; j += 1) {
      smallest = Math.min(smallest, oklabDistance(colours[i], colours[j]));
    }
  }
  return colours.length < 2 ? 0 : smallest;
}

function toHex(linear: number): string {
  const clamped = Math.min(1, Math.max(0, linearToChannel(Math.min(1, Math.max(0, linear)))));
  return Math.round(clamped * 255).toString(16).padStart(2, "0");
}

/**
 * Blend two colours in LINEAR light, `amount` of the way from `from` to `to`.
 *
 * Mixing in gamma-encoded sRGB - the obvious `(a + b) / 2` on hex pairs - darkens
 * and muddies midpoints, which is exactly the range a fade lives in.
 */
export function mixHex(from: string, to: string, amount: number): string {
  const a = hexToLinear(from);
  const b = hexToLinear(to);
  const t = Math.min(1, Math.max(0, amount));
  return `#${a.map((channel, index) => toHex(channel + (b[index] - channel) * t)).join("")}`;
}

/**
 * Same hue, lifted toward light and desaturated: a true pastel.
 *
 * Moved here from trailModel so the Trail's decision rows and the graph's
 * inferred nodes are the SAME pastel rather than two independent takes on the
 * word. Deliberately NOT a blend toward the page background - that reads as
 * muddy on a dark theme, because it darkens rather than lightens.
 *
 * Hex -> HSL -> hex, kept framework- and DOM-free. HSL lightness is not
 * perceptually even across hues, so a yellow pastel reads lighter than a blue
 * one; matching the Trail exactly is worth more here than perfect uniformity.
 */
export function pastelOf(hex: string): string {
  const value = hex.replace("#", "");
  const r = parseInt(value.slice(0, 2), 16) / 255;
  const g = parseInt(value.slice(2, 4), 16) / 255;
  const b = parseInt(value.slice(4, 6), 16) / 255;
  const max = Math.max(r, g, b);
  const min = Math.min(r, g, b);
  const delta = max - min;
  let h = 0;
  if (delta > 0) {
    if (max === r) h = ((g - b) / delta + (g < b ? 6 : 0)) / 6;
    else if (max === g) h = ((b - r) / delta + 2) / 6;
    else h = ((r - g) / delta + 4) / 6;
  }
  const s = 0.42;
  const l = 0.74;
  const q = l < 0.5 ? l * (1 + s) : l + s - l * s;
  const p = 2 * l - q;
  const channel = (t: number) => {
    let x = t;
    if (x < 0) x += 1;
    if (x > 1) x -= 1;
    if (x < 1 / 6) return p + (q - p) * 6 * x;
    if (x < 1 / 2) return q;
    if (x < 2 / 3) return p + (q - p) * (2 / 3 - x) * 6;
    return p;
  };
  const channelHex = (t: number) => Math.round(channel(t) * 255).toString(16).padStart(2, "0");
  return `#${channelHex(h + 1 / 3)}${channelHex(h)}${channelHex(h - 1 / 3)}`;
}

/**
 * Weighted perceptual mean of several colours.
 *
 * Averaged in OKLab, not sRGB: mixing two hues in gamma-encoded space produces
 * a muddy, too-dark result that sits nowhere near the perceptual midpoint.
 *
 * Opposing hues cancel toward grey, and that is semantically right here - an
 * entry pulled equally by two unrelated communities SHOULD look undecided
 * rather than confidently like a third colour it has nothing to do with.
 */
export function blendOklab(weighted: readonly (readonly [string, number])[]): string {
  const total = weighted.reduce((sum, [, weight]) => sum + weight, 0);
  if (!weighted.length || total <= 0) return "#808080";
  const mean: [number, number, number] = [0, 0, 0];
  // Sorted so floating-point accumulation order cannot vary between renders.
  for (const [hex, weight] of [...weighted].sort((a, b) => a[0].localeCompare(b[0]))) {
    const lab = hexToOklab(hex);
    for (let i = 0; i < 3; i += 1) mean[i] += (lab[i] * weight) / total;
  }
  return oklabToHex(mean);
}

function oklabToHex(lab: Oklab): string {
  const [L, a, b] = lab;
  const l = (L + 0.3963377774 * a + 0.2158037573 * b) ** 3;
  const m = (L - 0.1055613458 * a - 0.0638541728 * b) ** 3;
  const s = (L - 0.0894841775 * a - 1.291485548 * b) ** 3;
  const rgb = [
    4.0767416621 * l - 3.3077115913 * m + 0.2309699292 * s,
    -1.2684380046 * l + 2.6097574011 * m - 0.3413193965 * s,
    -0.0041960863 * l - 0.7034186147 * m + 1.707614701 * s,
  ];
  return `#${rgb.map(toHex).join("")}`;
}

/**
 * Shift a colour's perceptual lightness, holding hue and chroma.
 *
 * Used to extend the fixed palette when a corpus grows more communities than it
 * has base colours: the same hue at a clearly different lightness is a distinct
 * colour, which keeps assignment collision-free without inventing new hues that
 * would crowd the ones already measured as well separated.
 */
export function shiftLightness(hex: string, delta: number): string {
  const [L, a, b] = hexToOklab(hex);
  return oklabToHex([Math.min(0.97, Math.max(0.12, L + delta)), a, b]);
}
