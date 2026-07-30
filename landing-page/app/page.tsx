import type { Metadata } from "next";
import { GrowthStory } from "./growth-story";
import { InterestForm } from "./interest-form";

const _starterMetadata: Metadata = {
  title: "Memory Seed",
  description:
    "Your first version will appear here automatically when it’s ready.",
};

export const metadata: Metadata = {
  title: "Memory Seed — Project memory for people and agents",
  description: "Preserve the decisions, evidence, and agent handoffs that shape consequential projects.",
};

void _starterMetadata;

export default function Home() {
  return (
    <main>
      <header className="site-header shell">
        <a className="brand" href="#top" aria-label="Memory Seed home"><span className="brand-mark" aria-hidden="true">m/s</span><span>Memory Seed</span></a>
        <nav aria-label="Primary navigation"><a href="#why">Why it matters</a><a href="#handoffs">Agent handoffs</a><a href="#interest">Join the list</a></nav>
      </header>
      <section className="hero shell" id="top">
        <div><p className="eyebrow">Project memory for people and agents</p><h1>Your project remembers <em>what shaped it.</em></h1><p className="hero-deck">Memory Seed turns decisions, evidence, and handoffs into a durable local memory that engineering teams—and any consequential project—can inspect, carry forward, and trust.</p><div className="hero-actions"><a className="button button-primary" href="#interest">Join the early-access list</a><a className="text-link" href="#why">See the idea <span aria-hidden="true">↓</span></a></div><p className="microcopy">Local-first · Git-native · Vendor-neutral</p></div>
        <div className="memory-artefact" aria-label="Example project memory"><div className="artefact-topline"><span>Decision memory</span><span className="live-dot">captured</span></div><div className="artefact-entry"><div className="entry-date">17 Jul</div><div><p className="entry-label">Decision 04</p><h2>Keep project memory local and inspectable.</h2><p>The team rejected a hosted-only memory layer. Markdown remains the source of truth; every index is rebuildable.</p><div className="entry-tags"><span>rationale</span><span>evidence</span><span>2 alternatives</span></div></div></div><div className="artefact-thread"><span className="thread-line" aria-hidden="true" /><div><small>evolves</small><strong>Agent handoffs inherit the same evidence</strong></div></div></div>
      </section>
      <section className="problem-section" id="why"><div className="shell split-intro"><p className="section-kicker">The quiet project failure</p><div><h2>Work moves forward. The reasons fall behind.</h2><p>A ticket closes. A teammate leaves. An agent starts with a fresh context window. The final artefact survives, but the trade-offs, risks, and evidence that produced it become scattered across chats, meetings, commits, and memory.</p><p className="pull-quote">“When the why disappears, every handoff becomes a reinvention.”</p></div></div></section>
      <section className="outcomes shell"><div className="section-heading"><p className="section-kicker">A shared memory layer</p><h2>Continuity without the black box.</h2></div><div className="outcome-grid"><article><span>01</span><h3>Recover the reason, not just the result</h3><p>Keep decisions, rationale, rejected alternatives, evidence, and consequences connected to the work they shaped.</p></article><article><span>02</span><h3>Give every agent the right context</h3><p>Bound work with Task Packets, resolve only the evidence a worker needs, and return a traceable handoff for review.</p></article><article><span>03</span><h3>Make project history inspectable</h3><p>Read the same local Markdown memory through Git, search, a timeline, or Memory Trace—without another hidden source of truth.</p></article></div></section>
      <GrowthStory />
      <section className="handoff-section" id="handoffs"><div className="shell"><div className="section-heading handoff-heading"><p className="section-kicker">Built for agentic work</p><h2>A handoff should carry evidence, not hope.</h2><p>Memory Seed is developing a visible contract between orchestrators, workers, and reviewers—so tasks arrive bounded, context is reproducible, and validation returns with provenance.</p></div><div className="handoff-flow"><article><span className="flow-role">Orchestrator</span><h3>Task Packet</h3><p>Objective, scope, files, permissions, validation, and integration path.</p></article><span className="flow-arrow">→</span><article><span className="flow-role">Worker</span><h3>Evidence Pack</h3><p>Only the bounded, fingerprinted project memory needed for the work.</p></article><span className="flow-arrow">→</span><article><span className="flow-role">Reviewer</span><h3>Traceable return</h3><p>Changes, checks, decisions, and unresolved risk linked back into memory.</p></article></div><p className="roadmap-note">Task Packet and retrieval contracts are an active product direction. The durable Markdown and retrieval foundations already exist.</p></div></section>
      <section className="beyond shell"><div><p className="section-kicker">Engineering first, not engineering only</p><h2>Any project with consequential decisions has a memory problem.</h2><p>The first workflows are designed around software teams and coding agents. The underlying need is broader: preserve the decisions that constrain tomorrow’s work, wherever complex projects happen.</p></div><ul>{["Software delivery", "Product strategy", "Research programmes", "Policy and operations", "Creative production", "Complex client work"].map((type) => <li key={type}><span aria-hidden="true">◆</span>{type}</li>)}</ul></section>
      <section className="principles"><div className="shell principles-inner"><p className="section-kicker">The Memory Seed promise</p><div className="principle-list"><p><strong>Your files.</strong> Plain Markdown stays readable without Memory Seed.</p><p><strong>Your history.</strong> Git makes memory diffable, reviewable, and repairable.</p><p><strong>Your choice of agent.</strong> One memory can serve multiple file-reading tools.</p><p><strong>No silent authority.</strong> Generated views remain projections over inspectable evidence.</p></div></div></section>
      <section className="interest shell" id="interest"><div className="interest-copy"><p className="section-kicker">Follow the build</p><h2>Help shape project memory that survives the handoff.</h2><p>Join the early-access list for occasional product updates, research invitations, and opportunities to try Memory Seed with your team.</p><p className="frequency">No weekly content machine. Only meaningful progress.</p></div><InterestForm /></section>
      <footer><div className="shell footer-inner"><div><a className="brand footer-brand" href="#top"><span className="brand-mark" aria-hidden="true">m/s</span><span>Memory Seed</span></a><p>Durable project memory for people and agents.</p></div><div className="footer-links"><a href="/privacy">Privacy</a><a href="mailto:jnltshibuyi@gmail.com">Contact</a></div><p className="copyright">© {new Date().getFullYear()} Jean Nathan Tshibuyi</p></div></footer>
    </main>
  );
}
