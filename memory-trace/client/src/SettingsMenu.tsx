import { useEffect, useId, useRef, useState } from "react";
import { SlidersHorizontal } from "lucide-react";
import { prefersReducedMotion } from "./trailScroll";
import { DEFAULT_FORCES, type ForceSettings } from "./graphForces";

// One home for preferences that used to be scattered across three surfaces:
// dock buttons pinned inside the inspector, a Style menu in the Trail's view
// bar, and a theme icon in the top bar. Each was permanently on screen for a
// setting you change rarely.

export type TrailStyle = { thickness: "fine" | "thick"; style: "hand" | "slick"; wobble: number; pressure: number };
export type InspectorDock = "auto" | "right" | "bottom" | "hidden";
export type Theme = "light" | "dark";
/**
 * Graph motion and forces, per proposal §6.5 as amended 2026-07-22.
 *
 * `forces` are live: the simulation runs continuously, so moving a slider
 * retunes it in place rather than queueing a re-layout.
 */
export type GraphSettings = {
  dragResponse: "fixed" | "reheat";
  forces: ForceSettings;
  showOrphans: boolean;
};

const TABS = ["Trail", "Graph", "Inspector", "Appearance"] as const;
type Tab = (typeof TABS)[number];

export function SettingsMenu({
  trailStyle,
  onTrailStyle,
  graphSettings,
  onGraphSettings,
  dock,
  onDock,
  theme,
  onTheme,
}: {
  trailStyle: TrailStyle;
  onTrailStyle: (next: TrailStyle) => void;
  graphSettings: GraphSettings;
  onGraphSettings: (next: GraphSettings) => void;
  dock: InspectorDock;
  onDock: (next: InspectorDock) => void;
  theme: Theme;
  onTheme: (next: Theme) => void;
}) {
  const [open, setOpen] = useState(false);
  const [tab, setTab] = useState<Tab>("Trail");
  const container = useRef<HTMLDivElement>(null);
  const trigger = useRef<HTMLButtonElement>(null);
  const tabRefs = useRef<(HTMLButtonElement | null)[]>([]);
  const baseId = useId();

  // Dismiss on a click anywhere outside. Registered only while open, so the
  // closed menu costs nothing.
  useEffect(() => {
    if (!open) return;
    const onPointerDown = (event: PointerEvent) => {
      if (!container.current?.contains(event.target as Node)) setOpen(false);
    };
    document.addEventListener("pointerdown", onPointerDown);
    return () => document.removeEventListener("pointerdown", onPointerDown);
  }, [open]);

  // Focus the active tab on open so Escape and arrow keys have somewhere to
  // land; hand focus back to the trigger on close.
  useEffect(() => {
    if (open) tabRefs.current[TABS.indexOf(tab)]?.focus();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [open]);

  const close = () => {
    setOpen(false);
    trigger.current?.focus();
  };

  // Roving tabindex: only the selected tab is tabbable, arrows move between
  // them — the standard tablist pattern.
  const onTabKeyDown = (event: React.KeyboardEvent) => {
    const index = TABS.indexOf(tab);
    if (event.key !== "ArrowRight" && event.key !== "ArrowLeft") return;
    event.preventDefault();
    const next = (index + (event.key === "ArrowRight" ? 1 : -1) + TABS.length) % TABS.length;
    setTab(TABS[next]);
    tabRefs.current[next]?.focus();
  };

  const set = (patch: Partial<TrailStyle>) => onTrailStyle({ ...trailStyle, ...patch });
  const setGraph = (patch: Partial<GraphSettings>) => onGraphSettings({ ...graphSettings, ...patch });
  const setForce = (patch: Partial<ForceSettings>) => setGraph({ forces: { ...graphSettings.forces, ...patch } });
  const handDrawn = trailStyle.style === "hand";
  const reducedMotion = prefersReducedMotion();

  return (
    <div className="settings-menu" ref={container} onKeyDown={(event) => { if (event.key === "Escape") { event.stopPropagation(); close(); } }}>
      <button
        ref={trigger}
        className="icon-button"
        type="button"
        aria-expanded={open}
        aria-haspopup="dialog"
        aria-label="Settings"
        title="Settings"
        onClick={() => setOpen((value) => !value)}
      >
        <SlidersHorizontal size={17} />
      </button>
      {open && (
        <div className="settings-popover" role="dialog" aria-label="Settings">
          <div className="settings-tabs" role="tablist" aria-label="Settings sections" onKeyDown={onTabKeyDown}>
            {TABS.map((name, index) => (
              <button
                key={name}
                ref={(element) => { tabRefs.current[index] = element; }}
                type="button"
                role="tab"
                id={`${baseId}-tab-${name}`}
                aria-selected={tab === name}
                aria-controls={`${baseId}-panel-${name}`}
                tabIndex={tab === name ? 0 : -1}
                onClick={() => setTab(name)}
              >
                {name}
              </button>
            ))}
          </div>

          <div className="settings-panel" role="tabpanel" id={`${baseId}-panel-${tab}`} aria-labelledby={`${baseId}-tab-${tab}`}>
            {tab === "Trail" && (
              <>
                <div className="trail-settings-row">
                  <span>Line</span>
                  <div className="segment-control">
                    <button type="button" aria-pressed={trailStyle.thickness === "fine"} onClick={() => set({ thickness: "fine" })}>Fine</button>
                    <button type="button" aria-pressed={trailStyle.thickness === "thick"} onClick={() => set({ thickness: "thick" })}>Thick</button>
                  </div>
                </div>
                <div className="trail-settings-row">
                  <span>Stroke style</span>
                  <div className="segment-control">
                    <button type="button" aria-pressed={handDrawn} onClick={() => set({ style: "hand" })}>Drawn</button>
                    <button type="button" aria-pressed={!handDrawn} onClick={() => set({ style: "slick" })}>Slick</button>
                  </div>
                </div>
                {/* Wobble and pressure only mean anything to a drawn stroke. */}
                {handDrawn && (
                  <>
                    <div className="trail-settings-row">
                      <span>Wobble <b>{trailStyle.wobble.toFixed(2)}</b></span>
                      <input type="range" min={0} max={3} step={0.05} value={trailStyle.wobble} aria-label="Wobble" onChange={(event) => set({ wobble: Number(event.target.value) })} />
                    </div>
                    <div className="trail-settings-row">
                      <span>Pressure <b>{trailStyle.pressure.toFixed(2)}</b></span>
                      <input type="range" min={0} max={1} step={0.05} value={trailStyle.pressure} aria-label="Pressure" onChange={(event) => set({ pressure: Number(event.target.value) })} />
                    </div>
                  </>
                )}
              </>
            )}

            {tab === "Graph" && (
              <>
                {/* The simulation runs continuously and comes to rest on its
                    own, so these are live: a slider retunes physics already in
                    flight. Under a reduced-motion preference the controls are
                    disabled rather than hidden, so the override is visible and
                    the stored preference is left untouched. */}
                {reducedMotion && (
                  <div className="settings-note">Following your system's reduced-motion preference.</div>
                )}
                <div className="trail-settings-row">
                  <span>Centre force <b>{graphSettings.forces.centre.toFixed(2)}</b></span>
                  <input type="range" min={0} max={1} step={0.01} value={graphSettings.forces.centre} aria-label="Centre force"
                    onChange={(event) => setForce({ centre: Number(event.target.value) })} />
                </div>
                <div className="trail-settings-row">
                  <span>Repel force <b>{graphSettings.forces.repel.toFixed(2)}</b></span>
                  <input type="range" min={0} max={1} step={0.01} value={graphSettings.forces.repel} aria-label="Repel force"
                    onChange={(event) => setForce({ repel: Number(event.target.value) })} />
                </div>
                <div className="trail-settings-row">
                  <span>Link force <b>{graphSettings.forces.linkForce.toFixed(2)}</b></span>
                  <input type="range" min={0} max={1} step={0.01} value={graphSettings.forces.linkForce} aria-label="Link force"
                    onChange={(event) => setForce({ linkForce: Number(event.target.value) })} />
                </div>
                <div className="trail-settings-row">
                  <span>Link distance <b>{graphSettings.forces.linkDistance.toFixed(2)}</b></span>
                  <input type="range" min={0} max={1} step={0.01} value={graphSettings.forces.linkDistance} aria-label="Link distance"
                    onChange={(event) => setForce({ linkDistance: Number(event.target.value) })} />
                </div>
                <div className="trail-settings-row">
                  <span>Drag response</span>
                  <div className="segment-control">
                    <button type="button" disabled={reducedMotion} aria-pressed={graphSettings.dragResponse === "fixed"} onClick={() => setGraph({ dragResponse: "fixed" })}>Fixed</button>
                    <button type="button" disabled={reducedMotion} aria-pressed={graphSettings.dragResponse === "reheat"} onClick={() => setGraph({ dragResponse: "reheat" })}>Reheat on drag</button>
                  </div>
                </div>
                {graphSettings.dragResponse === "reheat" && !reducedMotion && (
                  <div className="settings-note">Dragging a node pulls its neighbours, then everything settles.</div>
                )}
                <button type="button" className="settings-reset" onClick={() => setGraph({ forces: DEFAULT_FORCES })}>Reset forces</button>
              </>
            )}

            {tab === "Inspector" && (
              <div className="trail-settings-row">
                <span>Dock position</span>
                <div className="segment-control">
                  {(["auto", "right", "bottom"] as const).map((option) => (
                    <button key={option} type="button" aria-pressed={dock === option} onClick={() => onDock(option)}>{option}</button>
                  ))}
                </div>
              </div>
            )}

            {tab === "Appearance" && (
              <div className="trail-settings-row">
                <span>Theme</span>
                <div className="segment-control">
                  <button type="button" aria-pressed={theme === "light"} onClick={() => onTheme("light")}>Light</button>
                  <button type="button" aria-pressed={theme === "dark"} onClick={() => onTheme("dark")}>Dark</button>
                </div>
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  );
}
