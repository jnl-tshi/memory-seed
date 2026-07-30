export function GrowthStory() {
  return (
    <section className="growth-story" aria-labelledby="growth-title">
      <div className="shell growth-layout">
        <div className="growth-copy">
          <p className="section-kicker">From one decision to living context</p>
          <h2 id="growth-title">A seed becomes a trail. A trail becomes shared understanding.</h2>
          <p>Memory starts small: one decision, captured with its reason. Over time, validated relationships reveal how the project evolved—without turning the graph into the source of truth.</p>
          <ol>
            <li><span>01</span><div><strong>Plant the decision</strong><p>Record what changed, why, and what evidence settled it.</p></div></li>
            <li><span>02</span><div><strong>Grow the Trail</strong><p>Keep each session connected to the branch and work that produced it.</p></div></li>
            <li><span>03</span><div><strong>See the community</strong><p>Related memories gather into visible neighbourhoods you can inspect and retrieve.</p></div></li>
          </ol>
        </div>
        <div className="growth-visual" aria-label="A seed growing into a decision trail and connected memory community">
          <div className="soil-line" />
          <div className="seed"><span /></div>
          <div className="stem" />
          <div className="trail-node node-one"><i /><span><small>Decision</small>Choose local Markdown</span></div>
          <div className="trail-node node-two"><i /><span><small>Evidence</small>Validate the contract</span></div>
          <div className="trail-node node-three"><i /><span><small>Handoff</small>Carry context forward</span></div>
          <div className="community">
            <span className="community-link link-a" />
            <span className="community-link link-b" />
            <span className="community-link link-c" />
            <b className="community-node community-main">project memory</b>
            <b className="community-node community-a">retrieval</b>
            <b className="community-node community-b">agent handoff</b>
            <b className="community-node community-c">decision trail</b>
          </div>
        </div>
      </div>
    </section>
  );
}
