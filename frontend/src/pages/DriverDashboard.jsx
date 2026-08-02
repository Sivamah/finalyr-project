import React, { useState, useEffect, useRef, useCallback } from 'react';
import { Users, Truck, Navigation, History, Search, Filter, RotateCcw, ShieldCheck } from 'lucide-react';
import api from '../services/api';
import toast from 'react-hot-toast';

import DriverStatistics from '../components/drivers/DriverStatistics';
import VehicleStatistics from '../components/drivers/VehicleStatistics';
import DriverTable from '../components/drivers/DriverTable';
import VehicleTable from '../components/drivers/VehicleTable';
import AssignmentHistory from '../components/drivers/AssignmentHistory';
import VehicleLocationMap from '../components/drivers/VehicleLocationMap';

export default function DriverDashboard() {
  const [activeTab, setActiveTab] = useState('drivers'); // 'drivers' | 'vehicles' | 'map' | 'history'

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

  // Fetch all driver & vehicle data
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

  // Polling: 2.5s
  useEffect(() => {
    fetchData();
    pollRef.current = setInterval(fetchData, 2500);
    return () => clearInterval(pollRef.current);
  }, [fetchData]);

  // Handlers
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

  return (
    <div className="space-y-6 pb-12">
      {/* ── Page Header ────────────────────────────────────────────────────────── */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold text-white flex items-center gap-2">
            <Users className="h-6 w-6 text-indigo-400" />
            Driver & Vehicle Management
          </h1>
          <p className="text-sm text-gray-400 mt-1">
            Manage drivers, vehicle fleet, live telemetry locations, and assignment audit logs
          </p>
        </div>

        {/* Live Refresh Badge */}
        <div className="flex items-center gap-1.5 px-3.5 py-2 bg-green-500/10 border border-green-500/30 rounded-lg text-xs font-semibold text-green-400 w-fit">
          <span className="w-2 h-2 rounded-full bg-green-400 animate-pulse" />
          Live Auto-Refresh (2.5s)
        </div>
      </div>

      {/* ── 1. Dual Statistics Section ───────────────────────────────────────── */}
      <div className="space-y-2">
        <h3 className="text-xs font-bold uppercase tracking-wider text-gray-400 mb-2">Driver Fleet Overview</h3>
        <DriverStatistics stats={driverStats} />

        <h3 className="text-xs font-bold uppercase tracking-wider text-gray-400 mb-2 pt-2">Vehicle Fleet Overview</h3>
        <VehicleStatistics stats={vehicleStats} />
      </div>

      {/* ── 2. Global Search & Filter Toolbar ─────────────────────────────────── */}
      <div className="bg-gray-800 border border-gray-700 rounded-xl p-4 shadow-sm">
        <div className="flex flex-col lg:flex-row gap-4 items-stretch lg:items-center justify-between">
          {/* Search */}
          <div className="relative flex-1 min-w-[280px]">
            <Search className="absolute left-3.5 top-2.5 h-4 w-4 text-gray-400" />
            <input
              type="text"
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              placeholder="Search by Driver Name, Phone, Vehicle Reg #, or Type..."
              className="w-full pl-10 pr-4 py-2 bg-gray-900 border border-gray-700 rounded-lg text-sm text-white placeholder-gray-500 focus:outline-none focus:ring-2 focus:ring-indigo-500"
            />
          </div>

          {/* Filters */}
          <div className="flex flex-wrap items-center gap-3">
            {/* Provider Filter */}
            <div className="flex items-center gap-1.5 bg-gray-900 border border-gray-700 rounded-lg px-3 py-1.5">
              <Filter className="h-3.5 w-3.5 text-indigo-400" />
              <select
                value={filters.provider_id}
                onChange={(e) => setFilters({ ...filters, provider_id: e.target.value })}
                className="bg-transparent text-gray-200 text-xs font-medium focus:outline-none cursor-pointer"
              >
                <option value="All" className="bg-gray-800 text-white">All Providers</option>
                {providers.map((p) => (
                  <option key={p.id} value={p.id} className="bg-gray-800 text-white">{p.name}</option>
                ))}
              </select>
            </div>

            {/* Vehicle Type Filter */}
            <div className="flex items-center gap-1.5 bg-gray-900 border border-gray-700 rounded-lg px-3 py-1.5">
              <Truck className="h-3.5 w-3.5 text-blue-400" />
              <select
                value={filters.vehicle_type}
                onChange={(e) => setFilters({ ...filters, vehicle_type: e.target.value })}
                className="bg-transparent text-gray-200 text-xs font-medium focus:outline-none cursor-pointer"
              >
                <option value="All" className="bg-gray-800 text-white">All Vehicle Types</option>
                <option value="Bike" className="bg-gray-800 text-white">Bike</option>
                <option value="Auto" className="bg-gray-800 text-white">Auto</option>
                <option value="Car" className="bg-gray-800 text-white">Car</option>
                <option value="Van" className="bg-gray-800 text-white">Van</option>
                <option value="Truck" className="bg-gray-800 text-white">Truck</option>
              </select>
            </div>

            {/* Driver Status Filter */}
            <div className="flex items-center gap-1.5 bg-gray-900 border border-gray-700 rounded-lg px-3 py-1.5">
              <ShieldCheck className="h-3.5 w-3.5 text-green-400" />
              <select
                value={filters.driver_status}
                onChange={(e) => setFilters({ ...filters, driver_status: e.target.value })}
                className="bg-transparent text-gray-200 text-xs font-medium focus:outline-none cursor-pointer"
              >
                <option value="All" className="bg-gray-800 text-white">All Driver Statuses</option>
                <option value="Available" className="bg-gray-800 text-white">Available</option>
                <option value="Busy" className="bg-gray-800 text-white">Busy</option>
                <option value="Offline" className="bg-gray-800 text-white">Offline</option>
              </select>
            </div>

            {/* Reset */}
            <button
              onClick={handleResetFilters}
              className="flex items-center gap-1 px-3 py-1.5 bg-gray-700 hover:bg-gray-600 text-gray-300 rounded-lg text-xs font-medium transition-colors"
            >
              <RotateCcw className="h-3.5 w-3.5" /> Reset
            </button>
          </div>
        </div>
      </div>

      {/* ── 3. Navigation Tabs & Content Views ───────────────────────────────── */}
      <div className="space-y-4">
        {/* Tabs Bar */}
        <div className="flex items-center border-b border-gray-700 overflow-x-auto">
          <button
            onClick={() => setActiveTab('drivers')}
            className={`flex items-center gap-2 py-3 px-5 font-bold text-sm border-b-2 whitespace-nowrap transition-colors ${
              activeTab === 'drivers'
                ? 'border-indigo-500 text-indigo-400'
                : 'border-transparent text-gray-400 hover:text-gray-200'
            }`}
          >
            <Users className="h-4 w-4" /> Driver Roster
            <span className="px-2 py-0.5 rounded-full text-xs bg-indigo-500/20 text-indigo-400 font-bold">
              {drivers.length}
            </span>
          </button>

          <button
            onClick={() => setActiveTab('vehicles')}
            className={`flex items-center gap-2 py-3 px-5 font-bold text-sm border-b-2 whitespace-nowrap transition-colors ${
              activeTab === 'vehicles'
                ? 'border-indigo-500 text-indigo-400'
                : 'border-transparent text-gray-400 hover:text-gray-200'
            }`}
          >
            <Truck className="h-4 w-4" /> Vehicle Fleet
            <span className="px-2 py-0.5 rounded-full text-xs bg-blue-500/20 text-blue-400 font-bold">
              {vehicles.length}
            </span>
          </button>

          <button
            onClick={() => setActiveTab('map')}
            className={`flex items-center gap-2 py-3 px-5 font-bold text-sm border-b-2 whitespace-nowrap transition-colors ${
              activeTab === 'map'
                ? 'border-indigo-500 text-indigo-400'
                : 'border-transparent text-gray-400 hover:text-gray-200'
            }`}
          >
            <Navigation className="h-4 w-4" /> Live Location Map
            <span className="px-2 py-0.5 rounded-full text-xs bg-green-500/20 text-green-400 font-bold">
              {locations.length}
            </span>
          </button>

          <button
            onClick={() => setActiveTab('history')}
            className={`flex items-center gap-2 py-3 px-5 font-bold text-sm border-b-2 whitespace-nowrap transition-colors ${
              activeTab === 'history'
                ? 'border-indigo-500 text-indigo-400'
                : 'border-transparent text-gray-400 hover:text-gray-200'
            }`}
          >
            <History className="h-4 w-4" /> Assignment History
            <span className="px-2 py-0.5 rounded-full text-xs bg-amber-500/20 text-amber-400 font-bold">
              {assignmentHistory.length}
            </span>
          </button>
        </div>

        {/* Tab 1: Driver Roster Table */}
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

        {/* Tab 2: Vehicle Fleet Table */}
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

        {/* Tab 3: Live Map */}
        {activeTab === 'map' && (
          <VehicleLocationMap locations={locations} onRefresh={fetchData} />
        )}

        {/* Tab 4: Assignment History */}
        {activeTab === 'history' && (
          <AssignmentHistory history={assignmentHistory} />
        )}
      </div>
    </div>
  );
}
