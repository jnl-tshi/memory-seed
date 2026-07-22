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
