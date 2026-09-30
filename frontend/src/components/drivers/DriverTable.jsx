import React, { useState } from 'react';
import { Plus, Edit2, Trash2, Phone, MapPin, Shield } from 'lucide-react';

const STATUS_STYLE = {
  Available: 'bg-green-500/10 text-green-400 border-green-500/30',
  Busy: 'bg-amber-500/10 text-amber-400 border-amber-500/30',
  Offline: 'bg-gray-500/10 text-gray-400 border-gray-500/30',
};

export default function DriverTable({ drivers = [], providers = [], vehicles = [], onAdd, onEdit, onDelete }) {
  const [showAddModal, setShowAddModal] = useState(false);
  const [editDriver, setEditDriver] = useState(null);
  const [submitting, setSubmitting] = useState(false);

  const [formData, setFormData] = useState({
    name: '',
    phone: '+91 ',
    email: '',
    provider_id: '',
    status: 'Available',
    license_number: 'TN37 2024',
    assigned_vehicle_id: '',
  });

  const handleOpenAdd = () => {
    setFormData({
      name: '',
      phone: '+91 98420 12345',
      email: '',
      provider_id: providers[0]?.id || '',
      status: 'Available',
      license_number: 'TN37 202400999',
      assigned_vehicle_id: '',
    });
    setShowAddModal(true);
  };

  const handleOpenEdit = (d) => {
    setEditDriver(d);
    setFormData({
      name: d.name,
      phone: d.phone || '',
      email: d.email || '',
      provider_id: d.provider_id || '',
      status: d.status || 'Available',
      license_number: d.license_number || '',
      assigned_vehicle_id: d.assigned_vehicle_id || '',
    });
  };

  const handleSubmitAdd = async (e) => {
    e.preventDefault();
    if (submitting) return;
    setSubmitting(true);
    try {
      await onAdd({
        ...formData,
        provider_id: formData.provider_id ? parseInt(formData.provider_id) : null,
        assigned_vehicle_id: formData.assigned_vehicle_id ? parseInt(formData.assigned_vehicle_id) : null,
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
      await onEdit(editDriver.id, {
        ...formData,
        provider_id: formData.provider_id ? parseInt(formData.provider_id) : null,
        assigned_vehicle_id: formData.assigned_vehicle_id ? parseInt(formData.assigned_vehicle_id) : null,
      });
    } finally {
      setSubmitting(false);
      setEditDriver(null);
    }
  };

  return (
    <>
      <div className="glass-panel rounded-[20px] overflow-hidden">
      {/* Table Header & Add Action */}
      <div className="flex items-center justify-between p-4 lg:p-5 border-b border-white/10">
        <h3 className="text-base font-display font-semibold text-white flex items-center gap-2">
          Driver Roster <span className="text-brand-text-muted text-sm font-medium">({drivers.length})</span>
        </h3>
        <button
          onClick={handleOpenAdd}
          className="btn-primary py-1.5 px-3.5 text-xs"
        >
          <Plus className="h-3.5 w-3.5" /> Add Driver
        </button>
      </div>

      {/* Table */}
      <div className="overflow-x-auto">
        <table className="w-full text-left border-collapse">
          <thead>
            <tr className="bg-black/20 border-b border-white/10 text-[10px] font-bold text-brand-text-muted uppercase tracking-wider">
              <th className="py-3 px-4">Driver ID</th>
              <th className="py-3 px-4">Driver Name</th>
              <th className="py-3 px-4">Provider</th>
              <th className="py-3 px-4">Contact</th>
              <th className="py-3 px-4">Vehicle Assigned</th>
              <th className="py-3 px-4">Status</th>
              <th className="py-3 px-4">Location</th>
              <th className="py-3 px-4 text-right">Actions</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-white/5 text-xs">
            {drivers.length === 0 ? (
              <tr>
                <td colSpan="8" className="text-center py-10 text-gray-500">
                  No drivers matching criteria
                </td>
              </tr>
            ) : (
              drivers.map((d) => {
                const sStyle = STATUS_STYLE[d.status] || STATUS_STYLE.Available;
                return (
                  <tr key={d.id} className="hover:bg-white/[0.02] transition-colors">
                    <td className="py-3.5 px-4 font-mono font-medium text-brand-primary">#{d.id}</td>
                    <td className="py-3.5 px-4">
                      <div className="font-semibold text-gray-100">{d.name}</div>
                      <div className="text-[10px] text-brand-text-muted flex items-center gap-1 mt-0.5">
                        <Shield className="h-3 w-3 text-gray-500" /> {d.license_number || 'N/A'}
                      </div>
                    </td>
                    <td className="py-3.5 px-4 font-medium text-gray-300">
                      <span className="bg-black/40 border border-white/10 px-2.5 py-1 rounded-[6px] text-[11px]">
                        {d.provider_name}
                      </span>
                    </td>
                    <td className="py-3.5 px-4 text-gray-300">
                      <div className="flex items-center gap-1.5 text-[11px]">
                        <Phone className="h-3 w-3 text-brand-text-muted" /> {d.phone || '—'}
                      </div>
                    </td>
                    <td className="py-3.5 px-4">
                      {d.assigned_vehicle_name !== 'None' ? (
                        <span className="text-brand-primary font-medium bg-brand-primary/10 border border-brand-primary/20 px-2 py-1 rounded-[6px] text-[11px]">
                          {d.assigned_vehicle_name}
                        </span>
                      ) : (
                        <span className="text-gray-500 italic text-[11px]">Unassigned</span>
                      )}
                    </td>
                    <td className="py-3.5 px-4">
                      <span className={`px-2.5 py-1 rounded-[6px] border text-[10px] uppercase tracking-wide font-bold ${sStyle}`}>
                        {d.status}
                      </span>
                    </td>
                    <td className="py-3.5 px-4 text-gray-400 font-mono text-[11px]">
                      <div className="flex items-center gap-1.5">
                        <MapPin className="h-3 w-3 text-brand-danger opacity-80" />
                        {d.current_lat?.toFixed(4)}, {d.current_lng?.toFixed(4)}
                      </div>
                    </td>
                    <td className="py-3.5 px-4 text-right">
                      <div className="flex items-center justify-end gap-1">
                        <button
                          onClick={() => handleOpenEdit(d)}
                          className="p-1.5 text-gray-400 hover:text-brand-primary hover:bg-white/10 rounded-lg transition-colors"
                          title="Edit Driver"
                        >
                          <Edit2 className="h-3.5 w-3.5" />
                        </button>
                        <button
                          onClick={() => onDelete(d.id)}
                          className="p-1.5 text-gray-400 hover:text-brand-danger hover:bg-white/10 rounded-lg transition-colors"
                          title="Delete Driver"
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
            <h3 className="text-lg font-bold text-white mb-4">Add New Driver</h3>
            <form onSubmit={handleSubmitAdd} className="space-y-4">
              <div>
                <label className="block text-xs font-semibold text-gray-400 mb-1">Full Name</label>
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
                  <label className="block text-xs font-semibold text-gray-400 mb-1">Phone</label>
                  <input
                    type="text"
                    value={formData.phone}
                    onChange={(e) => setFormData({ ...formData, phone: e.target.value })}
                    className="w-full input-glass rounded-lg px-3 py-2 text-sm text-white focus:outline-none focus:ring-2 focus:ring-indigo-500/50"
                  />
                </div>
                <div>
                  <label className="block text-xs font-semibold text-gray-400 mb-1">License #</label>
                  <input
                    type="text"
                    value={formData.license_number}
                    onChange={(e) => setFormData({ ...formData, license_number: e.target.value })}
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
                    className="w-full input-glass rounded-lg px-3 py-2 text-sm text-white focus:outline-none focus:ring-2 focus:ring-indigo-500/50"
                  >
                    <option value="" className="bg-gray-900 text-white">Select Provider</option>
                    {providers.map((p) => (
                      <option key={p.id} value={p.id}>{p.name}</option>
                    ))}
                  </select>
                </div>

                <div>
                  <label className="block text-xs font-semibold text-gray-400 mb-1">Status</label>
                  <select
                    value={formData.status}
                    onChange={(e) => setFormData({ ...formData, status: e.target.value })}
                    className="w-full input-glass rounded-lg px-3 py-2 text-sm text-white focus:outline-none focus:ring-2 focus:ring-indigo-500/50"
                  >
                    <option value="Available">Available</option>
                    <option value="Busy">Busy</option>
                    <option value="Offline">Offline</option>
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
                  {submitting ? 'Saving…' : 'Save Driver'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* Edit Modal */}
      {editDriver && (
        <div className="fixed inset-0 bg-black/60 z-50 flex items-center justify-center p-4">
          <div className="glass-panel rounded-xl p-6 w-full max-w-md shadow-2xl">
            <h3 className="text-lg font-bold text-white mb-4">Edit Driver #{editDriver.id}</h3>
            <form onSubmit={handleSubmitEdit} className="space-y-4">
              <div>
                <label className="block text-xs font-semibold text-gray-400 mb-1">Full Name</label>
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
                  <label className="block text-xs font-semibold text-gray-400 mb-1">Status</label>
                  <select
                    value={formData.status}
                    onChange={(e) => setFormData({ ...formData, status: e.target.value })}
                    className="w-full input-glass rounded-lg px-3 py-2 text-sm text-white focus:outline-none focus:ring-2 focus:ring-indigo-500/50"
                  >
                    <option value="Available">Available</option>
                    <option value="Busy">Busy</option>
                    <option value="Offline">Offline</option>
                  </select>
                </div>

                <div>
                  <label className="block text-xs font-semibold text-gray-400 mb-1">Assign Vehicle</label>
                  <select
                    value={formData.assigned_vehicle_id}
                    onChange={(e) => setFormData({ ...formData, assigned_vehicle_id: e.target.value })}
                    className="w-full input-glass rounded-lg px-3 py-2 text-sm text-white focus:outline-none focus:ring-2 focus:ring-indigo-500/50"
                  >
                    <option value="" className="bg-gray-900 text-white">None (Unassigned)</option>
                    {vehicles.map((v) => (
                      <option key={v.id} value={v.id}>{v.name} ({v.registration_number})</option>
                    ))}
                  </select>
                </div>
              </div>

              <div className="flex justify-end gap-2 pt-2 border-t border-white/10">
                <button
                  type="button"
                  onClick={() => setEditDriver(null)}
                  className="btn-ghost py-2 px-4 text-xs"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={submitting}
                  className="btn-primary py-2 px-4 text-xs disabled:opacity-50 disabled:cursor-not-allowed"
                >
                  {submitting ? 'Updating…' : 'Update Driver'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </>
  );
}
