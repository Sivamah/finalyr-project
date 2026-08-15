import React, { useState, useEffect, useMemo, useContext } from 'react';
import {
  FileText, Cpu, Users, Fuel, Leaf, MapPin, Radio, Activity,
  BrainCircuit, TrendingUp, Layers, Maximize, MousePointer2,
  Clock, Wallet, Cloud, Settings2, BarChart2, Search, Bell, Calendar
} from 'lucide-react';
import { motion } from 'framer-motion';
import { AreaChart, Area, PieChart, Pie, Cell, LineChart, Line, XAxis, YAxis, Tooltip, ResponsiveContainer } from 'recharts';
import api from '../services/api';
import LiveMapContainer from '../components/map/LiveMapContainer';
import ActivityTimeline from '../components/notifications/ActivityTimeline';
import AnimatedNumber from '../components/ui/AnimatedNumber';
import StatusBadge from '../components/ui/StatusBadge';
import { AuthContext } from '../context/AuthContext';

const PIE_COLORS = ['#3B82F6', '#F59E0B', '#10B981'];

const tooltipStyle = {
  backgroundColor: 'rgba(10, 11, 15, 0.95)',
  border: '1px solid rgba(255,255,255,0.1)',
  borderRadius: '12px',
  backdropFilter: 'blur(16px)',
  boxShadow: '0 12px 32px rgba(0,0,0,0.5)',
  fontSize: '12px',
  color: '#fff',
  padding: '8px 12px',
};

function ChartTooltip({ active, payload, label }) {
  if (!active || !payload?.length) return null;
  return (
    <div style={tooltipStyle}>
      {label && <p className="text-[10px] text-white/50 uppercase tracking-wider mb-1.5">{label}</p>}
      {payload.map((entry) => (
        <div key={entry.dataKey} className="flex items-center justify-between gap-6 text-[12px] mb-1 last:mb-0">
          <span className="flex items-center gap-1.5 text-white/70">
            <span className="h-2 w-2 rounded-full" style={{ background: entry.color || entry.stroke }} />
            {entry.name}
          </span>
          <span className="font-semibold text-white tabular-nums">{entry.value}</span>
        </div>
      ))}
    </div>
  );
}

/* ── Inline Sparkline for KPIs ─────────────────────────────────────────── */
const TinySparkline = ({ data, color, dataKey = 'count' }) => (
  <div className="h-10 w-24 relative">
    <ResponsiveContainer width="100%" height="100%">
      <LineChart data={data}>
        <Line type="monotone" dataKey={dataKey} stroke={color} strokeWidth={2} dot={false} isAnimationActive={false} />
      </LineChart>
    </ResponsiveContainer>
    <div className="absolute inset-0 bg-gradient-to-t from-[#0a0b0f] to-transparent pointer-events-none" />
  </div>
);

/* ── KPI Card Component ────────────────────────────────────────────────── */
const KpiCard = ({ icon: Icon, label, value, format, tone, sparklineData, trend, unit }) => {
  const styles = {
    blue: { bg: 'bg-blue-500/10', text: 'text-blue-400', border: 'border-blue-500/20', glow: 'shadow-[0_0_15px_rgba(59,130,246,0.2)]', hex: '#3B82F6' },
    purple: { bg: 'bg-purple-500/10', text: 'text-purple-400', border: 'border-purple-500/20', glow: 'shadow-[0_0_15px_rgba(168,85,247,0.2)]', hex: '#A855F7' },
    cyan: { bg: 'bg-cyan-500/10', text: 'text-cyan-400', border: 'border-cyan-500/20', glow: 'shadow-[0_0_15px_rgba(6,182,212,0.2)]', hex: '#06B6D4' },
    green: { bg: 'bg-green-500/10', text: 'text-green-400', border: 'border-green-500/20', glow: 'shadow-[0_0_15px_rgba(16,185,129,0.2)]', hex: '#10B981' },
    indigo: { bg: 'bg-indigo-500/10', text: 'text-indigo-400', border: 'border-indigo-500/20', glow: 'shadow-[0_0_15px_rgba(99,102,241,0.2)]', hex: '#6366F1' },
  }[tone];

  return (
    <div className="navy-glass-card p-4 overflow-hidden group transition-all duration-300">      
      <div className="relative z-10 flex flex-col h-full">
        <div className="flex items-center gap-3 mb-3">
          <div className={`h-9 w-9 rounded-full ${styles.bg} ${styles.border} border flex items-center justify-center ${styles.glow}`}>
            <Icon className={`h-4 w-4 ${styles.text}`} />
          </div>
          <span className="text-[13px] text-white/60 font-medium">{label}</span>
        </div>
        
        <div className="flex items-end justify-between mt-auto">
          <div>
            <div className="flex items-baseline gap-1">
              <span className="text-3xl font-display font-semibold text-white tabular-nums tracking-tight">
                {format ? format(value) : <AnimatedNumber value={value} format={(v) => Math.round(v).toLocaleString()} />}
              </span>
              {unit && <span className="text-[14px] text-white/50">{unit}</span>}
            </div>
            {trend && (
              <div className="flex items-center gap-1 mt-1 text-[11px] font-medium text-green-400">
                <TrendingUp className="h-3 w-3" />
                <span>{trend} vs yesterday</span>
              </div>
            )}
          </div>
          {sparklineData && sparklineData.length > 0 && (
            <div className="opacity-80">
              <TinySparkline data={sparklineData} color={styles.hex} />
            </div>
          )}
        </div>
      </div>
    </div>
  );
};

/* ── Operation Summary Component ────────────────────────────────────────── */
const OperationSummary = ({ meta, data }) => {
  return (
    <div className="navy-glass-card p-5 overflow-hidden flex flex-col h-full">
      <div className="flex justify-between items-start mb-6 relative z-10">
        <div className="flex items-center gap-2">
          <Activity className="h-4 w-4 text-brand-primary" />
          <h3 className="text-[14px] font-semibold text-white">Operation Summary</h3>
        </div>
      </div>

      <div className="flex-1 flex flex-col items-center justify-center relative z-10 mb-6">
        <div className="relative w-32 h-32 flex items-center justify-center">
          <div className="absolute inset-0 border border-brand-primary/20 rounded-full animate-[spin_10s_linear_infinite]" />
          <div className="absolute inset-2 border border-brand-primary/20 rounded-full animate-[spin_15s_linear_infinite_reverse]" />
          <div className="absolute inset-4 border border-brand-primary/20 rounded-full animate-[spin_20s_linear_infinite]" />
          
          <div className="relative z-10 flex flex-col items-center">
            <span className="text-[26px] font-semibold text-white tabular-nums leading-none tracking-tight">92.4%</span>
            <span className="text-[10px] font-medium text-brand-primary tracking-widest uppercase mt-1">Optimization</span>
          </div>
        </div>
      </div>

      <div className="space-y-4 relative z-10 text-[12px]">
        {[
          { label: 'Requests Processed', value: data?.total_requests || 0 },
          { label: 'Drivers Active', value: data?.active_drivers || 0 },
          { label: 'Vehicles Active', value: data?.active_vehicles || 0 },
          { label: 'Shared Trips', value: data?.total_optimizations || 0 },
          { label: 'Batches Created', value: data?.total_batches || 0 },
        ].map((row) => (
          <div key={row.label} className="flex items-center justify-between border-b border-white/5 pb-2 last:border-0 last:pb-0">
            <span className="text-white/60">{row.label}</span>
            <span className="text-white font-medium tabular-nums">{row.value}</span>
          </div>
        ))}
      </div>
    </div>
  );
};

/* ── Main Dashboard Component ──────────────────────────────────────────── */
export default function Dashboard() {
  const { user } = useContext(AuthContext);
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [mapRequests, setMapRequests] = useState([]);
  const [charts, setCharts] = useState({});
  const [timeAnalytics, setTimeAnalytics] = useState(null);
  const [aiMeta, setAiMeta] = useState({});
  const [timeline, setTimeline] = useState([]);
  const [lastUpdated, setLastUpdated] = useState(null);
  const [mapFilter, setMapFilter] = useState('All');

  useEffect(() => {
    const fetchAll = async () => {
      try {
        const [statsRes, queueRes, chartsRes, xaiRes, tlRes, simRes] = await Promise.allSettled([
          api.get('/dashboard/stats'),
          api.get('/simulation/queue?limit=120'),
          api.get('/simulation/advanced-analytics'),
          api.get('/xai/explanations?limit=200'),
          api.get('/notifications/timeline?limit=8'),
          api.get('/simulation/status'),
        ]);

        if (statsRes.status === 'fulfilled') setData(statsRes.value.data);
        if (queueRes.status === 'fulfilled') {
          const items = queueRes.value.data?.items || [];
          setMapRequests(items);
          setLastUpdated(new Date());
        }
        if (chartsRes.status === 'fulfilled') {
          setCharts(chartsRes.value.data?.charts || {});
          setTimeAnalytics(chartsRes.value.data?.time_analytics || null);
        }

        if (xaiRes.status === 'fulfilled') {
          const items = xaiRes.value.data || [];
          const n = items.length;
          if (n > 0) {
            const compat = items.reduce((s, e) => s + (e.factors?.overall_compatibility_score || 0), 0) / n;
            const conf = items.reduce((s, e) => s + (e.confidence_score || 0), 0) / n;
            setAiMeta({
              avgCompatibility: Math.round(compat * 10) / 10,
              avgConfidence: Math.round(conf * 10) / 10,
            });
          }
        }

        if (tlRes.status === 'fulfilled') setTimeline(tlRes.value.data || []);

        if (simRes.status === 'fulfilled') {
          const s = simRes.value.data;
          setAiMeta((prev) => ({ ...prev, engineOnline: s?.running || false }));
        } else {
          setAiMeta((prev) => ({ ...prev, engineOnline: false }));
        }
      } catch (err) {
        console.error(err);
      } finally {
        setLoading(false);
      }
    };
    fetchAll();
    const t = setInterval(() => {
      if (document.visibilityState === 'visible') fetchAll();
    }, 20000);
    return () => clearInterval(t);
  }, []);

  const requestMix = useMemo(() => {
    const count = { ride: 0, food: 0, parcel: 0 };
    mapRequests.forEach((r) => {
      const t = r.request_type?.toLowerCase();
      if (count[t] !== undefined) count[t]++;
      else count['ride']++; // default fallback
    });
    return [
      { name: 'Passenger', value: count.ride },
      { name: 'Food Delivery', value: count.food },
      { name: 'Parcel Delivery', value: count.parcel }
    ].filter(i => i.value > 0);
  }, [mapRequests]);

  const genTrend = (charts.request_generation_trend || []).map((d) => ({ ...d }));
  const compTrend = (charts.completed_requests_trend || []).map((d) => ({ ...d }));

  if (loading || !data) {
    return (
      <div className="flex items-center justify-center h-[70vh]">
        <div className="flex flex-col items-center gap-4">
          <div className="relative">
            <div className="h-14 w-14 rounded-full border-2 border-white/10 border-t-indigo-500 animate-spin" />
          </div>
          <p className="text-[12px] font-medium text-white/50 uppercase tracking-widest">Initializing Dashboard...</p>
        </div>
      </div>
    );
  }

  const mixTotal = requestMix.reduce((s, r) => s + r.value, 0);
  const firstName = user?.full_name ? user.full_name.split(' ')[0] : 'Admin';

  return (
    <div className="min-h-full text-white p-4 md:p-6 lg:p-8 relative overflow-hidden">
      {/* Ambient background glows */}
      <div className="absolute inset-0 pointer-events-none overflow-hidden" style={{ zIndex: 0 }}>
        <div className="absolute top-[-10%] left-[-5%] w-[50%] h-[50%] bg-brand-primary/10 rounded-full blur-[140px]" />
        <div className="absolute bottom-[10%] right-[-10%] w-[40%] h-[40%] bg-[#1677FF]/10 rounded-full blur-[140px]" />
        <div className="absolute top-[40%] left-[20%] w-[30%] h-[30%] bg-brand-cyan/5 rounded-full blur-[120px]" />
        <div className="absolute top-[10%] right-[10%] w-[35%] h-[35%] bg-brand-purple/5 rounded-full blur-[140px]" />
      </div>

      <div className="max-w-[1600px] mx-auto space-y-6 relative" style={{ zIndex: 10 }}>
        
        {/* ── Header Row ─────────────────────────────────────────────────── */}
        <div className="flex flex-col md:flex-row md:items-end justify-between gap-4 mb-8">
          <div>
            <h1 className="text-3xl font-display font-semibold text-white tracking-tight mb-1">
              Good Morning, {firstName} <span className="inline-block animate-wave">👋</span>
            </h1>
            <p className="text-[14px] text-white/50">AI-Powered Unified Mobility & Delivery Platform</p>
          </div>
          <div className="flex items-center gap-4">
            {/* Using mock search/date fields just for visual parity with mockup if desired, but standard layout handles header. 
                Assuming AdminLayout wraps this, but mockup has search inside the content area. We will omit redundant search 
                if AdminLayout already provides it, but mockup explicitly shows it. We'll add decorative date here. */}
            <div className="hidden md:flex items-center gap-3 bg-white/5 border border-white/10 rounded-full px-4 py-2 backdrop-blur-md text-[13px] text-white/70">
              <Calendar className="h-4 w-4 text-white/50" />
              <span>{new Date().toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: 'numeric' })}</span>
            </div>
          </div>
        </div>

        {/* ── Top 6 KPI Cards ────────────────────────────────────────────── */}
        <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-6 gap-4">
          <KpiCard 
            icon={FileText} label="Total Requests" value={data.total_requests} tone="blue" trend="+12.5%" 
            sparklineData={genTrend} 
          />
          <KpiCard 
            icon={Layers} label="Shared Trips" value={data.total_optimizations} tone="cyan" trend="+8.3%" 
            sparklineData={compTrend} 
          />
          <KpiCard 
            icon={Activity} label="Vehicle Util." value={data.batch_rate} format={v => `${Math.round(v)}%`} tone="blue" trend="+5.7%" 
            sparklineData={compTrend} 
          />
          <KpiCard 
            icon={Fuel} label="Fuel Saved" value={data.fuel_saved} format={v => `${v.toFixed(1)}`} unit="L" tone="green" trend="+15.3%" 
            sparklineData={compTrend} 
          />
          <KpiCard 
            icon={Cloud} label="CO₂ Reduction" value={data.co2_reduction} format={v => `${Math.round(v)}`} unit="kg" tone="cyan" trend="+14.8%" 
            sparklineData={compTrend} 
          />
          <KpiCard 
            icon={Clock} label="Avg Wait Time" value={(timeAnalytics?.avg_queue_waiting_time_sec / 60) || 0} format={v => `${v.toFixed(1)}`} unit="m" tone="purple" trend="-2.1%" 
            sparklineData={compTrend} 
          />
        </div>

        {/* ── Main Content Row (70/30) ───────────────────────────────────── */}
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          
          {/* LEFT: Live Operations (70%) */}
          <div className="lg:col-span-2 navy-glass-card p-4 flex flex-col min-h-[450px]">
            <div className="flex items-center justify-between mb-4 z-20">
              <h2 className="text-[16px] font-semibold text-white">Live Operations</h2>
              <div className="flex items-center gap-3">
                <div className="flex items-center gap-1.5 px-3 py-1 bg-green-500/10 border border-green-500/20 rounded-full">
                  <span className="h-1.5 w-1.5 rounded-full bg-green-500 animate-pulse" />
                  <span className="text-[11px] text-green-400 font-medium tracking-wide">Live</span>
                </div>
                <div className="flex items-center gap-2 bg-white/5 border border-white/10 rounded-lg p-1">
                  <button className="p-1.5 hover:bg-white/10 rounded-md transition-colors"><Maximize className="h-3.5 w-3.5 text-white/60" /></button>
                  <button className="p-1.5 hover:bg-white/10 rounded-md transition-colors"><Layers className="h-3.5 w-3.5 text-white/60" /></button>
                </div>
              </div>
            </div>

            {/* Map Filters overlay */}
            <div className="absolute top-16 left-6 z-20 flex gap-2">
               {['All', 'Passenger', 'Food', 'Parcel'].map(filter => (
                 <button 
                  key={filter}
                  onClick={() => setMapFilter(filter)}
                  className={`flex items-center gap-2 px-3 py-1.5 rounded-full text-[12px] font-medium transition-colors border ${
                    mapFilter === filter 
                      ? 'bg-white/20 border-white/30 text-white' 
                      : 'bg-[#0a0b0f]/80 border-white/10 text-white/60 hover:text-white hover:bg-white/10 backdrop-blur-md'
                  }`}
                 >
                   {filter !== 'All' && (
                     <span className="h-2 w-2 rounded-full" style={{
                       backgroundColor: filter === 'Passenger' ? PIE_COLORS[0] : filter === 'Food' ? PIE_COLORS[1] : PIE_COLORS[2]
                     }} />
                   )}
                   {filter}
                 </button>
               ))}
            </div>

            {/* Map Controls overlay bottom */}
            <div className="absolute bottom-6 left-1/2 -translate-x-1/2 z-20 flex items-center gap-2 bg-black/40 backdrop-blur-2xl shadow-[0_4px_16px_rgba(0,0,0,0.5)] shadow-[inset_0_1px_1px_rgba(255,255,255,0.1)] border border-white/10 rounded-full p-1.5">
              <button className="p-2 hover:bg-white/10 rounded-full text-white/60 hover:text-white transition-colors"><MousePointer2 className="h-4 w-4" /></button>
              <button className="p-2 hover:bg-white/10 rounded-full text-white/60 hover:text-white transition-colors"><Search className="h-4 w-4" /></button>
              <div className="w-px h-4 bg-white/20 mx-1" />
              <button className="p-2 hover:bg-white/10 rounded-full text-white/60 hover:text-white transition-colors"><Settings2 className="h-4 w-4" /></button>
            </div>

            {/* The Map itself */}
            <div className="flex-1 rounded-xl overflow-hidden relative border border-white/5">
               <LiveMapContainer
                requests={mapFilter === 'All' ? mapRequests : mapRequests.filter(r => r.request_type?.toLowerCase() === (mapFilter === 'Passenger' ? 'ride' : mapFilter.toLowerCase()))}
                onSelectRequest={() => {}}
                onClosePopup={() => {}}
                className="w-full h-full"
              />
              <div className="absolute inset-0 pointer-events-none shadow-[inset_0_0_80px_rgba(10,11,15,0.8)]" />
            </div>
          </div>

          {/* RIGHT: Operation Summary & Live Activity (30%) */}
          <div className="flex flex-col gap-6">
            <div className="h-[280px]">
              <OperationSummary meta={aiMeta} data={data} />
            </div>
            
            <div className="flex-1 navy-glass-card p-5 flex flex-col">
              <div className="flex items-center justify-between mb-4">
                <h3 className="text-[14px] font-semibold text-white">Live Activity</h3>
                <span className="text-[11px] text-white/40 hover:text-white/70 cursor-pointer">View All</span>
              </div>
              <div className="flex-1 overflow-hidden">
                <ActivityTimeline timeline={timeline} />
              </div>
            </div>
          </div>
        </div>

        {/* ── Bottom Cards (3 side by side) ──────────────────────────────── */}
        <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
          
          {/* Requests by Type */}
          <div className="navy-glass-card p-5">
            <h3 className="text-[14px] font-semibold text-white mb-4">Requests by Type</h3>
            {mixTotal === 0 ? (
              <div className="h-40 flex items-center justify-center text-white/40 text-[12px]">No data available</div>
            ) : (
              <div className="flex items-center gap-4 h-40">
                <div className="relative h-36 w-36 shrink-0">
                  <ResponsiveContainer width="100%" height="100%">
                    <PieChart>
                      <Pie data={requestMix} dataKey="value" nameKey="name" innerRadius={42} outerRadius={60} paddingAngle={3} stroke="none">
                        {requestMix.map((entry, i) => (
                          <Cell key={`cell-${i}`} fill={PIE_COLORS[i % PIE_COLORS.length]} />
                        ))}
                      </Pie>
                      <Tooltip content={<ChartTooltip />} />
                    </PieChart>
                  </ResponsiveContainer>
                  {/* Center Total */}
                  <div className="absolute inset-0 flex flex-col items-center justify-center pointer-events-none">
                    <span className="text-[18px] font-semibold text-white leading-tight">{mixTotal}</span>
                    <span className="text-[10px] text-white/40">Total</span>
                  </div>
                </div>
                <div className="flex-1 flex flex-col gap-3">
                  {requestMix.map((r, i) => (
                    <div key={r.name} className="flex flex-col gap-1">
                      <div className="flex items-center gap-2 text-[12px]">
                        <span className="h-2 w-2 rounded-full" style={{ background: PIE_COLORS[i % PIE_COLORS.length] }} />
                        <span className="text-white/60">{r.name}</span>
                      </div>
                      <div className="flex items-center justify-between text-[11px] text-white/40 pl-4">
                        <span>{r.value}</span>
                        <span>{Math.round((r.value / mixTotal) * 100)}%</span>
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            )}
          </div>

          {/* Performance Overview */}
          <div className="navy-glass-card p-5">
            <div className="flex items-center justify-between mb-4">
              <h3 className="text-[14px] font-semibold text-white">Performance Overview</h3>
              <span className="px-2 py-1 bg-white/5 border border-white/10 rounded text-[10px] text-white/50">Today</span>
            </div>
            <div className="h-32 w-full mb-3">
              <ResponsiveContainer width="100%" height="100%">
                <AreaChart data={genTrend}>
                  <defs>
                    <linearGradient id="genGrad" x1="0" y1="0" x2="0" y2="1">
                      <stop offset="5%" stopColor="#3B82F6" stopOpacity={0.3} />
                      <stop offset="95%" stopColor="#3B82F6" stopOpacity={0} />
                    </linearGradient>
                    <linearGradient id="compGrad" x1="0" y1="0" x2="0" y2="1">
                      <stop offset="5%" stopColor="#10B981" stopOpacity={0.3} />
                      <stop offset="95%" stopColor="#10B981" stopOpacity={0} />
                    </linearGradient>
                  </defs>
                  <XAxis dataKey="time" hide />
                  <YAxis hide />
                  <Tooltip content={<ChartTooltip />} />
                  <Area type="monotone" dataKey="count" name="Generated" stroke="#3B82F6" strokeWidth={2} fill="url(#genGrad)" dot={false} />
                  {/* Using same length data if available for completed */}
                  {compTrend.length > 0 && (
                     <Area type="monotone" data={compTrend} dataKey="count" name="Completed" stroke="#10B981" strokeWidth={2} fill="url(#compGrad)" dot={false} />
                  )}
                </AreaChart>
              </ResponsiveContainer>
            </div>
            <div className="flex items-center gap-4 text-[11px]">
              <div className="flex items-center gap-1.5"><span className="h-2 w-2 rounded-full bg-[#3B82F6]" /><span className="text-white/60">Generated</span></div>
              <div className="flex items-center gap-1.5"><span className="h-2 w-2 rounded-full bg-[#10B981]" /><span className="text-white/60">Completed</span></div>
            </div>
          </div>

          {/* Optimization Impact */}
          <div className="navy-glass-card p-5">
            <div className="flex items-center justify-between mb-4">
              <h3 className="text-[14px] font-semibold text-white">Optimization Impact</h3>
              <span className="px-2 py-1 bg-white/5 border border-white/10 rounded text-[10px] text-white/50">Today</span>
            </div>
            <div className="grid grid-cols-2 gap-4 h-full">
              <div className="bg-white/[0.02] rounded-xl p-3 flex flex-col">
                <span className="text-[11px] text-white/50 mb-1">Fuel Saved</span>
                <div className="flex items-baseline gap-1 mb-2">
                  <span className="text-xl font-semibold text-white">{data.fuel_saved?.toFixed(1)}</span>
                  <span className="text-[10px] text-white/50">L</span>
                  <Fuel className="h-3.5 w-3.5 text-green-400 ml-auto" />
                </div>
                <div className="mt-auto h-12 w-full">
                   <ResponsiveContainer width="100%" height="100%">
                     <LineChart data={compTrend}><Line type="monotone" dataKey="count" stroke="#3B82F6" strokeWidth={2} dot={false} /></LineChart>
                   </ResponsiveContainer>
                </div>
              </div>
              <div className="bg-white/[0.02] rounded-xl p-3 flex flex-col">
                <span className="text-[11px] text-white/50 mb-1">CO₂ Reduced</span>
                <div className="flex items-baseline gap-1 mb-2">
                  <span className="text-xl font-semibold text-white">{data.co2_reduction?.toFixed(1)}</span>
                  <span className="text-[10px] text-white/50">kg</span>
                  <Leaf className="h-3.5 w-3.5 text-green-400 ml-auto" />
                </div>
                <div className="mt-auto h-12 w-full opacity-60">
                   <ResponsiveContainer width="100%" height="100%">
                     <LineChart data={compTrend}><Line type="monotone" dataKey="count" stroke="#10B981" strokeWidth={2} dot={false} /></LineChart>
                   </ResponsiveContainer>
                </div>
              </div>
            </div>
          </div>

        </div>

        {/* ── Bottom Metric Strip ────────────────────────────────────────── */}
        <div className="flex flex-wrap md:flex-nowrap items-center gap-4 pt-2 pb-4">
          {[
            { icon: BarChart2, label: 'Total Optimization', value: `${Math.round(data.batch_rate || 0)}%`, fill: data.batch_rate || 0, color: 'bg-blue-500' },
            { icon: Clock, label: 'Avg Waiting Time', value: `${(timeAnalytics?.avg_queue_waiting_time_sec / 60 || 0).toFixed(1)} min`, fill: 75, color: 'bg-gray-400' },
            { icon: Leaf, label: 'CO₂ Reduced', value: `${Math.round(data.co2_reduction || 0)} kg`, fill: 60, color: 'bg-green-500' },
            { icon: Wallet, label: 'Avg Route Savings', value: `${(data.avg_route_savings || 0).toFixed(1)} km`, fill: 45, color: 'bg-indigo-500' },
          ].map((item, i) => (
            <div key={i} className="flex-1 navy-glass-card p-3 flex items-center justify-between min-w-[200px] !rounded-xl">
              <div className="flex items-center gap-3">
                <div className="h-8 w-8 rounded-full bg-white/5 flex items-center justify-center">
                  <item.icon className="h-4 w-4 text-white/60" />
                </div>
                <div>
                  <p className="text-[10px] text-white/50 mb-0.5">{item.label}</p>
                  <p className="text-[14px] font-semibold text-white tabular-nums leading-none">{item.value}</p>
                </div>
              </div>
              <div className="w-16 h-1 rounded-full bg-white/10 overflow-hidden">
                 <div className={`h-full ${item.color}`} style={{ width: `${item.fill}%` }} />
              </div>
            </div>
          ))}
        </div>

      </div>
    </div>
  );
}