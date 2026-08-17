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

  const handleSubmitAdd = (e) => {
    e.preventDefault();
    onAdd({
      ...formData,
      provider_id: formData.provider_id ? parseInt(formData.provider_id) : null,
      assigned_vehicle_id: formData.assigned_vehicle_id ? parseInt(formData.assigned_vehicle_id) : null,
    });
    setShowAddModal(false);
  };

  const handleSubmitEdit = (e) => {
    e.preventDefault();
    onEdit(editDriver.id, {
      ...formData,
      provider_id: formData.provider_id ? parseInt(formData.provider_id) : null,
      assigned_vehicle_id: formData.assigned_vehicle_id ? parseInt(formData.assigned_vehicle_id) : null,
    });
    setEditDriver(null);
  };

  return (
    <div className="bg-gray-800 border border-gray-700 rounded-xl shadow-sm overflow-hidden">
      {/* Table Header & Add Action */}
      <div className="flex items-center justify-between p-4 border-b border-gray-700">
        <h3 className="text-base font-bold text-white flex items-center gap-2">
          Driver Roster ({drivers.length})
        </h3>
        <button
          onClick={handleOpenAdd}
          className="flex items-center gap-1.5 px-3 py-1.5 bg-indigo-600 hover:bg-indigo-700 text-white text-xs font-bold rounded-lg transition-colors shadow-sm"
        >
          <Plus className="h-4 w-4" /> Add Driver
        </button>
      </div>

      {/* Table */}
      <div className="overflow-x-auto">
        <table className="w-full text-left border-collapse">
          <thead>
            <tr className="bg-gray-900/60 border-b border-gray-700 text-[11px] font-bold text-gray-400 uppercase tracking-wider">
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
          <tbody className="divide-y divide-gray-700 text-xs">
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
                  <tr key={d.id} className="hover:bg-gray-750/50 transition-colors">
                    <td className="py-3 px-4 font-mono font-bold text-indigo-400">#{d.id}</td>
                    <td className="py-3 px-4">
                      <div className="font-bold text-white">{d.name}</div>
                      <div className="text-[10px] text-gray-400 flex items-center gap-1">
                        <Shield className="h-3 w-3 text-gray-500" /> {d.license_number || 'N/A'}
                      </div>
                    </td>
                    <td className="py-3 px-4 font-medium text-gray-300">
                      <span className="bg-gray-900 border border-gray-700 px-2 py-0.5 rounded text-[11px]">
                        {d.provider_name}
                      </span>
                    </td>
                    <td className="py-3 px-4 text-gray-300">
                      <div className="flex items-center gap-1 text-[11px]">
                        <Phone className="h-3 w-3 text-gray-400" /> {d.phone || '—'}
                      </div>
                    </td>
                    <td className="py-3 px-4">
                      {d.assigned_vehicle_name !== 'None' ? (
                        <span className="text-indigo-300 font-medium bg-indigo-500/10 border border-indigo-500/20 px-2 py-0.5 rounded">
                          {d.assigned_vehicle_name}
                        </span>
                      ) : (
                        <span className="text-gray-500 italic">Unassigned</span>
                      )}
                    </td>
                    <td className="py-3 px-4">
                      <span className={`px-2 py-0.5 rounded border text-[11px] font-bold ${sStyle}`}>
                        {d.status}
                      </span>
                    </td>
                    <td className="py-3 px-4 text-gray-400 font-mono text-[11px]">
                      <div className="flex items-center gap-1">
                        <MapPin className="h-3 w-3 text-red-400" />
                        {d.current_lat?.toFixed(4)}, {d.current_lng?.toFixed(4)}
                      </div>
                    </td>
                    <td className="py-3 px-4 text-right">
                      <div className="flex items-center justify-end gap-1">
                        <button
                          onClick={() => handleOpenEdit(d)}
                          className="p-1.5 text-gray-400 hover:text-indigo-400 hover:bg-gray-700 rounded-lg transition-colors"
                          title="Edit Driver"
                        >
                          <Edit2 className="h-3.5 w-3.5" />
                        </button>
                        <button
                          onClick={() => onDelete(d.id)}
                          className="p-1.5 text-gray-400 hover:text-red-400 hover:bg-gray-700 rounded-lg transition-colors"
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

      {/* Add Modal */}
      {showAddModal && (
        <div className="fixed inset-0 bg-black/60 z-50 flex items-center justify-center p-4">
          <div className="bg-gray-800 border border-gray-700 rounded-xl p-6 w-full max-w-md shadow-2xl">
            <h3 className="text-lg font-bold text-white mb-4">Add New Driver</h3>
            <form onSubmit={handleSubmitAdd} className="space-y-4">
              <div>
                <label className="block text-xs font-semibold text-gray-400 mb-1">Full Name</label>
                <input
                  type="text"
                  required
                  value={formData.name}
                  onChange={(e) => setFormData({ ...formData, name: e.target.value })}
                  className="w-full bg-gray-900 border border-gray-700 rounded-lg px-3 py-2 text-sm text-white focus:outline-none focus:ring-2 focus:ring-indigo-500"
                />
              </div>

              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="block text-xs font-semibold text-gray-400 mb-1">Phone</label>
                  <input
                    type="text"
                    value={formData.phone}
                    onChange={(e) => setFormData({ ...formData, phone: e.target.value })}
                    className="w-full bg-gray-900 border border-gray-700 rounded-lg px-3 py-2 text-sm text-white focus:outline-none focus:ring-2 focus:ring-indigo-500"
                  />
                </div>
                <div>
                  <label className="block text-xs font-semibold text-gray-400 mb-1">License #</label>
                  <input
                    type="text"
                    value={formData.license_number}
                    onChange={(e) => setFormData({ ...formData, license_number: e.target.value })}
                    className="w-full bg-gray-900 border border-gray-700 rounded-lg px-3 py-2 text-sm text-white focus:outline-none focus:ring-2 focus:ring-indigo-500"
                  />
                </div>
              </div>

              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="block text-xs font-semibold text-gray-400 mb-1">Provider</label>
                  <select
                    value={formData.provider_id}
                    onChange={(e) => setFormData({ ...formData, provider_id: e.target.value })}
                    className="w-full bg-gray-900 border border-gray-700 rounded-lg px-3 py-2 text-sm text-white focus:outline-none focus:ring-2 focus:ring-indigo-500"
                  >
                    <option value="">Select Provider</option>
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
                    className="w-full bg-gray-900 border border-gray-700 rounded-lg px-3 py-2 text-sm text-white focus:outline-none focus:ring-2 focus:ring-indigo-500"
                  >
                    <option value="Available">Available</option>
                    <option value="Busy">Busy</option>
                    <option value="Offline">Offline</option>
                  </select>
                </div>
              </div>

              <div className="flex justify-end gap-2 pt-2 border-t border-gray-700">
                <button
                  type="button"
                  onClick={() => setShowAddModal(false)}
                  className="px-4 py-2 bg-gray-700 hover:bg-gray-600 text-gray-300 text-xs font-bold rounded-lg"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  className="px-4 py-2 bg-indigo-600 hover:bg-indigo-700 text-white text-xs font-bold rounded-lg"
                >
                  Save Driver
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* Edit Modal */}
      {editDriver && (
        <div className="fixed inset-0 bg-black/60 z-50 flex items-center justify-center p-4">
          <div className="bg-gray-800 border border-gray-700 rounded-xl p-6 w-full max-w-md shadow-2xl">
            <h3 className="text-lg font-bold text-white mb-4">Edit Driver #{editDriver.id}</h3>
            <form onSubmit={handleSubmitEdit} className="space-y-4">
              <div>
                <label className="block text-xs font-semibold text-gray-400 mb-1">Full Name</label>
                <input
                  type="text"
                  required
                  value={formData.name}
                  onChange={(e) => setFormData({ ...formData, name: e.target.value })}
                  className="w-full bg-gray-900 border border-gray-700 rounded-lg px-3 py-2 text-sm text-white focus:outline-none focus:ring-2 focus:ring-indigo-500"
                />
              </div>

              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="block text-xs font-semibold text-gray-400 mb-1">Status</label>
                  <select
                    value={formData.status}
                    onChange={(e) => setFormData({ ...formData, status: e.target.value })}
                    className="w-full bg-gray-900 border border-gray-700 rounded-lg px-3 py-2 text-sm text-white focus:outline-none focus:ring-2 focus:ring-indigo-500"
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
                    className="w-full bg-gray-900 border border-gray-700 rounded-lg px-3 py-2 text-sm text-white focus:outline-none focus:ring-2 focus:ring-indigo-500"
                  >
                    <option value="">None (Unassigned)</option>
                    {vehicles.map((v) => (
                      <option key={v.id} value={v.id}>{v.name} ({v.registration_number})</option>
                    ))}
                  </select>
                </div>
              </div>

              <div className="flex justify-end gap-2 pt-2 border-t border-gray-700">
                <button
                  type="button"
                  onClick={() => setEditDriver(null)}
                  className="px-4 py-2 bg-gray-700 hover:bg-gray-600 text-gray-300 text-xs font-bold rounded-lg"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  className="px-4 py-2 bg-indigo-600 hover:bg-indigo-700 text-white text-xs font-bold rounded-lg"
                >
                  Update Driver
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
}
