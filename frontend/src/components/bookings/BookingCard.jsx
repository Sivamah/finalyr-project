import { Car, UtensilsCrossed, Package, MapPin, IndianRupee, Clock, X } from 'lucide-react';
import StatusBadge from './StatusBadge';

const TYPE_CONFIG = {
  ride:   { icon: Car,              label: 'Ride',          color: 'text-violet-600', bg: 'bg-violet-50' },
  food:   { icon: UtensilsCrossed,  label: 'Food Delivery', color: 'text-orange-600', bg: 'bg-orange-50' },
  parcel: { icon: Package,          label: 'Parcel',        color: 'text-sky-600',    bg: 'bg-sky-50' },
};

export default function BookingCard({ booking, onCancel, showCancel = true }) {
  const cfg = TYPE_CONFIG[booking.type] || TYPE_CONFIG.ride;
  const Icon = cfg.icon;

  const canCancel = showCancel && ['Pending', 'Accepted'].includes(booking.status);
  const pickupAddress  = booking.pickup_address  || booking.from || '—';
  const dropAddress    = booking.drop_address    || booking.to   || '—';

  const formattedDate = booking.created_at
    ? new Date(booking.created_at).toLocaleString('en-IN', {
        day: '2-digit', month: 'short', year: 'numeric',
        hour: '2-digit', minute: '2-digit',
      })
    : '—';

  return (
    <div className="bg-white rounded-xl border border-gray-100 shadow-sm hover:shadow-md transition-shadow p-5">
      {/* Header */}
      <div className="flex items-start justify-between mb-4">
        <div className="flex items-center gap-3">
          <div className={`p-2.5 rounded-xl ${cfg.bg}`}>
            <Icon className={`h-5 w-5 ${cfg.color}`} />
          </div>
          <div>
            <p className={`text-xs font-semibold uppercase tracking-wide ${cfg.color}`}>
              {cfg.label}
            </p>
            <p className="text-sm text-gray-400">#{booking.id}</p>
          </div>
        </div>
        <StatusBadge status={booking.status} />
      </div>

      {/* Route */}
      <div className="space-y-2 mb-4">
        <div className="flex items-start gap-2">
          <MapPin className="h-4 w-4 text-emerald-500 mt-0.5 shrink-0" />
          <p className="text-sm text-gray-700 line-clamp-1">{pickupAddress}</p>
        </div>
        <div className="flex items-start gap-2">
          <MapPin className="h-4 w-4 text-red-500 mt-0.5 shrink-0" />
          <p className="text-sm text-gray-700 line-clamp-1">{dropAddress}</p>
        </div>
      </div>

      {/* Extra info */}
      {booking.restaurant_name && (
        <p className="text-xs text-gray-500 mb-3">
          🍽️ <span className="font-medium">{booking.restaurant_name}</span>
        </p>
      )}
      {booking.recipient_name && (
        <p className="text-xs text-gray-500 mb-3">
          📦 To: <span className="font-medium">{booking.recipient_name}</span>
          {booking.parcel_size && ` (${booking.parcel_size})`}
        </p>
      )}

      {/* Footer */}
      <div className="flex items-center justify-between pt-3 border-t border-gray-50">
        <div className="flex items-center gap-3">
          {booking.estimated_fare && (
            <span className="flex items-center text-sm font-semibold text-gray-800">
              <IndianRupee className="h-3.5 w-3.5 mr-0.5" />
              {booking.estimated_fare.toFixed(0)}
            </span>
          )}
          <span className="flex items-center text-xs text-gray-400 gap-1">
            <Clock className="h-3 w-3" /> {formattedDate}
          </span>
        </div>
        {canCancel && (
          <button
            onClick={() => onCancel?.(booking)}
            className="flex items-center gap-1 text-xs text-red-500 hover:text-red-700 font-medium transition-colors"
          >
            <X className="h-3.5 w-3.5" /> Cancel
          </button>
        )}
      </div>
    </div>
  );
}
