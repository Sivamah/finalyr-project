import React, { useState, useEffect, useRef, useCallback } from 'react';
import {
  BrainCircuit, RefreshCw, BarChart2, PieChart as PieIcon, FileText, Info
} from 'lucide-react';
import {
  BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, PieChart, Pie, Cell
} from 'recharts';
import api from '../services/api';

import PageHeader from '../components/ui/PageHeader';
import StatusBadge from '../components/ui/StatusBadge';

import ExplanationFilters from '../components/xai/ExplanationFilters';
import DecisionCard from '../components/xai/DecisionCard';
import ScoreBreakdown from '../components/xai/ScoreBreakdown';
import ExplanationTimeline from '../components/xai/ExplanationTimeline';
import CompatibilityGauge from '../components/xai/CompatibilityGauge';

const PIE_COLORS = ['#6366f1', '#10b981', '#f59e0b', '#ef4444', '#a855f7'];

function buildOverview(items) {
  const total = items.length;
  if (total === 0) {
    return {
      total_explanations: 0,
      avg_compatibility_score: 0,
      avg_confidence_score: 0,
      most_common_decision: 'N/A',
      decision_breakdown: [],
      score_distribution: [],
      explanations: [],
      timestamp: new Date().toISOString(),
    };
  }

  const sumCompat = items.reduce(
    (s, e) => s + (e.factors?.overall_compatibility_score || 0), 0
  );
  const sumConf = items.reduce((s, e) => s + (e.confidence_score || 0), 0);

  const decisionCounts = {};
  const scoreRanges = { '90-100%': 0, '80-89%': 0, '70-79%': 0, '<70%': 0 };

  items.forEach((e) => {
    const decision = e.decision || 'Unknown';
    decisionCounts[decision] = (decisionCounts[decision] || 0) + 1;

    const score = e.factors?.overall_compatibility_score || 0;
    if (score >= 90) scoreRanges['90-100%'] += 1;
    else if (score >= 80) scoreRanges['80-89%'] += 1;
    else if (score >= 70) scoreRanges['70-79%'] += 1;
    else scoreRanges['<70%'] += 1;
  });

  let mostCommon = 'N/A';
  let maxCount = -1;
  Object.entries(decisionCounts).forEach(([name, count]) => {
    if (count > maxCount) {
      mostCommon = name;
      maxCount = count;
    }
  });

  return {
    total_explanations: total,
    avg_compatibility_score: Math.round((sumCompat / total) * 10) / 10,
    avg_confidence_score: Math.round((sumConf / total) * 10) / 10,
    most_common_decision: mostCommon,
    decision_breakdown: Object.entries(decisionCounts).map(([name, count]) => ({ name, count })),
    score_distribution: Object.entries(scoreRanges).map(([name, count]) => ({ name, count })),
    explanations: items,
    timestamp: new Date().toISOString(),
  };
}

export default function ExplanationDashboard() {
  const [search, setSearch] = useState('');
  const [filters, setFilters] = useState({
    requestType: 'All',
    providerId: '0',
    decision: 'All',
    status: 'All',
  });

  const [overview, setOverview] = useState({
    total_explanations: 0,
    avg_compatibility_score: 0,
    avg_confidence_score: 0,
    most_common_decision: 'N/A',
    decision_breakdown: [],
    score_distribution: [],
    explanations: [],
  });

  const [providers, setProviders] = useState([]);
  const [selectedExp, setSelectedExp] = useState(null);
  const [loading, setLoading] = useState(true);

  const pollRef = useRef(null);

  // Fetch Providers list for filter dropdown once
  useEffect(() => {
    const fetchProviders = async () => {
      try {
        const res = await api.get('/providers/');
        setProviders(res.data || []);
      } catch (err) {
        console.error('Failed to load providers:', err);
      }
    };
    fetchProviders();
  }, []);

  // Fetch XAI Data
  const fetchData = useCallback(async () => {
    try {
      const params = new URLSearchParams();
      if (search) params.append('search', search);
      if (filters.requestType !== 'All') params.append('request_type', filters.requestType);
      if (filters.providerId !== '0') params.append('provider_id', filters.providerId);
      if (filters.decision !== 'All') params.append('decision', filters.decision);
      if (filters.status !== 'All') params.append('status', filters.status);
      params.append('limit', '200');

      const listRes = await api.get(`/xai/explanations?${params.toString()}`);

      const items = listRes.data || [];
      setOverview(buildOverview(items));

      // Keep selected item updated or pick first
      if (items.length > 0) {
        setSelectedExp((prev) => {
          if (!prev) return items[0];
          const match = items.find((i) => i.request_id === prev.request_id);
          return match || items[0];
        });
      } else {
        setSelectedExp(null);
      }
    } catch (err) {
      console.error('Failed to fetch XAI data:', err);
    } finally {
      setLoading(false);
    }
  }, [search, filters]);

  // Polling: 2.5s
  useEffect(() => {
    fetchData();
    pollRef.current = setInterval(() => { if (document.visibilityState === 'visible') fetchData(); }, 2500);
    return () => clearInterval(pollRef.current);
  }, [fetchData]);

  // Filter change handlers
  const handleFilterChange = (key, value) => {
    setFilters((prev) => ({ ...prev, [key]: value }));
  };

  const handleResetFilters = () => {
    setSearch('');
    setFilters({
      requestType: 'All',
      providerId: '0',
      decision: 'All',
      status: 'All',
    });
  };

  const filteredExplanations = overview.explanations || [];

  return (
    <div className="space-y-6 pb-10 max-w-[1500px] mx-auto">
      <PageHeader
        eyebrow="AI Insights"
        live
        title="Explainable Decisions"
        description="Inspect how the feasibility engine scores pairings — factor attribution, confidence and decision distribution."
        actions={
          <div className="flex items-center gap-2.5">
            <StatusBadge tone="success" label="Auto-refresh 2.5s" pulse />
            <button onClick={fetchData} className="btn-glass">
              <RefreshCw className="h-3.5 w-3.5" /> Refresh
            </button>
          </div>
        }
      />

      {/* ── Search & Filter Controls Bar ──────────────────────────────────────── */}
      <ExplanationFilters
        search={search}
        onSearchChange={setSearch}
        filters={filters}
        onFilterChange={handleFilterChange}
        onResetFilters={handleResetFilters}
        providerOptions={providers}
      />

      {loading && !overview.timestamp ? (
        <div className="flex items-center justify-center h-64">
          <div className="animate-spin rounded-full h-10 w-10 border-t-2 border-b-2 border-indigo-500" />
        </div>
      ) : (
        <>
          {/* ── Top Summary Cards ───────────────────────────────────────────── */}
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
            {[
              { label: 'Total Explanations', value: overview.total_explanations || 0, mono: true },
              { label: 'Avg Compatibility', value: `${overview.avg_compatibility_score || 0}%`, accent: 'text-brand-secondary' },
              { label: 'Avg Model Confidence', value: `${overview.avg_confidence_score || 0}%`, accent: 'text-brand-warning' },
              { label: 'Primary Outcome', value: overview.most_common_decision || 'N/A', small: true },
            ].map((card) => (
              <div key={card.label} className="glass-card rounded-[22px] p-5 relative overflow-hidden">
                <p className="section-label">{card.label}</p>
                <p className={`mt-2.5 text-[26px] font-display font-semibold tracking-tight ${card.small ? 'text-[18px] mt-3.5' : card.accent || 'text-white'} ${card.mono ? 'tabular-nums' : 'break-words'}`}>
                  {card.value}
                </p>
              </div>
            ))}
          </div>

          {/* ── Visualizations Section (3 Column Grid) ───────────────────────── */}
          <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
            {/* 1. Score Distribution Chart */}
            <div className="bg-gray-800 border border-gray-700 rounded-xl p-5 shadow-sm">
              <h3 className="text-sm font-bold text-white mb-4 flex items-center gap-2">
                <BarChart2 className="h-4 w-4 text-indigo-400" />
                Score Distribution Chart
              </h3>
              <div className="h-56 w-full">
                <ResponsiveContainer width="100%" height="100%">
                  <BarChart data={overview.score_distribution || []}>
                    <CartesianGrid strokeDasharray="3 3" stroke="#374151" />
                    <XAxis dataKey="name" stroke="#9ca3af" fontSize={11} />
                    <YAxis stroke="#9ca3af" fontSize={11} allowDecimals={false} />
                    <Tooltip contentStyle={{ backgroundColor: '#1f2937', borderColor: '#4b5563', color: '#fff', borderRadius: '8px' }} />
                    <Bar dataKey="count" fill="#6366f1" radius={[4, 4, 0, 0]} />
                  </BarChart>
                </ResponsiveContainer>
              </div>
            </div>

            {/* 2. Compatibility Gauge */}
            <CompatibilityGauge
              score={selectedExp?.factors?.overall_compatibility_score || overview.avg_compatibility_score || 85}
              confidence={selectedExp?.confidence_score || overview.avg_confidence_score || 90}
            />

            {/* 3. Decision Breakdown */}
            <div className="bg-gray-800 border border-gray-700 rounded-xl p-5 shadow-sm">
              <h3 className="text-sm font-bold text-white mb-4 flex items-center gap-2">
                <PieIcon className="h-4 w-4 text-orange-400" />
                Decision Breakdown
              </h3>
              <div className="h-56 w-full flex items-center justify-center">
                {(overview.decision_breakdown || []).length === 0 ? (
                  <p className="text-sm text-gray-500">No decisions evaluated</p>
                ) : (
                  <ResponsiveContainer width="100%" height="100%">
                    <PieChart>
                      <Pie
                        data={overview.decision_breakdown || []}
                        dataKey="count"
                        nameKey="name"
                        cx="50%"
                        cy="50%"
                        innerRadius={45}
                        outerRadius={75}
                        paddingAngle={3}
                      >
                        {(overview.decision_breakdown || []).map((entry, index) => (
                          <Cell key={`cell-${index}`} fill={PIE_COLORS[index % PIE_COLORS.length]} />
                        ))}
                      </Pie>
                      <Tooltip contentStyle={{ backgroundColor: '#1f2937', borderColor: '#4b5563', color: '#fff', borderRadius: '8px' }} />
                    </PieChart>
                  </ResponsiveContainer>
                )}
              </div>
            </div>
          </div>

          {/* ── Main Decision Explanation Panel ─────────────────────────────── */}
          <div className="grid grid-cols-1 lg:grid-cols-5 gap-6">
            {/* Left Column: Decision Cards List (2 cols) */}
            <div className="lg:col-span-2 space-y-4">
              <div className="flex items-center justify-between">
                <h3 className="text-sm font-bold text-white flex items-center gap-2">
                  <FileText className="h-4 w-4 text-indigo-400" />
                  Decision Explanation Cards
                </h3>
                <span className="text-xs text-gray-400 font-mono">
                  {filteredExplanations.length} records
                </span>
              </div>

              {filteredExplanations.length === 0 ? (
                <div className="bg-gray-800 border border-gray-700 rounded-xl p-12 text-center text-gray-500">
                  <BrainCircuit className="h-10 w-10 mx-auto mb-2 opacity-40" />
                  <p className="text-base font-medium">No explanations match your filter</p>
                  <p className="text-xs text-gray-600 mt-1">Start simulation engine or reset search filters</p>
                </div>
              ) : (
                <div className="space-y-3 max-h-[700px] overflow-y-auto pr-1">
                  {filteredExplanations.map((exp) => (
                    <DecisionCard
                      key={exp.id || exp.request_id}
                      explanation={exp}
                      isSelected={selectedExp?.request_id === exp.request_id}
                      onSelect={() => setSelectedExp(exp)}
                    />
                  ))}
                </div>
              )}
            </div>

            {/* Right Column: Detailed Explanation & Factors Inspection (3 cols) */}
            <div className="lg:col-span-3 space-y-6">
              {selectedExp ? (
                <>
                  {/* Detailed Factor Breakdown Progress Bars */}
                  <ScoreBreakdown factors={selectedExp.factors} />

                  {/* Chronological Event Timeline */}
                  <ExplanationTimeline timeline={selectedExp.timeline} />
                </>
              ) : (
                <div className="bg-gray-800 border border-gray-700 rounded-xl p-16 text-center text-gray-500">
                  <Info className="h-10 w-10 mx-auto mb-2 opacity-40 text-indigo-400" />
                  <p className="text-base font-medium text-gray-300">Select a Decision Card</p>
                  <p className="text-xs text-gray-500 mt-1">Click any decision card on the left to inspect detailed factor attributions and timeline events.</p>
                </div>
              )}
            </div>
          </div>
        </>
      )}
    </div>
  );
}
