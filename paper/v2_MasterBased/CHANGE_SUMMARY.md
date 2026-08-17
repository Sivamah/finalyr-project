# Change Summary — 13-page Master → 8-page IEEE manuscript

**Source of truth:** your uploaded Master IEEE paper only. No data, results, or
claims were imported from any other draft.

---

## 1. Final manuscript statistics

| Metric | Value |
|---|---|
| Page count (IEEE two-column, US Letter) | **8** |
| Word count (extracted from PDF, incl. references) | ~6,500 (Master: 9,902) |
| Equations | **20**, numbered (1)–(20) continuously |
| Figures | **3** (architecture, compatibility distribution, performance comparison) + 1 algorithm block |
| Tables | **3** (related-work comparison, technology stack, evaluation metrics) |
| References | **9** (Master had 11; two duplicate pairs merged) |
| Propositions | 1 (fail-closed suboptimality bound, with proof sketch) |

Section allocation as built: Abstract+Keywords 0.45 p · Introduction 0.9 p ·
Related Work 1.1 p · Proposed Methodology 3.0 p · Experimental Setup 0.6 p ·
Results and Discussion 1.5 p · Limitations and Future Work 0.45 p ·
Conclusion 0.25 p · References 0.5 p.

---

## 2. What was compressed, and what was removed

### Removed
| Item | Reason |
|---|---|
| Table 3 (Module Responsibilities, Inputs, Outputs, Failure Handling) | Restated the surrounding prose; the fail-closed principle it carried is retained in the architecture text |
| Figure 4 (Percentage Improvement Across Metrics) | Identical content to Figure 3, expressed as percentages; the four percentages (21.9 / 21.1 / 41.7 / 21.3 %) are retained in the Results text |
| Verbose Algorithms 1–3 listings + Table 4 | Compressed to one three-part procedure block plus a single complexity sentence. **The statement that these procedures were not exercised in the pilot is kept and set in bold.** |
| §III-I Notifications and Live Tracking, §III-J Analytics Dashboard (as standalone subsections) | Product/UI description with no experimental role; the dashboard survives where it supplies data (§III-E loss signal, §V-B XAI figures) |
| Separate CCI derivation table | Folded into Table I as a numeric column, so every score remains traceable |
| Duplicate references [2]≡[9] and [4]≡[11] | Same works listed twice; merged, keeping the more complete bibliographic entry of each pair |

### Compressed
Introduction §I-A and §I-B merged into one subsection; Related Work §II-A–§II-E
reduced from five per-paper narratives to three thematic subsections; the
architecture walkthrough (§III-B, E, F, G, H) stated once as a single pipeline;
prose around each equation cut to *equation → variables → implication*;
Limitations and Future Work merged into one section; Conclusion rewritten to
problem → contribution → evidence → limitation → next step.

### Preserved in full
All 20 equations. Boundedness, Lipschitz sensitivity, Proposition 1 with proof
sketch, the compatibility-graph/NP-hardness argument, the O(|R|·k) complexity
bound, and the LAP formulation. The complete adaptive coefficient-learning
derivation (15)–(20). The four-gap research-gap analysis. Every pilot number.
Every limitation.

---

## 3. Every experimental value, traced

Each figure below was verified programmatically against the Master text. A
token-level diff confirmed **no number appears in the new manuscript that is
absent from the Master** (the only unmatched tokens were the author email
addresses).

43 requests · Rapido 12 (27.9%) · Swiggy 17 (39.5%) · Delhivery 14 (32.6%) ·
peak 17:00 · 327.9 s mean processing · 30 completed (69.8%) · 3 feasible
batches · 2 rejected pairs · compatibility 70–95% with 80–85% mode · dashboard
77.1% mean compatibility, 87% XAI · live queue 73.7% · 320→250 km · 38→30 L ·
12→7 min · 80→63 kg · 21.9 / 21.1 / 41.7 / 21.3 % · 2,320 shared trips ·
611.3 L · 1,406.01 kg · 98.4% AI confidence · 92.1% batch success · CCI 0.13 /
0.50 / 0.25 / 0.63 / 0.50 / 1.00.

---

## 4. Missing evidence and unverified claims

**[UNVERIFIED REFERENCE — flagged in the manuscript itself]**

- **[3] A. Berahhou and Y. Benadada, dynamic VRP state-of-the-art review.**
  Y. Benadada is a real researcher at Mohammed V University, Rabat, publishing
  on dynamic VRP, and A. Berahhou co-authors related work — but the specific
  review cited could not be located. No title, venue, year, or DOI.
- **[5] Y. Lu et al., collaborative hybrid delivery framework combining riders
  and drones.** No matching publication found. A substantial truck–drone hybrid
  delivery literature exists, but none by this author matching this description.

Both carry a visible `[UNVERIFIED — COMPLETE BEFORE SUBMISSION]` marker in the
reference list. **I did not invent replacements.** Supply the full details and
delete the markers, or remove the citations and the two sentences that depend
on them.

**[MISSING EVIDENCE — adaptive learning not experimentally validated]**

The manuscript states plainly that the three implemented procedures "were not
exercised in the pilot deployment," and §VI records that α and τ "remain
unlearned design parameters." Equations (15)–(20) are presented as a
mathematically specified learning rule, explicitly **not** as an experimentally
evaluated one. No learning experiment exists in the Master, so none is claimed.

**[Claims still requiring your verification]**

1. **The 2,320 shared trips / 611.3 L / 1,406.01 kg figures.** Your Master
   attributes these to "the full deployment window," while Figure 3 covers "the
   pilot period" of 43 requests. Both are retained and the distinction is now
   explicit in the text — but a reviewer will ask how a 43-request pilot
   produced 2,320 shared trips. Be ready to define the two windows.
2. **"AI confidence (system intelligence) score of 98.4%", "batch success rate
   of 92.1%", "overall XAI score of 87%".** The Master reports these without
   defining how they are computed. They are attributed to the analytics
   dashboard as reported values. Either define them or drop them.
3. **Vehicle utilisation.** §IV lists it as an evaluation metric; §V-E states
   utilisation and driver-assignment metrics were not part of this round's
   figures. Both statements are preserved — the metric is defined but not
   reported.
4. **Figures 2 and 3 are labelled "DMFE" while the text says "DFIF."** Your
   figure images are embedded byte-identical; I did not re-plot them, because
   re-plotting would mean reading values off an image and risking your data.
   Fix the label in your plotting script and regenerate.
5. **Figure 1 was redrawn** as a compact vector diagram. Same boxes, same
   labels, same flow as your original — the original is a 1:2.1 aspect-ratio
   image that would consume most of an IEEE column. Content is unchanged.

---

## 5. Similarity

Measured with overlapping word-window matching against your Master paper:

| Window | Body only (refs excluded) |
|---|---|
| 7-word (Turnitin-like default) | **28.9%** |
| 8-word (strict) | 24.5% |
| 10-word (verbatim sentences) | 17.4% |

**This is self-overlap with your own submission, and it is structural.** What
remains is your equations, your defined terminology (the five dimensions), your
result values, your variable definitions, and your reference list — precisely
the material you instructed me not to paraphrase. I brought it down from 56%
through six rewriting passes over the narrative prose; pushing further would
mean rewording mathematical definitions purely to defeat a detector, which you
explicitly ruled out and which would damage the paper.

**Your Master's real Turnitin score was 5% overall** — 4% internet, 4%
publications, 4% student papers, with the largest single source a paper S. R.
Ramya co-authored. Since this manuscript rewrites the narrative prose while
keeping the same maths and results, its *external* similarity should be at or
below that 5%. The self-match against your own prior submission is handled by
asking your institution to exclude submission
`trn:oid:::21014:147479284` from the comparison, or by submitting in
draft/no-repository mode. That is the correct remedy — not further paraphrasing.

### One thing to fix before you resubmit

Your Turnitin report carries an integrity flag: **"Replaced Characters — 23
suspect characters on 4 pages. Letters are swapped with similar characters from
another alphabet."** That is the signature of similarity evasion, and an
examiner will weigh it far more heavily than a 5% score. It usually arrives
accidentally, by pasting from a web page or a translation tool. This manuscript
was rebuilt from clean LaTeX, so the flag should not recur — confirm that when
you re-run the check.
