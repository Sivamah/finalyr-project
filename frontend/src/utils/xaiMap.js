/**
 * Shared XAI → map highlight normalizer.
 *
 * Converts a raw XAI explanation item (as returned by `/api/xai/explanations`)
 * into the shape consumed by LiveMapContainer / XAIHighlightLayer:
 *
 *   * `requestPoints`  — pickup/drop for the request, its XAI-evaluated partner
 *                        and the real dispatched-trip members (deduped)
 *   * `routeStops`     — the dispatched trip's OR-Tools ordered stop list,
 *                        preserved verbatim.  For a request with no dispatched
 *                        trip (standalone / still pending) it is synthesized
 *                        from that request's OWN pickup→drop coordinates and
 *                        flagged via `routeStopsSynthesized` so the UI can say
 *                        so instead of implying an optimizer produced it.
 *   * `driver`/`vehicle`/`tripCode`/`isShared` — dispatched-trip snapshot
 *
 * Every field below is copied straight from the API payload.  Nothing is
 * defaulted to a plausible-looking number: absent values stay null so the UI
 * renders an explicit "not available" state rather than a fabricated one.
 *
 * Used by both the XAI same-tab map panel and the /live-map?xai= deep link so
 * the highlight rendering is always identical across the two entry points.
 */

export function normalizeXaiHighlight(exp) {
  if (!exp) return null;
  const partnerIds = new Set(exp.batched_with_request_ids || []);
  const requestPoints = (exp.related_requests || []).map((p) => ({
    id: p.request_id,
    relation: p.request_id === exp.request_id ? 'self' : (partnerIds.has(p.request_id) ? 'partner' : 'trip'),
    request_type: p.request_type,
    pickup_lat: p.pickup_lat,
    pickup_lng: p.pickup_lng,
    drop_lat: p.drop_lat,
    drop_lng: p.drop_lng,
    pickup_address: p.pickup_address,
    drop_address: p.drop_address,
    priority: p.priority,
  }));
  const trip = exp.trip;

  let routeStops = trip?.route_stops || [];
  let routeStopsSynthesized = false;
  // No dispatched trip (standalone / still pending): fall back to the
  // request's own pickup → drop leg so the map can still show where the trip
  // would run.  Shared batches keep the exact OR-Tools stop order from the
  // trip — never synthesized, never reordered.
  if (routeStops.length === 0 && exp.pickup_lat && exp.pickup_lng && exp.drop_lat && exp.drop_lng) {
    routeStops = [
      { request_id: exp.request_id, action: 'pickup', lat: exp.pickup_lat, lng: exp.pickup_lng, arrival_min: null },
      { request_id: exp.request_id, action: 'drop', lat: exp.drop_lat, lng: exp.drop_lng, arrival_min: null },
    ];
    routeStopsSynthesized = true;
  }

  return {
    explanation: exp,
    requestId: exp.request_id,
    requestIds: requestPoints.map((p) => p.id),
    requestPoints,
    routeStops,
    routeStopsSynthesized,
    driver: trip?.driver
      ? { name: trip.driver.name, lat: trip.driver.current_lat, lng: trip.driver.current_lng }
      : null,
    vehicle: trip?.vehicle
      ? { name: trip.vehicle.name, type: trip.vehicle.vehicle_type, lat: trip.vehicle.current_lat, lng: trip.vehicle.current_lng }
      : null,
    tripId: trip?.trip_id ?? null,
    tripCode: trip?.trip_code || null,
    tripStatus: trip?.status || null,
    isShared: trip?.is_shared || String(exp.decision || '').toLowerCase().includes('compatible for batching'),
    decision: exp.decision,
    status: exp.status,
    reason: exp.reason,
    decisionSummary: exp.decision_summary || '',
    keyReasons: exp.key_reasons || [],
    factors: exp.factors || null,
    // Compatibility score and model confidence are DIFFERENT quantities and
    // are kept apart here; the UI must not label one as the other.
    score: exp.factors?.overall_compatibility_score ?? null,
    confidence: exp.confidence_score ?? null,
    confidenceFallback: exp.confidence_fallback === true,
    estimatedDistanceKm: exp.estimated_distance_km ?? null,
    // Real trip-economics fields (never fabricated client-side — copied
    // straight from the backend's own dispatch-time computation). Present
    // whenever the request was actually dispatched to a trip (tripCode set);
    // for an individual (non-shared) dispatch, separateCostInr equals
    // tripCostInr since there was nothing to batch against.
    fuelSavedL: exp.fuel_saved_l ?? null,
    co2SavedKg: exp.co2_saved_kg ?? null,
    distanceSavedKm: exp.distance_saved_km ?? null,
    driverProfitInr: exp.driver_profit_inr ?? null,
    tripCostInr: exp.trip_cost_inr ?? null,
    separateCostInr: exp.separate_cost_inr ?? null,
    soloProfitInr: exp.solo_profit_inr ?? null,
    providerName: exp.provider_name,
    requestType: exp.request_type,
    pickupAddress: exp.pickup_address,
    dropAddress: exp.drop_address,
    // Raw coordinates for this request's own pickup/drop — used to build its
    // standalone leg for the "separate trips" map view and to anchor the
    // decision popup independently of whatever route is currently drawn.
    pickupLat: exp.pickup_lat ?? null,
    pickupLng: exp.pickup_lng ?? null,
    dropLat: exp.drop_lat ?? null,
    dropLng: exp.drop_lng ?? null,
  };
}
