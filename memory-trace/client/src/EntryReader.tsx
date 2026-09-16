import { Fragment, useEffect, useId, useRef, useState, type ReactNode } from "react";
import { ChevronRight } from "lucide-react";
import type { ChunkResponse } from "./api";
import { DiagramView } from "./DiagramView";
import type { TraceLook } from "./mermaidConfig";
import { decisionSections, entrySections, evidenceAnchor, selectedDecision } from "./decisionReaderModel";

// ChunkResponse.diagrams is typed as a generic record array in the OpenAPI
// contract (the backend's sidecar dict has no schema of its own); this is the
// runtime shape memory_seed.retrieval actually produces.
// Exported because App opens the same sidecars in the modal viewer from the
// Trail badge; a second local copy of the shape is how the two drift.
export interface DiagramSidecar {
  title?: string | null;
  mermaid_blocks?: string[];
}

export type ReaderRelationship = {
  kind: "replaces" | "evolves" | "related";
  entryId: string;
  title: string;
  outgoing: boolean;
};

// Every entry body opens with a fenced YAML metadata block. Most of it is
// either shown in the inspector's metadata grid or rarely needed, so it is
// folded away by default rather than sitting at the top of every entry.
function CollapsibleMeta({ yaml }: { yaml: string }) {
  const [open, setOpen] = useState(false);
  const panelId = useId();
  const fieldCount = yaml.split("\n").filter((line) => /^[\w-]+:/.test(line)).length;
  return (
    <div className="meta-fold">
      <button type="button" className="meta-fold-toggle" aria-expanded={open} aria-controls={panelId} onClick={() => setOpen((value) => !value)}>
        <ChevronRight size={13} aria-hidden="true" />
        <span>Entry metadata</span>
        <span className="count">{fieldCount} field{fieldCount === 1 ? "" : "s"}</span>
      </button>
      <div className="meta-fold-panel" id={panelId} data-open={open}>
        <div className="meta-fold-inner">
          <pre><code>{yaml}</code></pre>
        </div>
      </div>
    </div>
  );
}

// Source entries are hard-wrapped at an authoring column (~100 chars) but the
// reader pane is narrower and its width varies. Rejoin continuation lines back
// into their logical block so paragraphs and bullets reflow to the pane; fenced
// code is preserved verbatim. Ported from the vanilla reader's unwrapLines.
function unwrapLines(lines: string[]): string[] {
  const out: string[] = [];
  let inCode = false;
  for (const line of lines) {
    if (line.trim().startsWith("```")) {
      inCode = !inCode;
      out.push(line);
      continue;
    }
    if (inCode) {
      out.push(line);
      continue;
    }
    const trimmed = line.trim();
    const startsBlock =
      !trimmed
      || /^#{1,6}\s/.test(trimmed)
      || trimmed.startsWith("- ")
      || trimmed.startsWith("* ")
      || /^\d+\.\s/.test(trimmed)
      || trimmed.startsWith(">")
      || trimmed.startsWith("|");
    const prev = out.length ? out[out.length - 1] : "";
    const prevTrimmed = prev.trim();
    const prevJoinable =
      Boolean(prevTrimmed)
      && !prevTrimmed.startsWith("```")
      && !/^#{1,6}\s/.test(prevTrimmed)
      && !prevTrimmed.startsWith("|");
    if (!startsBlock && prevJoinable) {
      out[out.length - 1] = `${prev.replace(/\s+$/, "")} ${trimmed}`;
    } else {
      out.push(line);
    }
  }
  return out;
}

// Inline `code` and **bold** spans. JSX escapes the text nodes, so entry
// content can never inject markup through the reader.
function inline(text: string): ReactNode[] {
  const nodes: ReactNode[] = [];
  const pattern = /`([^`]+)`|\*\*([^*]+)\*\*/g;
  let last = 0;
  let key = 0;
  let match: RegExpExecArray | null;
  while ((match = pattern.exec(text)) !== null) {
    if (match.index > last) nodes.push(text.slice(last, match.index));
    if (match[1] !== undefined) nodes.push(<code key={key++}>{match[1]}</code>);
    else nodes.push(<strong key={key++}>{match[2]}</strong>);
    last = pattern.lastIndex;
  }
  if (last < text.length) nodes.push(text.slice(last));
  return nodes;
}

// Purpose-built markdown-to-JSX renderer at parity with the vanilla reader:
// fenced code, h3-h6 headings, bullet and paragraph blocks, inline code/bold.
// When `highlight` names a heading, that subsection (its heading plus every
// block until the next heading) carries the match-highlight classes.
function renderMarkdown(text: string, highlight: string | null, onOpenFile: (path: string) => void): ReactNode[] {
  const lines = unwrapLines(text.split("\n"));
  const out: ReactNode[] = [];
  let inCode = false;
  let code: string[] = [];
  let fence = "";
  let inMatch = false;
  let key = 0;
  let draft: string | null = null;
  for (const line of lines) {
    if (line.trim().startsWith("```")) {
      if (inCode) {
        const body = code.join("\n");
        // The entry's own metadata block, not just any YAML: the writer emits
        // ```yaml (core.py accepts ya?ml) and entry_id is always present.
        const isMetadata = /^ya?ml$/i.test(fence) && /(^|\n)entry_id:/.test(body);
        out.push(
          isMetadata
            ? <CollapsibleMeta key={key++} yaml={body} />
            : <pre key={key++} className={inMatch ? "match-highlight-body" : undefined}><code>{body}</code></pre>,
        );
        code = [];
        fence = "";
        inCode = false;
      } else {
        fence = line.trim().match(/^```\s*([\w-]+)/)?.[1] ?? "";
        inCode = true;
      }
      continue;
    }
    if (inCode) {
      code.push(line);
      continue;
    }
    const heading = line.match(/^(#{3,6})\s+(.+)/);
    if (heading) {
      inMatch = highlight != null && heading[2].trim() === highlight;
      draft = null;
      out.push(
        <h4 key={key++} className={inMatch ? "match-highlight" : undefined}>
          {heading[2]}
        </h4>,
      );
      continue;
    }
    const draftBullet = line.trim().match(DRAFT_BULLET);
    if (draftBullet) {
      draft = draftBullet[1];
      const body = draftBullet[2].trim();
      out.push(<h5 key={key++} className={`draft-label draft-${draft.toLowerCase()}`}>{DRAFT_LABELS[draft]}</h5>);
      if (!body) continue;
      if (draft === "F") {
        const files = fileTokens(body);
        out.push(files.length
          ? <div key={key++} className="file-pills">{files.map((file) => <button key={file} type="button" className="file-pill" title={`Show the graph of entries that touched ${file}`} onClick={() => onOpenFile(file)}>{file}</button>)}</div>
          : <p key={key++} className="draft-body">{inline(body)}</p>);
      } else {
        out.push(<p key={key++} className={`draft-body${inMatch ? " match-highlight-body" : ""}`}>{inline(body)}</p>);
      }
      continue;
    }
    if (line.trim().startsWith("- ")) {
      const body = line.trim().slice(2);
      // Sub-bullets belong to the DRAFT block they sit under.
      if (draft === "F") {
        const files = fileTokens(body);
        if (files.length) {
          out.push(<div key={key++} className="file-pills">{files.map((file) => <button key={file} type="button" className="file-pill" title={`Show the graph of entries that touched ${file}`} onClick={() => onOpenFile(file)}>{file}</button>)}</div>);
          continue;
        }
      }
      out.push(
        <p key={key++} className={`${draft ? "draft-body " : ""}${inMatch ? "match-highlight-body" : ""}`.trim() || undefined}>
          {"• "}
          {inline(body)}
        </p>,
      );
    } else if (line.trim()) {
      out.push(
        <p key={key++} className={inMatch ? "match-highlight-body" : undefined}>
          {inline(line)}
        </p>,
      );
    }
  }
  return out;
}

// DRAFTS is the entry grammar: Decision, Reason, Alternatives, Files, Tests, Sources.
// Stored as terse "- D:" / "- R:" bullets, which is compact to author and
// unreadable to scan — so the reader spells every field out consistently.
const DRAFT_LABELS: Record<string, string> = { D: "Decision", R: "Reason", A: "Alternatives", F: "Files", T: "Tests", S: "Sources" };
const DRAFT_BULLET = /^-\s*([DRAFTS]):\s*(.*)$/;

/**
 * File references out of an F block. Entries write them as backticked paths,
 * usually comma-separated and sometimes annotated ("(new)"); fall back to
 * comma splitting so an unbackticked list still yields pills.
 */
function fileTokens(text: string): string[] {
  const backticked = [...text.matchAll(/`([^`]+)`/g)].map((match) => match[1].trim()).filter(Boolean);
  if (backticked.length) return backticked;
  return text
    .split(/,\s+/)
    .map((token) => token.trim().replace(/[.,;]$/, ""))
    .filter((token) => token.length > 1 && /[/\\]|\.\w{1,5}$/.test(token));
}

export function EntryReader({
  chunk,
  matchHeading,
  decisionHeading,
  relationships,
  evidenceOpen,
  onOpenEntry,
  onOpenDecision,
  onOpenFile,
  onOpenEvidence,
  onReturnEvidence,
  onOpenDiagram,
  look,
  theme,
}: {
  chunk: ChunkResponse | null;
  matchHeading: string | null;
  decisionHeading: string | null;
  relationships: ReaderRelationship[];
  evidenceOpen: boolean;
  onOpenEntry: (entryId: string) => void;
  onOpenDecision: (heading: string) => void;
  onOpenFile: (path: string) => void;
  onOpenEvidence: () => void;
  onReturnEvidence: () => void;
  onOpenDiagram: (title: string | null, source: string) => void;
  look: TraceLook;
  theme: string;
}) {
  const decisionWindow = useRef<HTMLDivElement>(null);
  const decisionNodes = useRef<Record<string, HTMLElement | null>>({});
  const decisionRegionId = useId();
  const markdown = chunk?.text || chunk?.excerpt || "";
  const sourceAnchor = evidenceAnchor(chunk?.path, chunk?.line_range);
  const decisions = decisionSections(markdown);
  const activeDecision = selectedDecision(decisions, decisionHeading);
  const sections = entrySections(markdown);
  const summarySections = sections.filter((section) => section.heading.toLowerCase() === "summary");
  const supportingSections = sections.filter((section) => section.heading.toLowerCase() !== "summary");

  useEffect(() => {
    const container = decisionWindow.current;
    const target = activeDecision ? decisionNodes.current[activeDecision.heading] : null;
    if (!container || !target) return;
    const reducedMotion = window.matchMedia?.("(prefers-reduced-motion: reduce)").matches ?? false;
    const top = target.getBoundingClientRect().top - container.getBoundingClientRect().top + container.scrollTop;
    container.scrollTo({ top: Math.max(0, top), behavior: reducedMotion ? "auto" : "smooth" });
  }, [activeDecision?.heading, chunk?.chunk_id]);

  if (!chunk) return <p className="reader-empty">Loading entry details</p>;

  // Evidence is an in-place reader mode rather than a route change. The App
  // keeps the selected `(entry_id, decision)` and the inspector scroll snapshot,
  // so Return restores the Trail context instead of re-running selection.
  if (evidenceOpen) {
    return (
      <div className="reader evidence-reader" data-reader-mode="evidence">
        <section className="detail-section evidence-source" aria-labelledby="evidence-source-title">
          <div className="reader-return-row">
            <button type="button" className="reader-return" onClick={onReturnEvidence} autoFocus>
              Return to decision
            </button>
          </div>
          <h4 id="evidence-source-title">Exact Markdown</h4>
          {sourceAnchor.available ? (
            <p className="evidence-path"><code>{sourceAnchor.label}</code></p>
          ) : (
            <p className="missing-source" role="status">{sourceAnchor.label}. No excerpt or generated replacement is shown.</p>
          )}
          {sourceAnchor.available && <pre className="raw-markdown"><code>{chunk.text || chunk.excerpt || "No source excerpt was returned."}</code></pre>}
        </section>
      </div>
    );
  }

  const suggestionGroups: Array<[string, ChunkResponse["suggestions"][keyof ChunkResponse["suggestions"]]]> = (
    Object.entries(chunk.suggestions ?? {}) as Array<
      [string, ChunkResponse["suggestions"][keyof ChunkResponse["suggestions"]]]
    >
  ).filter(([, items]) => items.length > 0);

  return (
    <div className="reader">
      {summarySections.length ? summarySections.map((section, index) => (
        <section className={`detail-section entry-segment${section.heading === matchHeading ? " reader-match-anchor" : ""}`} key={`${section.heading}-${index}`}>
          <h4>{section.heading}</h4>
          <div className="markdown">{renderMarkdown(section.text, null, onOpenFile)}</div>
        </section>
      )) : (
        <section className="detail-section entry-segment reader-legacy-summary">
          <h4>Summary</h4>
          <p className="reader-empty">No summary was recorded for this legacy entry.</p>
        </section>
      )}

      {decisions.length > 0 && (
        <section className="detail-section decisions-segment" aria-labelledby={`${decisionRegionId}-title`}>
          <div className="segment-heading">
            <h4 id={`${decisionRegionId}-title`}>Records</h4>
            <span className="count">{decisions.length}</span>
          </div>
          {decisions.length > 1 && (
            <nav className="decision-selector" aria-label="Decisions in this entry">
              {decisions.map((decision) => {
                const selected = decision.heading === activeDecision?.heading;
                return (
                  <button key={decision.heading} type="button" className="decision-selector-item" aria-current={selected ? "true" : undefined} aria-controls={decisionRegionId} onClick={() => onOpenDecision(decision.heading)}>
                    <span>{decision.ordinal?.toUpperCase() ?? "Decision"} · {decision.kind === "documentation" ? "Documentation" : "Decision"}</span>
                    <small>{decision.title}</small>
                  </button>
                );
              })}
            </nav>
          )}
          <div className="decision-window" id={decisionRegionId} ref={decisionWindow} tabIndex={0} aria-label="Decision details">
            {decisions.map((decision) => {
              const selected = decision.heading === activeDecision?.heading;
              const headingId = `${decisionRegionId}-${decision.ordinal ?? "decision"}`;
              return (
                <article
                  key={decision.heading}
                  ref={(node) => { decisionNodes.current[decision.heading] = node; }}
                  className={`decision-entry${selected ? " selected" : ""}${decision.heading === matchHeading ? " reader-match-anchor" : ""}`}
                  data-decision-reader={selected ? true : undefined}
                  tabIndex={selected ? -1 : undefined}
                  aria-labelledby={headingId}
                >
                  <header className="decision-entry-heading">
                    {decision.ordinal && <span className="decision-ordinal">{decision.ordinal.toUpperCase()} · {decision.kind === "documentation" ? "Documentation" : "Decision"}</span>}
                    <h3 id={headingId}>{decision.title}</h3>
                  </header>
                  {decision.text ? <div className="markdown decision-body">{renderMarkdown(decision.text, null, onOpenFile)}</div> : <p className="reader-empty">No decision body was recorded.</p>}
                </article>
              );
            })}
          </div>
        </section>
      )}

      {supportingSections.map((section, index) => (
        <section className={`detail-section entry-segment${section.heading === matchHeading ? " reader-match-anchor" : ""}`} key={`${section.heading}-${index}`}>
          <h4>{section.heading}</h4>
          <div className="markdown">{renderMarkdown(section.text, null, onOpenFile)}</div>
        </section>
      ))}

      {relationships.length > 0 && (
        <section className="detail-section reader-lifecycle">
          <h4>Related decisions</h4>
          {relationships.map((relationship) => (
            <button key={`${relationship.kind}-${relationship.entryId}`} type="button" className={`link-card relationship-${relationship.outgoing ? "out" : "in"}`} onClick={() => onOpenEntry(relationship.entryId)}>
              <span>{relationship.kind} {relationship.outgoing ? "→" : "←"} {relationship.title}</span>
            </button>
          ))}
        </section>
      )}

      <section className="detail-section">
        <h4>Source</h4>
        {sourceAnchor.available ? (
          <button type="button" className="evidence-link" onClick={onOpenEvidence}>
            <span>View exact Markdown</span>
            <small>{sourceAnchor.label}</small>
          </button>
        ) : (
          <p className="missing-source" role="status">{sourceAnchor.label}. This reader will not manufacture a summary.</p>
        )}
      </section>

      {suggestionGroups.length > 0 && (
        <details className="reader-disclosure">
          <summary>Related activity <span className="count">{suggestionGroups.reduce((total, [, items]) => total + items.length, 0)}</span></summary>
          <div className="reader-disclosure-content">
            {suggestionGroups.map(([label, items]) => (
              <div key={label} className="link-group">
                <div className="count">{label.replace(/_/g, " ")}</div>
                {items.map((item) => (
                  <button key={item.chunk_id} type="button" className="link-card" disabled={!item.entry_id} onClick={() => item.entry_id && onOpenEntry(item.entry_id)}>
                    <span>{item.title}</span>
                    <small className="count">{item.date}</small>
                  </button>
                ))}
              </div>
            ))}
          </div>
        </details>
      )}

      {chunk.diagrams.length > 0 && (
        <section className="detail-section">
          <h4>Decision diagrams <span className="count">· click to zoom</span></h4>
          {(chunk.diagrams as DiagramSidecar[]).flatMap((sidecar, sidecarIndex) =>
            (sidecar.mermaid_blocks ?? []).map((source, blockIndex) => (
              // Clickable, matching the vanilla reader: the inspector column
              // is narrower than most authored diagrams, so inline rendering
              // alone leaves them unreadable with no way to enlarge.
              <figure
                key={`${sidecarIndex}-${blockIndex}`}
                className="diagram diagram-openable"
                title="Click to inspect (zoom + pan)"
                role="button"
                tabIndex={0}
                onClick={() => onOpenDiagram(sidecar.title ?? null, source)}
                onKeyDown={(event) => {
                  if (event.key === "Enter" || event.key === " ") {
                    event.preventDefault();
                    onOpenDiagram(sidecar.title ?? null, source);
                  }
                }}
              >
                {sidecar.title && <figcaption className="count">{sidecar.title}</figcaption>}
                <DiagramView source={source} look={look} theme={theme} />
              </figure>
            )),
          )}
        </section>
      )}

      {!chunk.text && !activeDecision && (
        <Fragment>
          <p className="reader-empty">No further detail recorded for this entry.</p>
        </Fragment>
      )}
    </div>
  );
}
