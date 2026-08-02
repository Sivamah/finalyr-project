import React, { useState, useEffect } from 'react';
import { Plus, Edit2, Trash2, Truck, X, ChevronDown, ChevronUp, Zap, Building2 } from 'lucide-react';
import api from '../services/api';
import toast from 'react-hot-toast';

const PROVIDER_TYPES = [
  { value: 'Ride', label: 'Ride', examples: 'Rapido, Uber, Ola' },
  { value: 'Food', label: 'Food', examples: 'Swiggy, Zomato' },
  { value: 'Parcel', label: 'Parcel', examples: 'Porter, DTDC, Delhivery, India Post' },
];

const VEHICLE_TYPES = ['Bike', 'Auto', 'Car', 'Van', 'Truck'];

export default function ProviderManagement() {
  const [providers, setProviders] = useState([]);
  const [loading, setLoading] = useState(true);
  const [showForm, setShowForm] = useState(false);
  const [editing, setEditing] = useState(null);
  const [expanded, setExpanded] = useState({});
  const [showVehicleForm, setShowVehicleForm] = useState(null);
  const [seeding, setSeeding] = useState(false);
  const [form, setForm] = useState({ name: '', provider_type: 'Ride', description: '' });
  const [vform, setVform] = useState({ name: '', vehicle_type: 'Bike', capacity: 1, cost_per_km: 10, fuel_type: 'Petrol', mileage_kmpl: 15 });

  useEffect(() => { fetchProviders(); }, []);

  const fetchProviders = async () => {
    try {
      const res = await api.get('/providers/');
      setProviders(res.data);
    } catch (err) {
      toast.error('Failed to load providers');
    } finally {
      setLoading(false);
    }
  };

  const handleSeed = async () => {
    setSeeding(true);
    try {
      const res = await api.post('/providers/seed');
      if (res.data.created > 0) {
        toast.success(res.data.message);
        fetchProviders();
      } else {
        toast.error(res.data.message);
      }
    } catch (err) {
      toast.error(err.response?.data?.detail || 'Seed failed');
    } finally {
      setSeeding(false);
    }
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    try {
      if (editing) {
        await api.patch(`/providers/${editing}`, form);
        toast.success('Provider updated');
      } else {
        await api.post('/providers/', form);
        toast.success('Provider created');
      }
      setShowForm(false);
      setEditing(null);
      setForm({ name: '', provider_type: 'Ride', description: '' });
      fetchProviders();
    } catch (err) {
      toast.error(err.response?.data?.detail || 'Failed to save');
    }
  };

  const handleDelete = async (id) => {
    if (!confirm('Delete this provider?')) return;
    try {
      await api.delete(`/providers/${id}`);
      toast.success('Provider deleted');
      fetchProviders();
    } catch {
      toast.error('Failed to delete');
    }
  };

  const handleVehicleSubmit = async (e) => {
    e.preventDefault();
    if (!showVehicleForm) return;
    try {
      await api.post(`/providers/${showVehicleForm}/vehicles`, vform);
      toast.success('Vehicle added');
      setShowVehicleForm(null);
      setVform({ name: '', vehicle_type: 'Bike', capacity: 1, cost_per_km: 10, fuel_type: 'Petrol', mileage_kmpl: 15 });
      fetchProviders();
    } catch {
      toast.error('Failed to add vehicle');
    }
  };

  const handleDeleteVehicle = async (vehicleId) => {
    if (!confirm('Delete this vehicle?')) return;
    try {
      await api.delete(`/providers/vehicles/${vehicleId}`);
      toast.success('Vehicle deleted');
      fetchProviders();
    } catch {
      toast.error('Failed to delete');
    }
  };

  const editProvider = (p) => {
    setForm({ name: p.name, provider_type: p.provider_type, description: p.description || '' });
    setEditing(p.id);
    setShowForm(true);
  };

  const typeColors = { Ride: 'bg-blue-600', Food: 'bg-orange-600', Parcel: 'bg-purple-600' };

  return (
    <div>
      <div className="flex items-center justify-between mb-6">
        <div>
          <h1 className="text-2xl font-bold text-white">Provider Management</h1>
          <p className="text-gray-400 mt-1">Manage simulated transportation providers</p>
        </div>
        <div className="flex gap-2">
          <button onClick={handleSeed} disabled={seeding} className="flex items-center gap-2 px-4 py-2 bg-amber-600 hover:bg-amber-700 rounded-lg text-white font-medium transition-colors disabled:opacity-50">
            <Zap className={`h-4 w-4 ${seeding ? 'animate-pulse' : ''}`} /> {seeding ? 'Seeding...' : 'Seed Providers'}
          </button>
          <button onClick={() => { setEditing(null); setForm({ name: '', provider_type: 'Ride', description: '' }); setShowForm(true); }} className="flex items-center gap-2 px-4 py-2 bg-indigo-600 hover:bg-indigo-700 rounded-lg text-white font-medium transition-colors">
            <Plus className="h-4 w-4" /> Add Provider
          </button>
        </div>
      </div>

      {showForm && (
        <div className="fixed inset-0 bg-black/50 z-50 flex items-center justify-center p-4" onClick={() => setShowForm(false)}>
          <div className="bg-gray-800 rounded-xl border border-gray-700 p-6 w-full max-w-md" onClick={(e) => e.stopPropagation()}>
            <div className="flex items-center justify-between mb-4">
              <h2 className="text-lg font-bold text-white">{editing ? 'Edit Provider' : 'New Provider'}</h2>
              <button onClick={() => setShowForm(false)} className="text-gray-400 hover:text-white"><X className="h-5 w-5" /></button>
            </div>
            <form onSubmit={handleSubmit} className="space-y-4">
              <div>
                <label className="block text-sm font-medium text-gray-300 mb-1">Name</label>
                <input type="text" required value={form.name} onChange={(e) => setForm({ ...form, name: e.target.value })} className="w-full px-3 py-2 bg-gray-700 border border-gray-600 rounded-lg text-white focus:outline-none focus:ring-2 focus:ring-indigo-500" placeholder="e.g. Rapido" />
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-300 mb-1">Type</label>
                <select value={form.provider_type} onChange={(e) => setForm({ ...form, provider_type: e.target.value })} className="w-full px-3 py-2 bg-gray-700 border border-gray-600 rounded-lg text-white focus:outline-none focus:ring-2 focus:ring-indigo-500">
                  {PROVIDER_TYPES.map((t) => <option key={t.value} value={t.value}>{t.label} ({t.examples})</option>)}
                </select>
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-300 mb-1">Description</label>
                <textarea value={form.description} onChange={(e) => setForm({ ...form, description: e.target.value })} rows={3} className="w-full px-3 py-2 bg-gray-700 border border-gray-600 rounded-lg text-white focus:outline-none focus:ring-2 focus:ring-indigo-500" placeholder="Optional description" />
              </div>
              <button type="submit" className="w-full py-2 bg-indigo-600 hover:bg-indigo-700 text-white font-medium rounded-lg transition-colors">{editing ? 'Update' : 'Create'} Provider</button>
            </form>
          </div>
        </div>
      )}

      {showVehicleForm && (
        <div className="fixed inset-0 bg-black/50 z-50 flex items-center justify-center p-4" onClick={() => setShowVehicleForm(null)}>
          <div className="bg-gray-800 rounded-xl border border-gray-700 p-6 w-full max-w-md" onClick={(e) => e.stopPropagation()}>
            <div className="flex items-center justify-between mb-4">
              <h2 className="text-lg font-bold text-white">Add Vehicle</h2>
              <button onClick={() => setShowVehicleForm(null)} className="text-gray-400 hover:text-white"><X className="h-5 w-5" /></button>
            </div>
            <form onSubmit={handleVehicleSubmit} className="space-y-4">
              <div>
                <label className="block text-sm font-medium text-gray-300 mb-1">Name</label>
                <input type="text" required value={vform.name} onChange={(e) => setVform({ ...vform, name: e.target.value })} className="w-full px-3 py-2 bg-gray-700 border border-gray-600 rounded-lg text-white focus:outline-none focus:ring-2 focus:ring-indigo-500" placeholder="e.g. Honda Activa" />
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-300 mb-1">Type</label>
                <select value={vform.vehicle_type} onChange={(e) => setVform({ ...vform, vehicle_type: e.target.value })} className="w-full px-3 py-2 bg-gray-700 border border-gray-600 rounded-lg text-white focus:outline-none focus:ring-2 focus:ring-indigo-500">
                  {VEHICLE_TYPES.map((t) => <option key={t} value={t}>{t}</option>)}
                </select>
              </div>
              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="block text-sm font-medium text-gray-300 mb-1">Capacity</label>
                  <input type="number" min="1" value={vform.capacity} onChange={(e) => setVform({ ...vform, capacity: parseInt(e.target.value) || 1 })} className="w-full px-3 py-2 bg-gray-700 border border-gray-600 rounded-lg text-white focus:outline-none focus:ring-2 focus:ring-indigo-500" />
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-300 mb-1">Cost/km (₹)</label>
                  <input type="number" min="1" step="0.5" value={vform.cost_per_km} onChange={(e) => setVform({ ...vform, cost_per_km: parseFloat(e.target.value) || 10 })} className="w-full px-3 py-2 bg-gray-700 border border-gray-600 rounded-lg text-white focus:outline-none focus:ring-2 focus:ring-indigo-500" />
                </div>
              </div>
              <button type="submit" className="w-full py-2 bg-green-600 hover:bg-green-700 text-white font-medium rounded-lg transition-colors">Add Vehicle</button>
            </form>
          </div>
        </div>
      )}

      {loading ? (
        <div className="flex items-center justify-center h-64"><div className="animate-spin rounded-full h-8 w-8 border-t-2 border-indigo-500" /></div>
      ) : providers.length === 0 ? (
        <div className="text-center py-16 text-gray-500">
          <Building2 className="h-12 w-12 mx-auto mb-3 opacity-50" />
          <p className="text-lg font-medium">No providers yet</p>
          <p className="text-sm">Click "Add Provider" to create your first simulated provider</p>
        </div>
      ) : (
        <div className="grid grid-cols-1 lg:grid-cols-2 xl:grid-cols-3 gap-4">
          {providers.map((p) => (
            <div key={p.id} className="bg-gray-800 border border-gray-700 rounded-xl overflow-hidden">
              <div className="p-5">
                <div className="flex items-start justify-between">
                  <div className="flex items-center gap-3">
                    <div className={`p-2.5 rounded-lg ${typeColors[p.provider_type] || 'bg-gray-600'}`}>
                      <Building2 className="h-5 w-5 text-white" />
                    </div>
                    <div>
                      <h3 className="font-semibold text-white">{p.name}</h3>
                      <span className="inline-block px-2 py-0.5 rounded text-xs font-medium bg-gray-700 text-gray-300 mt-1">{p.provider_type}</span>
                    </div>
                  </div>
                  <div className="flex gap-1">
                    <button onClick={() => editProvider(p)} className="p-1.5 text-gray-400 hover:text-blue-400 rounded"><Edit2 className="h-4 w-4" /></button>
                    <button onClick={() => handleDelete(p.id)} className="p-1.5 text-gray-400 hover:text-red-400 rounded"><Trash2 className="h-4 w-4" /></button>
                  </div>
                </div>
                {p.description && <p className="text-sm text-gray-400 mt-3">{p.description}</p>}
                <div className="flex items-center gap-2 mt-3 text-xs text-gray-500">
                  <span className={`px-2 py-0.5 rounded-full ${p.status === 'Active' ? 'bg-green-900 text-green-300' : 'bg-gray-700 text-gray-400'}`}>{p.status}</span>
                  <span className="px-2 py-0.5 rounded-full bg-gray-700 text-gray-400">{p.api_status}</span>
                </div>

                <button onClick={() => setExpanded({ ...expanded, [p.id]: !expanded[p.id] })} className="flex items-center gap-1 text-sm text-gray-400 hover:text-white mt-3 transition-colors">
                  <Truck className="h-4 w-4" /> {p.vehicles?.length || 0} Vehicles
                  {expanded[p.id] ? <ChevronUp className="h-4 w-4" /> : <ChevronDown className="h-4 w-4" />}
                </button>
              </div>

              {expanded[p.id] && (
                <div className="border-t border-gray-700 px-5 py-3 space-y-2">
                  {p.vehicles?.length > 0 ? p.vehicles.map((v) => (
                    <div key={v.id} className="flex items-center justify-between text-sm bg-gray-700/50 rounded-lg px-3 py-2">
                      <div>
                        <span className="text-white font-medium">{v.name}</span>
                        <span className="text-gray-400 ml-2">({v.vehicle_type} · ₹{v.cost_per_km}/km)</span>
                      </div>
                      <button onClick={() => handleDeleteVehicle(v.id)} className="text-gray-500 hover:text-red-400"><Trash2 className="h-3.5 w-3.5" /></button>
                    </div>
                  )) : <p className="text-sm text-gray-500">No vehicles</p>}
                  <button onClick={() => { setShowVehicleForm(p.id); setVform({ name: '', vehicle_type: 'Bike', capacity: 1, cost_per_km: 10, fuel_type: 'Petrol', mileage_kmpl: 15 }); }} className="flex items-center gap-1 text-sm text-indigo-400 hover:text-indigo-300 transition-colors">
                    <Plus className="h-3.5 w-3.5" /> Add Vehicle
                  </button>
                </div>
              )}
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
