import { useState, useEffect, useCallback } from 'react';
import { History, RefreshCw, Loader2, MapPin } from 'lucide-react';
import schedulerService from '../../services/schedulerService';
import toast from 'react-hot-toast';

export default function DriverAllocationTab() {
  const [history, setHistory] = useState([]);
  const [loading, setLoading] = useState(false);
  const [drivers, setDrivers] = useState([]);

  const loadData = useCallback(async () => {
    setLoading(true);
    try {
      const [histRes, drvRes] = await Promise.all([
        schedulerService.getAssignmentHistory(),
        schedulerService.getAvailableDrivers()
      ]);
      setHistory(histRes);
      setDrivers(drvRes);
    } catch (err) {
      toast.error('Failed to load allocation data');
    }
    setLoading(false);
  }, []);

  useEffect(() => {
    loadData();
  }, [loadData]);

  return (
    <div className="space-y-6">
      <div className="flex justify-between items-center">
        <h2 className="text-lg font-semibold text-gray-800">Driver Allocation & Availability</h2>
        <button
          onClick={loadData}
          className="text-sm text-indigo-600 flex items-center gap-1 hover:text-indigo-800"
        >
          <RefreshCw className={`h-4 w-4 ${loading ? 'animate-spin' : ''}`} /> Refresh
        </button>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        {/* Available Drivers List */}
        <div className="bg-white rounded-xl border border-gray-100 shadow-sm p-5">
          <div className="flex items-center gap-2 mb-4">
            <MapPin className="h-5 w-5 text-indigo-500" />
            <h3 className="font-semibold text-gray-800">Available Drivers Online</h3>
          </div>
          {loading ? (
            <div className="flex justify-center py-6">
              <Loader2 className="h-6 w-6 animate-spin text-indigo-500" />
            </div>
          ) : drivers.length === 0 ? (
            <p className="text-sm text-gray-400 py-6 text-center">No drivers currently available.</p>
          ) : (
            <ul className="space-y-3">
              {drivers.map(drv => (
                <li key={drv.id} className="flex justify-between items-center p-3 bg-gray-50 rounded-lg">
                  <div>
                    <p className="text-sm font-medium text-gray-900">Driver #{drv.driver_id}</p>
                    <p className="text-xs text-gray-500">
                      Lat: {drv.lat.toFixed(4)}, Lng: {drv.lng.toFixed(4)}
                    </p>
                  </div>
                  <span className="px-2 py-1 bg-emerald-100 text-emerald-700 text-xs font-semibold rounded-full">
                    Online
                  </span>
                </li>
              ))}
            </ul>
          )}
        </div>

        {/* Assignment History */}
        <div className="bg-white rounded-xl border border-gray-100 shadow-sm p-5 overflow-hidden flex flex-col">
          <div className="flex items-center gap-2 mb-4">
            <History className="h-5 w-5 text-indigo-500" />
            <h3 className="font-semibold text-gray-800">Allocation History</h3>
          </div>
          <div className="overflow-y-auto max-h-[400px]">
            {loading ? (
              <div className="flex justify-center py-6">
                <Loader2 className="h-6 w-6 animate-spin text-indigo-500" />
              </div>
            ) : history.length === 0 ? (
              <p className="text-sm text-gray-400 py-6 text-center">No assignment history found.</p>
            ) : (
              <div className="space-y-3 pr-2">
                {history.map(item => (
                  <div key={item.id} className="p-3 border border-gray-100 rounded-lg">
                    <div className="flex justify-between items-start mb-1">
                      <p className="text-sm font-medium text-gray-900">
                        Trip #{item.trip_id} → Driver #{item.driver_id}
                      </p>
                      <span className={`text-xs font-semibold px-2 py-0.5 rounded-full ${
                        item.status === 'Accepted' ? 'bg-emerald-100 text-emerald-700' :
                        item.status === 'Offered' ? 'bg-blue-100 text-blue-700' :
                        'bg-red-100 text-red-700'
                      }`}>
                        {item.status}
                      </span>
                    </div>
                    <p className="text-xs text-gray-600 mb-2">{item.reason}</p>
                    <p className="text-[10px] text-gray-400 text-right">
                      {new Date(item.created_at).toLocaleString('en-IN')}
                    </p>
                  </div>
                ))}
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
