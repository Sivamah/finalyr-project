import React, { useState, useEffect, useCallback } from 'react';
import { Save, RotateCcw, Zap, Building2, Truck, BrainCircuit, Sliders, FileCode, History } from 'lucide-react';
import api from '../services/api';
import toast from 'react-hot-toast';

import PageHeader from '../components/ui/PageHeader';

import SimulationSettings from '../components/config/SimulationSettings';
import ProviderConfiguration from '../components/config/ProviderConfiguration';
import VehicleRules from '../components/config/VehicleRules';
import AIRules from '../components/config/AIRules';
import SystemPreferences from '../components/config/SystemPreferences';
import BackupRestore from '../components/config/BackupRestore';
import AuditLog from '../components/config/AuditLog';

export default function SystemConfiguration() {
  const [activeTab, setActiveTab] = useState('simulation'); // simulation | provider | vehicle | ai_rules | preferences | backup | audit
  const [configData, setConfigData] = useState({
    simulation: {},
    provider: {},
    vehicle: {},
    ai_rules: {},
    preferences: {},
  });
  const [providers, setProviders] = useState([]);
  const [auditLogs, setAuditLogs] = useState([]);
  const [saving, setSaving] = useState(false);

  // Fetch all configuration data
  const fetchData = useCallback(async () => {
    try {
      const [cfgRes, provRes, auditRes] = await Promise.all([
        api.get('/config'),
        api.get('/providers'),
        api.get('/config/audit-logs?limit=100'),
      ]);

      setConfigData(cfgRes.data || {});
      setProviders(provRes.data || []);
      setAuditLogs(auditRes.data || []);
    } catch (err) {
      console.error('Failed to fetch configuration data:', err);
      toast.error('Failed to load system configurations');
    }
  }, []);

  useEffect(() => {
    fetchData();
  }, [fetchData]);

  // Handle local change in config state
  const handleConfigChange = (category, key, value) => {
    setConfigData((prev) => ({
      ...prev,
      [category]: {
        ...prev[category],
        [key]: value,
      },
    }));
  };

  // Validate and Save Changes
  const handleSaveChanges = async () => {
    // Validation
    const sim = configData.simulation || {};
    if (sim.simulation_speed < 1 || sim.simulation_speed > 60) {
      toast.error('Simulation speed must be between 1 and 60 seconds');
      return;
    }
    if (sim.max_queue_size < 10) {
      toast.error('Maximum Queue Size must be at least 10');
      return;
    }

    // Flatten all categories into a single settings dictionary
    const flatSettings = {};
    Object.values(configData).forEach((catDict) => {
      if (typeof catDict === 'object' && catDict !== null) {
        Object.entries(catDict).forEach(([k, v]) => {
          flatSettings[k] = v;
        });
      }
    });

    setSaving(true);
    try {
      const res = await api.patch('/config', { settings: flatSettings });
      toast.success(res.data.message || 'Configuration saved successfully');
      fetchData();
    } catch {
      toast.error('Failed to save configuration parameters');
    } finally {
      setSaving(false);
    }
  };

  // Export JSON
  const handleExportJSON = async () => {
    try {
      const res = await api.post('/config/export');
      const dataStr = "data:text/json;charset=utf-8," + encodeURIComponent(JSON.stringify(res.data, null, 2));
      const downloadAnchor = document.createElement('a');
      downloadAnchor.setAttribute("href", dataStr);
      downloadAnchor.setAttribute("download", `system_config_${new Date().toISOString().slice(0, 10)}.json`);
      document.body.appendChild(downloadAnchor);
      downloadAnchor.click();
      downloadAnchor.remove();
      toast.success('Configuration JSON exported');
    } catch {
      toast.error('Failed to export configuration JSON');
    }
  };

  // Import JSON
  const handleImportJSON = async (importPayload) => {
    try {
      const res = await api.post('/config/import', importPayload);
      toast.success(res.data.message || 'Configuration imported successfully');
      fetchData();
    } catch {
      toast.error('Failed to import configuration payload');
    }
  };

  // Reset to Factory Defaults
  const handleResetDefaults = async () => {
    if (!confirm('Are you sure you want to reset all configurations to factory defaults?')) return;
    try {
      const res = await api.post('/config/reset');
      toast.success(res.data.message || 'Configurations reset to factory defaults');
      fetchData();
    } catch {
      toast.error('Failed to reset configurations');
    }
  };

  return (
    <div className="space-y-6 pb-10 max-w-[1500px] mx-auto">
      <PageHeader
        eyebrow="System"
        title="Configuration"
        description="Engine parameters, provider constraints, vehicle rules and AI thresholds — audited and reversible."
        actions={
          <div className="flex items-center gap-2.5">
            <button
              onClick={handleResetDefaults}
              className="btn-glass !text-brand-warning"
            >
              <RotateCcw className="h-4 w-4" /> Factory Reset
            </button>
            <button
              onClick={handleSaveChanges}
              disabled={saving}
              className="btn-primary disabled:opacity-50 disabled:cursor-not-allowed"
            >
              <Save className="h-4 w-4" /> {saving ? 'Saving…' : 'Save Configuration'}
            </button>
          </div>
        }
      />

      {/* ── Navigation Tabs ─────────────────────────────────────────────────── */}
      <div className="space-y-5">
        <div className="glass-panel rounded-[18px] p-1.5 flex items-center gap-1.5 overflow-x-auto custom-scrollbar">
          {[
            { id: 'simulation', label: 'Simulation', icon: Zap },
            { id: 'provider', label: 'Provider Rules', icon: Building2 },
            { id: 'vehicle', label: 'Vehicle', icon: Truck },
            { id: 'ai_rules', label: 'AI Rules', icon: BrainCircuit },
            { id: 'preferences', label: 'Preferences', icon: Sliders },
            { id: 'backup', label: 'Backup & Restore', icon: FileCode },
            { id: 'audit', label: `Audit Log (${auditLogs.length})`, icon: History },
          ].map((tab) => (
            <button
              key={tab.id}
              onClick={() => setActiveTab(tab.id)}
              className={`tab-pill shrink-0 ${activeTab === tab.id ? 'tab-pill-active' : ''}`}
            >
              <tab.icon className="h-4 w-4" />
              {tab.label}
            </button>
          ))}
        </div>

        {/* Tab 1: Simulation Settings */}
        {activeTab === 'simulation' && (
          <SimulationSettings
            config={configData.simulation}
            onChange={(key, val) => handleConfigChange('simulation', key, val)}
          />
        )}

        {/* Tab 2: Provider Rules */}
        {activeTab === 'provider' && (
          <ProviderConfiguration
            config={configData.provider}
            providers={providers}
            onChange={(key, val) => handleConfigChange('provider', key, val)}
          />
        )}

        {/* Tab 3: Vehicle Constraints */}
        {activeTab === 'vehicle' && (
          <VehicleRules
            config={configData.vehicle}
            onChange={(key, val) => handleConfigChange('vehicle', key, val)}
          />
        )}

        {/* Tab 4: AI Rule Configs */}
        {activeTab === 'ai_rules' && (
          <AIRules
            config={configData.ai_rules}
            onChange={(key, val) => handleConfigChange('ai_rules', key, val)}
          />
        )}

        {/* Tab 5: Preferences */}
        {activeTab === 'preferences' && (
          <SystemPreferences
            config={configData.preferences}
            onChange={(key, val) => handleConfigChange('preferences', key, val)}
          />
        )}

        {/* Tab 6: Backup & Restore */}
        {activeTab === 'backup' && (
          <BackupRestore
            onExport={handleExportJSON}
            onImport={handleImportJSON}
            onReset={handleResetDefaults}
          />
        )}

        {/* Tab 7: Audit Log */}
        {activeTab === 'audit' && (
          <AuditLog logs={auditLogs} />
        )}
      </div>
    </div>
  );
}
