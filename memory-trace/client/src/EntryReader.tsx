import { Fragment, type ReactNode } from "react";
import type { ChunkResponse } from "./api";

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
  let inMatch = false;
  let key = 0;
  for (const line of lines) {
    if (line.trim().startsWith("```")) {
      if (inCode) {
        out.push(
          <pre key={key++} className={inMatch ? "match-highlight-body" : undefined}>
            <code>{code.join("\n")}</code>
          </pre>,
        );
        code = [];
      }
      inCode = !inCode;
      continue;
    }
    if (inCode) {
      code.push(line);
      continue;
    }
    const heading = line.match(/^(#{3,6})\s+(.+)/);
    if (heading) {
      inMatch = highlight != null && heading[2].trim() === highlight;
      out.push(
        <h4 key={key++} className={inMatch ? "match-highlight" : undefined}>
          {heading[2]}
        </h4>,
      );
    } else if (line.trim().startsWith("- ")) {
      out.push(
        <p key={key++} className={inMatch ? "match-highlight-body" : undefined}>
          {"• "}
          {inline(line.trim().slice(2))}
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
