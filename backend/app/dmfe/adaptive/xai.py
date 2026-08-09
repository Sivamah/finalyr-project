"""
A-DMFE Module 7 — Explainable AI (attribution & confidence)
===========================================================
Every A-DMFE decision carries:

  - factor attribution  a_f = w_f · (f_f − f̄)   (additive, signed contributions)
  - the final Compatibility Score (CS)
  - the decision confidence (Module 6)
  - natural-language reasons: why a batch was formed, why it was rejected,
    and which factors contributed the most.

Attribution uses the neutral baseline f̄ = 0.5 (no prior information), so a
factor with score f_f above 0.5 pushes the score up proportionally to its
adaptive weight w_f.  The top contributors are ranked by |a_f|.
"""

from __future__ import annotations

from typing import Any, Dict, List

# Removed FACTOR_KEYS to make attribution dynamic for both CS and Unified scores

NEUTRAL_BASELINE = 0.5


def factor_contributions(
    weights: Dict[str, float],
    factor_scores: Dict[str, float],
    baseline: float = NEUTRAL_BASELINE,
) -> Dict[str, float]:
    """Signed additive attribution: a_f = w_f · (f_f − baseline)."""
    out: Dict[str, float] = {}
    for factor in weights.keys():
        w = float(weights.get(factor, 0.0))
        f = float(factor_scores.get(factor, 0.0))
        out[factor] = round(w * (f - baseline), 4)
    return out


def top_contributors(
    contributions: Dict[str, float], n: int = 3
) -> List[Dict[str, Any]]:
    """Rank factors by |contribution|; returns [{factor, contribution}]."""
    ranked = sorted(
        contributions.items(), key=lambda kv: abs(kv[1]), reverse=True
    )
    return [
        {"factor": f, "contribution": c} for f, c in ranked[:n] if abs(c) > 1e-4
    ]


def build_adaptive_reasons(
    compatibility_score: float,
    threshold: float,
    batch_score: float,
    bqs_threshold_value: float,
    confidence: float,
    contributions: Dict[str, float],
    extensions: Dict[str, float],
    delay_min: float,
    decided: str,
    mode: str = "adaptive",
) -> List[str]:
    """
    Natural-language decision rationale for the XAI layer.

    `decided` is one of "Compatible" | "Incompatible" | "Individual".
    Static mode returns an empty list (the Phase 9 template reasons are kept).
    """
    if mode != "adaptive":
        return []

    reasons: List[str] = []
    top = top_contributors(contributions, n=3)

    if decided == "Compatible":
        reasons.append(
            f"ℹ️ A-DMFE: BATCHED — CS {compatibility_score:.1f}% ≥ θ_eff {threshold:.1f}%, "
            f"BQS {batch_score:.2f} ≥ θ_bqs {bqs_threshold_value:.2f}"
        )
        for t in top:
            sign = "+" if t["contribution"] >= 0 else ""
            reasons.append(
                f"ℹ️ Factor '{t['factor']}' contributed {sign}{t['contribution']:.3f}"
            )
    elif decided == "Incompatible":
        reasons.append(
            f"✗ A-DMFE: REJECTED — CS {compatibility_score:.1f}% vs θ_eff {threshold:.1f}%, "
            f"BQS {batch_score:.2f} vs θ_bqs {bqs_threshold_value:.2f}"
        )
        for t in top:
            sign = "+" if t["contribution"] >= 0 else ""
            reasons.append(
                f"ℹ️ Factor '{t['factor']}' contributed {sign}{t['contribution']:.3f}"
            )
        reasons.append(
            f"ℹ️ Expected delay {delay_min:.1f} min, "
            f"corridor success {extensions.get('historical_success', 0.5):.2f}"
        )
    else:
        reasons.append(
            f"ℹ️ A-DMFE: INDIVIDUAL — no batch passed the adaptive gates "
            f"(θ_eff {threshold:.1f}%, θ_bqs {bqs_threshold_value:.2f})"
        )

    reasons.append(
        f"ℹ️ Decision confidence {confidence:.1f}% "
        f"(margin over θ_eff + factor agreement + delay headroom)"
    )
    return reasons
