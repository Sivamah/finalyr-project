import React, { useState, useEffect } from 'react';
import {
  BarChart, Bar, PieChart, Pie, Cell, RadarChart, Radar, PolarGrid,
  PolarAngleAxis, PolarRadiusAxis,
  XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer
} from 'recharts';
import {
  Brain, Loader2, ChevronDown, ChevronRight, CheckCircle, AlertTriangle,
  XCircle, Sparkles, TrendingUp, Leaf, Clock, Route
} from 'lucide-react';
import { getDmfeAnalytics, getAIDecisions } from '../../services/analyticsService';
import toast from 'react-hot-toast';

const COLORS = ['#4f46e5', '#10b981', '#f59e0b', '#ef4444', '#8b5cf6'];
const IMPACT_COLORS = { positive: 'text-emerald-600', acceptable: 'text-amber-600', negative: 'text-red-600' };
const IMPACT_BG     = { positive: 'bg-emerald-50',    acceptable: 'bg-amber-50',    negative: 'bg-red-50' };
const IMPACT_ICONS  = { positive: CheckCircle,        acceptable: AlertTriangle,     negative: XCircle };

export default function AIInsightsTab() {
  const [dmfe, setDmfe] = useState(null);
  const [decisions, setDecisions] = useState([]);
  const [loading, setLoading] = useState(true);
  const [expandedId, setExpandedId] = useState(null);

  useEffect(() => { loadData(); }, []);

  const loadData = async () => {
    setLoading(true);
    try {
      const [dmfeRes, decRes] = await Promise.all([
        getDmfeAnalytics(),
        getAIDecisions(0, 50),
      ]);
      setDmfe(dmfeRes);
      setDecisions(decRes);
    } catch {
      toast.error('Failed to load AI insights');
    }
    setLoading(false);
  };

  if (loading || !dmfe) {
    return (
      <div className="flex items-center justify-center py-24">
        <div className="animate-spin rounded-full h-12 w-12 border-t-2 border-b-2 border-violet-600"></div>
      </div>
    );
  }

  const typePie = [
    { name: 'Combined', value: dmfe.combined_count },
    { name: 'Single',   value: dmfe.single_count },
  ];

  // Radar chart data from averages
  const radarData = [
    { metric: 'Feasibility',  value: dmfe.avg_feasibility },
    { metric: 'Route Sim.',   value: dmfe.avg_route_similarity },
    { metric: 'Fuel Saved',   value: dmfe.avg_fuel_saved_pct * 2 },   // scale to 0-100
    { metric: 'CO₂ Reduced',  value: dmfe.avg_co2_reduction_pct * 2 },
    { metric: 'Low Delay',    value: Math.max(0, 100 - dmfe.avg_delay_min * 10) },
  ];

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center gap-3 bg-gradient-to-r from-violet-600 to-indigo-700 text-white p-5 rounded-xl">
        <Brain className="h-7 w-7" />
        <div>
          <h2 className="text-lg font-bold">AI Decision Intelligence</h2>
          <p className="text-violet-200 text-sm">Explainable AI insights from the Dynamic Multi-Service Feasibility Engine</p>
        </div>
        <span className="ml-auto bg-white/20 px-3 py-1 rounded-full text-sm font-semibold">
          {dmfe.total_decisions} Decisions
        </span>
      </div>

      {/* KPI Row */}
      <div className="grid grid-cols-2 md:grid-cols-5 gap-4">
        <MiniCard icon={Sparkles}    label="Avg Score"      value={`${dmfe.avg_feasibility}%`} color="bg-violet-500" />
        <MiniCard icon={Route}       label="Route Sim."     value={`${dmfe.avg_route_similarity}%`} color="bg-indigo-500" />
        <MiniCard icon={Clock}       label="Avg Delay"      value={`${dmfe.avg_delay_min} min`} color="bg-amber-500" />
        <MiniCard icon={Leaf}        label="Fuel Saved"     value={`${dmfe.avg_fuel_saved_pct}%`} color="bg-emerald-500" />
        <MiniCard icon={TrendingUp}  label="CO₂ Reduced"    value={`${dmfe.avg_co2_reduction_pct}%`} color="bg-teal-500" />
      </div>

      {/* Charts Row */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Combined vs Single Pie */}
        <div className="bg-white p-5 rounded-xl border border-gray-100 shadow-sm">
          <h3 className="text-sm font-bold text-gray-700 mb-3">Decision Breakdown</h3>
          <div className="h-56">
            <ResponsiveContainer width="100%" height="100%">
              <PieChart>
                <Pie data={typePie} cx="50%" cy="50%" innerRadius={50} outerRadius={80} paddingAngle={5} dataKey="value" label>
                  <Cell fill="#8b5cf6" />
                  <Cell fill="#94a3b8" />
                </Pie>
                <Tooltip />
                <Legend />
              </PieChart>
            </ResponsiveContainer>
          </div>
        </div>

        {/* Score Distribution Bar */}
        <div className="bg-white p-5 rounded-xl border border-gray-100 shadow-sm">
          <h3 className="text-sm font-bold text-gray-700 mb-3">Feasibility Score Distribution</h3>
          <div className="h-56">
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={dmfe.score_distribution}>
                <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="#e5e7eb" />
                <XAxis dataKey="range" axisLine={false} tickLine={false} tick={{fontSize: 11}} />
                <YAxis axisLine={false} tickLine={false} />
                <Tooltip />
                <Bar dataKey="count" fill="#4f46e5" radius={[4, 4, 0, 0]} barSize={30} />
              </BarChart>
            </ResponsiveContainer>
          </div>
        </div>

        {/* Radar Chart */}
        <div className="bg-white p-5 rounded-xl border border-gray-100 shadow-sm">
          <h3 className="text-sm font-bold text-gray-700 mb-3">DMFE Performance Radar</h3>
          <div className="h-56">
            <ResponsiveContainer width="100%" height="100%">
              <RadarChart cx="50%" cy="50%" outerRadius="70%" data={radarData}>
                <PolarGrid stroke="#e5e7eb" />
                <PolarAngleAxis dataKey="metric" tick={{fontSize: 11, fill: '#6b7280'}} />
                <PolarRadiusAxis angle={30} domain={[0, 100]} tick={false} axisLine={false} />
                <Radar dataKey="value" stroke="#8b5cf6" fill="#8b5cf6" fillOpacity={0.3} strokeWidth={2} />
              </RadarChart>
            </ResponsiveContainer>
          </div>
        </div>
      </div>

      {/* Decision History Table */}
      <div className="bg-white rounded-xl border border-gray-100 shadow-sm overflow-hidden">
        <div className="px-5 py-4 border-b border-gray-100 flex items-center gap-2">
          <Brain className="h-4 w-4 text-violet-600" />
          <h3 className="font-bold text-gray-800">AI Decision History</h3>
          <span className="ml-auto text-xs text-gray-400">{decisions.length} records</span>
        </div>
        <div className="divide-y divide-gray-50">
          {decisions.length === 0 ? (
            <div className="text-center py-12 text-gray-400">
              <Brain className="h-10 w-10 mx-auto mb-2 text-gray-300" />
              No AI decisions yet. Run the DMFE to generate decisions.
            </div>
          ) : decisions.map((d) => {
            const isExpanded = expandedId === d.id;
            let explanation = null;
            try { explanation = JSON.parse(d.explanation_json); } catch {}

            return (
              <div key={d.id}>
                {/* Row */}
                <button
                  onClick={() => setExpandedId(isExpanded ? null : d.id)}
                  className="w-full flex items-center gap-4 px-5 py-3 text-left hover:bg-gray-50 transition-colors"
                >
                  {isExpanded ? <ChevronDown className="h-4 w-4 text-gray-400" /> : <ChevronRight className="h-4 w-4 text-gray-400" />}
                  <span className={`px-2 py-0.5 rounded-full text-xs font-bold ${d.decision_type === 'combined' ? 'bg-violet-100 text-violet-700' : 'bg-slate-100 text-slate-600'}`}>
                    {d.decision_type === 'combined' ? 'Combined' : 'Single'}
                  </span>
                  <span className="text-sm text-gray-600">Batch #{d.batch_id}</span>
                  <span className="text-sm font-semibold text-gray-800">{d.request_count} requests</span>

                  {/* Score badge */}
                  <span className={`ml-auto px-3 py-1 rounded-full text-xs font-bold
                    ${d.feasibility_score >= 70 ? 'bg-emerald-100 text-emerald-700' :
                      d.feasibility_score >= 40 ? 'bg-amber-100 text-amber-700' :
                      'bg-red-100 text-red-700'}`}>
                    Score: {d.feasibility_score}%
                  </span>
                  <span className="text-xs text-gray-400 w-24 text-right">
                    {new Date(d.created_at).toLocaleDateString('en-IN')}
                  </span>
                </button>

                {/* Expanded Explanation */}
                {isExpanded && explanation && (
                  <div className="px-10 pb-5 bg-gray-50/50 animate-in">
                    <div className="grid grid-cols-1 md:grid-cols-2 gap-3 mt-2">
                      {explanation.reasons?.map((reason, idx) => {
                        const ImpactIcon = IMPACT_ICONS[reason.impact] || CheckCircle;
                        return (
                          <div key={idx} className={`flex items-center gap-3 p-3 rounded-lg ${IMPACT_BG[reason.impact] || 'bg-gray-50'}`}>
                            <ImpactIcon className={`h-4 w-4 ${IMPACT_COLORS[reason.impact] || 'text-gray-500'}`} />
                            <div className="flex-1">
                              <p className="text-xs font-semibold text-gray-700">{reason.factor}</p>
                              <p className="text-sm font-bold text-gray-900">{reason.value}</p>
                            </div>
                            <span className={`text-xs font-bold capitalize ${IMPACT_COLORS[reason.impact]}`}>
                              {reason.impact}
                            </span>
                          </div>
                        );
                      })}
                    </div>
                    <div className="mt-3 flex items-center gap-2 text-sm">
                      <Sparkles className="h-4 w-4 text-violet-500" />
                      <span className="font-bold text-gray-800">Final Feasibility Score: {explanation.final_score}%</span>
                    </div>
                  </div>
                )}
              </div>
            );
          })}
        </div>
      </div>
    </div>
  );
}

function MiniCard({ icon: Icon, label, value, color }) {
  return (
    <div className="bg-white p-4 rounded-xl border border-gray-100 shadow-sm flex items-center gap-3">
      <div className={`p-2 rounded-lg ${color} text-white`}>
        <Icon className="h-5 w-5" />
      </div>
      <div>
        <p className="text-xs font-semibold text-gray-500 uppercase">{label}</p>
        <h4 className="text-lg font-bold text-gray-900">{value}</h4>
      </div>
    </div>
  );
}
