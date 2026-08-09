import os
import sys
import json

EVAL_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, EVAL_DIR)
sys.path.insert(0, os.path.dirname(EVAL_DIR))

import framework
from app.db.database import SessionLocal
from app.dmfe.models import DMFEBatch
from app.db.models import SimulationRequest, Trip

def run_experiment(mode: str, unified: bool):
    framework.SYSTEM_CONFIG["admfe.unified_scoring_enabled"] = "true" if unified else "false"
    # Ensure same seed
    framework.random.seed(42)
    
    print(f"Starting workload for mode={mode}, unified={unified}...")
    res = framework.run_workload(50, mode=mode)
    
    db = SessionLocal()
    batches = db.query(DMFEBatch).all()
    
    batch_data = []
    for b in batches:
        # Avoid serialization issues with datetime
        batch_data.append({
            "id": b.id,
            "decision": b.decision,
            "reasons": json.loads(b.reason_json) if b.reason_json else [],
            "factor_details": json.loads(b.factor_details_json) if b.factor_details_json else {},
            "factor_scores": json.loads(b.factor_scores_json) if b.factor_scores_json else {},
            "compatibility_score": float(b.compatibility_score) if b.compatibility_score is not None else None
        })
        
    db.close()
    
    return {
        "metrics": res,
        "batches": batch_data
    }

def main():
    os.makedirs(framework.RESULTS_DIR, exist_ok=True)
    
    static_a = run_experiment("static", False)
    static_b = run_experiment("static", True)
    adaptive_c = run_experiment("adaptive", False)
    adaptive_d = run_experiment("adaptive", True)
    
    with open(os.path.join(framework.RESULTS_DIR, "unified_validation.json"), "w") as f:
        json.dump({
            "static_a": static_a,
            "static_b": static_b,
            "adaptive_c": adaptive_c,
            "adaptive_d": adaptive_d
        }, f, indent=2)
    print("Done!")

if __name__ == "__main__":
    main()
