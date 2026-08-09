import React, { useState, useEffect, useRef, useCallback } from 'react';
import { Users, Truck, History, Search, Filter, RotateCcw, MapPin } from 'lucide-react';
import { motion, AnimatePresence } from 'framer-motion';
import api from '../services/api';
import toast from 'react-hot-toast';

import PageHeader from '../components/ui/PageHeader';
import StatusBadge from '../components/ui/StatusBadge';
import DriverStatistics from '../components/drivers/DriverStatistics';
import VehicleStatistics from '../components/drivers/VehicleStatistics';
import DriverTable from '../components/drivers/DriverTable';
import VehicleTable from '../components/drivers/VehicleTable';
import AssignmentHistory from '../components/drivers/AssignmentHistory';
import VehicleLocationMap from '../components/drivers/VehicleLocationMap';

export default function DriverDashboard() {
  const [activeTab, setActiveTab] = useState('drivers');

  const [search, setSearch] = useState('');
  const [filters, setFilters] = useState({
    provider_id: 'All',
    vehicle_type: 'All',
    driver_status: 'All',
  });

  const [drivers, setDrivers] = useState([]);
  const [vehicles, setVehicles] = useState([]);
  const [providers, setProviders] = useState([]);
  const [driverStats, setDriverStats] = useState({});
  const [vehicleStats, setVehicleStats] = useState({});
  const [locations, setLocations] = useState([]);
  const [assignmentHistory, setAssignmentHistory] = useState([]);

  const pollRef = useRef(null);

  const fetchData = useCallback(async () => {
    try {
      const dParams = new URLSearchParams();
      if (search) dParams.append('search', search);
      if (filters.provider_id !== 'All') dParams.append('provider_id', filters.provider_id);
      if (filters.driver_status !== 'All') dParams.append('status', filters.driver_status);

      const vParams = new URLSearchParams();
      if (search) vParams.append('search', search);
      if (filters.provider_id !== 'All') vParams.append('provider_id', filters.provider_id);
      if (filters.vehicle_type !== 'All') vParams.append('vehicle_type', filters.vehicle_type);

      const [dListRes, dStatsRes, vListRes, vStatsRes, pListRes, locRes, histRes] = await Promise.all([
        api.get(`/drivers?${dParams.toString()}`),
        api.get('/drivers/stats'),
        api.get(`/vehicles?${vParams.toString()}`),
        api.get('/vehicles/stats'),
        api.get('/providers'),
        api.get('/vehicles/locations'),
        api.get('/drivers/assignments/history?limit=100'),
      ]);

      setDrivers(dListRes.data || []);
      setDriverStats(dStatsRes.data || {});
      setVehicles(vListRes.data || []);
      setVehicleStats(vStatsRes.data || {});
      setProviders(pListRes.data || []);
      setLocations(locRes.data || []);
      setAssignmentHistory(histRes.data || []);
    } catch (err) {
      console.error('Failed to fetch Driver & Vehicle data:', err);
    }
  }, [search, filters]);

  useEffect(() => {
    fetchData();
    pollRef.current = setInterval(() => { if (document.visibilityState === 'visible') fetchData(); }, 2500);
    return () => clearInterval(pollRef.current);
  }, [fetchData]);

  const handleResetFilters = () => {
    setSearch('');
    setFilters({ provider_id: 'All', vehicle_type: 'All', driver_status: 'All' });
  };

  const handleAddDriver = async (driverData) => {
    try {
      await api.post('/drivers', driverData);
      fetchData();
      toast.success('Driver added successfully');
    } catch {
      toast.error('Failed to add driver');
    }
  };

  const handleEditDriver = async (id, driverData) => {
    try {
      await api.patch(`/drivers/${id}`, driverData);
      fetchData();
      toast.success('Driver updated');
    } catch {
      toast.error('Failed to update driver');
    }
  };

  const handleDeleteDriver = async (id) => {
    if (!confirm('Are you sure you want to delete this driver?')) return;
    try {
      await api.delete(`/drivers/${id}`);
      fetchData();
      toast.success('Driver deleted');
    } catch {
      toast.error('Failed to delete driver');
    }
  };

  const handleAddVehicle = async (vehicleData) => {
    try {
      await api.post('/vehicles', vehicleData);
      fetchData();
      toast.success('Vehicle registered successfully');
    } catch {
      toast.error('Failed to add vehicle');
    }
  };

  const handleEditVehicle = async (id, vehicleData) => {
    try {
      await api.patch(`/vehicles/${id}`, vehicleData);
      fetchData();
      toast.success('Vehicle updated');
    } catch {
      toast.error('Failed to update vehicle');
    }
  };

  const handleDeleteVehicle = async (id) => {
    if (!confirm('Are you sure you want to delete this vehicle?')) return;
    try {
      await api.delete(`/vehicles/${id}`);
      fetchData();
      toast.success('Vehicle deleted');
    } catch {
      toast.error('Failed to delete vehicle');
    }
  };

  const TABS = [
    { id: 'drivers', label: 'Driver Roster', icon: Users, count: drivers.length },
    { id: 'vehicles', label: 'Vehicle Fleet', icon: Truck, count: vehicles.length },
    { id: 'map', label: 'Fleet Locations', icon: MapPin, count: locations.length },
    { id: 'history', label: 'Assignment History', icon: History, count: assignmentHistory.length },
  ];

  return (
    <div className="space-y-7 max-w-[1500px] mx-auto">
      <PageHeader
        eyebrow="Fleet"
        live
        title="Drivers & Vehicles"
        description="Roster, vehicle status and assignment audit — refreshed from the network every 2.5 seconds (positions are simulated, not live GPS)."
        actions={<StatusBadge tone="success" label="Auto-refresh 2.5s" pulse />}
      />

      {/* ── Stats ────────────────────────────────────────────────────────── */}
      <div className="space-y-5">
        <div>
          <h3 className="section-label mb-3">Driver Network</h3>
          <DriverStatistics stats={driverStats} />
        </div>
        <div>
          <h3 className="section-label mb-3">Vehicle Fleet</h3>
          <VehicleStatistics stats={vehicleStats} />
        </div>
      </div>

      {/* ── Search & filters ─────────────────────────────────────────────── */}
      <motion.div
        initial={{ opacity: 0, y: 10 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.5, ease: [0.22, 1, 0.36, 1] }}
        className="glass-panel rounded-[20px] p-4 flex flex-col lg:flex-row gap-3 lg:items-center"
      >
        <div className="relative flex-1 min-w-[260px]">
          <Search className="absolute left-4 top-1/2 -translate-y-1/2 h-4 w-4 text-brand-text-muted pointer-events-none" />
          <input
            type="text"
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            placeholder="Search driver, phone, vehicle registration…"
            className="input-glass !pl-11"
          />
        </div>

        <div className="flex flex-wrap items-center gap-2.5">
          <span className="hidden md:flex items-center gap-1.5 text-brand-text-muted">
            <Filter className="h-3.5 w-3.5" />
          </span>
          <select
            value={filters.provider_id}
            onChange={(e) => setFilters({ ...filters, provider_id: e.target.value })}
            className="select-glass max-w-[160px]"
          >
            <option value="All">All Providers</option>
            {providers.map((p) => (
              <option key={p.id} value={p.id}>{p.name}</option>
            ))}
          </select>

          <select
            value={filters.vehicle_type}
            onChange={(e) => setFilters({ ...filters, vehicle_type: e.target.value })}
            className="select-glass"
          >
            <option value="All">All Vehicles</option>
            {['Bike', 'Auto', 'Car', 'Van', 'Truck'].map((t) => (
              <option key={t} value={t}>{t}</option>
            ))}
          </select>

          <select
            value={filters.driver_status}
            onChange={(e) => setFilters({ ...filters, driver_status: e.target.value })}
            className="select-glass"
          >
            <option value="All">All Statuses</option>
            {['Available', 'Busy', 'Offline'].map((s) => (
              <option key={s} value={s}>{s}</option>
            ))}
          </select>

          <button onClick={handleResetFilters} className="btn-ghost !text-brand-primary">
            <RotateCcw className="h-3.5 w-3.5" /> Reset
          </button>
        </div>
      </motion.div>

      {/* ── Tabs & content ───────────────────────────────────────────────── */}
      <div className="space-y-5">
        <div className="glass-panel rounded-[18px] p-1.5 flex items-center gap-1.5 overflow-x-auto custom-scrollbar">
          {TABS.map((tab) => (
            <button
              key={tab.id}
              onClick={() => setActiveTab(tab.id)}
              className={`tab-pill shrink-0 ${activeTab === tab.id ? 'tab-pill-active' : ''}`}
            >
              <tab.icon className="h-4 w-4" />
              {tab.label}
              <span className={`px-1.5 py-0.5 rounded-full text-[10px] font-bold ${
                activeTab === tab.id ? 'bg-white/15 text-white' : 'bg-white/[0.06] text-brand-text-muted'
              }`}>
                {tab.count}
              </span>
            </button>
          ))}
        </div>

        <AnimatePresence mode="wait">
          <motion.div
            key={activeTab}
            initial={{ opacity: 0, y: 12 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: -8 }}
            transition={{ duration: 0.3, ease: [0.22, 1, 0.36, 1] }}
          >
            {activeTab === 'drivers' && (
              <DriverTable
                drivers={drivers}
                providers={providers}
                vehicles={vehicles}
                onAdd={handleAddDriver}
                onEdit={handleEditDriver}
                onDelete={handleDeleteDriver}
              />
            )}
            {activeTab === 'vehicles' && (
              <VehicleTable
                vehicles={vehicles}
                providers={providers}
                drivers={drivers}
                onAdd={handleAddVehicle}
                onEdit={handleEditVehicle}
                onDelete={handleDeleteVehicle}
              />
            )}
            {activeTab === 'map' && (
              <VehicleLocationMap locations={locations} onRefresh={fetchData} />
            )}
            {activeTab === 'history' && (
              <AssignmentHistory history={assignmentHistory} />
            )}
          </motion.div>
        </AnimatePresence>
      </div>
    </div>
  );
}