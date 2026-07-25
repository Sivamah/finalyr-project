import { useState } from 'react';
import { Car, Bike, Navigation2, FileText, Loader2, CheckCircle2 } from 'lucide-react';
import LocationPicker from '../../components/maps/LocationPicker';
import RoutePreview from '../../components/maps/RoutePreview';
import { createRideBooking } from '../../services/bookingService';
import { validateCoimbatore } from '../../utils/coimbatore';
import toast from 'react-hot-toast';

const VEHICLE_TYPES = [
  { id: 'Bike',  label: 'Bike',  icon: Bike,        desc: '2-wheeler, fastest',    fare: '₹12/km' },
  { id: 'Auto',  label: 'Auto',  icon: Navigation2, desc: '3-wheeler, comfortable', fare: '₹15/km' },
  { id: 'Car',   label: 'Car',   icon: Car,         desc: '4-wheeler, AC cabin',    fare: '₹20/km' },
];

export default function BookRide({ onSuccess }) {
  const [pickup,   setPickup]      = useState(null);
  const [drop,     setDrop]        = useState(null);
  const [vehicle,  setVehicle]     = useState('Bike');
  const [notes,    setNotes]       = useState('');
  const [routeInfo, setRouteInfo]  = useState(null);
  const [loading,  setLoading]     = useState(false);
  const [success,  setSuccess]     = useState(false);

  const handleSubmit = async (e) => {
    e.preventDefault();
    if (!pickup) { toast.error('Please set a pickup location'); return; }
    if (!drop)   { toast.error('Please set a drop location');   return; }

    try {
      validateCoimbatore(pickup.lat, pickup.lng, 'Pickup location');
      validateCoimbatore(drop.lat, drop.lng, 'Drop location');
    } catch (err) { toast.error(err.message); return; }
    setLoading(true);
    try {
      await createRideBooking({
        pickup_address:  pickup.address,
        pickup_lat:      pickup.lat,
        pickup_lng:      pickup.lng,
        drop_address:    drop.address,
        drop_lat:        drop.lat,
        drop_lng:        drop.lng,
        vehicle_type:    vehicle,
        distance_km:     routeInfo ? parseFloat(routeInfo.distanceKm) : null,
        estimated_fare:  routeInfo ? routeInfo.fare : null,
        notes:           notes || null,
      });
      toast.success('🚗 Ride booked! Waiting for a driver…');
      setSuccess(true);
      setTimeout(() => { setSuccess(false); onSuccess?.(); }, 2000);
      setPickup(null); setDrop(null); setNotes(''); setRouteInfo(null);
    } catch (err) {
      toast.error(err.response?.data?.detail || 'Failed to book ride');
    }
    setLoading(false);
  };

  return (
    <form onSubmit={handleSubmit} className="space-y-6">
      {success && (
        <div className="flex items-center gap-3 bg-emerald-50 border border-emerald-200 rounded-xl px-4 py-3">
          <CheckCircle2 className="h-5 w-5 text-emerald-600" />
          <p className="text-emerald-700 font-medium">Ride booked successfully!</p>
        </div>
      )}

      {/* Vehicle type selector */}
      <div>
        <label className="block text-sm font-semibold text-gray-700 mb-3">Vehicle Type</label>
        <div className="grid grid-cols-3 gap-3">
          {VEHICLE_TYPES.map((v) => {
            const VIcon = v.icon;
            return (
              <button
                key={v.id}
                type="button"
                onClick={() => setVehicle(v.id)}
                className={`flex flex-col items-center gap-2 p-4 rounded-xl border-2 transition-all
                  ${vehicle === v.id
                    ? 'border-violet-500 bg-violet-50 shadow-sm'
                    : 'border-gray-100 bg-white hover:border-violet-200'
                  }`}
              >
                <VIcon className={`h-6 w-6 ${vehicle === v.id ? 'text-violet-600' : 'text-gray-400'}`} />
                <span className={`text-sm font-semibold ${vehicle === v.id ? 'text-violet-700' : 'text-gray-600'}`}>
                  {v.label}
                </span>
                <span className="text-xs text-gray-400">{v.fare}</span>
              </button>
            );
          })}
        </div>
      </div>

      {/* Location pickers */}
      <LocationPicker
        label="Pickup Location"
        color="green"
        value={pickup}
        onChange={setPickup}
      />
      <LocationPicker
        label="Drop Location"
        color="red"
        value={drop}
        onChange={setDrop}
      />

      {/* Route preview */}
      {pickup && drop && (
        <RoutePreview pickup={pickup} drop={drop} onRouteData={setRouteInfo} />
      )}

      {/* Notes */}
      <div>
        <label className="block text-sm font-semibold text-gray-700 mb-1.5">
          <FileText className="inline h-4 w-4 mr-1 text-gray-400" />
          Notes (optional)
        </label>
        <textarea
          value={notes}
          onChange={(e) => setNotes(e.target.value)}
          placeholder="Any special instructions for the driver…"
          rows={2}
          className="w-full px-4 py-3 border border-gray-200 rounded-xl text-sm text-gray-800
            placeholder-gray-400 focus:outline-none focus:border-violet-400 focus:ring-2 focus:ring-violet-100 resize-none"
        />
      </div>

      {/* Submit */}
      <button
        type="submit"
        disabled={loading || !pickup || !drop}
        className="w-full flex items-center justify-center gap-2 py-3.5 px-6 rounded-xl
          bg-gradient-to-r from-violet-600 to-purple-600 text-white font-semibold text-sm
          hover:from-violet-700 hover:to-purple-700 transition-all shadow-md
          disabled:opacity-50 disabled:cursor-not-allowed"
      >
        {loading ? (
          <><Loader2 className="h-4 w-4 animate-spin" /> Booking…</>
        ) : (
          <><Car className="h-4 w-4" /> Book Ride</>
        )}
      </button>
    </form>
  );
}
