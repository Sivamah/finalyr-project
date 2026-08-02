"""
DMFE ORM Models
===============
Defines the database tables used exclusively by the Dynamic Multi-Service
Feasibility Engine.  These models share the same SQLAlchemy `Base` as the
rest of the application so that `Base.metadata.create_all()` in main.py
creates them automatically.
"""

from sqlalchemy import Column, Integer, String, Float, Text, DateTime, Boolean
from sqlalchemy.sql import func
from app.db.database import Base


class DMFEBatch(Base):
    """
    A candidate batch produced by one DMFE analysis run.

    One batch groups 2–3 SimulationRequests that have been evaluated as
    either Compatible (Compatibility Score ≥ threshold) or Incompatible.
    Compatible batches have status='Pending' ready for route optimisation
    in the next phase; Incompatible ones have status='Rejected'.
    """
    __tablename__ = "dmfe_batches"

    id                  = Column(Integer, primary_key=True, index=True)
    batch_code          = Column(String, nullable=False)          # e.g. "BATCH-17"
    analysis_run_id     = Column(Integer, nullable=True, index=True)

    # JSON list of SimulationRequest IDs included in this batch
    request_ids_json    = Column(Text, nullable=False, default="[]")

    # Aggregate compatibility score (0–100)
    compatibility_score = Column(Float, default=0.0)

    # "Compatible" | "Incompatible"
    decision            = Column(String, default="Incompatible")

    # JSON list of human-readable explanation strings
    reason_json         = Column(Text, default="[]")

    # JSON dict with individual factor scores {factor_name: score_0_to_1}
    factor_scores_json  = Column(Text, default="{}")

    # "Pending" | "Dispatched" | "Rejected"
    status              = Column(String, default="Pending")

    # Estimated delay introduced by batching (minutes)
    estimated_delay_min = Column(Float, default=0.0)

    created_at          = Column(DateTime(timezone=True), server_default=func.now())


class DMFEAnalysisRun(Base):
    """
    Summary record for each triggered DMFE analysis execution.
    Enables the /history and /statistics endpoints.
    """
    __tablename__ = "dmfe_analysis_runs"

    id                      = Column(Integer, primary_key=True, index=True)
    total_pending           = Column(Integer, default=0)
    total_evaluated_pairs   = Column(Integer, default=0)
    batches_created         = Column(Integer, default=0)
    rejected_count          = Column(Integer, default=0)
    avg_compatibility_score = Column(Float, default=0.0)
    threshold_used          = Column(Float, default=70.0)
    run_at                  = Column(DateTime(timezone=True), server_default=func.now())
