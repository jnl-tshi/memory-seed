"use client";

import { useEffect, useRef, useState, type CSSProperties } from "react";

const clamp = (value: number) => Math.min(1, Math.max(0, value));
const reveal = (progress: number, start: number, end: number) => clamp((progress - start) / (end - start));

const communityNotes = {
  main: "The durable record: decisions, reasons, evidence, and the work that changed the project.",
  a: "A path back to the exact context needed to make the next decision with confidence.",
  b: "A bounded packet that lets an orchestrator or teammate continue work without re-investigation.",
  c: "An inspectable history that shows how one validated choice led to the next.",
} as const;
type CommunityId = keyof typeof communityNotes;

export function GrowthStory() {
  const sectionRef = useRef<HTMLElement>(null);
  const replayFrame = useRef<number | null>(null);
  const [progress, setProgress] = useState(0);
  const [motionReady, setMotionReady] = useState(false);
  const [reducedMotion, setReducedMotion] = useState(false);
  const [selectedCommunity, setSelectedCommunity] = useState<CommunityId | null>(null);

  useEffect(() => {
    const media = window.matchMedia("(prefers-reduced-motion: reduce)");
    const syncPreference = () => {
      setReducedMotion(media.matches);
      setMotionReady(!media.matches);
      if (media.matches) setProgress(1);
    };
    let frame: number | null = null;
    const updateProgress = () => {
      if (media.matches || !sectionRef.current) return;
      const bounds = sectionRef.current.getBoundingClientRect();
      const next = clamp((window.innerHeight - bounds.top) / (window.innerHeight + bounds.height));
      setProgress((current) => (Math.abs(current - next) > 0.012 ? next : current));
    };
    const onScroll = () => {
      if (frame === null) frame = window.requestAnimationFrame(() => {
        frame = null;
        updateProgress();
      });
    };

    syncPreference();
    updateProgress();
    window.addEventListener("scroll", onScroll, { passive: true });
    window.addEventListener("resize", onScroll);
    media.addEventListener("change", syncPreference);
    return () => {
      if (frame !== null) window.cancelAnimationFrame(frame);
      if (replayFrame.current !== null) window.cancelAnimationFrame(replayFrame.current);
      window.removeEventListener("scroll", onScroll);
      window.removeEventListener("resize", onScroll);
      media.removeEventListener("change", syncPreference);
    };
  }, []);

  const replay = () => {
    if (reducedMotion) return;
    if (replayFrame.current !== null) window.cancelAnimationFrame(replayFrame.current);
    const startedAt = window.performance.now();
    const tick = (now: number) => {
      const next = clamp((now - startedAt) / 2300);
      setProgress(next);
      if (next < 1) replayFrame.current = window.requestAnimationFrame(tick);
    };
    setProgress(0);
    replayFrame.current = window.requestAnimationFrame(tick);
  };

  const stepIndex = progress < 0.34 ? 0 : progress < 0.68 ? 1 : 2;
  const stemProgress = reveal(progress, 0.04, 0.35);
  const nodeOne = reveal(progress, 0.19, 0.4);
  const nodeTwo = reveal(progress, 0.36, 0.57);
  const nodeThree = reveal(progress, 0.53, 0.74);
  const communityProgress = reveal(progress, 0.63, 0.92);
  const visualStyle = { "--stem-progress": String(stemProgress) } as CSSProperties;
  const readout = selectedCommunity ? communityNotes[selectedCommunity] : [
    "Record what changed, why, and what evidence settled it.",
    "Keep each session connected to the branch and work that produced it.",
    "Related memories gather into visible neighbourhoods you can inspect and retrieve.",
  ][stepIndex];

  return (
    <section className="growth-story" ref={sectionRef} aria-labelledby="growth-title">
      <div className="shell growth-layout">
        <div className="growth-copy">
          <p className="section-kicker">From one decision to living context</p>
          <h2 id="growth-title">A seed becomes a trail. A trail becomes shared understanding.</h2>
          <p>Memory starts small: one decision, captured with its reason. Over time, validated relationships reveal how the project evolved—without turning the graph into the source of truth.</p>
          <ol className="growth-steps">
            <li className={stepIndex === 0 ? "is-active" : ""}><span>01</span><div><strong>Plant the decision</strong><p>Record what changed, why, and what evidence settled it.</p></div></li>
            <li className={stepIndex === 1 ? "is-active" : ""}><span>02</span><div><strong>Grow the Trail</strong><p>Keep each session connected to the branch and work that produced it.</p></div></li>
            <li className={stepIndex === 2 ? "is-active" : ""}><span>03</span><div><strong>See the community</strong><p>Related memories gather into visible neighbourhoods you can inspect and retrieve.</p></div></li>
          </ol>
          <div className="growth-controls">
            <button className="motion-trigger" type="button" onClick={replay} disabled={reducedMotion}>Replay the memory journey <span aria-hidden="true">↗</span></button>
            <p className="motion-readout" aria-live="polite"><span>{selectedCommunity ? "Memory connected" : `Stage 0${stepIndex + 1}`}</span>{readout}</p>
          </div>
        </div>
        <div className="growth-visual" data-motion-ready={motionReady || undefined} style={visualStyle} role="group" aria-label="An interactive seed growing into a decision trail and connected memory community">
          <div className="soil-line" />
          <div className="seed"><span /></div>
          <div className="stem" />
          <div className="trail-node node-one" style={{ opacity: nodeOne, transform: `translateY(${(1 - nodeOne) * 24}px)` }}><i /><span><small>Decision</small>Choose local Markdown</span></div>
          <div className="trail-node node-two" style={{ opacity: nodeTwo, transform: `translateY(${(1 - nodeTwo) * 24}px)` }}><i /><span><small>Evidence</small>Validate the contract</span></div>
          <div className="trail-node node-three" style={{ opacity: nodeThree, transform: `translateY(${(1 - nodeThree) * 24}px)` }}><i /><span><small>Handoff</small>Carry context forward</span></div>
          <div className="community" style={{ opacity: communityProgress, transform: `scale(${0.84 + communityProgress * 0.16})`, pointerEvents: communityProgress > 0.96 ? "auto" : "none" }}>
            <span className="community-link link-a" />
            <span className="community-link link-b" />
            <span className="community-link link-c" />
            <button className={`community-node community-main${selectedCommunity === "main" ? " is-selected" : ""}`} type="button" aria-pressed={selectedCommunity === "main"} onClick={() => setSelectedCommunity("main")}>project memory</button>
            <button className={`community-node community-a${selectedCommunity === "a" ? " is-selected" : ""}`} type="button" aria-pressed={selectedCommunity === "a"} onClick={() => setSelectedCommunity("a")}>retrieval</button>
            <button className={`community-node community-b${selectedCommunity === "b" ? " is-selected" : ""}`} type="button" aria-pressed={selectedCommunity === "b"} onClick={() => setSelectedCommunity("b")}>agent handoff</button>
            <button className={`community-node community-c${selectedCommunity === "c" ? " is-selected" : ""}`} type="button" aria-pressed={selectedCommunity === "c"} onClick={() => setSelectedCommunity("c")}>decision trail</button>
          </div>
        </div>
      </div>
    </section>
  );
}
