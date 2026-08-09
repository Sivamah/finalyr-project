import React, { useState, useEffect, useRef, useCallback } from 'react';
import api from '../services/api';

import AnalyticsFilters from '../components/analytics/AnalyticsFilters';
import KPICards from '../components/analytics/KPICards';
import AnalyticsCharts from '../components/analytics/AnalyticsCharts';
import RequestAnalytics from '../components/analytics/RequestAnalytics';
import ProviderAnalytics from '../components/analytics/ProviderAnalytics';
import TimeAnalytics from '../components/analytics/TimeAnalytics';
import ReportExport from '../components/analytics/ReportExport';
import PageHeader from '../components/ui/PageHeader';
import StatusBadge from '../components/ui/StatusBadge';

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

  // Polling setup: 2.5s interval
  useEffect(() => {
    fetchAnalytics();
    pollRef.current = setInterval(() => { if (document.visibilityState === 'visible') fetchAnalytics(); }, 2500);
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
    <div className="space-y-6 pb-10 max-w-[1500px] mx-auto">
      <PageHeader
        eyebrow="Analytics"
        live
        title="Operational Intelligence"
        description="Real-time throughput, provider performance and request lifecycle metrics across the network."
        actions={
          <div className="flex items-center gap-2.5">
            <StatusBadge tone="success" label="Auto-refresh 2.5s" pulse />
            <ReportExport analyticsData={analyticsData} filters={filters} />
          </div>
        }
      />

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
