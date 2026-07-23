import { useState, useEffect, useCallback } from 'react';
import { RefreshCw, Car, UtensilsCrossed, Package, Filter, Loader2, Navigation } from 'lucide-react';
import BookingCard from '../../components/bookings/BookingCard';
import LiveTracking from './LiveTracking';
import {
  getBookingHistory,
  cancelRideBooking,
  cancelFoodBooking,
  cancelParcelBooking,
} from '../../services/bookingService';
import toast from 'react-hot-toast';

const TABS = [
  { id: 'All',    label: 'All',    icon: null },
  { id: 'ride',   label: 'Rides',  icon: Car },
  { id: 'food',   label: 'Food',   icon: UtensilsCrossed },
  { id: 'parcel', label: 'Parcel', icon: Package },
];

const STATUS_FILTERS = ['All', 'Pending', 'Accepted', 'In_Progress', 'Completed', 'Cancelled'];

const CANCEL_FNS = {
  ride:   cancelRideBooking,
  food:   cancelFoodBooking,
  parcel: cancelParcelBooking,
};

export default function BookingHistory() {
  const [bookings,      setBookings]      = useState([]);
  const [activeTab,     setActiveTab]     = useState('All');
  const [statusFilter,  setStatusFilter]  = useState('All');
  const [loading,       setLoading]       = useState(false);
  const [cancelling,    setCancelling]    = useState(null);

  const fetchHistory = useCallback(async () => {
    setLoading(true);
    try {
      const res = await getBookingHistory({ limit: 100 });
      setBookings(res.data);
    } catch {
      toast.error('Failed to load booking history');
    }
    setLoading(false);
  }, []);

  useEffect(() => { fetchHistory(); }, [fetchHistory]);

  const handleCancel = async (booking) => {
    if (!window.confirm('Cancel this booking?')) return;
    setCancelling(`${booking.type}-${booking.id}`);
    try {
      await CANCEL_FNS[booking.type](booking.id);
      toast.success('Booking cancelled');
      fetchHistory();
    } catch (err) {
      toast.error(err.response?.data?.detail || 'Cannot cancel this booking');
    }
    setCancelling(null);
  };

  // Filter
  const filtered = bookings.filter((b) => {
    const typeMatch   = activeTab === 'All' || b.type === activeTab;
    const statusMatch = statusFilter === 'All' || b.status === statusFilter;
    return typeMatch && statusMatch;
  });

  return (
    <div className="space-y-5">
      {/* Header */}
      <div className="flex items-center justify-between">
        <h3 className="text-lg font-bold text-gray-900">Booking History</h3>
        <button
          onClick={fetchHistory}
          disabled={loading}
          className="flex items-center gap-1.5 text-sm text-violet-600 hover:text-violet-800 font-medium"
        >
          <RefreshCw className={`h-4 w-4 ${loading ? 'animate-spin' : ''}`} />
          Refresh
        </button>
      </div>

      {/* Type tabs */}
      <div className="flex gap-2 flex-wrap">
        {TABS.map((tab) => {
          const TIcon = tab.icon;
          return (
            <button
              key={tab.id}
              onClick={() => setActiveTab(tab.id)}
              className={`flex items-center gap-1.5 px-4 py-2 rounded-full text-sm font-medium transition-all
                ${activeTab === tab.id
                  ? 'bg-violet-600 text-white shadow-sm'
                  : 'bg-white text-gray-600 border border-gray-200 hover:border-violet-300'
                }`}
            >
              {TIcon && <TIcon className="h-3.5 w-3.5" />}
              {tab.label}
            </button>
          );
        })}
      </div>

      {/* Status filter */}
      <div className="flex items-center gap-2 flex-wrap">
        <Filter className="h-4 w-4 text-gray-400" />
        {STATUS_FILTERS.map((s) => (
          <button
            key={s}
            onClick={() => setStatusFilter(s)}
            className={`px-3 py-1 rounded-full text-xs font-medium border transition-all
              ${statusFilter === s
                ? 'bg-gray-800 text-white border-gray-800'
                : 'bg-white text-gray-500 border-gray-200 hover:border-gray-400'
              }`}
          >
            {s.replace('_', ' ')}
          </button>
        ))}
      </div>

      {/* Bookings grid */}
      {loading ? (
        <div className="flex items-center justify-center py-16">
          <Loader2 className="h-8 w-8 animate-spin text-violet-500" />
        </div>
      ) : filtered.length === 0 ? (
        <div className="text-center py-16">
          <Package className="h-12 w-12 text-gray-300 mx-auto mb-3" />
          <p className="text-gray-500 font-medium">No bookings found</p>
          <p className="text-gray-400 text-sm">Your booking history will appear here</p>
        </div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          {filtered.map((booking) => (
            <div key={`${booking.type}-${booking.id}`} className={cancelling === `${booking.type}-${booking.id}` ? 'opacity-50 pointer-events-none' : ''}>
              <BookingCard
                booking={booking}
                onCancel={handleCancel}
                showCancel={true}
              />
              
              {/* Live Tracking for Active Bookings */}
              {booking.trip_id && ['Accepted', 'In_Progress'].includes(booking.status) && (
                <div className="mt-4">
                  <LiveTracking 
                    tripId={booking.trip_id}
                    status={booking.status}
                    pickup={{ lat: booking.pickup_lat, lng: booking.pickup_lng, address: booking.pickup_address }}
                    drop={{ lat: booking.drop_lat, lng: booking.drop_lng, address: booking.drop_address }}
                  />
                </div>
              )}
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
