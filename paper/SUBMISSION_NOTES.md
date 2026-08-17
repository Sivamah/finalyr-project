# A-DMFE IEEE Conference Paper — Submission Notes

**Title:** AI-Powered Unified Mobility and Delivery System Using Dynamic Feasibility Analysis
*(your original title, restored)*

**Authors:** Sivasubramanian M (corresponding, sivamah25@gmail.com), Sadhana T, Rakshana S, S. R. Ramya

**Files**

| File | What it is |
|---|---|
| `A-DMFE_IEEE_8page.pdf` | 8 pages, IEEE two-column. **This is the submission version.** |
| `A-DMFE_IEEE_paper.docx` | Same content, single-column Word. For sharing, reading, editing. |
| `A-DMFE_IEEE_latex_source.zip` | `main.tex` + 3 figure PDFs, for Overleaf. |

---

## 1. Similarity — measured, not estimated

I cannot run Turnitin or iThenticate. What I *can* do is measure the paper
against the highest-risk source there is: **your own previous draft.** If that
draft is anywhere in a checker's database — your college portal, a supervisor's
prior check, a repository — it is what will flag.

I compared the final paper to your original 13-page PDF using overlapping
word-window matching, which is the same basic technique commercial checkers use.

| Match window | Body only | Including references |
|---|---|---|
| 6 words (loose) | 4.56% | 7.27% |
| **7 words (Turnitin-like default)** | **2.22%** | 5.09% |
| 8 words (strict) | 1.80% | 4.30% |
| 10 words (verbatim sentences) | 0.63% | 2.47% |

**Headline: 2.22% against your own prior draft, references excluded.**

The gap between the two columns is entirely the bibliography — paper titles,
author names, and journal names are identical by necessity, since they are the
same twelve sources. This is exactly why every checker offers a
"exclude bibliography" setting, and why you must switch it on.

Of the 148 matching words that remain in the body, nearly all are mathematical
notation extracted from the equations (`CS(i,j)`, `Cost(d,ρ)`, variable lists)
and the Proposition 1 statement. Those cannot be paraphrased without changing
the mathematics.

**Internal repetition check:** the only phrases repeating inside the paper are
the four author affiliation blocks, which is standard IEEE format. No padding,
no recycled paragraphs.

**Web check:** I searched several of the paper's most distinctive sentences and
the term "Dynamic Feasibility Intelligence Framework". No external matches.

### Settings to use when you run the check

1. **Exclude bibliography** — without this you will see ~5% instead of ~2%.
2. **Exclude quoted material.**
3. **Exclude matches below 1%** (sometimes "small matches" or "small sources").
4. **Ask for your own prior submission to be excluded from comparison**, or
   submit in draft / no-repository mode. This is the single most common cause of
   a surprise high score on genuinely original work.

### What will still match, and is fine

Reference list entries; standard technical collocations ("vehicle routing
problem", "time-window overlap", "mixed-integer linear program", "reinforcement
learning"); and equation notation. Every reviewer and every supervisor knows
this. A 2–4% score composed of these is a clean paper.

---

## 2. How to compile the LaTeX

`main.tex` targets the **official IEEEtran class**, which Overleaf provides.

1. New Overleaf project → upload `main.tex`, `fig_compat.pdf`,
   `fig_efficiency.pdf`, `fig_co2.pdf`.
2. Compiler: **pdfLaTeX**. Compile **twice** (cross-references need two passes).
3. Confirm it is still 8 pages.

The attached PDF was built offline against a close emulation of IEEEtran, since
the official class could not be downloaded in the build environment. Margins,
column widths, font sizes and section styles match. If Overleaf pushes it to 9
pages, delete the subsection "Revisiting the Research Gaps" in Section V — it is
summarised again in the Conclusion.

## 3. About the Word version

It is **single-column**, not IEEE two-column. That is deliberate: the results
tables have six columns, and in a 3.4-inch IEEE column Word crushes them until
they are unreadable. Single-column keeps every number visible.

Everything is fully portable — equations are embedded as images and all inline
mathematics is plain text, so it renders identically in Word, LibreOffice,
Google Docs, and on a phone. Nothing depends on Word's equation engine.

Use the **PDF** for submission and the **Word file** for sharing and comments.

---

## 4. What changed from your original draft

### Defects fixed

| Issue in original | Fix |
|---|---|
| References [2] and [9] were the same Zhang/Markos/Yu paper | Merged |
| References [4] and [11] were the same Chen et al. paper | Merged |
| References [3] and [5] had no venue, year, or DOI | [3] replaced with Pillac et al., *EJOR* 2013; [5] removed, citations redirected |
| References [7]–[11] never cited in the body | All 12 references now cited |
| V-A reported 43 requests / 3 batches; V-C reported 2,320 trips, 611.3 L fuel | Both removed; replaced with the seeded 50/100/250/500 experiment |
| "69.8% completion rate" | Removed — your code counts `Assigned`, so it was a dispatch rate |
| Delay reported as distinct from waiting time | `avg_delay_min` and `avg_waiting_min` are the identical expression in `evaluation/framework.py:527,550`. Reported once, as **waiting time** |
| "XAI score 87%", "AI confidence 98.4%", "batch success rate 92.1%" | Removed — undefined |
| Claimed compatibility scores sit "between 70% and 95%" | False. Measured mean 57, SD 14; ~60% fall **below** τ=70. Corrected and reframed |
| Table 2 before Table 1; Arabic numerals; inconsistent captions | Roman numerals, correct order, captions above tables / below figures |
| Orphan float page "8a" | Gone |
| Figure 1 unreadable | Redrawn as a vector diagram |
| Algorithms 1–3 + Table 4 (never exercised) | One consolidated Algorithm 1 |
| Notifications / dashboard / module-responsibility sections | Cut as product description |

### Evaluation replaced

The 43-request pilot is gone. The paper reports
`backend/evaluation/results/admfe_repetitions.json`: **36 runs**, four pool
sizes, 5 seeds each at N≤250 and 3 at N=500, 60-vehicle fleet — enabling a
**seed-matched paired ablation (n=18)**. Every number was recomputed from that
file and independently re-verified against it.

---

## 5. Three things the paper now admits

Each is verifiable from your own repo, so volunteering it is far safer than
being caught.

**a) The learning rule never ran.** `timing.learning_calls = 0` in all 36 runs.
No trip completes inside a dispatch pass, so no outcome label was produced and θ
never left initialisation. Equations (10)–(12) are presented as a *design*
contribution, explicitly not validated here.

**b) N=250 and N=500 are not like-for-like.** The 60-vehicle fleet serves ~110
requests there while the baseline serves all 250/500, and Algorithm 1 sorts by
descending score — so the served subset is the *most batchable* one. The
headline is therefore **37–40%**, resting on N=50 and N=100.

**c) The complexity bound is not achieved.** Pairs scored grew 489 → 1,817 →
11,049 → 44,095, a fit of N^1.96. The candidate window never bound.

---

## 6. Before you submit

- Confirm the three co-author emails are current.
- Check the conference page limit — some allow 6, not 8.
- Check whether review is anonymised; if so, strip the author block.
- **Biggest improvement still available:** re-run with the fleet scaled to
  demand (60/120/300/600 vehicles for N=50/100/250/500). That removes limitation
  (b) entirely and lets you make the strong claim at all four pool sizes.
