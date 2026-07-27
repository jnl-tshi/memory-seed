"""Turn a cycle-4 swarm run's two blind passes into an agreement table and a split.

Companion to tally_swarm_area.py, which does the same job for the cycle-3 TSVs.
This one reads the Workflow result JSON directly, so a run can be re-analysed
without hand-editing anything.

Same rule as tally_swarm_area.py: quote the AGREED label. A count both workers
reached independently is evidence; a count one worker reached is a hypothesis.

Usage: python scripts/tally_area_swarm_json.py answers.json <mt|ms>
"""
import json
import sys
from collections import Counter, defaultdict

answers = json.load(open(sys.argv[1], encoding="utf-8"))["answers"]
pop = sys.argv[2]
w1 = answers[pop]["1"] if "1" in answers[pop] else answers[pop][1]
w2 = answers[pop]["2"] if "2" in answers[pop] else answers[pop][2]

ids = sorted(set(w1) & set(w2))
agreed = {i: w1[i] for i in ids if w1[i] == w2[i]}
print(f"population {pop}")
print(f"  judged by both : {len(ids)}   (w1 alone {len(set(w1) - set(w2))}, w2 alone {len(set(w2) - set(w1))})")
print(f"  agreement      : {len(agreed)}/{len(ids)} = {len(agreed) / max(1, len(ids)):.0%}")
print()

c1, c2 = Counter(w1[i] for i in ids), Counter(w2[i] for i in ids)
ca = Counter(agreed.values())
print(f"{'label':20} {'w1':>4} {'w2':>4} {'agreed':>7}")
for label, _n in sorted(c1.items(), key=lambda kv: -kv[1]):
    print(f"{label:20} {c1[label]:4} {c2[label]:4} {ca[label]:7}")
for label in sorted(set(c2) - set(c1)):
    print(f"{label:20} {0:4} {c2[label]:4} {ca[label]:7}")
print()

# Where they disagreed - the rows a human should look at.
print("DISAGREEMENTS:")
for i in ids:
    if w1[i] != w2[i]:
        print(f"  {i}  w1={w1[i]:16} w2={w2[i]}")
print()

NOT_A_CHILD = {"TRACE-WIDE", "NONE", "SEED-WIDE", "OTHER-ROOT"}
split = defaultdict(list)
for entry_id, label in agreed.items():
    if label not in NOT_A_CHILD:
        split[label].append(entry_id)
out = sys.argv[1].replace(".json", f"_{pop}_split.json")
json.dump(dict(split), open(out, "w"), indent=1)
print(f"wrote {out}")
for label, entries in sorted(split.items()):
    print(f"  {label:20} {len(entries):4}")
