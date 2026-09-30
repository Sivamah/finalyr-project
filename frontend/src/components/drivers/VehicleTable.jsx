import React, { useState } from 'react';
import { Plus, Edit2, Trash2, Fuel } from 'lucide-react';

const STATUS_STYLE = {
  Available: 'bg-green-500/10 text-green-400 border-green-500/30',
  Busy: 'bg-blue-500/10 text-blue-400 border-blue-500/30',
  Offline: 'bg-gray-500/10 text-gray-400 border-gray-500/30',
  Maintenance: 'bg-amber-500/10 text-amber-400 border-amber-500/30',
};

export default function VehicleTable({ vehicles = [], providers = [], drivers = [], onAdd, onEdit, onDelete }) {
  const [showAddModal, setShowAddModal] = useState(false);
  const [editVehicle, setEditVehicle] = useState(null);
  const [submitting, setSubmitting] = useState(false);

  const [formData, setFormData] = useState({
    name: '',
    vehicle_type: 'Bike',
    registration_number: '',
    capacity: 1,
    fuel_type: 'Petrol',
    provider_id: '',
    status: 'Available',
    current_driver_id: '',
  });

  const handleOpenAdd = () => {
    setFormData({
      name: '',
      vehicle_type: 'Bike',
      // Left blank deliberately: this used to pre-fill a random
      // `TN-37-X-####` plate, which meant one careless save wrote a fabricated
      // registration into the fleet. The operator types the real one.
      registration_number: '',
      capacity: 1,
      fuel_type: 'Petrol',
      provider_id: providers[0]?.id || '',
      status: 'Available',
      current_driver_id: '',
    });
    setShowAddModal(true);
  };

  const handleOpenEdit = (v) => {
    setEditVehicle(v);
    setFormData({
      name: v.name,
      vehicle_type: v.vehicle_type,
      registration_number: v.registration_number || '',
      capacity: v.capacity || 1,
      fuel_type: v.fuel_type || 'Petrol',
      provider_id: v.provider_id || '',
      status: v.status || 'Available',
      current_driver_id: v.current_driver_id || '',
    });
  };

  const handleSubmitAdd = async (e) => {
    e.preventDefault();
    if (submitting) return;
    setSubmitting(true);
    try {
      await onAdd({
        ...formData,
        provider_id: parseInt(formData.provider_id),
        capacity: parseInt(formData.capacity),
        current_driver_id: formData.current_driver_id ? parseInt(formData.current_driver_id) : null,
      });
    } finally {
      setSubmitting(false);
      setShowAddModal(false);
    }
  };

  const handleSubmitEdit = async (e) => {
    e.preventDefault();
    if (submitting) return;
    setSubmitting(true);
    try {
      await onEdit(editVehicle.id, {
        ...formData,
        provider_id: formData.provider_id ? parseInt(formData.provider_id) : undefined,
        capacity: parseInt(formData.capacity),
        current_driver_id: formData.current_driver_id ? parseInt(formData.current_driver_id) : null,
      });
    } finally {
      setSubmitting(false);
      setEditVehicle(null);
    }
  };

  return (
    <>
      <div className="glass-panel rounded-[20px] overflow-hidden">
      {/* Header */}
      <div className="flex items-center justify-between p-4 lg:p-5 border-b border-white/10">
        <h3 className="text-base font-display font-semibold text-white flex items-center gap-2">
          Vehicle Fleet <span className="text-brand-text-muted text-sm font-medium">({vehicles.length})</span>
        </h3>
        <button
          onClick={handleOpenAdd}
          className="btn-primary py-1.5 px-3.5 text-xs"
        >
          <Plus className="h-3.5 w-3.5" /> Add Vehicle
        </button>
      </div>

      {/* Table */}
      <div className="overflow-x-auto">
        <table className="w-full text-left border-collapse">
          <thead>
            <tr className="bg-black/20 border-b border-white/10 text-[10px] font-bold text-brand-text-muted uppercase tracking-wider">
              <th className="py-3 px-4">Vehicle ID</th>
              <th className="py-3 px-4">Registration #</th>
              <th className="py-3 px-4">Vehicle / Type</th>
              <th className="py-3 px-4">Capacity</th>
              <th className="py-3 px-4">Provider</th>
              <th className="py-3 px-4">Fuel Type</th>
              <th className="py-3 px-4">Current Driver</th>
              <th className="py-3 px-4">Status</th>
              <th className="py-3 px-4 text-right">Actions</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-white/5 text-xs">
            {vehicles.length === 0 ? (
              <tr>
                <td colSpan="9" className="text-center py-10 text-gray-500">
                  No vehicles matching criteria
                </td>
              </tr>
            ) : (
              vehicles.map((v) => {
                const sStyle = STATUS_STYLE[v.status] || STATUS_STYLE.Available;
                return (
                  <tr key={v.id} className="hover:bg-white/[0.02] transition-colors">
                    <td className="py-3.5 px-4 font-mono font-medium text-brand-primary">#{v.id}</td>
                    <td className="py-3.5 px-4 font-mono font-semibold text-gray-100">
                      {v.registration_number || 'TN-37-AB-1001'}
                    </td>
                    <td className="py-3.5 px-4">
                      <div className="font-semibold text-gray-100">{v.name}</div>
                      <div className="text-[10px] text-brand-text-muted mt-0.5">{v.vehicle_type}</div>
                    </td>
                    <td className="py-3.5 px-4 font-mono text-gray-300">
                      {v.capacity} pax
                    </td>
                    <td className="py-3.5 px-4 font-medium text-gray-300">
                      <span className="bg-black/40 border border-white/10 px-2.5 py-1 rounded-[6px] text-[11px]">
                        {v.provider_name}
                      </span>
                    </td>
                    <td className="py-3.5 px-4 text-gray-300">
                      <span className="flex items-center gap-1.5 text-[11px]">
                        <Fuel className="h-3 w-3 text-brand-warning opacity-80" /> {v.fuel_type}
                      </span>
                    </td>
                    <td className="py-3.5 px-4">
                      {v.current_driver_name !== 'Unassigned' ? (
                        <span className="text-brand-success font-medium bg-brand-success/10 border border-brand-success/20 px-2 py-1 rounded-[6px] text-[11px]">
                          {v.current_driver_name}
                        </span>
                      ) : (
                        <span className="text-gray-500 italic text-[11px]">Unassigned</span>
                      )}
                    </td>
                    <td className="py-3.5 px-4">
                      <span className={`px-2.5 py-1 rounded-[6px] border text-[10px] uppercase tracking-wide font-bold ${sStyle}`}>
                        {v.status}
                      </span>
                    </td>
                    <td className="py-3.5 px-4 text-right">
                      <div className="flex items-center justify-end gap-1">
                        <button
                          onClick={() => handleOpenEdit(v)}
                          className="p-1.5 text-gray-400 hover:text-brand-primary hover:bg-white/10 rounded-lg transition-colors"
                          title="Edit Vehicle"
                        >
                          <Edit2 className="h-3.5 w-3.5" />
                        </button>
                        <button
                          onClick={() => onDelete(v.id)}
                          className="p-1.5 text-gray-400 hover:text-red-400 hover:bg-gray-700 rounded-lg transition-colors"
                          title="Delete Vehicle"
                        >
                          <Trash2 className="h-3.5 w-3.5" />
                        </button>
                      </div>
                    </td>
                  </tr>
                );
              })
            )}
          </tbody>
        </table>
      </div>

      </div>

      {/* Add Modal */}
      {showAddModal && (
        <div className="fixed inset-0 bg-black/60 z-50 flex items-center justify-center p-4">
          <div className="glass-panel rounded-xl p-6 w-full max-w-md shadow-2xl">
            <h3 className="text-lg font-bold text-white mb-4">Add New Vehicle</h3>
            <form onSubmit={handleSubmitAdd} className="space-y-4">
              <div>
                <label className="block text-xs font-semibold text-gray-400 mb-1">Vehicle Name</label>
                <input
                  type="text"
                  required
                  value={formData.name}
                  onChange={(e) => setFormData({ ...formData, name: e.target.value })}
                  className="w-full input-glass rounded-lg px-3 py-2 text-sm text-white focus:outline-none focus:ring-2 focus:ring-indigo-500/50"
                />
              </div>

              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="block text-xs font-semibold text-gray-400 mb-1">Type</label>
                  <select
                    value={formData.vehicle_type}
                    onChange={(e) => setFormData({ ...formData, vehicle_type: e.target.value })}
                    className="w-full input-glass rounded-lg px-3 py-2 text-sm text-white focus:outline-none focus:ring-2 focus:ring-indigo-500/50"
                  >
                    <option value="Bike">Bike</option>
                    <option value="Auto">Auto</option>
                    <option value="Car">Car</option>
                    <option value="Van">Van</option>
                    <option value="Truck">Truck</option>
                  </select>
                </div>
                <div>
                  <label className="block text-xs font-semibold text-gray-400 mb-1">Registration #</label>
                  <input
                    type="text"
                    value={formData.registration_number}
                    onChange={(e) => setFormData({ ...formData, registration_number: e.target.value })}
                    className="w-full input-glass rounded-lg px-3 py-2 text-sm text-white focus:outline-none focus:ring-2 focus:ring-indigo-500/50"
                  />
                </div>
              </div>

              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="block text-xs font-semibold text-gray-400 mb-1">Provider</label>
                  <select
                    value={formData.provider_id}
                    onChange={(e) => setFormData({ ...formData, provider_id: e.target.value })}
                    required
                    className="w-full input-glass rounded-lg px-3 py-2 text-sm text-white focus:outline-none focus:ring-2 focus:ring-indigo-500/50"
                  >
                    <option value="" className="bg-gray-900 text-white">Select Provider</option>
                    {providers.map((p) => (
                      <option key={p.id} value={p.id}>{p.name}</option>
                    ))}
                  </select>
                </div>
                <div>
                  <label className="block text-xs font-semibold text-gray-400 mb-1">Fuel Type</label>
                  <select
                    value={formData.fuel_type}
                    onChange={(e) => setFormData({ ...formData, fuel_type: e.target.value })}
                    className="w-full input-glass rounded-lg px-3 py-2 text-sm text-white focus:outline-none focus:ring-2 focus:ring-indigo-500/50"
                  >
                    <option value="Petrol">Petrol</option>
                    <option value="EV">EV</option>
                    <option value="CNG">CNG</option>
                    <option value="Diesel">Diesel</option>
                  </select>
                </div>
              </div>

              <div className="flex justify-end gap-2 pt-2 border-t border-white/10">
                <button
                  type="button"
                  onClick={() => setShowAddModal(false)}
                  className="btn-ghost py-2 px-4 text-xs"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={submitting}
                  className="btn-primary py-2 px-4 text-xs disabled:opacity-50 disabled:cursor-not-allowed"
                >
                  {submitting ? 'Saving…' : 'Save Vehicle'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* Edit Modal */}
      {editVehicle && (
        <div className="fixed inset-0 bg-black/60 z-50 flex items-center justify-center p-4">
          <div className="glass-panel rounded-xl p-6 w-full max-w-md shadow-2xl">
            <h3 className="text-lg font-bold text-white mb-4">Edit Vehicle #{editVehicle.id}</h3>
            <form onSubmit={handleSubmitEdit} className="space-y-4">
              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="block text-xs font-semibold text-gray-400 mb-1">Status</label>
                  <select
                    value={formData.status}
                    onChange={(e) => setFormData({ ...formData, status: e.target.value })}
                    className="w-full input-glass rounded-lg px-3 py-2 text-sm text-white focus:outline-none focus:ring-2 focus:ring-indigo-500/50"
                  >
                    <option value="Available">Available</option>
                    <option value="Busy">Busy (In Service)</option>
                    <option value="Offline">Offline</option>
                    <option value="Maintenance">Maintenance</option>
                  </select>
                </div>

                <div>
                  <label className="block text-xs font-semibold text-gray-400 mb-1">Current Driver</label>
                  <select
                    value={formData.current_driver_id}
                    onChange={(e) => setFormData({ ...formData, current_driver_id: e.target.value })}
                    className="w-full input-glass rounded-lg px-3 py-2 text-sm text-white focus:outline-none focus:ring-2 focus:ring-indigo-500/50"
                  >
                    <option value="" className="bg-gray-900 text-white">Unassigned</option>
                    {drivers.map((d) => (
                      <option key={d.id} value={d.id}>{d.name}</option>
                    ))}
                  </select>
                </div>
              </div>

              <div className="flex justify-end gap-2 pt-2 border-t border-white/10">
                <button
                  type="button"
                  onClick={() => setEditVehicle(null)}
                  className="btn-ghost py-2 px-4 text-xs"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={submitting}
                  className="btn-primary py-2 px-4 text-xs disabled:opacity-50 disabled:cursor-not-allowed"
                >
                  {submitting ? 'Updating…' : 'Update Vehicle'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </>
  );
}
