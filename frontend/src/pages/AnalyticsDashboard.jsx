import React, { useState, useEffect, useRef, useCallback } from 'react';
import api from '../services/api';

import AnalyticsFilters from '../components/analytics/AnalyticsFilters';
import KPICards from '../components/analytics/KPICards';
import AnalyticsCharts from '../components/analytics/AnalyticsCharts';
import RequestAnalytics from '../components/analytics/RequestAnalytics';
import ProviderAnalytics from '../components/analytics/ProviderAnalytics';
import TimeAnalytics from '../components/analytics/TimeAnalytics';
import ReportExport from '../components/analytics/ReportExport';

export default function AnalyticsDashboard() {
  const [filters, setFilters] = useState({
    preset: 'all', // 'all' | 'today' | 'hour'
    requestType: 'All', // 'All' | 'ride' | 'food' | 'parcel'
    providerId: '0', // '0' or provider ID string
    status: 'All', // 'All' | 'Pending' | 'Completed'
  });

  const [analyticsData, setAnalyticsData] = useState({
    kpi: {},
    charts: {},
    request_analytics: {},
    provider_analytics: {},
    time_analytics: {},
    timestamp: '',
  });

  const [providers, setProviders] = useState([]);
  const [loading, setLoading] = useState(true);
  const pollRef = useRef(null);

  // Fetch Providers List once for filter dropdown
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

  // Fetch Analytics Data
  const fetchAnalytics = useCallback(async () => {
    try {
      // Build query params
      const params = new URLSearchParams();
      if (filters.requestType !== 'All') params.append('request_type', filters.requestType);
      if (filters.providerId !== '0') params.append('provider_id', filters.providerId);
      if (filters.status !== 'All') params.append('status', filters.status);

      if (filters.preset === 'today') {
        const today = new Date();
        today.setHours(0, 0, 0, 0);
        params.append('start_date', today.toISOString());
      } else if (filters.preset === 'hour') {
        const oneHourAgo = new Date(Date.now() - 3600 * 1000);
        params.append('start_date', oneHourAgo.toISOString());
      }

      const res = await api.get(`/simulation/advanced-analytics?${params.toString()}`);
      setAnalyticsData(res.data || {});
    } catch (err) {
      console.error('Failed to fetch advanced analytics:', err);
    } finally {
      setLoading(false);
    }
  }, [filters]);

  // Polling setup: 10s interval
  useEffect(() => {
    fetchAnalytics();
    // Analytics aggregation changes slowly; 10 s is sufficient and cuts load 4×.
    pollRef.current = setInterval(() => { if (document.visibilityState === 'visible') fetchAnalytics(); }, 10000);
    return () => clearInterval(pollRef.current);
  }, [fetchAnalytics]);

  // Filter Change Handlers
  const handleFilterChange = (key, value) => {
    setFilters((prev) => ({ ...prev, [key]: value }));
  };

  const handleResetFilters = () => {
    setFilters({
      preset: 'all',
      requestType: 'All',
      providerId: '0',
      status: 'All',
    });
  };

  return (
    <div className="space-y-5 pb-10 max-w-[1600px] mx-auto">
      {/* 1. Page Header */}
      <div className="flex flex-col lg:flex-row lg:items-end justify-between gap-4 mb-2">
        <div>
          <p className="section-label mb-2 flex items-center gap-2">
            <span className="relative flex h-1.5 w-1.5">
              <span className="absolute inline-flex h-full w-full rounded-full bg-brand-danger opacity-60 animate-ping" />
              <span className="relative inline-flex rounded-full h-1.5 w-1.5 bg-brand-danger" />
            </span>
            Analytics
          </p>
          <h1 className="page-title">Operational Intelligence</h1>
          <p className="mt-1.5 text-[13px] leading-relaxed text-brand-text-secondary max-w-2xl">
            Real-time throughput, provider performance and request lifecycle metrics across the network.
          </p>
        </div>
        <div className="flex items-center gap-3 shrink-0">
          <div className="bg-brand-success/10 border border-brand-success/20 text-brand-success px-3 py-1.5 rounded-[8px] text-[11px] font-bold uppercase tracking-wider flex items-center gap-2">
            <span className="relative flex h-1.5 w-1.5">
              <span className="absolute inline-flex h-full w-full rounded-full bg-brand-success opacity-60 animate-ping" />
              <span className="relative inline-flex rounded-full h-1.5 w-1.5 bg-brand-success" />
            </span>
            Auto-refresh 10s
          </div>
          <ReportExport analyticsData={analyticsData} filters={filters} />
        </div>
      </div>

      {/* 1. Filters */}
      <AnalyticsFilters
        filters={filters}
        onFilterChange={handleFilterChange}
        onResetFilters={handleResetFilters}
        providerOptions={providers}
      />

      {loading && !analyticsData.timestamp ? (
        <div className="flex items-center justify-center h-64">
          <div className="animate-spin rounded-full h-10 w-10 border-t-2 border-b-2 border-indigo-500" />
        </div>
      ) : (
        <>
          {/* 2. KPI Cards */}
          <KPICards kpi={analyticsData.kpi} />

          {/* 3. Interactive Charts */}
          <AnalyticsCharts charts={analyticsData.charts} />

          {/* 4. Request Analytics Breakdown */}
          <RequestAnalytics data={analyticsData.request_analytics} />

          {/* 5. Provider Analytics */}
          <ProviderAnalytics data={analyticsData.provider_analytics} />

          {/* 6. Time & Temporal Analytics */}
          <TimeAnalytics data={analyticsData.time_analytics} />
        </>
      )}
    </div>
  );
}
