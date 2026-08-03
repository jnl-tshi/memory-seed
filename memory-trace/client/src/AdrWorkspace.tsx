import { useEffect, useMemo, useState } from "react";
import { CheckCircle2, GitMerge, Search } from "lucide-react";
import { adrQuery, adrsQuery, type AdrEvent, type AdrRecord } from "./api";

type Props = {
  scopeKey: string;
  onOpenDecision: (decisionRef: string, excerpt: string) => void;
};

function eventLabel(event: AdrEvent) {
  return event.kind.replace(/-/g, " ");
}

function DecisionLink({ decisionRef, excerpts, onOpen }: { decisionRef: string; excerpts: Record<string, string>; onOpen: Props["onOpenDecision"] }) {
  return <button type="button" className="adr-ref" onClick={() => onOpen(decisionRef, excerpts[decisionRef] ?? "")}>{decisionRef}</button>;
}

export function AdrWorkspace({ scopeKey, onOpenDecision }: Props) {
  const [records, setRecords] = useState<AdrRecord[]>([]);
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [selected, setSelected] = useState<AdrRecord | null>(null);
  const [query, setQuery] = useState("");
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let live = true;
    setError(null);
    void adrsQuery().then(({ adrs }) => {
      if (!live) return;
      setRecords(adrs);
      setSelectedId((current) => current && adrs.some((item) => item.adr_id === current) ? current : adrs[0]?.adr_id ?? null);
    }).catch((reason) => live && setError(reason instanceof Error ? reason.message : "Unable to load ADRs."));
    return () => { live = false; };
  }, [scopeKey]);

  useEffect(() => {
    let live = true;
    if (!selectedId) { setSelected(null); return; }
    void adrQuery(selectedId).then((record) => live && setSelected(record)).catch((reason) => live && setError(reason instanceof Error ? reason.message : "Unable to load ADR."));
    return () => { live = false; };
  }, [selectedId, scopeKey]);

  const filtered = useMemo(() => {
    const needle = query.trim().toLowerCase();
    if (!needle) return records;
    return records.filter((record) => [record.adr_id, record.title, record.current.decision, record.current.why, ...record.topics].join(" ").toLowerCase().includes(needle));
  }, [query, records]);

  if (error) return <div className="error-state" role="alert">{error}</div>;
  if (!records.length) return <div className="adr-empty"><h2>No architectural decisions yet</h2><p>Promote a session decision with <code>memory-seed adr promote</code> to start the living ADR corpus.</p></div>;

  return <div className="adr-workspace">
    <aside className="adr-index" aria-label="Architectural concerns">
      <label className="adr-search"><Search size={14} aria-hidden="true" /><span className="sr-only">Search ADRs</span><input value={query} onChange={(event) => setQuery(event.target.value)} placeholder="Search concerns" /></label>
      <div className="adr-index-list">{filtered.map((record) => <button type="button" key={record.adr_id} className={record.adr_id === selectedId ? "adr-index-item active" : "adr-index-item"} onClick={() => setSelectedId(record.adr_id)} aria-pressed={record.adr_id === selectedId}>
        <span>{record.title}</span><small>{record.current_status} · {record.authoritative_decision ?? "no accepted head"}</small>
      </button>)}</div>
    </aside>
    <section className="adr-detail" aria-live="polite">
      {!selected ? <div className="loading-state">Loading ADR</div> : <>
        <header className="adr-current">
          <div className="adr-current-heading"><div><span className="eyebrow">{selected.adr_id}</span><h2>{selected.title}</h2></div><span className={`adr-status ${selected.current_status}`}>{selected.current_status}</span></div>
          <div className="adr-authority"><CheckCircle2 size={17} aria-hidden="true" /><span>Authoritative</span>{selected.authoritative_decision ? <DecisionLink decisionRef={selected.authoritative_decision} excerpts={selected.source_excerpts} onOpen={onOpenDecision} /> : <b>Not yet accepted</b>}</div>
          <h3>Decision</h3><p>{selected.current.decision || "Not recorded."}</p>
          <h3>Why</h3><p>{selected.current.why || "Not recorded."}</p>
          <h3>How it evolved</h3><p>{selected.current.evolution || "No evolution recorded."}</p>
          {!!selected.topics.length && <div className="adr-topics">{selected.topics.map((topic) => <span key={topic}>{topic}</span>)}</div>}
        </header>
        {!!selected.pending_decisions.length && <section className="adr-pending"><h3>Pending proposals</h3>{selected.pending_decisions.map((ref) => <DecisionLink key={ref} decisionRef={ref} excerpts={selected.source_excerpts} onOpen={onOpenDecision} />)}</section>}
        <section className="adr-ledger"><h3><GitMerge size={16} aria-hidden="true" /> Evolution ledger</h3>{selected.events.map((event) => event.kind === "reviewed-no-change" ? <details className="adr-event adr-event-muted" key={event.event_id}><summary>{eventLabel(event)} · {event.timestamp}</summary><p>{event.reason}</p></details> : <article className={`adr-event ${event.decision_ref === selected.authoritative_decision && event.kind === "revision-proposed" ? "authoritative" : ""}`} key={event.event_id}>
          <div className="adr-event-head"><span>{eventLabel(event)}</span><time>{event.timestamp}</time></div>
          {event.decision_ref && <DecisionLink decisionRef={event.decision_ref} excerpts={selected.source_excerpts} onOpen={onOpenDecision} />}
          {!!event.predecessors.length && <div className="adr-predecessors"><span>From</span>{event.predecessors.map((item) => <DecisionLink key={item.decision} decisionRef={item.decision} excerpts={selected.source_excerpts} onOpen={onOpenDecision} />)}</div>}
          {event.decision && <p>{event.decision}</p>}{event.reason && <p>{event.reason}</p>}
        </article>)}</section>
      </>}
    </section>
  </div>;
}
