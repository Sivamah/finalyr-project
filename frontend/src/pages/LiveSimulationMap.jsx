import React, { useState, useEffect, useRef, useCallback, useMemo } from 'react';
import { useSearchParams } from 'react-router-dom';
import { motion } from 'framer-motion';
import api from '../services/api';
import toast from 'react-hot-toast';

import LiveMapContainer from '../components/map/LiveMapContainer';
import KpiBar from '../components/map/KpiBar';
import MapFilterPanel from '../components/map/MapFilterPanel';
import TripDetailsPanel from '../components/map/TripDetailsPanel';
import ActiveTripsPanel from '../components/map/ActiveTripsPanel';
import { normalizeXaiHighlight } from '../utils/xaiMap';
import useOperationalNetwork from '../hooks/useOperationalNetwork';

export default function LiveSimulationMap() {
  const [searchParams, setSearchParams] = useSearchParams();
  const xaiParam = searchParams.get('xai');
  // ── State ──────────────────────────────────────────────────────────────────
  const [queue, setQueue] = useState([]);
  const [status, setStatus] = useState({
    running: false,
    paused: false,
    status_text: 'Stopped',
    total_generated: 0,
    queue_size: 0,
  });

  const [selectedRequest, setSelectedRequest] = useState(null);
  const [selectedVehicle, setSelectedVehicle] = useState(null);
  const [loading, setLoading] = useState(false);
  const [panelOpen, setPanelOpen] = useState(true);

  const [xaiHighlight, setXaiHighlight] = useState(null);
  const [xaiLoading, setXaiLoading] = useState(false);
  const [xaiError, setXaiError] = useState(null);

  const [searchTerm, setSearchTerm] = useState('');
  const [filterType, setFilterType] = useState('All');
  const [filterProvider, setFilterProvider] = useState('All');
  const [filterPriority, setFilterPriority] = useState('All');

  const pollRef = useRef(null);

  // ── XAI Focus (from "View on Map" on the XAI dashboard) ─────────────────────
  useEffect(() => {
    if (!xaiParam) {
      setXaiHighlight(null);
      setXaiLoading(false);
      setXaiError(null);
      return;
    }
    let cancelled = false;
    setXaiLoading(true);
    setXaiError(null);
    api.get(`/xai/explanations/${xaiParam}`, { noCache: true })
      .then((res) => {
        if (cancelled) return;
        const normalized = normalizeXaiHighlight(res.data);
        setXaiHighlight(normalized);
        setSelectedRequest(null);
      })
      .catch(() => {
        if (cancelled) return;
        setXaiError(`Could not load XAI explanation for request #${xaiParam}.`);
        setXaiHighlight(null);
      })
      .finally(() => {
        if (!cancelled) setXaiLoading(false);
      });
    return () => { cancelled = true; };
  }, [xaiParam]);

  const clearXaiFocus = useCallback(() => {
    setSearchParams({}, { replace: true });
    setXaiHighlight(null);
    setXaiError(null);
  }, [setSearchParams]);

  // Selecting a queue/trip marker clears the XAI deep-link focus so the right
  // panel switches to the tapped trip.
  const handleSelectRequest = useCallback((req) => {
    setSelectedRequest(req);
    setSelectedVehicle(null);
    setXaiHighlight(null);
    setXaiError(null);
    setPanelOpen(true);
    if (xaiParam) setSearchParams({}, { replace: true });
  }, [xaiParam, setSearchParams]);

  const handleSelectVehicle = useCallback((veh) => {
    setSelectedVehicle(veh);
    setSelectedRequest(null);
    setXaiHighlight(null);
    setXaiError(null);
    setPanelOpen(true);
    if (xaiParam) setSearchParams({}, { replace: true });
  }, [xaiParam, setSearchParams]);

  // ── Data Fetching ──────────────────────────────────────────────────────────
  // The operational network (fleet positions + active trips + pending queue)
  // comes from the shared hook; this page only needs the engine status on top
  // of that. Previously the map fetched the queue alone, which is why a live
  // operations view of a 115-vehicle fleet rendered five markers.
  const {
    vehicles, activeTrips, queue: netQueue, refresh: refreshNetwork,
  } = useOperationalNetwork({ intervalMs: 5000 });

  useEffect(() => { setQueue(netQueue); }, [netQueue]);

  const fetchLiveData = useCallback(async () => {
    try {
      const statusRes = await api.get('/simulation/status');
      setStatus(statusRes.data);
    } catch {
      // Silently ignore poll errors
    }
    refreshNetwork();
  }, [refreshNetwork]);

  useEffect(() => {
    let cancelled = false;
    const tick = async () => {
      try {
        const res = await api.get('/simulation/status');
        if (!cancelled) setStatus(res.data);
      } catch { /* poll errors are non-fatal */ }
    };
    tick();
    pollRef.current = setInterval(() => {
      if (document.visibilityState === 'visible') tick();
    }, 5000);
    return () => { cancelled = true; clearInterval(pollRef.current); };
  }, []);

  // ── Controls Handlers ──────────────────────────────────────────────────────
  const handleStartResume = async () => {
    setLoading(true);
    try {
      const endpoint = status.paused ? '/simulation/resume' : '/simulation/start';
      const res = await api.post(endpoint);
      setStatus(res.data);
      toast.success(status.paused ? 'Simulation Resumed' : 'Simulation Started');
      fetchLiveData();
    } catch {
      toast.error('Failed to start simulation');
    } finally { setLoading(false); }
  };

  const handleStop = async () => {
    setLoading(true);
    try {
      const res = await api.post('/simulation/stop');
      setStatus(res.data);
      toast.success('Simulation Stopped');
      fetchLiveData();
    } catch {
      toast.error('Failed to stop simulation');
    } finally { setLoading(false); }
  };

  // ── Provider Options for Filter Dropdown ───────────────────────────────────
  const providerOptions = useMemo(() => {
    const set = new Set();
    queue.forEach(i => i.provider_name && set.add(i.provider_name));
    return Array.from(set);
  }, [queue]);

  // ── Filtered Requests Computation ──────────────────────────────────────────
  // Requests being shown by the XAI highlight overlay are excluded from the
  // live-queue markers so they are not drawn twice.
  const highlightRequestIds = useMemo(
    () => new Set(xaiHighlight?.requestIds || []),
    [xaiHighlight],
  );

  const filteredRequests = useMemo(() => {
    return queue
      .filter(item => !highlightRequestIds.has(item.id))
      .filter(item => {
        const searchLower = searchTerm.toLowerCase();
        const matchesSearch = !searchTerm || (
          String(item.id).includes(searchLower) ||
          (item.provider_name && item.provider_name.toLowerCase().includes(searchLower)) ||
          (item.pickup_address && item.pickup_address.toLowerCase().includes(searchLower)) ||
          (item.drop_address && item.drop_address.toLowerCase().includes(searchLower))
        );

        const matchesType = filterType === 'All' || item.request_type?.toLowerCase() === filterType.toLowerCase();
        const matchesProvider = filterProvider === 'All' || item.provider_name === filterProvider;
        const matchesPriority = filterPriority === 'All' || item.priority === filterPriority;

        return matchesSearch && matchesType && matchesProvider && matchesPriority;
      });
  }, [queue, searchTerm, filterType, filterProvider, filterPriority, highlightRequestIds]);

  const handleResetFilters = () => {
    setSearchTerm('');
    setFilterType('All');
    setFilterProvider('All');
    setFilterPriority('All');
  };

  const hasFilters = searchTerm || filterType !== 'All' || filterProvider !== 'All' || filterPriority !== 'All';
  const hasSelection = Boolean(selectedRequest || selectedVehicle || xaiHighlight || xaiLoading || xaiError);
  const engineActive = status.running && !status.paused;

  return (
    <div className="h-full flex flex-col">
      <motion.div
        initial={{ opacity: 0, scale: 0.992 }}
        animate={{ opacity: 1, scale: 1 }}
        transition={{ duration: 0.5, ease: [0.22, 1, 0.36, 1] }}
        className="relative flex-1 min-h-0 rounded-[28px] overflow-hidden glass-panel-strong border border-white/[0.08]"
      >
        <LiveMapContainer
          mode="operations"
          requests={filteredRequests}
          vehicles={vehicles}
          activeTrips={activeTrips}
          selectedRequest={selectedRequest}
          onSelectRequest={handleSelectRequest}
          onClosePopup={() => setSelectedRequest(null)}
          selectedVehicleId={selectedVehicle?.vehicle_id ?? null}
          onSelectVehicle={handleSelectVehicle}
          xaiHighlight={xaiHighlight}
          className="absolute inset-0"
        />

        {/* Floating top control bar: engine state, Start/Stop, search */}
        <div className="absolute top-4 inset-x-0 z-30 flex justify-center px-4 pointer-events-none">
          <KpiBar
            status={status}
            engineActive={engineActive}
            loading={loading}
            onStartResume={handleStartResume}
            onStop={handleStop}
            searchTerm={searchTerm}
            onSearchChange={setSearchTerm}
          />
        </div>

        {/* Active trips */}
        {activeTrips.length > 0 && (
          <div className="absolute inset-x-4 bottom-6 md:inset-x-auto md:left-4 z-20 pointer-events-none flex justify-center md:justify-start">
            <ActiveTripsPanel trips={activeTrips} onCompleted={refreshNetwork} />
          </div>
        )}

        {/* Compact left filter panel */}
        <div className="absolute left-4 top-20 z-30 pointer-events-none">
          <MapFilterPanel
            filterType={filterType}
            onFilterTypeChange={setFilterType}
            filterProvider={filterProvider}
            onFilterProviderChange={setFilterProvider}
            filterPriority={filterPriority}
            onFilterPriorityChange={setFilterPriority}
            providerOptions={providerOptions}
            hasFilters={hasFilters}
            onResetFilters={handleResetFilters}
          />
        </div>

        {/* Right inspector (or bottom sheet on mobile) */}
        {hasSelection && panelOpen && (
          <div className="absolute inset-x-4 bottom-6 md:inset-x-auto md:right-4 md:top-20 md:bottom-auto z-40 pointer-events-none flex justify-center md:justify-end">
            <TripDetailsPanel
              selectedRequest={selectedRequest}
              selectedVehicle={selectedVehicle}
              xaiHighlight={xaiHighlight}
              xaiLoading={xaiLoading}
              xaiError={xaiError}
              onCloseTrip={() => setSelectedRequest(null)}
              onCloseVehicle={() => setSelectedVehicle(null)}
              onDismissXai={clearXaiFocus}
            />
          </div>
        )}
        {hasSelection && !panelOpen && (
          <button
            onClick={() => setPanelOpen(true)}
            className="absolute right-4 bottom-6 md:top-20 md:bottom-auto z-40 pointer-events-auto bg-[#0A0F1A]/80 backdrop-blur-xl border border-white/10 rounded-xl px-3 py-2 text-[11px] text-white/70 hover:text-white hover:border-[#00F0FF]/40 transition-colors shadow-lg"
          >
            Show details
          </button>
        )}

        {/* Soft inner vignette so overlays sit on a calm backdrop */}
        <div className="absolute inset-0 pointer-events-none rounded-[28px] shadow-[inset_0_0_120px_rgba(5,8,22,0.55)] border border-white/[0.04]" />
      </motion.div>
    </div>
  );
}