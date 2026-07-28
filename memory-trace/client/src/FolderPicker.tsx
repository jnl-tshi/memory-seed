import { useCallback, useEffect, useRef, useState } from "react";
import { ArrowUp, Folder, FolderCheck, Loader2, X } from "lucide-react";
import { browseQuery, openProject, type DirectoryEntry } from "./api";

// Modal folder browser: walks the SERVER's filesystem (not this browser tab's)
// to find and open a project. Modelled on DiagramViewer's backdrop/Escape/
// outside-click pattern rather than a new one.
//
// Browsing and opening are deliberately two different requests, not one: a
// listed subfolder only carries a CHEAP "has a .memory-seed/ directory"
// check (see graphCrossings.ts's sibling reasoning for why - a full check on
// every row of a listing would be the kind of per-render cost this file's
// neighbours are careful to avoid), so "has one" is a hint to try, never a
// promise it opens. The real gate is the doctor() check the open action runs
// server-side; a hinted folder can still come back refused, and refusal shows
// the actual reasons rather than just failing silently.
export function FolderPicker({ onClose, onOpened }: { onClose: () => void; onOpened: (path: string) => void | Promise<void> }) {
  const [path, setPath] = useState<string | null>(null);
  const [parent, setParent] = useState<string | null>(null);
  const [entries, setEntries] = useState<DirectoryEntry[]>([]);
  const [loading, setLoading] = useState(true);
  const [browseError, setBrowseError] = useState<string | null>(null);
  const [opening, setOpening] = useState(false);
  const [openIssues, setOpenIssues] = useState<string[] | null>(null);
  // Guards a stale browse response from clobbering a faster, later one - the
  // same request-token pattern App.tsx's loadGraph uses.
  const request = useRef(0);

  const browse = useCallback(async (target: string | null) => {
    const current = ++request.current;
    setLoading(true);
    setBrowseError(null);
    try {
      const result = await browseQuery(target);
      if (current !== request.current) return;
      setPath(result.path);
      setParent(result.parent);
      setEntries(result.entries);
    } catch (reason) {
      if (current !== request.current) return;
      setBrowseError(reason instanceof Error ? reason.message : "Unable to read that folder.");
    } finally {
      if (current === request.current) setLoading(false);
    }
  }, []);

  useEffect(() => {
    void browse(null);
  }, [browse]);

  useEffect(() => {
    const onKey = (event: KeyboardEvent) => {
      if (event.key === "Escape") {
        event.stopPropagation();
        onClose();
      }
    };
    document.addEventListener("keydown", onKey, true);
    return () => document.removeEventListener("keydown", onKey, true);
  }, [onClose]);

  async function handleOpen(target: string) {
    setOpening(true);
    setOpenIssues(null);
    try {
      const result = await openProject(target);
      if (result.ok) {
        await onOpened(target);
        return;
      }
      setOpenIssues(result.issues?.length ? result.issues : ["Not a correctly initialised memory-seed project."]);
    } catch (reason) {
      setOpenIssues([reason instanceof Error ? reason.message : "Unable to open that folder."]);
    } finally {
      setOpening(false);
    }
  }

  return (
    <div className="folder-picker-backdrop" onMouseDown={(event) => { if (event.target === event.currentTarget) onClose(); }}>
      <div className="folder-picker" role="dialog" aria-modal="true" aria-label="Open folder">
        <div className="folder-picker-head">
          <span className="count">Open folder</span>
          <button type="button" className="folder-picker-close" onClick={onClose} aria-label="Close"><X size={16} /></button>
        </div>
        <div className="folder-picker-path">
          <button type="button" onClick={() => void browse(parent)} disabled={!parent || loading} aria-label="Up one level" title="Up one level">
            <ArrowUp size={14} />
          </button>
          <code>{path ?? "…"}</code>
        </div>
        <div className="folder-picker-body">
          {browseError && <div className="error-state">{browseError}</div>}
          {!browseError && loading && <div className="loading-state"><Loader2 size={14} className="spin" aria-hidden="true" /> Reading folder…</div>}
          {!browseError && !loading && entries.length === 0 && <div className="empty">No subfolders here.</div>}
          {!browseError && !loading && entries.map((entry) => (
            <div key={entry.path} className="folder-picker-row">
              <button type="button" className="folder-picker-entry" onClick={() => void browse(entry.path)}>
                {entry.has_memory_seed ? <FolderCheck size={15} className="folder-picker-marked" /> : <Folder size={15} />}
                <span>{entry.name}</span>
              </button>
              <button type="button" className="folder-picker-open-row" disabled={opening} onClick={() => void handleOpen(entry.path)}>
                Open
              </button>
            </div>
          ))}
        </div>
        {openIssues && (
          <div className="folder-picker-issues">
            <p>Can&rsquo;t open this folder:</p>
            <ul>{openIssues.map((issue) => <li key={issue}>{issue}</li>)}</ul>
          </div>
        )}
        <div className="folder-picker-foot">
          <button type="button" onClick={onClose}>Cancel</button>
          <button type="button" className="primary" disabled={!path || loading || opening} onClick={() => path && void handleOpen(path)}>
            {opening ? <Loader2 size={14} className="spin" aria-hidden="true" /> : null} Open this folder
          </button>
        </div>
      </div>
    </div>
  );
}
