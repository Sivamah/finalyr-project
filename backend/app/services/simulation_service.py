"""
Simulation Service — Phase 2: Live Simulation Engine & Monitoring
==================================================================
An in-memory singleton that drives a background thread to continuously
generate realistic transportation requests every 3–5 seconds.

Architecture:
- SimulationEngine  : state machine (IDLE / RUNNING / PAUSED / STOPPED) + thread lifecycle
- RequestGenerator  : one-request factory wrapping the existing mock_adapters helper
- QueueManager      : query layer over `simulation_requests` DB table with analytics aggregations

Reuses existing `generate_simulation_requests()` adapter and `SimulationRequest` ORM model.
"""

import random
import threading
import logging
from datetime import datetime, timezone
from typing import Optional, List, Callable, Dict, Any
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.db.models import SimulationRequest, Provider, Trip
from app.services.mock_adapters import generate_simulation_requests
from app.services.notification_service import log_system_notification

logger = logging.getLogger(__name__)

# ─────────────────────────────────────────────────────────────────
# Request Generator — wraps mock_adapters for a single-request tick
# ─────────────────────────────────────────────────────────────────

class RequestGenerator:
    """Thin wrapper calling generate_simulation_requests(count=1) per tick."""

    TYPE_PROVIDER_MAP = {
        "ride":   ["Rapido", "Uber", "Ola"],
        "food":   ["Swiggy", "Zomato"],
        "parcel": ["DTDC", "Delhivery"],
    }

    def generate_one(self, db: Session) -> Optional[SimulationRequest]:
        """Generate a single random request and persist it. Returns None on failure."""
        try:
            results = generate_simulation_requests(count=1, db=db)
            return results[0] if results else None
        except Exception as exc:
            logger.warning("RequestGenerator.generate_one() failed: %s", exc)
            return None


# ─────────────────────────────────────────────────────────────────
# Queue Manager — query & aggregation helpers
# ─────────────────────────────────────────────────────────────────

class QueueManager:
    """Read access and analytical queries for simulation requests."""

    def get_pending(self, db: Session, limit: int = 200) -> List[SimulationRequest]:
        """Return most-recent pending (queued) requests."""
        return (
            db.query(SimulationRequest)
            .filter(SimulationRequest.status == "Pending")
            .order_by(SimulationRequest.created_at.desc())
            .limit(limit)
            .all()
        )

    def get_completed(self, db: Session, limit: int = 200) -> List[SimulationRequest]:
        """Return requests that have been completed/processed."""
        return (
            db.query(SimulationRequest)
            .filter(SimulationRequest.status != "Pending")
            .order_by(SimulationRequest.created_at.desc())
            .limit(limit)
            .all()
        )

    def count_pending(self, db: Session) -> int:
        return db.query(SimulationRequest).filter(SimulationRequest.status == "Pending").count()

    def count_completed(self, db: Session) -> int:
        return db.query(SimulationRequest).filter(SimulationRequest.status != "Pending").count()

    def clear_pending(self, db: Session) -> int:
        """Delete only pending requests from DB."""
        count = db.query(SimulationRequest).filter(SimulationRequest.status == "Pending").delete()
        db.commit()
        return count

    def clear_completed(self, db: Session) -> int:
        """Delete only completed (non-pending) requests from DB."""
        count = db.query(SimulationRequest).filter(SimulationRequest.status != "Pending").delete()
        db.commit()
        return count

    def clear_all(self, db: Session) -> int:
        """Delete ALL simulation requests (Pending + Completed)."""
        count = db.query(SimulationRequest).delete()
        db.commit()
        return count

    def get_breakdown_metrics(self, db: Session) -> Dict[str, int]:
        """Get counts broken down by category (Ride, Food, Parcel) for pending & completed."""
        rows = (
            db.query(SimulationRequest.status, SimulationRequest.request_type, func.count(SimulationRequest.id))
            .group_by(SimulationRequest.status, SimulationRequest.request_type)
            .all()
        )
        metrics = {
            "pending_ride": 0, "pending_food": 0, "pending_parcel": 0,
            "completed_ride": 0, "completed_food": 0, "completed_parcel": 0
        }
        for status, req_type, count in rows:
            st = "pending" if status == "Pending" else "completed"
            key = f"{st}_{req_type.lower()}"
            if key in metrics:
                metrics[key] = count
        return metrics

    def get_analytics(self, db: Session) -> Dict[str, Any]:
        """Gather analytical series for Recharts dashboard visualizations."""
        requests = db.query(SimulationRequest).order_by(SimulationRequest.created_at.asc()).all()

        # Provider map
        provider_ids = {r.provider_id for r in requests if r.provider_id}
        providers = {p.id: p.name for p in db.query(Provider).filter(Provider.id.in_(provider_ids)).all()} if provider_ids else {}

        # 1. Type distribution
        type_counts: Dict[str, int] = {}
        # 2. Provider distribution
        provider_counts: Dict[str, int] = {}
        # 3. Requests over time (grouped by minute)
        time_series: Dict[str, int] = {}
        # 4. Queue size trend
        queue_trend: List[Dict[str, Any]] = []

        curr_queue = 0
        for r in requests:
            # Type count
            t_name = r.request_type.capitalize() if r.request_type else "Other"
            type_counts[t_name] = type_counts.get(t_name, 0) + 1

            # Provider count
            p_name = providers.get(r.provider_id, "Unassigned") if r.provider_id else "Unassigned"
            provider_counts[p_name] = provider_counts.get(p_name, 0) + 1

            # Time series
            if r.created_at:
                t_str = r.created_at.strftime("%H:%M")
                time_series[t_str] = time_series.get(t_str, 0) + 1
            
            # Queue trend
            if r.status == "Pending":
                curr_queue += 1
            elif curr_queue > 0:
                curr_queue -= 1
            if r.created_at:
                queue_trend.append({
                    "time": r.created_at.strftime("%H:%M:%S"),
                    "count": curr_queue
                })

        return {
            "requests_over_time": [{"time": k, "count": v} for k, v in time_series.items()][-20:],
            "type_distribution": [{"name": k, "count": v} for k, v in type_counts.items()],
            "provider_distribution": [{"name": k, "count": v} for k, v in provider_counts.items()],
            "queue_trend": queue_trend[-30:] if queue_trend else [{"time": "Now", "count": curr_queue}],
        }

    def get_advanced_analytics(
        self,
        db: Session,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        request_type: Optional[str] = None,
        provider_id: Optional[int] = None,
        status: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Gather comprehensive Phase 4 operational metrics and series data with filtering support."""
        query = db.query(SimulationRequest)

        # Filters
        if request_type and request_type.lower() != "all":
            query = query.filter(func.lower(SimulationRequest.request_type) == request_type.lower())
        if provider_id and provider_id != 0:
            query = query.filter(SimulationRequest.provider_id == provider_id)
        if status and status.lower() != "all":
            query = query.filter(func.lower(SimulationRequest.status) == status.lower())

        if start_date:
            try:
                dt_start = datetime.fromisoformat(start_date)
                query = query.filter(SimulationRequest.created_at >= dt_start)
            except Exception:
                pass
        if end_date:
            try:
                dt_end = datetime.fromisoformat(end_date)
                query = query.filter(SimulationRequest.created_at <= dt_end)
            except Exception:
                pass

        requests = query.order_by(SimulationRequest.created_at.asc()).all()

        # All Providers map
        all_providers = db.query(Provider).all()
        total_providers_count = len(all_providers)
        active_providers_count = sum(1 for p in all_providers if p.status == "Active")

        total_requests = len(requests)
        pending_requests = sum(1 for r in requests if r.status == "Pending")
        completed_requests = sum(1 for r in requests if r.status == "Completed")
        active_requests = pending_requests

        completion_rate = round((completed_requests / total_requests * 100), 1) if total_requests > 0 else 0.0
        pending_rate = round((pending_requests / total_requests * 100), 1) if total_requests > 0 else 0.0

        # Request types
        ride_reqs = [r for r in requests if r.request_type and r.request_type.lower() == "ride"]
        food_reqs = [r for r in requests if r.request_type and r.request_type.lower() == "food"]
        parcel_reqs = [r for r in requests if r.request_type and r.request_type.lower() == "parcel"]

        distances = [r.estimated_distance_km for r in requests if r.estimated_distance_km is not None]
        avg_distance = round(sum(distances) / len(distances), 2) if distances else 0.0
        avg_travel_time = round((avg_distance / 25.0) * 60.0, 1) if avg_distance > 0 else 0.0

        # Durations & Waiting times
        now_utc = datetime.now(timezone.utc)
        processing_times = []
        queue_wait_times = []

        for r in requests:
            if r.status == "Completed":
                if r.request_timestamp and r.created_at:
                    dur = max(1.0, abs((r.created_at - r.request_timestamp).total_seconds()))
                    processing_times.append(dur)
                else:
                    processing_times.append(12.5)
            elif r.status == "Pending" and r.created_at:
                try:
                    c_at = r.created_at
                    if c_at.tzinfo is None:
                        c_at = c_at.replace(tzinfo=timezone.utc)
                    wait = max(0.0, (now_utc - c_at).total_seconds())
                    queue_wait_times.append(wait)
                except Exception:
                    queue_wait_times.append(8.0)

        avg_processing_time = round(sum(processing_times) / len(processing_times), 1) if processing_times else 0.0
        avg_queue_wait = round(sum(queue_wait_times) / len(queue_wait_times), 1) if queue_wait_times else 0.0

        # Genuine completion duration: completed_at − created_at of finished trips
        completion_times = []
        for t in db.query(Trip).filter(Trip.completed_at.isnot(None)).all():
            if t.created_at and t.completed_at:
                c_at, d_at = t.created_at, t.completed_at
                if c_at.tzinfo is None:
                    c_at = c_at.replace(tzinfo=timezone.utc)
                if d_at.tzinfo is None:
                    d_at = d_at.replace(tzinfo=timezone.utc)
                completion_times.append(max(1.0, (d_at - c_at).total_seconds()))
        avg_completion_time = (
            round(sum(completion_times) / len(completion_times), 1)
            if completion_times else 0.0
        )

        if total_requests > 1 and requests[0].created_at and requests[-1].created_at:
            span_sec = (requests[-1].created_at - requests[0].created_at).total_seconds()
            time_span_min = max(0.5, span_sec / 60.0)
            rpm = round(total_requests / time_span_min, 1)
        else:
            rpm = round(float(total_requests), 1)

        # Provider Analytics
        provider_stats_dict = {}
        for p in all_providers:
            provider_stats_dict[p.id] = {
                "provider_id": p.id,
                "provider_name": p.name,
                "total_requests": 0,
                "completed_requests": 0,
                "pending_requests": 0,
                "distances": [],
            }

        for r in requests:
            pid = r.provider_id
            if pid and pid in provider_stats_dict:
                provider_stats_dict[pid]["total_requests"] += 1
                if r.status == "Completed":
                    provider_stats_dict[pid]["completed_requests"] += 1
                else:
                    provider_stats_dict[pid]["pending_requests"] += 1
                if r.estimated_distance_km:
                    provider_stats_dict[pid]["distances"].append(r.estimated_distance_km)

        provider_stats_list = []
        max_reqs = -1
        min_reqs = 999999
        most_active = "None"
        least_active = "None"

        for pid, pdata in provider_stats_dict.items():
            tot = pdata["total_requests"]
            util = round((tot / total_requests * 100), 1) if total_requests > 0 else 0.0
            avg_d = round(sum(pdata["distances"]) / len(pdata["distances"]), 2) if pdata["distances"] else 0.0
            pitem = {
                "provider_id": pid,
                "provider_name": pdata["provider_name"],
                "total_requests": tot,
                "completed_requests": pdata["completed_requests"],
                "pending_requests": pdata["pending_requests"],
                "utilization_pct": util,
                "avg_distance_km": avg_d,
            }
            provider_stats_list.append(pitem)

            if tot > max_reqs:
                max_reqs = tot
                most_active = pdata["provider_name"]
            if tot < min_reqs:
                min_reqs = tot
                least_active = pdata["provider_name"]

        if total_requests == 0:
            most_active = "None"
            least_active = "None"

        # Time distributions & series
        hourly_counts = {f"{h:02d}:00": 0 for h in range(24)}
        daily_counts = {}
        time_series_gen = {}
        time_series_comp = {}
        type_counts = {"Ride": len(ride_reqs), "Food": len(food_reqs), "Parcel": len(parcel_reqs)}

        curr_queue = 0
        queue_trend_list = []

        for r in requests:
            if r.created_at:
                h_key = r.created_at.strftime("%H:00")
                hourly_counts[h_key] = hourly_counts.get(h_key, 0) + 1

                d_key = r.created_at.strftime("%Y-%m-%d")
                daily_counts[d_key] = daily_counts.get(d_key, 0) + 1

                m_key = r.created_at.strftime("%H:%M")
                time_series_gen[m_key] = time_series_gen.get(m_key, 0) + 1

                if r.status == "Completed":
                    time_series_comp[m_key] = time_series_comp.get(m_key, 0) + 1
                    if curr_queue > 0:
                        curr_queue -= 1
                else:
                    curr_queue += 1

                queue_trend_list.append({
                    "time": r.created_at.strftime("%H:%M:%S"),
                    "count": curr_queue,
                })

        peak_hour_str = "N/A"
        max_h_val = -1
        for h, cnt in hourly_counts.items():
            if cnt > max_h_val and cnt > 0:
                max_h_val = cnt
                peak_hour_str = f"{h} ({cnt} reqs)"

        gen_trend = [{"time": k, "count": v} for k, v in time_series_gen.items()][-25:]
        comp_trend = [{"time": k, "count": v} for k, v in time_series_comp.items()][-25:]
        prov_dist = [{"name": p["provider_name"], "count": p["total_requests"]} for p in provider_stats_list]
        type_dist = [{"name": k, "count": v} for k, v in type_counts.items()]
        q_trend = queue_trend_list[-30:] if queue_trend_list else [{"time": "Now", "count": curr_queue}]

        return {
            "kpi": {
                "total_requests": total_requests,
                "active_requests": active_requests,
                "pending_requests": pending_requests,
                "completed_requests": completed_requests,
                "requests_per_minute": rpm,
                "avg_processing_time_sec": avg_processing_time,
                "total_providers": total_providers_count,
                "active_providers": active_providers_count,
            },
            "charts": {
                "request_generation_trend": gen_trend,
                "request_type_distribution": type_dist,
                "provider_distribution": prov_dist,
                "queue_size_trend": q_trend,
                "completed_requests_trend": comp_trend,
            },
            "request_analytics": {
                "total_ride_requests": len(ride_reqs),
                "total_food_requests": len(food_reqs),
                "total_parcel_requests": len(parcel_reqs),
                "avg_estimated_distance_km": avg_distance,
                "avg_estimated_travel_time_min": avg_travel_time,
                "completion_rate_pct": completion_rate,
                "pending_rate_pct": pending_rate,
            },
            "provider_analytics": {
                "provider_stats": provider_stats_list,
                "most_active_provider": most_active,
                "least_active_provider": least_active,
            },
            "time_analytics": {
                "avg_queue_waiting_time_sec": avg_queue_wait,
                "avg_completion_time_sec": avg_completion_time,
                "peak_request_hour": peak_hour_str,
                "hourly_distribution": [{"name": k, "count": v} for k, v in hourly_counts.items()],
                "daily_distribution": [{"name": k, "count": v} for k, v in daily_counts.items()],
            },
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }


# ─────────────────────────────────────────────────────────────────
# Simulation Engine — singleton state machine
# ─────────────────────────────────────────────────────────────────

class SimulationEngine:
    """
    Singleton engine managing simulation state and thread lifecycle.

    States: Running / Paused / Stopped
    """

    MIN_INTERVAL_S: float = 3.0
    MAX_INTERVAL_S: float = 5.0

    def __init__(self):
        self._lock = threading.Lock()
        self._stop_event = threading.Event()
        self._thread: Optional[threading.Thread] = None

        self._running: bool = False
        self._paused: bool = False
        self._total_generated: int = 0
        self._started_at: Optional[datetime] = None
        self._stopped_at: Optional[datetime] = None

        self.request_generator = RequestGenerator()
        self.queue_manager = QueueManager()

    def start(self, db_factory: Callable[[], Session]) -> dict:
        """Start or resume the simulation loop."""
        is_resume = False
        with self._lock:
            if self._running and not self._paused:
                return self.get_status_snapshot()

            is_resume = self._paused
            if self._paused:
                self._paused = False
                logger.info("SimulationEngine resumed")
            else:
                self._stop_event.clear()
                self._running = True
                self._paused = False
                self._started_at = datetime.now(timezone.utc)
                self._stopped_at = None

                self._thread = threading.Thread(
                    target=self._run_loop,
                    args=(db_factory,),
                    daemon=True,
                    name="SimulationEngineThread",
                )
                self._thread.start()
                logger.info("SimulationEngine started at %s", self._started_at)

        try:
            db = db_factory()
            if is_resume:
                log_system_notification(db, title="Simulation Resumed", description="Request generation engine resumed", category="Information", event_type="simulation_state")
            else:
                log_system_notification(db, title="Simulation Started", description="Request generation engine started", category="Information", event_type="simulation_state")
            db.close()
        except Exception:
            pass

        return self.get_status_snapshot()

    def pause(self) -> dict:
        """Pause generation ticks without shutting down the thread."""
        with self._lock:
            if self._running and not self._paused:
                self._paused = True
                logger.info("SimulationEngine paused")
        return self.get_status_snapshot()

    def resume(self, db_factory: Callable[[], Session]) -> dict:
        """Resume generation from paused state."""
        return self.start(db_factory)

    def stop(self) -> dict:
        """Signal background thread to stop."""
        with self._lock:
            if not self._running:
                return self.get_status_snapshot()

            self._stop_event.set()
            self._running = False
            self._paused = False
            self._stopped_at = datetime.now(timezone.utc)
            logger.info("SimulationEngine stopped at %s", self._stopped_at)
        return self.get_status_snapshot()

    def clear(self, db: Session) -> dict:
        """Stop engine and delete ALL simulation requests from DB."""
        self.stop()
        deleted = self.queue_manager.clear_all(db)
        with self._lock:
            self._total_generated = 0
            self._started_at = None
            self._stopped_at = None
        logger.info("SimulationEngine cleared — deleted %d requests", deleted)
        log_system_notification(db, title="Queue & History Cleared", description=f"Cleared {deleted} simulation requests from database", category="Warning", event_type="simulation_state")
        return {"deleted": deleted, **self.get_status_snapshot()}

    def clear_queue_only(self, db: Session) -> dict:
        """Delete only Pending requests from DB."""
        deleted = self.queue_manager.clear_pending(db)
        log_system_notification(db, title="Queue Cleared", description=f"Cleared {deleted} pending requests from queue", category="Warning", event_type="simulation_state")
        return {"deleted": deleted, **self.get_status_snapshot()}

    def clear_history_only(self, db: Session) -> dict:
        """Delete only Completed requests from DB."""
        deleted = self.queue_manager.clear_completed(db)
        log_system_notification(db, title="History Cleared", description=f"Cleared {deleted} completed requests from history", category="Warning", event_type="simulation_state")
        return {"deleted": deleted, **self.get_status_snapshot()}

    def get_status_snapshot(self) -> dict:
        """Return snapshot of engine state and calculated metrics."""
        now = datetime.now(timezone.utc)
        runtime_sec = 0.0
        if self._started_at:
            end_time = self._stopped_at if self._stopped_at and not self._running else now
            runtime_sec = max(0.0, (end_time - self._started_at).total_seconds())

        rpm = 0.0
        if runtime_sec > 0:
            rpm = round((self._total_generated / runtime_sec) * 60.0, 1)

        status_text = "Running" if (self._running and not self._paused) else ("Paused" if self._paused else "Stopped")

        return {
            "running": self._running,
            "paused": self._paused,
            "status_text": status_text,
            "total_generated": self._total_generated,
            "started_at": self._started_at,
            "stopped_at": self._stopped_at,
            "runtime_seconds": round(runtime_sec, 1),
            "requests_per_minute": rpm,
        }

    def _run_loop(self, db_factory: Callable[[], Session]) -> None:
        """
        Core background loop — drives the FULL lifecycle:

          1. Generate realistic request bursts (1-3 requests; 40% are
             same-cluster surges so nearby pickups arrive within 5-8 min).
          2. Every few ticks run the DMFE pipeline (compatibility → batching →
             decision → OR-Tools route → driver/vehicle assignment → Trip).
          3. Complete trips older than the simulated trip duration so their
             drivers/vehicles are released for the next dispatch wave.

        This replaced the old loop that "completed" pending requests directly
        (which bypassed the DMFE pipeline and faked trip completions).
        """
        logger.info("SimulationEngine loop started")
        tick_count = 0

        while not self._stop_event.is_set():
            if not self._paused:
                db = db_factory()
                try:
                    tick_count += 1

                    # ── 1. Generate a burst of requests ─────────────────────
                    # 40% chance: same-cluster surge (2-3 requests, tight
                    # pickups, staggered timestamps) — realistic demand at
                    # hotspots like Gandhipuram / RS Puram / Peelamedu.
                    same_cluster = random.random() < 0.40
                    burst_size = random.choices(
                        [1, 2, 3],
                        weights=[0.55, 0.30, 0.15],
                        k=1,
                    )[0]
                    if same_cluster and burst_size < 2:
                        burst_size = 2

                    generated = generate_simulation_requests(
                        count=burst_size,
                        db=db,
                        same_cluster=same_cluster,
                        time_window_min=8.0,
                    )
                    for req in generated:
                        with self._lock:
                            self._total_generated += 1
                        r_type = (req.request_type or "ride").capitalize()
                        log_system_notification(
                            db,
                            title=f"New {r_type} Request Generated",
                            description=(
                                f"Request #{req.id} created "
                                f"({req.pickup_address or 'Origin'} → "
                                f"{req.drop_address or 'Destination'})"
                            ),
                            category="Information",
                            event_type="request_lifecycle",
                            request_id=req.id,
                        )

                    # ── 2. Run the DMFE pipeline periodically ──────────────
                    # Every 3rd tick (≈9-15 s) or when the pending queue is
                    # large, dispatch everything feasible.
                    pending_count = (
                        db.query(SimulationRequest)
                        .filter(SimulationRequest.status == "Pending")
                        .count()
                    )
                    if pending_count >= 6 and (tick_count % 3 == 0):
                        try:
                            from app.dmfe.pipeline import pipeline_runner
                            result = pipeline_runner.run(db, limit=200)
                            if result.dispatches:
                                batch_trips = sum(
                                    1 for d in result.dispatches if d["is_shared"]
                                )
                                log_system_notification(
                                    db,
                                    title="DMFE Dispatch Cycle",
                                    description=(
                                        f"{result.requests_processed} requests → "
                                        f"{result.shared_trips} shared + "
                                        f"{result.individual_trips} individual trips"
                                        f"{f' ({batch_trips} batched)' if batch_trips else ''}"
                                    ),
                                    category="Success",
                                    event_type="simulation_state",
                                )
                        except Exception as exc:
                            logger.error("DMFE pipeline tick error: %s", exc)
                            log_system_notification(
                                db,
                                title="DMFE Pipeline Error",
                                description=f"Pipeline run failed: {str(exc)[:200]}",
                                category="Error",
                                event_type="system_error",
                            )

                    # ── 3. Complete trips that have run long enough ─────────
                    # Time-compressed trips: any trip older than 60-120 s
                    # finishes, releasing its driver/vehicle for new dispatch.
                    from app.dmfe.driver_selection import complete_trip
                    from app.db.models import Trip
                    from datetime import timedelta

                    trip_age_s = random.randint(60, 120)
                    cutoff = datetime.now(timezone.utc) - timedelta(seconds=trip_age_s)
                    due_trips = (
                        db.query(Trip)
                        .filter(
                            Trip.status.in_(["Planned", "Active"]),
                            Trip.created_at < cutoff,
                        )
                        .all()
                    )
                    for t in due_trips:
                        completed = complete_trip(db, t.id, commit=False)
                        log_system_notification(
                            db,
                            title="Trip Completed",
                            description=(
                                f"Trip {completed.trip_code} finished — "
                                f"{'shared' if completed.is_shared else 'individual'} "
                                f"{completed.total_distance_km:.1f} km, "
                                f"{completed.fuel_saved_l:.2f} L fuel saved"
                            ),
                            category="Success",
                            event_type="request_lifecycle",
                        )
                    if due_trips:
                        db.commit()

                except Exception as exc:
                    logger.error("SimulationEngine tick error: %s", exc)
                    log_system_notification(
                        db,
                        title="Simulation Error",
                        description=f"Engine loop error: {str(exc)[:200]}",
                        category="Error",
                        event_type="system_error",
                    )
                finally:
                    db.close()

            interval = random.uniform(self.MIN_INTERVAL_S, self.MAX_INTERVAL_S)
            self._stop_event.wait(timeout=interval)

        logger.info("SimulationEngine loop exited cleanly")


simulation_engine = SimulationEngine()
