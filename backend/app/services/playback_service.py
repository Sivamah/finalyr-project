import json
import logging
from typing import List, Dict, Any, Optional
from datetime import datetime, timezone
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.core.json_utils import json_loads
from app.db.models import SimulationScenario, SavedSimulation, SimulationRequest, Provider
from app.services.notification_service import log_system_notification

logger = logging.getLogger(__name__)

PRESET_SCENARIOS = [
    {
        "name": "Peak Hour Traffic",
        "description": "High commute rush during 08:00–10:00 AM with heavy traffic delays",
        "traffic_multiplier": 1.8,
        "demand_multiplier": 2.0,
        "weather_condition": "Clear",
        "is_preset": True,
    },
    {
        "name": "Rainy Day Rush",
        "description": "Monsoon rainfall causing 2x pickup delays and surged delivery requests",
        "traffic_multiplier": 1.5,
        "demand_multiplier": 1.4,
        "weather_condition": "Rain",
        "is_preset": True,
    },
    {
        "name": "Festival Traffic",
        "description": "Diwali/Pongal shopping season with maximum demand and road congestion",
        "traffic_multiplier": 2.2,
        "demand_multiplier": 2.5,
        "weather_condition": "Heavy Traffic",
        "is_preset": True,
    },
    {
        "name": "High Demand Spurt",
        "description": "Sudden surge in food and parcel deliveries across Coimbatore IT parks",
        "traffic_multiplier": 1.2,
        "demand_multiplier": 1.8,
        "weather_condition": "Clear",
        "is_preset": True,
    },
    {
        "name": "Low Demand Off-Peak",
        "description": "Late night / early morning low request activity with smooth traffic flow",
        "traffic_multiplier": 0.8,
        "demand_multiplier": 0.5,
        "weather_condition": "Clear",
        "is_preset": True,
    },
    {
        "name": "Standard Baseline Run",
        "description": "Default simulation scenario with balanced 1.0x demand and clear weather",
        "traffic_multiplier": 1.0,
        "demand_multiplier": 1.0,
        "weather_condition": "Clear",
        "is_preset": True,
    },
]


class PlaybackService:
    """Service layer managing scenario presets, saved simulations, replay telemetry, and comparisons."""

    def seed_scenario_presets_if_needed(self, db: Session):
        """Seed standard scenario presets into database."""
        try:
            existing_names = {s.name for s in db.query(SimulationScenario).all()}
            for sc in PRESET_SCENARIOS:
                if sc["name"] not in existing_names:
                    scenario = SimulationScenario(**sc)
                    db.add(scenario)
            db.commit()
        except Exception as exc:
            logger.warning("seed_scenario_presets_if_needed error: %s", exc)
            db.rollback()

    def get_scenarios(self, db: Session) -> List[Dict[str, Any]]:
        self.seed_scenario_presets_if_needed(db)
        items = db.query(SimulationScenario).order_by(SimulationScenario.is_preset.desc(), SimulationScenario.id.asc()).all()
        return [
            {
                "id": s.id,
                "name": s.name,
                "description": s.description or "",
                "traffic_multiplier": s.traffic_multiplier or 1.0,
                "demand_multiplier": s.demand_multiplier or 1.0,
                "weather_condition": s.weather_condition or "Clear",
                "is_preset": bool(s.is_preset),
            }
            for s in items
        ]

    def create_scenario(self, db: Session, data: Dict[str, Any]) -> Dict[str, Any]:
        scenario = SimulationScenario(
            name=data["name"],
            description=data.get("description", ""),
            traffic_multiplier=data.get("traffic_multiplier", 1.0),
            demand_multiplier=data.get("demand_multiplier", 1.0),
            weather_condition=data.get("weather_condition", "Clear"),
            is_preset=False,
        )
        db.add(scenario)
        db.commit()
        db.refresh(scenario)
        return {
            "id": scenario.id,
            "name": scenario.name,
            "description": scenario.description,
            "traffic_multiplier": scenario.traffic_multiplier,
            "demand_multiplier": scenario.demand_multiplier,
            "weather_condition": scenario.weather_condition,
            "is_preset": False,
        }

    def delete_scenario(self, db: Session, scenario_id: int) -> bool:
        sc = db.query(SimulationScenario).filter(SimulationScenario.id == scenario_id).first()
        if sc and not sc.is_preset:
            db.delete(sc)
            db.commit()
            return True
        return False

    def save_current_simulation_snapshot(
        self,
        db: Session,
        name: str,
        scenario_name: str = "Standard Baseline Run",
    ) -> Dict[str, Any]:
        """Snapshot current database simulation requests and generate replay frames timeline."""
        requests = db.query(SimulationRequest).all()
        providers = db.query(Provider).all()
        provider_map = {p.id: p.name for p in providers}

        total_reqs = len(requests)
        completed_reqs = sum(1 for r in requests if r.status == "Completed")
        comp_rate = round((completed_reqs / total_reqs * 100), 1) if total_reqs > 0 else 0.0

        # Provider Breakdown
        p_stats = {}
        for p in providers:
            p_stats[p.name] = sum(1 for r in requests if r.provider_id == p.id)

        # ── Real replay timeline built from actual request timestamps ────────
        # Sort requests chronologically; each frame marks the next milestone
        # (request created / completed) so the replay mirrors real events
        # instead of synthetic 20-frame interpolation.
        sorted_reqs = sorted(
            requests,
            key=lambda r: r.request_timestamp or r.created_at
            if (r.request_timestamp or r.created_at) else datetime.min,
        )
        timeline_frames = []
        frame_completed = 0
        prev_key = None
        frame_idx = 1
        for r in sorted_reqs:
            ts = r.request_timestamp or r.created_at
            if ts is None:
                continue
            key = ts.strftime("%H:%M:%S")
            if key == prev_key:
                continue  # merge same-second events into one frame
            prev_key = key
            is_done = r.status == "Completed"
            if is_done:
                frame_completed += 1
            timeline_frames.append({
                "frame": frame_idx,
                "timestamp": key,
                "active_requests": len(sorted_reqs) - frame_completed,
                "completed_requests": frame_completed,
                "completion_rate": round(
                    (frame_completed / max(total_reqs, 1)) * 100, 1
                ),
                "event": (
                    f"Request #{r.id} completed"
                    if is_done else f"Request #{r.id} generated"
                ),
            })
            frame_idx += 1
            if frame_idx > 60:
                break

        # ── Real average waiting time (created → completed) ───────────────────
        wait_times = []
        for r in requests:
            c_at = r.created_at
            r_ts = r.request_timestamp
            if r.status == "Completed" and c_at and r_ts:
                try:
                    wait = max(0.0, abs((c_at - r_ts).total_seconds()))
                    wait_times.append(wait)
                except Exception:
                    continue
        avg_wait = round(sum(wait_times) / len(wait_times), 1) if wait_times else 0.0

        saved = SavedSimulation(
            name=name,
            scenario_name=scenario_name,
            duration_seconds=float(
                (requests[-1].created_at - requests[0].created_at).total_seconds()
                if total_reqs > 1 and requests[0].created_at and requests[-1].created_at
                else total_reqs * 12.5
            ),
            total_requests=total_reqs,
            completed_requests=completed_reqs,
            completion_rate=comp_rate,
            avg_waiting_time_sec=avg_wait,
            provider_stats_json=json.dumps(p_stats),
            queue_stats_json=json.dumps({"pending": total_reqs - completed_reqs, "completed": completed_reqs}),
            events_timeline_json=json.dumps(timeline_frames),
        )
        db.add(saved)
        db.commit()
        db.refresh(saved)

        log_system_notification(
            db,
            title="Simulation Run Saved",
            description=f"Saved simulation run '{name}' ({total_reqs} requests, {comp_rate}% completion)",
            category="Success",
            event_type="simulation_state",
        )

        return self.get_saved_simulation_by_id(db, saved.id)

    def get_saved_simulations(
        self,
        db: Session,
        search: Optional[str] = None,
        scenario: Optional[str] = None,
        provider: Optional[str] = None,
        date: Optional[str] = None,
        limit: int = 100,
    ) -> List[Dict[str, Any]]:
        self.seed_scenario_presets_if_needed(db)
        query = db.query(SavedSimulation)

        if scenario and scenario.lower() != "all":
            query = query.filter(func.lower(SavedSimulation.scenario_name) == scenario.lower())

        if search:
            s_lower = search.lower()
            query = query.filter(
                (func.lower(SavedSimulation.name).contains(s_lower)) |
                (func.lower(SavedSimulation.scenario_name).contains(s_lower))
            )

        items = query.order_by(SavedSimulation.created_at.desc()).limit(limit).all()

        if not items:
            # Seed synthetic initial saved run for rich baseline display
            dummy = self.save_current_simulation_snapshot(db, "Baseline Peak Hour Run", "Peak Hour Traffic")
            items = db.query(SavedSimulation).order_by(SavedSimulation.created_at.desc()).limit(limit).all()

        result = []
        for s in items:
            result.append(self._saved_simulation_to_dict(s))
        return result

    @staticmethod
    def _saved_simulation_to_dict(s) -> Dict[str, Any]:
        c_at = s.created_at or datetime.now(timezone.utc)
        if c_at.tzinfo is None:
            c_at = c_at.replace(tzinfo=timezone.utc)

        return {
            "id": s.id,
            "name": s.name,
            "scenario_name": s.scenario_name or "Standard Baseline Run",
            "duration_seconds": s.duration_seconds or 0.0,
            "total_requests": s.total_requests or 0,
            "completed_requests": s.completed_requests or 0,
            "completion_rate": s.completion_rate or 0.0,
            "avg_waiting_time_sec": s.avg_waiting_time_sec or 0.0,
            "provider_stats": json_loads(s.provider_stats_json, {}),
            "queue_stats": json_loads(s.queue_stats_json, {}),
            "events_timeline": json_loads(s.events_timeline_json, []),
            "created_at": c_at.strftime("%Y-%m-%d %I:%M %p"),
        }

    def get_saved_simulation_by_id(self, db: Session, sim_id: int) -> Optional[Dict[str, Any]]:
        s = db.query(SavedSimulation).filter(SavedSimulation.id == sim_id).first()
        if not s:
            return None

        return self._saved_simulation_to_dict(s)

    def delete_saved_simulation(self, db: Session, sim_id: int) -> bool:
        s = db.query(SavedSimulation).filter(SavedSimulation.id == sim_id).first()
        if s:
            db.delete(s)
            db.commit()
            return True
        return False

    def compare_simulations(self, db: Session, sim_id_1: int, sim_id_2: int) -> Optional[Dict[str, Any]]:
        s1 = self.get_saved_simulation_by_id(db, sim_id_1)
        s2 = self.get_saved_simulation_by_id(db, sim_id_2)

        if not s1 or not s2:
            return None

        delta_rate = round(s1["completion_rate"] - s2["completion_rate"], 1)
        delta_wait = round(s1["avg_waiting_time_sec"] - s2["avg_waiting_time_sec"], 1)

        winner_id = s1["id"] if s1["completion_rate"] >= s2["completion_rate"] else s2["id"]

        return {
            "simulation_1": s1,
            "simulation_2": s2,
            "delta_completion_rate": delta_rate,
            "delta_waiting_time_sec": delta_wait,
            "winner_simulation_id": winner_id,
        }

    def get_dashboard_overview(self, db: Session) -> Dict[str, Any]:
        sims = self.get_saved_simulations(db)
        total_saved = len(sims)

        if not sims:
            return {
                "total_saved": 0,
                "recent_simulations_count": 0,
                "best_performing_scenario": "N/A",
                "worst_performing_scenario": "N/A",
            }

        sorted_sims = sorted(sims, key=lambda x: x["completion_rate"], reverse=True)
        best_scen = sorted_sims[0]["scenario_name"]
        worst_scen = sorted_sims[-1]["scenario_name"]

        return {
            "total_saved": total_saved,
            "recent_simulations_count": min(5, total_saved),
            "best_performing_scenario": best_scen,
            "worst_performing_scenario": worst_scen,
        }


playback_service = PlaybackService()
