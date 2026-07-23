import { useState, useEffect, useCallback } from 'react';
import { Calendar, RefreshCw, Loader2, Play, Info, X } from 'lucide-react';
import schedulerService from '../../services/schedulerService';
import toast from 'react-hot-toast';
import StatusBadge from '../bookings/StatusBadge';
import TripRouteView from '../maps/TripRouteView';

export default function TripSchedulerTab() {
  const [trips, setTrips] = useState([]);
  const [loading, setLoading] = useState(false);
  const [creating, setCreating] = useState(false);
  const [selectedTrip, setSelectedTrip] = useState(null);

  const loadTrips = useCallback(async () => {
    setLoading(true);
    try {
      const data = await schedulerService.getAllTrips();
      setTrips(data);
    } catch (err) {
      toast.error('Failed to load trips');
    }
    setLoading(false);
  }, []);

  useEffect(() => {
    loadTrips();
  }, [loadTrips]);

  const handleCreateTrips = async () => {
    setCreating(true);
    try {
      const res = await schedulerService.createTripsFromBatches();
      toast.success(`${res.message}`);
      loadTrips();
    } catch (err) {
      toast.error(err.response?.data?.detail || 'Failed to create trips');
    }
    setCreating(false);
  };

  const handleAllocate = async (tripId) => {
    try {
      const res = await schedulerService.assignDriver(tripId);
      if (res.assigned) {
        toast.success(`Driver #${res.driver_id} allocated (Score: ${res.score.toFixed(1)})`);
      } else {
        toast.error(res.message);
      }
      loadTrips();
    } catch (err) {
      toast.error(err.response?.data?.detail || 'Failed to allocate driver');
    }
  };

  return (
    <div className="space-y-4">
      <div className="flex justify-between items-center">
        <h2 className="text-lg font-semibold text-gray-800">Scheduled Trips</h2>
        <div className="flex gap-2">
          <button
            onClick={loadTrips}
            className="text-sm text-indigo-600 flex items-center gap-1 hover:text-indigo-800"
          >
            <RefreshCw className={`h-4 w-4 ${loading ? 'animate-spin' : ''}`} /> Refresh
          </button>
          <button
            onClick={handleCreateTrips}
            disabled={creating}
            className="bg-indigo-600 hover:bg-indigo-700 text-white px-4 py-2 rounded-xl text-sm font-semibold transition-colors flex items-center gap-2"
          >
            {creating ? <Loader2 className="h-4 w-4 animate-spin" /> : <Calendar className="h-4 w-4" />}
            Generate Trips from Batches
          </button>
        </div>
      </div>

      <div className="bg-white rounded-xl border border-gray-100 shadow-sm overflow-hidden">
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead className="bg-gray-50 border-b border-gray-100">
              <tr>
                <th className="px-4 py-3 text-left text-xs font-semibold text-gray-500 uppercase">Trip ID</th>
                <th className="px-4 py-3 text-left text-xs font-semibold text-gray-500 uppercase">Batch ID</th>
                <th className="px-4 py-3 text-left text-xs font-semibold text-gray-500 uppercase">Type</th>
                <th className="px-4 py-3 text-left text-xs font-semibold text-gray-500 uppercase">Priority</th>
                <th className="px-4 py-3 text-left text-xs font-semibold text-gray-500 uppercase">Status</th>
                <th className="px-4 py-3 text-left text-xs font-semibold text-gray-500 uppercase">Created At</th>
                <th className="px-4 py-3 text-left text-xs font-semibold text-gray-500 uppercase">Actions</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-50">
              {loading ? (
                <tr>
                  <td colSpan={7} className="text-center py-12">
                    <Loader2 className="h-6 w-6 animate-spin text-indigo-500 mx-auto" />
                  </td>
                </tr>
              ) : trips.length === 0 ? (
                <tr>
                  <td colSpan={7} className="text-center py-12 text-gray-400">No scheduled trips found</td>
                </tr>
              ) : (
                trips.map((trip) => (
                  <tr key={trip.id} className="hover:bg-gray-50 transition-colors">
                    <td className="px-4 py-3 font-medium text-gray-900">#{trip.id}</td>
                    <td className="px-4 py-3 text-gray-600">#{trip.batch_id}</td>
                    <td className="px-4 py-3 text-gray-600">{trip.trip_type}</td>
                    <td className="px-4 py-3">
                      <span className={`px-2 py-1 rounded-full text-xs font-semibold ${trip.priority === 'High' ? 'bg-red-100 text-red-700' : 'bg-blue-100 text-blue-700'}`}>
                        {trip.priority}
                      </span>
                    </td>
                    <td className="px-4 py-3">
                      <StatusBadge status={trip.status} size="sm" />
                    </td>
                    <td className="px-4 py-3 text-gray-400 text-xs">
                      {new Date(trip.created_at).toLocaleString('en-IN')}
                    </td>
                    <td className="px-4 py-3">
                      <div className="flex gap-2">
                        {(trip.status === 'Pending' || trip.status === 'Queued') && (
                          <button
                            onClick={() => handleAllocate(trip.id)}
                            className="bg-emerald-100 text-emerald-700 hover:bg-emerald-200 px-3 py-1 rounded-lg text-xs font-semibold flex items-center gap-1 transition-colors"
                          >
                            <Play className="h-3 w-3" /> Allocate
                          </button>
                        )}
                        <button
                          onClick={() => setSelectedTrip(trip)}
                          className="bg-indigo-50 text-indigo-700 hover:bg-indigo-100 px-3 py-1 rounded-lg text-xs font-semibold flex items-center gap-1 transition-colors"
                        >
                          <Info className="h-3 w-3" /> Details
                        </button>
                      </div>
                    </td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>
      </div>

      {/* Trip Details Modal */}
      {selectedTrip && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 p-4">
          <div className="bg-white rounded-2xl shadow-xl w-full max-w-lg overflow-hidden flex flex-col">
            <div className="flex justify-between items-center p-4 border-b border-gray-100">
              <h3 className="font-bold text-lg text-gray-800">Trip Details #{selectedTrip.id}</h3>
              <button onClick={() => setSelectedTrip(null)} className="text-gray-400 hover:text-gray-600">
                <X className="h-5 w-5" />
              </button>
            </div>
            <div className="p-5 space-y-4">
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <p className="text-xs text-gray-500 uppercase font-semibold">Batch ID</p>
                  <p className="text-sm font-medium text-gray-900">#{selectedTrip.batch_id}</p>
                </div>
                <div>
                  <p className="text-xs text-gray-500 uppercase font-semibold">Type</p>
                  <p className="text-sm font-medium text-gray-900">{selectedTrip.trip_type}</p>
                </div>
                <div>
                  <p className="text-xs text-gray-500 uppercase font-semibold">Status</p>
                  <StatusBadge status={selectedTrip.status} size="sm" />
                </div>
                <div>
                  <p className="text-xs text-gray-500 uppercase font-semibold">Priority</p>
                  <span className={`px-2 py-0.5 rounded-full text-xs font-semibold ${selectedTrip.priority === 'High' ? 'bg-red-100 text-red-700' : 'bg-blue-100 text-blue-700'}`}>
                    {selectedTrip.priority}
                  </span>
                </div>
              </div>
              <div className="pt-4 border-t border-gray-100">
                <TripRouteView tripId={selectedTrip.id} />
              </div>
            </div>
            <div className="p-4 border-t border-gray-100 bg-gray-50 flex justify-end">
              <button onClick={() => setSelectedTrip(null)} className="px-4 py-2 bg-gray-200 text-gray-800 rounded-lg text-sm font-medium hover:bg-gray-300">
                Close
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
