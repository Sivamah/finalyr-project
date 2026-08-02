import React, { useState, useEffect, useCallback } from 'react';
import { Settings, Save, RotateCcw, Zap, Building2, Truck, BrainCircuit, Sliders, FileCode, History } from 'lucide-react';
import api from '../services/api';
import toast from 'react-hot-toast';

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
  const [loading, setLoading] = useState(true);
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
    } finally {
      setLoading(false);
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
    } catch (err) {
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
    <div className="space-y-6 pb-12">
      {/* ── Page Header ────────────────────────────────────────────────────────── */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold text-white flex items-center gap-2">
            <Settings className="h-6 w-6 text-indigo-400" />
            System Configuration & AI Rules Management
          </h1>
          <p className="text-sm text-gray-400 mt-1">
            Centralized admin configuration portal for simulation engine, provider constraints, vehicle rules, and AI parameters
          </p>
        </div>

        {/* Global Action Buttons */}
        <div className="flex items-center gap-2">
          <button
            onClick={handleResetDefaults}
            className="flex items-center gap-1.5 px-3.5 py-2 bg-gray-800 hover:bg-gray-700 border border-gray-700 text-gray-300 font-medium rounded-lg text-xs transition-colors"
          >
            <RotateCcw className="h-4 w-4 text-amber-400" /> Factory Reset
          </button>

          <button
            onClick={handleSaveChanges}
            disabled={saving}
            className="flex items-center gap-1.5 px-4 py-2 bg-indigo-600 hover:bg-indigo-700 text-white font-bold rounded-lg text-xs transition-colors shadow-sm disabled:opacity-50"
          >
            <Save className="h-4 w-4" /> {saving ? 'Saving...' : 'Save Configuration'}
          </button>
        </div>
      </div>

      {/* ── Navigation Tabs ─────────────────────────────────────────────────── */}
      <div className="space-y-4">
        <div className="flex items-center border-b border-gray-700 overflow-x-auto">
          <button
            onClick={() => setActiveTab('simulation')}
            className={`flex items-center gap-2 py-3 px-4 font-bold text-sm border-b-2 whitespace-nowrap transition-colors ${
              activeTab === 'simulation'
                ? 'border-indigo-500 text-indigo-400'
                : 'border-transparent text-gray-400 hover:text-gray-200'
            }`}
          >
            <Zap className="h-4 w-4" /> Simulation Settings
          </button>

          <button
            onClick={() => setActiveTab('provider')}
            className={`flex items-center gap-2 py-3 px-4 font-bold text-sm border-b-2 whitespace-nowrap transition-colors ${
              activeTab === 'provider'
                ? 'border-indigo-500 text-indigo-400'
                : 'border-transparent text-gray-400 hover:text-gray-200'
            }`}
          >
            <Building2 className="h-4 w-4" /> Provider Rules
          </button>

          <button
            onClick={() => setActiveTab('vehicle')}
            className={`flex items-center gap-2 py-3 px-4 font-bold text-sm border-b-2 whitespace-nowrap transition-colors ${
              activeTab === 'vehicle'
                ? 'border-indigo-500 text-indigo-400'
                : 'border-transparent text-gray-400 hover:text-gray-200'
            }`}
          >
            <Truck className="h-4 w-4" /> Vehicle Constraints
          </button>

          <button
            onClick={() => setActiveTab('ai_rules')}
            className={`flex items-center gap-2 py-3 px-4 font-bold text-sm border-b-2 whitespace-nowrap transition-colors ${
              activeTab === 'ai_rules'
                ? 'border-indigo-500 text-indigo-400'
                : 'border-transparent text-gray-400 hover:text-gray-200'
            }`}
          >
            <BrainCircuit className="h-4 w-4" /> AI Rule Configs
          </button>

          <button
            onClick={() => setActiveTab('preferences')}
            className={`flex items-center gap-2 py-3 px-4 font-bold text-sm border-b-2 whitespace-nowrap transition-colors ${
              activeTab === 'preferences'
                ? 'border-indigo-500 text-indigo-400'
                : 'border-transparent text-gray-400 hover:text-gray-200'
            }`}
          >
            <Sliders className="h-4 w-4" /> Preferences
          </button>

          <button
            onClick={() => setActiveTab('backup')}
            className={`flex items-center gap-2 py-3 px-4 font-bold text-sm border-b-2 whitespace-nowrap transition-colors ${
              activeTab === 'backup'
                ? 'border-indigo-500 text-indigo-400'
                : 'border-transparent text-gray-400 hover:text-gray-200'
            }`}
          >
            <FileCode className="h-4 w-4" /> Backup & Restore
          </button>

          <button
            onClick={() => setActiveTab('audit')}
            className={`flex items-center gap-2 py-3 px-4 font-bold text-sm border-b-2 whitespace-nowrap transition-colors ${
              activeTab === 'audit'
                ? 'border-indigo-500 text-indigo-400'
                : 'border-transparent text-gray-400 hover:text-gray-200'
            }`}
          >
            <History className="h-4 w-4" /> Audit Log ({auditLogs.length})
          </button>
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
