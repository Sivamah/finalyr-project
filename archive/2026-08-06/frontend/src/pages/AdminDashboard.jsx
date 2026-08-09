import { useState, useEffect, useCallback } from 'react';
import {
  Users, Activity, BarChart3, Car, UtensilsCrossed, Package,
  Shield, RefreshCw, Loader2, ChevronDown, Search, Edit2, Calendar, Brain
} from 'lucide-react';
import StatusBadge from '../components/bookings/StatusBadge';
import { listUsers, changeRole, listAllBookings, forceBookingStatus } from '../services/adminService';
import { dmfeService } from '../services/dmfeService';
import toast from 'react-hot-toast';
import TripSchedulerTab from '../components/admin/TripSchedulerTab';
import DriverAllocationTab from '../components/admin/DriverAllocationTab';
import AnalyticsTab from '../components/admin/AnalyticsTab';
import AIInsightsTab from '../components/admin/AIInsightsTab';

const BOOKING_STATUSES = ['Pending', 'Accepted', 'In_Progress', 'Completed', 'Cancelled'];
const ROLES            = ['Admin', 'Driver', 'Customer'];

// ─────────────────────────────────────────────
// Stat Card
// ─────────────────────────────────────────────
function StatCard({ label, value, icon: Icon, color, sub }) {
  return (
    <div className="bg-white rounded-xl border border-gray-100 shadow-sm p-5">
      <div className="flex items-center justify-between mb-3">
        <p className="text-sm font-medium text-gray-500">{label}</p>
        <div className={`p-2 rounded-lg ${color}`}>
          <Icon className="h-4 w-4 text-white" />
        </div>
      </div>
      <p className="text-3xl font-bold text-gray-900">{value}</p>
      {sub && <p className="text-xs text-gray-400 mt-1">{sub}</p>}
    </div>
  );
}

// ─────────────────────────────────────────────
// Admin Dashboard
// ─────────────────────────────────────────────
export default function AdminDashboard() {
  const [activeTab,  setActiveTab]  = useState('analytics');
  const [users,      setUsers]      = useState([]);
  const [bookings,   setBookings]   = useState([]);
  const [loading,    setLoading]    = useState(false);
  const [userSearch, setUserSearch] = useState('');
  const [roleFilter, setRoleFilter] = useState('All');
  const [typeFilter, setTypeFilter] = useState('');
  const [statusFlt,  setStatusFlt]  = useState('');
  const [changingRole, setChangingRole] = useState(null);
  const [forcingStatus, setForcingStatus] = useState(null);
  const [optimizing, setOptimizing] = useState(false);

  const loadUsers = useCallback(async () => {
    setLoading(true);
    try {
      const params = roleFilter !== 'All' ? { role: roleFilter } : {};
      const r = await listUsers(params);
      setUsers(r.data);
    } catch { toast.error('Failed to load users'); }
    setLoading(false);
  }, [roleFilter]);

  const loadBookings = useCallback(async () => {
    setLoading(true);
    try {
      const params = {};
      if (typeFilter)  params.booking_type = typeFilter;
      if (statusFlt)   params.status = statusFlt;
      const r = await listAllBookings(params);
      setBookings(r.data);
    } catch { toast.error('Failed to load bookings'); }
    setLoading(false);
  }, [typeFilter, statusFlt]);

  useEffect(() => { if (activeTab === 'users')    loadUsers();    }, [activeTab, loadUsers]);
  useEffect(() => { if (activeTab === 'bookings') loadBookings(); }, [activeTab, loadBookings]);

  const handleRoleChange = async (userId, newRole) => {
    setChangingRole(userId);
    try {
      await changeRole(userId, newRole);
      toast.success(`Role changed to ${newRole}`);
      loadUsers();
    } catch (err) { toast.error(err.response?.data?.detail || 'Failed'); }
    setChangingRole(null);
  };

  const handleForceStatus = async (booking, newStatus) => {
    const key = `${booking.type}-${booking.id}`;
    setForcingStatus(key);
    try {
      await forceBookingStatus(booking.type, booking.id, newStatus);
      toast.success(`Status → ${newStatus}`);
      loadBookings();
    } catch (err) { toast.error(err.response?.data?.detail || 'Failed'); }
    setForcingStatus(null);
  };

  const handleRunDMFE = async () => {
    setOptimizing(true);
    try {
      const res = await dmfeService.triggerOptimization();
      toast.success(`${res.message} (${res.batches_created} batches formed)`);
      if (activeTab === 'bookings') loadBookings();
    } catch (err) {
      toast.error('DMFE Error: ' + (err.response?.data?.detail || err.message));
    }
    setOptimizing(false);
  };

  const filteredUsers = users.filter((u) =>
    u.full_name?.toLowerCase().includes(userSearch.toLowerCase()) ||
    u.email?.toLowerCase().includes(userSearch.toLowerCase())
  );

  const TYPE_ICON = { ride: Car, food: UtensilsCrossed, parcel: Package };

  return (
    <div className="flex-1 w-full space-y-6 max-w-6xl mx-auto">
      {/* Header */}
      <div className="bg-gradient-to-r from-slate-800 to-indigo-900 rounded-2xl p-6 text-white shadow-lg flex justify-between items-center flex-wrap gap-4">
        <div className="flex items-center gap-3">
          <div className="p-2.5 bg-white/10 rounded-xl">
            <Shield className="h-6 w-6 text-white" />
          </div>
          <div>
            <h1 className="text-xl font-bold">Admin Control Panel</h1>
            <p className="text-slate-300 text-sm">Manage users, bookings, and system operations</p>
          </div>
        </div>
        <button 
          onClick={handleRunDMFE} 
          disabled={optimizing}
          className="bg-emerald-500 hover:bg-emerald-600 text-white px-4 py-2 rounded-xl text-sm font-semibold transition-colors flex items-center gap-2 shadow-sm disabled:opacity-50 whitespace-nowrap">
          {optimizing ? <Loader2 className="h-4 w-4 animate-spin" /> : <RefreshCw className="h-4 w-4" />}
          Run DMFE Optimization
        </button>
      </div>

      {/* Tab nav */}
      <div className="flex gap-2 flex-wrap">
        {[
          { id: 'analytics', label: 'Analytics & Reports', icon: BarChart3 },
          { id: 'ai',        label: 'AI Insights',     icon: Brain },
          { id: 'users',     label: 'Users',           icon: Users },
          { id: 'bookings',  label: 'All Bookings',    icon: Activity },
          { id: 'scheduler', label: 'Trip Scheduler',  icon: Calendar },
          { id: 'allocation',label: 'Allocation Engine',icon: RefreshCw },
        ].map((t) => {
          const TIcon = t.icon;
          return (
            <button key={t.id} onClick={() => setActiveTab(t.id)}
              className={`flex items-center gap-2 px-5 py-2 rounded-full text-sm font-medium transition-all
                ${activeTab === t.id
                  ? 'bg-indigo-700 text-white shadow-sm'
                  : 'bg-white text-gray-600 border border-gray-200 hover:border-indigo-300'
                }`}>
              <TIcon className="h-4 w-4" /> {t.label}
            </button>
          );
        })}
        <button onClick={() => { if (activeTab === 'users') loadUsers(); if (activeTab === 'bookings') loadBookings(); }}
          className="ml-auto text-sm text-indigo-600 flex items-center gap-1 hover:text-indigo-800">
          <RefreshCw className={`h-4 w-4 ${loading ? 'animate-spin' : ''}`} /> Refresh
        </button>
      </div>

      {/* ── ANALYTICS TAB ── */}
      {activeTab === 'analytics' && <AnalyticsTab />}

      {/* ── USERS TAB ── */}
      {activeTab === 'users' && (
        <div className="space-y-4">
          {/* Filters */}
          <div className="flex flex-wrap gap-3 items-center">
            <div className="relative flex-1 min-w-[200px]">
              <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-gray-400" />
              <input type="text" value={userSearch} onChange={(e) => setUserSearch(e.target.value)}
                placeholder="Search by name or email…"
                className="w-full pl-9 pr-4 py-2 border border-gray-200 rounded-xl text-sm focus:outline-none focus:border-indigo-400" />
            </div>
            <div className="flex gap-2">
              {['All', ...ROLES].map((r) => (
                <button key={r} onClick={() => setRoleFilter(r)}
                  className={`px-3 py-2 rounded-xl text-xs font-medium border transition-all
                    ${roleFilter === r ? 'bg-indigo-600 text-white border-indigo-600' : 'bg-white text-gray-600 border-gray-200'}`}>
                  {r}
                </button>
              ))}
            </div>
          </div>

          {/* Users table */}
          <div className="bg-white rounded-xl border border-gray-100 shadow-sm overflow-hidden">
            <div className="overflow-x-auto">
              <table className="w-full text-sm">
                <thead className="bg-gray-50 border-b border-gray-100">
                  <tr>
                    {['ID', 'Name', 'Email', 'Phone', 'Role', 'Joined', 'Actions'].map((h) => (
                      <th key={h} className="px-4 py-3 text-left text-xs font-semibold text-gray-500 uppercase tracking-wide">{h}</th>
                    ))}
                  </tr>
                </thead>
                <tbody className="divide-y divide-gray-50">
                  {loading ? (
                    <tr><td colSpan={7} className="text-center py-12">
                      <Loader2 className="h-6 w-6 animate-spin text-indigo-500 mx-auto" />
                    </td></tr>
                  ) : filteredUsers.length === 0 ? (
                    <tr><td colSpan={7} className="text-center py-12 text-gray-400">No users found</td></tr>
                  ) : filteredUsers.map((u) => (
                    <tr key={u.id} className="hover:bg-gray-50 transition-colors">
                      <td className="px-4 py-3 text-gray-400">#{u.id}</td>
                      <td className="px-4 py-3 font-medium text-gray-900">{u.full_name}</td>
                      <td className="px-4 py-3 text-gray-600">{u.email}</td>
                      <td className="px-4 py-3 text-gray-600">{u.phone || '—'}</td>
                      <td className="px-4 py-3">
                        <span className={`px-2 py-1 rounded-full text-xs font-semibold
                          ${u.role === 'Admin'    ? 'bg-red-100 text-red-700' :
                            u.role === 'Driver'   ? 'bg-violet-100 text-violet-700' :
                                                    'bg-blue-100 text-blue-700'}`}>
                          {u.role}
                        </span>
                      </td>
                      <td className="px-4 py-3 text-gray-400 text-xs">
                        {u.created_at ? new Date(u.created_at).toLocaleDateString('en-IN') : '—'}
                      </td>
                      <td className="px-4 py-3">
                        <div className="flex items-center gap-2">
                          <Edit2 className="h-3.5 w-3.5 text-gray-400" />
                          <select
                            value={u.role}
                            onChange={(e) => handleRoleChange(u.id, e.target.value)}
                            disabled={changingRole === u.id}
                            className="text-xs border border-gray-200 rounded-lg px-2 py-1 focus:outline-none focus:border-indigo-400 disabled:opacity-50"
                          >
                            {ROLES.map((r) => <option key={r}>{r}</option>)}
                          </select>
                          {changingRole === u.id && <Loader2 className="h-3 w-3 animate-spin text-indigo-500" />}
                        </div>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        </div>
      )}

      {/* ── BOOKINGS TAB ── */}
      {activeTab === 'bookings' && (
        <div className="space-y-4">
          {/* Filters */}
          <div className="flex flex-wrap gap-3">
            <select value={typeFilter} onChange={(e) => setTypeFilter(e.target.value)}
              className="px-4 py-2 border border-gray-200 rounded-xl text-sm focus:outline-none focus:border-indigo-400">
              <option value="">All Types</option>
              <option value="ride">Rides</option>
              <option value="food">Food</option>
              <option value="parcel">Parcels</option>
            </select>
            <select value={statusFlt} onChange={(e) => setStatusFlt(e.target.value)}
              className="px-4 py-2 border border-gray-200 rounded-xl text-sm focus:outline-none focus:border-indigo-400">
              <option value="">All Statuses</option>
              {BOOKING_STATUSES.map((s) => <option key={s}>{s}</option>)}
            </select>
          </div>

          {/* Bookings table */}
          <div className="bg-white rounded-xl border border-gray-100 shadow-sm overflow-hidden">
            <div className="overflow-x-auto">
              <table className="w-full text-sm">
                <thead className="bg-gray-50 border-b border-gray-100">
                  <tr>
                    {['ID', 'Type', 'Customer', 'Driver', 'From', 'To', 'Fare', 'Status', 'Override', 'Created'].map((h) => (
                      <th key={h} className="px-4 py-3 text-left text-xs font-semibold text-gray-500 uppercase tracking-wide whitespace-nowrap">{h}</th>
                    ))}
                  </tr>
                </thead>
                <tbody className="divide-y divide-gray-50">
                  {loading ? (
                    <tr><td colSpan={10} className="text-center py-12">
                      <Loader2 className="h-6 w-6 animate-spin text-indigo-500 mx-auto" />
                    </td></tr>
                  ) : bookings.length === 0 ? (
                    <tr><td colSpan={10} className="text-center py-12 text-gray-400">No bookings found</td></tr>
                  ) : bookings.map((b) => {
                    const TIcon = TYPE_ICON[b.type] || Car;
                    const key   = `${b.type}-${b.id}`;
                    return (
                      <tr key={key} className="hover:bg-gray-50 transition-colors">
                        <td className="px-4 py-3 text-gray-400">#{b.id}</td>
                        <td className="px-4 py-3">
                          <div className="flex items-center gap-1.5">
                            <TIcon className="h-4 w-4 text-indigo-500" />
                            <span className="capitalize text-gray-700">{b.type}</span>
                          </div>
                        </td>
                        <td className="px-4 py-3 text-gray-600">#{b.customer_id}</td>
                        <td className="px-4 py-3 text-gray-600">{b.driver_id ? `#${b.driver_id}` : <span className="text-gray-300">—</span>}</td>
                        <td className="px-4 py-3 text-gray-700 max-w-[140px] truncate">{b.from || b.restaurant || '—'}</td>
                        <td className="px-4 py-3 text-gray-700 max-w-[140px] truncate">{b.to || '—'}</td>
                        <td className="px-4 py-3 text-emerald-700 font-medium">{b.fare ? `₹${b.fare}` : '—'}</td>
                        <td className="px-4 py-3"><StatusBadge status={b.status} size="sm" /></td>
                        <td className="px-4 py-3">
                          <div className="flex items-center gap-1">
                            <select
                              defaultValue={b.status}
                              onChange={(e) => handleForceStatus(b, e.target.value)}
                              disabled={forcingStatus === key}
                              className="text-xs border border-gray-200 rounded-lg px-2 py-1 focus:outline-none focus:border-indigo-400 disabled:opacity-50"
                            >
                              {BOOKING_STATUSES.map((s) => <option key={s}>{s}</option>)}
                            </select>
                            {forcingStatus === key && <Loader2 className="h-3 w-3 animate-spin text-indigo-500" />}
                          </div>
                        </td>
                        <td className="px-4 py-3 text-gray-400 text-xs whitespace-nowrap">
                          {b.created_at ? new Date(b.created_at).toLocaleDateString('en-IN') : '—'}
                        </td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>
          </div>
        </div>
      )}

      {/* ── SCHEDULER TAB ── */}
      {activeTab === 'scheduler' && <TripSchedulerTab />}

      {/* ── ALLOCATION TAB ── */}
      {activeTab === 'allocation' && <DriverAllocationTab />}

      {/* ── AI INSIGHTS TAB ── */}
      {activeTab === 'ai' && <AIInsightsTab />}
    </div>
  );
}
