import React, { useState, useEffect } from 'react';
import { 
  BarChart, Bar, LineChart, Line, AreaChart, Area, PieChart, Pie, Cell, 
  XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer 
} from 'recharts';
import { 
  Download, Users, TrendingUp, Car, CheckCircle, Clock, 
  MapPin, Leaf, AlertCircle 
} from 'lucide-react';
import { getSummary, getTripAnalytics, getDriverAnalytics, exportReport } from '../../services/analyticsService';
import toast from 'react-hot-toast';

const COLORS = ['#4f46e5', '#10b981', '#f59e0b', '#ef4444', '#8b5cf6', '#06b6d4'];

export default function AnalyticsTab() {
  const [summary, setSummary] = useState(null);
  const [trips, setTrips] = useState([]);
  const [drivers, setDrivers] = useState({ status: [], vehicles: [] });
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    loadData();
  }, []);

  const loadData = async () => {
    setLoading(true);
    try {
      const [sumRes, tripRes, driverRes] = await Promise.all([
        getSummary(),
        getTripAnalytics(),
        getDriverAnalytics()
      ]);
      setSummary(sumRes);
      setTrips(tripRes.trend);
      setDrivers(driverRes);
    } catch (err) {
      toast.error('Failed to load analytics data');
    }
    setLoading(false);
  };

  const handleExport = async (type, report) => {
    try {
      await exportReport(type, report);
      toast.success(`${report} report exported successfully!`);
    } catch (err) {
      toast.error('Export failed');
    }
  };

  if (loading || !summary) {
    return (
      <div className="flex items-center justify-center py-24">
        <div className="animate-spin rounded-full h-12 w-12 border-t-2 border-b-2 border-indigo-600"></div>
      </div>
    );
  }

  // Derived metrics for DMFE
  const dmfePieData = [
    { name: 'Combined (Batched)', value: summary.combined_trips },
    { name: 'Single Trips', value: summary.single_trips }
  ];

  const tripStatusData = [
    { name: 'Completed', value: summary.completed_trips },
    { name: 'Pending', value: summary.pending_trips },
    { name: 'Cancelled', value: summary.cancelled_trips }
  ];

  return (
    <div className="space-y-6">
      {/* Top Action Bar */}
      <div className="flex justify-between items-center bg-white p-4 rounded-xl border border-gray-100 shadow-sm">
        <h2 className="text-lg font-bold text-gray-800">Platform Analytics</h2>
        <div className="flex gap-2">
          <button onClick={() => handleExport('csv', 'trips')} className="flex items-center gap-2 px-4 py-2 bg-indigo-50 text-indigo-700 rounded-lg text-sm font-semibold hover:bg-indigo-100 transition-colors">
            <Download className="h-4 w-4" /> Export Trips (CSV)
          </button>
          <button onClick={() => handleExport('csv', 'drivers')} className="flex items-center gap-2 px-4 py-2 bg-emerald-50 text-emerald-700 rounded-lg text-sm font-semibold hover:bg-emerald-100 transition-colors">
            <Download className="h-4 w-4" /> Export Drivers (CSV)
          </button>
        </div>
      </div>

      {/* KPI Cards */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        <KPICard title="Total Users" value={summary.total_users} sub={`${summary.active_customers} Customers`} icon={Users} color="bg-blue-500" />
        <KPICard title="Active Drivers" value={summary.active_drivers} sub={`${summary.online_drivers} Online Now`} icon={Car} color="bg-indigo-500" />
        <KPICard title="Total Trips" value={summary.total_trips} sub={`${summary.completed_trips} Completed`} icon={TrendingUp} color="bg-emerald-500" />
        <KPICard title="Avg Driver Rating" value={`${summary.average_rating} ★`} icon={CheckCircle} color="bg-amber-500" />
        
        {/* Environmental & DMFE Impact */}
        <KPICard title="Fuel Saved" value={`${summary.fuel_saved_l} L`} sub="Via DMFE Batches" icon={Leaf} color="bg-green-500" />
        <KPICard title="CO₂ Reduced" value={`${summary.co2_reduction_kg} kg`} icon={Leaf} color="bg-teal-500" />
        <KPICard title="Total Distance" value={`${summary.total_distance_km} km`} icon={MapPin} color="bg-slate-500" />
        <KPICard title="Combined Trips" value={summary.combined_trips} icon={Clock} color="bg-violet-500" />
      </div>

      {/* Charts Grid */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        
        {/* Trip Trend Chart */}
        <div className="bg-white p-5 rounded-xl border border-gray-100 shadow-sm">
          <h3 className="text-sm font-bold text-gray-700 mb-4">Trip Volume Trend</h3>
          <div className="h-72">
            <ResponsiveContainer width="100%" height="100%">
              <AreaChart data={trips}>
                <defs>
                  <linearGradient id="colorTrips" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="5%" stopColor="#4f46e5" stopOpacity={0.8}/>
                    <stop offset="95%" stopColor="#4f46e5" stopOpacity={0}/>
                  </linearGradient>
                </defs>
                <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="#e5e7eb" />
                <XAxis dataKey="date" axisLine={false} tickLine={false} tick={{fontSize: 12, fill: '#6b7280'}} />
                <YAxis axisLine={false} tickLine={false} tick={{fontSize: 12, fill: '#6b7280'}} />
                <Tooltip contentStyle={{borderRadius: '8px', border: 'none', boxShadow: '0 4px 6px -1px rgb(0 0 0 / 0.1)'}} />
                <Area type="monotone" dataKey="trips" stroke="#4f46e5" strokeWidth={3} fillOpacity={1} fill="url(#colorTrips)" />
              </AreaChart>
            </ResponsiveContainer>
          </div>
        </div>

        {/* Driver Status Chart */}
        <div className="bg-white p-5 rounded-xl border border-gray-100 shadow-sm">
          <h3 className="text-sm font-bold text-gray-700 mb-4">Driver Availability</h3>
          <div className="h-72">
            <ResponsiveContainer width="100%" height="100%">
              <PieChart>
                <Pie data={drivers.status} cx="50%" cy="50%" innerRadius={60} outerRadius={100} paddingAngle={5} dataKey="value" label>
                  {drivers.status.map((entry, index) => (
                    <Cell key={`cell-${index}`} fill={COLORS[index % COLORS.length]} />
                  ))}
                </Pie>
                <Tooltip />
                <Legend verticalAlign="bottom" height={36} />
              </PieChart>
            </ResponsiveContainer>
          </div>
        </div>

        {/* DMFE Efficacy (Combined vs Single) */}
        <div className="bg-white p-5 rounded-xl border border-gray-100 shadow-sm">
          <h3 className="text-sm font-bold text-gray-700 mb-4">DMFE Optimization (Trips)</h3>
          <div className="h-72">
            <ResponsiveContainer width="100%" height="100%">
              <PieChart>
                <Pie data={dmfePieData} cx="50%" cy="50%" outerRadius={100} dataKey="value" label>
                  <Cell fill="#8b5cf6" />
                  <Cell fill="#94a3b8" />
                </Pie>
                <Tooltip />
                <Legend verticalAlign="bottom" height={36} />
              </PieChart>
            </ResponsiveContainer>
          </div>
        </div>

        {/* Driver Vehicle Breakdown */}
        <div className="bg-white p-5 rounded-xl border border-gray-100 shadow-sm">
          <h3 className="text-sm font-bold text-gray-700 mb-4">Driver Fleet Types</h3>
          <div className="h-72">
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={drivers.vehicles} layout="vertical" margin={{ top: 5, right: 30, left: 20, bottom: 5 }}>
                <CartesianGrid strokeDasharray="3 3" horizontal={false} stroke="#e5e7eb" />
                <XAxis type="number" axisLine={false} tickLine={false} />
                <YAxis dataKey="name" type="category" axisLine={false} tickLine={false} />
                <Tooltip cursor={{fill: '#f3f4f6'}} />
                <Bar dataKey="value" fill="#10b981" radius={[0, 4, 4, 0]} barSize={30}>
                  {drivers.vehicles.map((entry, index) => (
                    <Cell key={`cell-${index}`} fill={COLORS[(index + 2) % COLORS.length]} />
                  ))}
                </Bar>
              </BarChart>
            </ResponsiveContainer>
          </div>
        </div>

      </div>
    </div>
  );
}

function KPICard({ title, value, sub, icon: Icon, color }) {
  return (
    <div className="bg-white p-4 rounded-xl border border-gray-100 shadow-sm flex items-start gap-4">
      <div className={`p-3 rounded-lg ${color} text-white`}>
        <Icon className="h-6 w-6" />
      </div>
      <div>
        <p className="text-xs font-semibold text-gray-500 uppercase tracking-wider mb-1">{title}</p>
        <h4 className="text-2xl font-bold text-gray-900 leading-none">{value}</h4>
        {sub && <p className="text-xs text-gray-400 mt-1">{sub}</p>}
      </div>
    </div>
  );
}
