"""
A-DMFE — Adaptive Dynamic Feasibility Analysis
===============================================
Research-grade extension of the DMFE core engine.  The package adds seven
intelligent modules on top of the existing (unchanged) Phase 9 pipeline:

  Module 1  context.py    — Context Awareness Engine
  Module 2  weights.py    — Adaptive Weight Generator
  Module 3  factors.py    — Advanced Compatibility Engine (extension factors)
  Module 4  matrix.py     — Compatibility Matrix
  Module 5  batching.py   — Intelligent Batch Formation (BQS gate)
  Module 6  decision.py   — Adaptive Decision Engine (dynamic threshold)
  Module 7  xai.py        — Explainable AI (factor attribution + confidence)
  Module 8  learning.py   — Outcome-driven lightweight learning

Every module is additive: the original DMFE classes, APIs, dashboards,
database schema and OR-Tools integration are untouched.  The whole adaptive
stack can be disabled with SystemConfig key ``admfe.mode = "static"`` which
restores the exact fixed-weight Phase 9 behaviour (used for controlled
experiments and backwards compatibility).
"""

from __future__ import annotations
