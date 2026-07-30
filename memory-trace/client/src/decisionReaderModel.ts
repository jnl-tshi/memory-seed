/**
 * Reader-only interpretation of the decision grammar. This is deliberately a
 * projection of the Markdown entry: it does not create a second decision
 * store, nor does it accept a renderer-owned identifier.
 */
export type DecisionSection = {
  ordinal: string | null;
  heading: string;
  title: string;
  text: string;
};

const NUMBERED_DECISION = /^(#{3,6})\s+(?:decision\s*)?(d?\d+)\s*[-:]\s*(.+)$/i;
const SINGLE_DECISION = /^(#{3,6})\s+decision\s*$/i;

function normalise(value: string): string {
  return value.trim().replace(/^#+\s*/, "").replace(/\s+/g, " ").toLowerCase();
}

function draftDecisionTitle(text: string): string | null {
  const match = text.match(/^\s*-\s*D:\s*(.+)$/mi);
  return match?.[1].trim() || null;
}

/** Extract numbered decisions, or the ordinary single `### Decision` block. */
export function decisionSections(markdown: string): DecisionSection[] {
  const lines = markdown.replace(/\r\n/g, "\n").split("\n");
  const sections: Array<Omit<DecisionSection, "text"> & { start: number; level: number }> = [];
  let inFence = false;

  lines.forEach((line, index) => {
    if (line.trim().startsWith("```")) { inFence = !inFence; return; }
    if (inFence) return;
    const numbered = line.match(NUMBERED_DECISION);
    if (numbered) {
      sections.push({ ordinal: numbered[2].toLowerCase().startsWith("d") ? numbered[2].toLowerCase() : `d${numbered[2]}`, heading: line.replace(/^#+\s*/, "").trim(), title: numbered[3].trim(), start: index, level: numbered[1].length });
      return;
    }
    const single = line.match(SINGLE_DECISION);
    if (single) sections.push({ ordinal: null, heading: "Decision", title: "Recorded decision", start: index, level: single[1].length });
  });

  return sections.map((section, index) => {
    let end = lines.length;
    for (let cursor = section.start + 1; cursor < lines.length; cursor += 1) {
      const heading = lines[cursor].match(/^(#{1,6})\s+/);
      if (heading && heading[1].length <= section.level) { end = cursor; break; }
    }
    const text = lines.slice(section.start + 1, end).join("\n").trim();
    return { ...section, title: section.ordinal ? section.title : draftDecisionTitle(text) ?? section.title, text };
  });
}

/** The Trail label is authoritative when it names one numbered decision. */
export function selectedDecision(sections: DecisionSection[], heading: string | null): DecisionSection | null {
  if (!sections.length) return null;
  if (!heading) return sections[0];
  const wanted = normalise(heading);
  return sections.find((section) => normalise(section.heading) === wanted || normalise(section.title) === wanted) ?? sections[0];
}

export type EvidenceAnchor = { available: boolean; label: string; source: string | null };

/** Exact file + line data is evidence. If either is absent, say so plainly. */
export function evidenceAnchor(path: string | null | undefined, lineRange: number[] | null | undefined): EvidenceAnchor {
  if (!path) return { available: false, label: "Missing canonical source anchor", source: null };
  const [start, end] = lineRange ?? [];
  const location = start ? `:${start}${end && end !== start ? `-${end}` : ""}` : "";
  return { available: true, label: `Recorded source · ${path}${location}`, source: path };
}

/** Information state is an explicit grammar, not a colour choice. */
export function readerInformationState(authorityClass: string | null | undefined, provenanceClass: string | null | undefined): "Recorded" | "Derived" | "Suggested" {
  if (["provider_extracted", "provider_resolved", "provider_inferred", "generated"].includes(authorityClass ?? "")) return "Suggested";
  return provenanceClass === "source_control" ? "Derived" : "Recorded";
}

export type DecisionEdge = { source: string; target: string; type: string };
export type DecisionRelationship = { kind: "replaces" | "evolves" | "related"; entryId: string; otherId: string; outgoing: boolean };

/**
 * Keep a focused decision's lifecycle precise. An entry-level reader may use
 * its entry id; a decision reader must never widen a sibling decision's edge.
 */
export function relationshipsForDecision(edges: readonly DecisionEdge[], activeId: string, entryId: string): DecisionRelationship[] {
  const out: DecisionRelationship[] = [];
  const seen = new Set<string>();
  for (const edge of edges) {
    const outgoing = edge.source === activeId;
    const incoming = edge.target === activeId;
    if (!outgoing && !incoming) continue;
    if (edge.type !== "replaces" && edge.type !== "evolves" && edge.type !== "related") continue;
    const otherId = outgoing ? edge.target : edge.source;
    const otherEntryId = otherId.split("#")[0];
    if (otherEntryId === entryId && otherId === activeId) continue;
    const key = `${edge.type}:${otherId}:${outgoing ? "out" : "in"}`;
    if (seen.has(key)) continue;
    seen.add(key);
    out.push({ kind: edge.type, entryId: otherEntryId, otherId, outgoing });
  }
  return out;
}
