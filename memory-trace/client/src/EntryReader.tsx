import { Fragment, useId, useState, type ReactNode } from "react";
import { ChevronRight } from "lucide-react";
import type { ChunkResponse } from "./api";

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
function renderMarkdown(text: string, highlight: string | null): ReactNode[] {
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
      // "Decision" is already the heading above; labelling it again is noise.
      if (draft !== "D") {
        out.push(<h5 key={key++} className={`draft-label draft-${draft.toLowerCase()}`}>{DRAFT_LABELS[draft]}</h5>);
      }
      if (!body) continue;
      if (draft === "F") {
        const files = fileTokens(body);
        out.push(files.length
          ? <div key={key++} className="file-pills">{files.map((file) => <span key={file} className="file-pill" title={file}>{file}</span>)}</div>
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
          out.push(<div key={key++} className="file-pills">{files.map((file) => <span key={file} className="file-pill" title={file}>{file}</span>)}</div>);
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

// DRAFT is the entry grammar: Decision, Reason, Alternatives, Files, Tests.
// Stored as terse "- D:" / "- R:" bullets, which is compact to author and
// unreadable to scan — so the reader spells them out. D carries no label of its
// own: the "Decision" heading above it already names it.
const DRAFT_LABELS: Record<string, string> = { D: "Decision", R: "Reason", A: "Alternatives", F: "Files", T: "Tests" };
const DRAFT_BULLET = /^-\s*([DRAFT]):\s*(.*)$/;

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

function lineRangeLabel(range: number[]): string {
  if (range.length === 2 && (range[0] || range[1])) return `:${range[0]}-${range[1]}`;
  return "";
}

export function EntryReader({
  chunk,
  matchHeading,
  onOpenEntry,
}: {
  chunk: ChunkResponse | null;
  matchHeading: string | null;
  onOpenEntry: (entryId: string) => void;
}) {
  if (!chunk) return <p className="reader-empty">Loading entry details</p>;

  const linkGroups: Array<[string, string[]]> = (
    [
      ["Related", chunk.related_entries ?? []],
      ["Backlinks", chunk.backlinks ?? []],
    ] as Array<[string, string[]]>
  ).filter(([, ids]) => ids.length > 0);

  const suggestionGroups: Array<[string, ChunkResponse["suggestions"][keyof ChunkResponse["suggestions"]]]> = (
    Object.entries(chunk.suggestions ?? {}) as Array<
      [string, ChunkResponse["suggestions"][keyof ChunkResponse["suggestions"]]]
    >
  ).filter(([, items]) => items.length > 0);

  const commit = chunk.commit;

  return (
    <div className="reader">
      {chunk.sections.length > 0 && (
        <div className="chip-list">
          {chunk.sections.map((section) => (
            <span key={section} className="chip">
              {section}
            </span>
          ))}
        </div>
      )}

      <div className="markdown">{renderMarkdown(chunk.text || chunk.excerpt || "", matchHeading)}</div>

      {(commit || chunk.path) && (
        <section className="detail-section">
          <h4>Evidence</h4>
          {commit && (
            <div className="commit-card">
              <code>{commit.short}</code>
              <span>{commit.subject}</span>
              <small className="count">{commit.date}</small>
            </div>
          )}
          {chunk.path && (
            <div className="count evidence-path">
              {chunk.path}
              {lineRangeLabel(chunk.line_range ?? [])}
            </div>
          )}
        </section>
      )}

      {linkGroups.length > 0 && (
        <section className="detail-section">
          <h4>Linked memories</h4>
          {linkGroups.map(([label, ids]) => (
            <div key={label} className="link-group">
              <div className="count">
                {label} · {ids.length}
              </div>
              {ids.map((id) => (
                <button key={id} type="button" className="link-card" onClick={() => onOpenEntry(id)}>
                  {id}
                </button>
              ))}
            </div>
          ))}
        </section>
      )}

      {suggestionGroups.length > 0 && (
        <section className="detail-section">
          <h4>Related activity</h4>
          {suggestionGroups.map(([label, items]) => (
            <div key={label} className="link-group">
              <div className="count">{label.replace(/_/g, " ")}</div>
              {items.map((item) => (
                <button
                  key={item.chunk_id}
                  type="button"
                  className="link-card"
                  disabled={!item.entry_id}
                  onClick={() => item.entry_id && onOpenEntry(item.entry_id)}
                >
                  <span>{item.title}</span>
                  <small className="count">{item.date}</small>
                </button>
              ))}
            </div>
          ))}
        </section>
      )}

      {chunk.diagrams.length > 0 && (
        <p className="reader-note">
          {chunk.diagrams.length} decision diagram{chunk.diagrams.length === 1 ? "" : "s"} — in-reader
          rendering lands in a later slice.
        </p>
      )}

      {!chunk.text && !linkGroups.length && !commit && (
        <Fragment>
          <p className="reader-empty">No further detail recorded for this entry.</p>
        </Fragment>
      )}
    </div>
  );
}
