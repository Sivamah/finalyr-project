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

  const [formData, setFormData] = useState({
    name: '',
    vehicle_type: 'Bike',
    registration_number: 'TN-37-AB-1001',
    capacity: 1,
    fuel_type: 'Petrol',
    provider_id: '',
    status: 'Available',
    current_driver_id: '',
  });

  const handleOpenAdd = () => {
    setFormData({
      name: 'Rapido Bike GT',
      vehicle_type: 'Bike',
      registration_number: `TN-37-X-${Math.floor(1000 + Math.random() * 9000)}`,
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

  const handleSubmitAdd = (e) => {
    e.preventDefault();
    onAdd({
      ...formData,
      provider_id: parseInt(formData.provider_id),
      capacity: parseInt(formData.capacity),
      current_driver_id: formData.current_driver_id ? parseInt(formData.current_driver_id) : null,
    });
    setShowAddModal(false);
  };

  const handleSubmitEdit = (e) => {
    e.preventDefault();
    onEdit(editVehicle.id, {
      ...formData,
      provider_id: formData.provider_id ? parseInt(formData.provider_id) : undefined,
      capacity: parseInt(formData.capacity),
      current_driver_id: formData.current_driver_id ? parseInt(formData.current_driver_id) : null,
    });
    setEditVehicle(null);
  };

  return (
    <div className="bg-gray-800 border border-gray-700 rounded-xl shadow-sm overflow-hidden">
      {/* Header */}
      <div className="flex items-center justify-between p-4 border-b border-gray-700">
        <h3 className="text-base font-bold text-white flex items-center gap-2">
          Vehicle Fleet ({vehicles.length})
        </h3>
        <button
          onClick={handleOpenAdd}
          className="flex items-center gap-1.5 px-3 py-1.5 bg-indigo-600 hover:bg-indigo-700 text-white text-xs font-bold rounded-lg transition-colors shadow-sm"
        >
          <Plus className="h-4 w-4" /> Add Vehicle
        </button>
      </div>

      {/* Table */}
      <div className="overflow-x-auto">
        <table className="w-full text-left border-collapse">
          <thead>
            <tr className="bg-gray-900/60 border-b border-gray-700 text-[11px] font-bold text-gray-400 uppercase tracking-wider">
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
          <tbody className="divide-y divide-gray-700 text-xs">
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
                  <tr key={v.id} className="hover:bg-gray-750/50 transition-colors">
                    <td className="py-3 px-4 font-mono font-bold text-indigo-400">#{v.id}</td>
                    <td className="py-3 px-4 font-mono font-semibold text-white">
                      {v.registration_number || 'TN-37-AB-1001'}
                    </td>
                    <td className="py-3 px-4">
                      <div className="font-bold text-white">{v.name}</div>
                      <div className="text-[10px] text-gray-400">{v.vehicle_type}</div>
                    </td>
                    <td className="py-3 px-4 font-mono text-gray-300">
                      {v.capacity} passenger(s)
                    </td>
                    <td className="py-3 px-4 font-medium text-gray-300">
                      <span className="bg-gray-900 border border-gray-700 px-2 py-0.5 rounded text-[11px]">
                        {v.provider_name}
                      </span>
                    </td>
                    <td className="py-3 px-4 text-gray-300">
                      <span className="flex items-center gap-1 text-[11px]">
                        <Fuel className="h-3 w-3 text-amber-400" /> {v.fuel_type}
                      </span>
                    </td>
                    <td className="py-3 px-4">
                      {v.current_driver_name !== 'Unassigned' ? (
                        <span className="text-green-400 font-medium bg-green-500/10 border border-green-500/20 px-2 py-0.5 rounded">
                          {v.current_driver_name}
                        </span>
                      ) : (
                        <span className="text-gray-500 italic">Unassigned</span>
                      )}
                    </td>
                    <td className="py-3 px-4">
                      <span className={`px-2 py-0.5 rounded border text-[11px] font-bold ${sStyle}`}>
                        {v.status}
                      </span>
                    </td>
                    <td className="py-3 px-4 text-right">
                      <div className="flex items-center justify-end gap-1">
                        <button
                          onClick={() => handleOpenEdit(v)}
                          className="p-1.5 text-gray-400 hover:text-indigo-400 hover:bg-gray-700 rounded-lg transition-colors"
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

      {/* Add Modal */}
      {showAddModal && (
        <div className="fixed inset-0 bg-black/60 z-50 flex items-center justify-center p-4">
          <div className="bg-gray-800 border border-gray-700 rounded-xl p-6 w-full max-w-md shadow-2xl">
            <h3 className="text-lg font-bold text-white mb-4">Add New Vehicle</h3>
            <form onSubmit={handleSubmitAdd} className="space-y-4">
              <div>
                <label className="block text-xs font-semibold text-gray-400 mb-1">Vehicle Name</label>
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
                  <label className="block text-xs font-semibold text-gray-400 mb-1">Type</label>
                  <select
                    value={formData.vehicle_type}
                    onChange={(e) => setFormData({ ...formData, vehicle_type: e.target.value })}
                    className="w-full bg-gray-900 border border-gray-700 rounded-lg px-3 py-2 text-sm text-white focus:outline-none focus:ring-2 focus:ring-indigo-500"
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
                    required
                    className="w-full bg-gray-900 border border-gray-700 rounded-lg px-3 py-2 text-sm text-white focus:outline-none focus:ring-2 focus:ring-indigo-500"
                  >
                    <option value="">Select Provider</option>
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
                    className="w-full bg-gray-900 border border-gray-700 rounded-lg px-3 py-2 text-sm text-white focus:outline-none focus:ring-2 focus:ring-indigo-500"
                  >
                    <option value="Petrol">Petrol</option>
                    <option value="EV">EV</option>
                    <option value="CNG">CNG</option>
                    <option value="Diesel">Diesel</option>
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
                  Save Vehicle
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* Edit Modal */}
      {editVehicle && (
        <div className="fixed inset-0 bg-black/60 z-50 flex items-center justify-center p-4">
          <div className="bg-gray-800 border border-gray-700 rounded-xl p-6 w-full max-w-md shadow-2xl">
            <h3 className="text-lg font-bold text-white mb-4">Edit Vehicle #{editVehicle.id}</h3>
            <form onSubmit={handleSubmitEdit} className="space-y-4">
              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="block text-xs font-semibold text-gray-400 mb-1">Status</label>
                  <select
                    value={formData.status}
                    onChange={(e) => setFormData({ ...formData, status: e.target.value })}
                    className="w-full bg-gray-900 border border-gray-700 rounded-lg px-3 py-2 text-sm text-white focus:outline-none focus:ring-2 focus:ring-indigo-500"
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
                    className="w-full bg-gray-900 border border-gray-700 rounded-lg px-3 py-2 text-sm text-white focus:outline-none focus:ring-2 focus:ring-indigo-500"
                  >
                    <option value="">Unassigned</option>
                    {drivers.map((d) => (
                      <option key={d.id} value={d.id}>{d.name}</option>
                    ))}
                  </select>
                </div>
              </div>

              <div className="flex justify-end gap-2 pt-2 border-t border-gray-700">
                <button
                  type="button"
                  onClick={() => setEditVehicle(null)}
                  className="px-4 py-2 bg-gray-700 hover:bg-gray-600 text-gray-300 text-xs font-bold rounded-lg"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  className="px-4 py-2 bg-indigo-600 hover:bg-indigo-700 text-white text-xs font-bold rounded-lg"
                >
                  Update Vehicle
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
}
