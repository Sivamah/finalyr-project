import React, { useState, useEffect, useMemo } from 'react';
import {
  FileText, Cpu, Users, Fuel, Leaf, MapPin, Radio, CheckCircle2, XCircle, BrainCircuit,
} from 'lucide-react';
import { motion } from 'framer-motion';
import { AreaChart, Area, PieChart, Pie, Cell, XAxis, YAxis, Tooltip, ResponsiveContainer } from 'recharts';
import api from '../services/api';
import LiveMapContainer from '../components/map/LiveMapContainer';
import ActivityTimeline from '../components/notifications/ActivityTimeline';
import AnimatedNumber from '../components/ui/AnimatedNumber';
import StatusBadge from '../components/ui/StatusBadge';

const PIE_COLORS = ['#3B82F6', '#06B6D4', '#8B5CF6'];

const tooltipStyle = {
  backgroundColor: 'rgba(10, 16, 32, 0.92)',
  border: '1px solid rgba(255,255,255,0.1)',
  borderRadius: '14px',
  backdropFilter: 'blur(16px)',
  boxShadow: '0 12px 32px rgba(0,0,0,0.4)',
  fontSize: '12px',
  color: '#fff',
};

function ChartTooltip({ active, payload, label }) {
  if (!active || !payload?.length) return null;
  return (
    <div style={tooltipStyle} className="px-3.5 py-2.5">
      {label && <p className="text-[10px] text-brand-text-muted uppercase tracking-wider mb-1">{label}</p>}
      {payload.map((entry) => (
        <div key={entry.dataKey} className="flex items-center justify-between gap-6 text-[12px]">
          <span className="flex items-center gap-1.5 text-brand-text-secondary">
            <span className="h-2 w-2 rounded-full" style={{ background: entry.color || entry.stroke }} />
            {entry.name}
          </span>
          <span className="font-semibold text-white tabular-nums">{entry.value}</span>
        </div>
      ))}
    </div>
  );
}

/* ── KPI cards ─────────────────────────────────────────────────────────── */

const KpiCard = ({ icon: Icon, label, value, format, tone, className }) => {
  const gradient = {
    blue: 'from-brand-primary to-brand-secondary',
    purple: 'from-brand-accent to-brand-primary',
    cyan: 'from-brand-secondary to-brand-primary',
    amber: 'from-brand-warning to-brand-primary',
    green: 'from-brand-success to-brand-secondary',
  }[tone];

  const glow = {
    blue: 'shadow-[0_0_24px_rgba(59,130,246,0.35)]',
    purple: 'shadow-[0_0_24px_rgba(139,92,246,0.35)]',
    cyan: 'shadow-[0_0_24px_rgba(6,182,212,0.35)]',
    amber: 'shadow-[0_0_24px_rgba(245,158,11,0.3)]',
    green: 'shadow-[0_0_24px_rgba(16,185,129,0.3)]',
  }[tone];

  return (
    <motion.div
      initial={{ opacity: 0, y: 18 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.5, ease: [0.22, 1, 0.36, 1] }}
      className={`glass-card rounded-[24px] p-5 relative overflow-hidden group ${className}`}
    >
      {/* colored radial ambience */}
      <div
        className={`absolute -right-10 -top-10 h-36 w-36 rounded-full bg-gradient-to-br ${gradient} opacity-[0.08] blur-[40px] group-hover:opacity-[0.18] transition-opacity duration-700 pointer-events-none`}
      />
      <div className="relative z-10 flex flex-col h-full">
        <div className="flex items-center justify-between mb-4">
          <span className="section-label">{label}</span>
          <div className={`h-10 w-10 rounded-2xl bg-gradient-to-br ${gradient} border border-white/20 flex items-center justify-center ${glow}`}>
            <Icon className="h-[18px] w-[18px] text-white" />
          </div>
        </div>
        <div className="mt-auto">
          <div className="text-[32px] md:text-[34px] font-display font-medium text-white leading-none tracking-tight tabular-nums">
            <AnimatedNumber value={value} format={(v) => (format ? format(v) : Math.round(v).toLocaleString())} />
          </div>
          <div className="mt-3 h-[3px] w-full rounded-full bg-white/[0.05] overflow-hidden">
            <div className={`h-full rounded-full bg-gradient-to-r ${gradient} opacity-70 transition-all duration-1000`} style={{ width: '100%' }} />
          </div>
        </div>
      </div>
    </motion.div>
  );
};

const HeroKpi = ({ icon: Icon, value, sub }) => (
  <motion.div
    initial={{ opacity: 0, y: 18 }}
    animate={{ opacity: 1, y: 0 }}
    transition={{ duration: 0.5, ease: [0.22, 1, 0.36, 1] }}
    className="glass-card rounded-[24px] p-6 relative overflow-hidden md:col-span-2 glass-reflect"
  >
    <div className="absolute -right-16 -top-16 h-56 w-56 rounded-full bg-brand-primary opacity-[0.12] blur-[60px] pointer-events-none" />
    <div className="relative flex h-full flex-col">
      <div className="flex items-start justify-between">
        <div className="flex items-center gap-3">
          <div className="h-12 w-12 rounded-2xl bg-gradient-to-br from-brand-primary to-brand-accent border border-white/20 flex items-center justify-center shadow-[0_0_24px_rgba(59,130,246,0.35)]">
            <Icon className="h-5 w-5 text-white" />
          </div>
          <div>
            <p className="section-label">Total Requests</p>
            <div className="text-[40px] font-display font-semibold text-white leading-none tracking-tight tabular-nums mt-1.5">
              <AnimatedNumber value={value} format={(v) => Math.round(v).toLocaleString()} />
            </div>
          </div>
        </div>
        <StatusBadge tone="success" label="Live" pulse />
      </div>
      {sub && (
        <div className="mt-auto pt-5 flex flex-wrap items-center gap-x-6 gap-y-2 text-[12px] text-brand-text-secondary">
          {sub.map((s) => (
            <span key={s.label} className="flex items-center gap-1.5">
              <span className="h-1 w-1 rounded-full bg-brand-primary" />
              <span className="text-brand-text-muted">{s.label}</span>
              <span className="font-semibold text-white tabular-nums">{s.value}</span>
              {s.unit && <span className="text-brand-text-muted">{s.unit}</span>}
            </span>
          ))}
        </div>
      )}
    </div>
  </motion.div>
);

/* ── System Intelligence widget (real model metrics) ───────────────────── */
function SystemIntelligence({ meta }) {
  const { avgCompatibility, avgConfidence, batchRate, rejectedRatio, engineOnline } = meta || {};
  return (
    <div className="glass-card rounded-[24px] p-6 h-full flex flex-col relative overflow-hidden">
      <div className="absolute -right-14 -bottom-14 w-48 h-48 rounded-full bg-brand-accent opacity-[0.1] blur-[50px] pointer-events-none" />
      <div className="flex items-center justify-between mb-6 relative">
        <div className="flex items-center gap-3">
          <div className="h-10 w-10 rounded-2xl bg-brand-accent/20 border border-brand-accent/30 flex items-center justify-center">
            <BrainCircuit className="h-5 w-5 text-brand-accent" />
          </div>
          <div>
            <h3 className="font-display font-semibold text-[15px] text-white tracking-tight">System Intelligence</h3>
            <p className="text-[11px] text-brand-text-muted mt-0.5">Adaptive engine telemetry</p>
          </div>
        </div>
        <StatusBadge tone={engineOnline ? 'success' : 'neutral'} label={engineOnline ? 'Online' : 'Standby'} pulse={engineOnline} />
      </div>

      <div className="space-y-6 flex-1 relative">
        {[
          { label: 'Compatibility Mean', value: avgCompatibility, color: '#8B5CF6' },
          { label: 'Model Confidence', value: avgConfidence, color: '#06B6D4' },
        ].map((row) => (
          <div key={row.label} className="space-y-2">
            <div className="flex items-center justify-between">
              <span className="text-[13px] font-medium text-brand-text-secondary">{row.label}</span>
              <span className="text-[13px] font-semibold text-white tabular-nums">
                {(row.value ?? 0).toFixed(1)}%
              </span>
            </div>
            <div className="h-1.5 w-full rounded-full bg-white/[0.05] overflow-hidden">
              <motion.div
                className="h-full rounded-full"
                style={{ background: row.color }}
                initial={{ width: 0 }}
                animate={{ width: `${row.value ?? 0}%` }}
                transition={{ duration: 1, ease: [0.22, 1, 0.36, 1] }}
              />
            </div>
          </div>
        ))}
      </div>

      <div className="mt-6 pt-5 border-t border-white/[0.06] grid grid-cols-2 gap-3">
        <div className="surface-well rounded-2xl p-3.5">
          <div className="flex items-center gap-2 text-[11px] text-brand-text-muted mb-1">
            <CheckCircle2 className="h-3.5 w-3.5 text-brand-success" /> Batching rate
          </div>
          <p className="text-[20px] font-display font-semibold text-white tabular-nums">
            {batchRate}%
          </p>
        </div>
        <div className="surface-well rounded-2xl p-3.5">
          <div className="flex items-center gap-2 text-[11px] text-brand-text-muted mb-1">
            <XCircle className="h-3.5 w-3.5 text-brand-warning" /> Rejected pairs
          </div>
          <p className="text-[20px] font-display font-semibold text-white tabular-nums">
            {rejectedRatio ?? 0}%
          </p>
        </div>
      </div>
    </div>
  );
}

/* ── Page ──────────────────────────────────────────────────────────────── */
export default function Dashboard() {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [mapRequests, setMapRequests] = useState([]);
  const [charts, setCharts] = useState({});
  const [aiMeta, setAiMeta] = useState({});
  const [timeline, setTimeline] = useState([]);
  const [lastUpdated, setLastUpdated] = useState(null);

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
        if (chartsRes.status === 'fulfilled') setCharts(chartsRes.value.data?.charts || {});

        if (xaiRes.status === 'fulfilled') {
          const items = xaiRes.value.data || [];
          const n = items.length;
          if (n > 0) {
            const compat = items.reduce((s, e) => s + (e.factors?.overall_compatibility_score || 0), 0) / n;
            const conf = items.reduce((s, e) => s + (e.confidence_score || 0), 0) / n;
            const rejected = items.filter((e) => String(e.decision || '').toLowerCase().includes('reject')).length;
            setAiMeta({
              avgCompatibility: Math.round(compat * 10) / 10,
              avgConfidence: Math.round(conf * 10) / 10,
              rejectedRatio: Math.round((rejected / n) * 1000) / 10,
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
    const count = {};
    mapRequests.forEach((r) => {
      const t = r.request_type?.toLowerCase() || 'ride';
      count[t] = (count[t] || 0) + 1;
    });
    return Object.entries(count).map(([name, value]) => ({ name: name.charAt(0).toUpperCase() + name.slice(1), value }));
  }, [mapRequests]);

  const genTrend = (charts.request_generation_trend || []).map((d) => ({ ...d }));
  const compTrend = (charts.completed_requests_trend || []).map((d) => ({ ...d }));

  if (loading || !data) {
    return (
      <div className="flex items-center justify-center h-[70vh]">
        <div className="flex flex-col items-center gap-4">
          <div className="relative">
            <div className="h-14 w-14 rounded-full border-2 border-white/10 border-t-brand-primary animate-spin shadow-[0_0_30px_rgba(59,130,246,0.3)]" />
          </div>
          <p className="text-[11px] font-semibold tracking-[0.24em] text-brand-text-muted uppercase">Synchronizing live network</p>
        </div>
      </div>
    );
  }

  const mixTotal = requestMix.reduce((s, r) => s + r.value, 0);

  return (
    <div className="space-y-7 max-w-[1500px] mx-auto">
      {/* ── Hero: Live Operations map ─────────────────────────────────── */}
      <motion.div
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.6, ease: [0.22, 1, 0.36, 1] }}
        className="glass-panel-strong rounded-[30px] p-2 glass-reflect"
      >
        <div className="relative rounded-[24px] overflow-hidden h-[52vh] min-h-[440px]">
          <LiveMapContainer
            requests={mapRequests}
            onSelectRequest={() => {}}
            onClosePopup={() => {}}
            className="relative w-full h-full rounded-[24px] overflow-hidden"
          />

          {/* Top-left — Live status panel */}
          <div className="absolute top-5 left-5 z-20">
            <div className="glass-panel-strong rounded-2xl px-4 py-3 backdrop-blur-xl">
              <div className="flex items-center gap-2.5 mb-1.5">
                <span className="relative flex h-2 w-2">
                  <span className="absolute inline-flex h-full w-full rounded-full bg-brand-danger opacity-60 animate-ping" />
                  <span className="relative inline-flex rounded-full h-2 w-2 bg-brand-danger shadow-[0_0_10px_rgba(239,68,68,0.8)]" />
                </span>
                <span className="text-[11px] font-bold tracking-[0.18em] text-white uppercase">Live Operations</span>
              </div>
              <div className="flex items-center gap-2 text-[11px] text-brand-text-secondary">
                <MapPin className="h-3 w-3 text-brand-primary" />
                Coimbatore · {lastUpdated ? lastUpdated.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', second: '2-digit' }) : '—'}
              </div>
            </div>
          </div>

          {/* Top-right — Request mix chips */}
          <div className="absolute top-5 right-5 z-20 flex flex-wrap gap-2 justify-end max-w-[60%]">
            {requestMix.map((r) => (
              <div key={r.name} className="glass-panel-strong rounded-full px-3.5 py-2 flex items-center gap-2 backdrop-blur-xl">
                <span
                  className="h-2 w-2 rounded-full"
                  style={{ background: PIE_COLORS[Math.max(0, ['Ride', 'Food', 'Parcel'].indexOf(r.name))] }}
                />
                <span className="text-[11px] text-brand-text-secondary">{r.name}</span>
                <span className="text-[12px] font-bold text-white tabular-nums">{r.value}</span>
              </div>
            ))}
            <div className="glass-panel-strong rounded-full px-3.5 py-2 flex items-center gap-2 backdrop-blur-xl">
              <Radio className="h-3.5 w-3.5 text-brand-success" />
              <span className="text-[12px] font-bold text-white tabular-nums">{mapRequests.length}</span>
              <span className="text-[11px] text-brand-text-secondary">active</span>
            </div>
          </div>

          {/* Bottom-left — derived efficiency snapshot */}
          <div className="absolute bottom-5 left-5 z-20 hidden md:block">
            <div className="glass-panel-strong rounded-2xl backdrop-blur-xl overflow-hidden">
              <div className="flex divide-x divide-white/[0.07]">
                {[
                  { label: 'Optimization Rate', value: `${data.batch_rate}%`, tone: 'text-brand-secondary' },
                  { label: 'Fuel Saved', value: `${(data.fuel_saved || 0).toFixed(1)}L`, tone: 'text-brand-warning' },
                  { label: 'CO₂ Reduced', value: `${(data.co2_reduction || 0).toFixed(1)}kg`, tone: 'text-brand-success' },
                ].map((item) => (
                  <div key={item.label} className="px-4 py-3 text-center min-w-[104px]">
                    <p className="text-[16px] font-display font-semibold text-white tabular-nums">{item.value}</p>
                    <p className="text-[10px] text-brand-text-muted mt-0.5 tracking-wide">{item.label}</p>
                  </div>
                ))}
              </div>
            </div>
          </div>

          {/* Vignette to seat the map into the glass */}
          <div className="absolute inset-0 pointer-events-none rounded-[24px] shadow-[inset_0_0_120px_rgba(5,8,22,0.55)] border border-white/[0.04]" />
        </div>
      </motion.div>

      {/* ── Five KPI cards — varying sizes ────────────────────────────── */}
      <div className="grid grid-cols-2 md:grid-cols-6 gap-4 md:gap-5">
        <HeroKpi
          icon={FileText}
          value={data.total_requests}
          sub={[
            { label: 'Providers', value: data.total_providers },
            { label: 'Vehicles', value: data.total_vehicles },
            { label: 'Avg route savings', value: (data.avg_route_savings || 0).toFixed(1), unit: 'km' },
          ]}
        />
        <KpiCard icon={Cpu} label="Shared Trips" value={data.total_optimizations} tone="purple" />
        <KpiCard icon={Users} label="Driver Util." value={data.batch_rate} format={(v) => `${Math.round(v)}%`} tone="cyan" />
        <KpiCard icon={Fuel} label="Fuel Saved" value={data.fuel_saved} format={(v) => `${v.toFixed(1)} L`} tone="amber" />
        <KpiCard icon={Leaf} label="CO₂ Reduction" value={data.co2_reduction} format={(v) => `${v.toFixed(1)} kg`} tone="green" />
      </div>

      {/* ── Intelligence & analytics ──────────────────────────────────── */}
      <div className="grid grid-cols-1 xl:grid-cols-3 gap-6">
        {/* Charts column */}
        <div className="xl:col-span-2 flex flex-col gap-6">
          {/* Throughput */}
          <div className="glass-card rounded-[24px] p-6">
            <div className="flex items-center justify-between mb-5">
              <div>
                <h3 className="text-[15px] font-semibold text-white tracking-tight">Network Throughput</h3>
                <p className="text-[11px] text-brand-text-muted mt-0.5">Generated vs completed requests over time</p>
              </div>
              <StatusBadge tone="info" label="Real-time" pulse />
            </div>
            <div className="h-56 w-full">
              <ResponsiveContainer width="100%" height="100%">
                <AreaChart data={compTrend.length ? compTrend : genTrend}>
                  <defs>
                    <linearGradient id="throughputGrad" x1="0" y1="0" x2="0" y2="1">
                      <stop offset="5%" stopColor="#3B82F6" stopOpacity={0.35} />
                      <stop offset="95%" stopColor="#3B82F6" stopOpacity={0} />
                    </linearGradient>
                  </defs>
                  <XAxis dataKey="time" hide />
                  <YAxis hide />
                  <Tooltip content={<ChartTooltip />} />
                  <Area type="monotone" dataKey="count" name="Requests" stroke="#3B82F6" strokeWidth={2.5} fill="url(#throughputGrad)" dot={false} />
                </AreaChart>
              </ResponsiveContainer>
            </div>
          </div>

          {/* Two-up */}
          <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
            <div className="glass-card rounded-[24px] p-6">
              <div className="flex items-center justify-between mb-5">
                <div>
                  <h3 className="text-[15px] font-semibold text-white tracking-tight">Request Generation</h3>
                  <p className="text-[11px] text-brand-text-muted mt-0.5">Inbound rate</p>
                </div>
              </div>
              <div className="h-40 w-full">
                <ResponsiveContainer width="100%" height="100%">
                  <AreaChart data={genTrend}>
                    <defs>
                      <linearGradient id="genGrad" x1="0" y1="0" x2="0" y2="1">
                        <stop offset="5%" stopColor="#06B6D4" stopOpacity={0.32} />
                        <stop offset="95%" stopColor="#06B6D4" stopOpacity={0} />
                      </linearGradient>
                    </defs>
                    <XAxis dataKey="time" hide />
                    <YAxis hide />
                    <Tooltip content={<ChartTooltip />} />
                    <Area type="monotone" dataKey="count" name="Generated" stroke="#06B6D4" strokeWidth={2.5} fill="url(#genGrad)" dot={false} />
                  </AreaChart>
                </ResponsiveContainer>
              </div>
            </div>

            {/* Live request mix */}
            <div className="glass-card rounded-[24px] p-6">
              <div className="flex items-center justify-between mb-4">
                <div>
                  <h3 className="text-[15px] font-semibold text-white tracking-tight">Live Request Mix</h3>
                  <p className="text-[11px] text-brand-text-muted mt-0.5">Queue composition</p>
                </div>
              </div>
              {mixTotal === 0 ? (
                <div className="h-40 flex items-center justify-center text-brand-text-muted text-[12px]">
                  Awaiting inbound requests
                </div>
              ) : (
                <div className="flex items-center gap-3 h-40 w-full">
                  <div className="relative h-32 w-32 shrink-0">
                    <ResponsiveContainer width="100%" height="100%">
                      <PieChart>
                        <Pie data={requestMix} dataKey="value" nameKey="name" innerRadius={36} outerRadius={58} paddingAngle={4} stroke="none">
                          {requestMix.map((entry, i) => (
                            <Cell key={`cell-${i}`} fill={PIE_COLORS[i % PIE_COLORS.length]} />
                          ))}
                        </Pie>
                        <Tooltip content={<ChartTooltip />} />
                      </PieChart>
                    </ResponsiveContainer>
                  </div>
                  <div className="flex-1 space-y-2.5">
                    {requestMix.map((r, i) => (
                      <div key={r.name} className="flex items-center justify-between gap-3">
                        <span className="flex items-center gap-2 text-[12px] text-brand-text-secondary">
                          <span className="h-2 w-2 rounded-full" style={{ background: PIE_COLORS[i % PIE_COLORS.length] }} />
                          {r.name}
                        </span>
                        <span className="text-[12px] font-semibold text-white tabular-nums">
                          {Math.round((r.value / mixTotal) * 100)}%
                        </span>
                      </div>
                    ))}
                  </div>
                </div>
              )}
            </div>
          </div>
        </div>

        {/* Sidebar column */}
        <div className="flex flex-col gap-6">
          <SystemIntelligence meta={{ ...aiMeta, batchRate: data.batch_rate }} />
        </div>
      </div>

      {/* ── Activity stream ───────────────────────────────────────────── */}
      <div>
        <div className="flex items-center justify-between mb-4">
          <h3 className="text-[15px] font-semibold text-white tracking-tight">Live Activity</h3>
          <StatusBadge tone="neutral" label="Engine feed" pulse />
        </div>
        <div className="max-w-3xl">
          <ActivityTimeline timeline={timeline} />
        </div>
      </div>
    </div>
  );
}