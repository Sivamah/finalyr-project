import { useState } from 'react';
import { UtensilsCrossed, Store, FileText, Loader2, CheckCircle2 } from 'lucide-react';
import LocationPicker from '../../components/maps/LocationPicker';
import RoutePreview from '../../components/maps/RoutePreview';
import { createFoodBooking } from '../../services/bookingService';
import { validateCoimbatore } from '../../utils/coimbatore';
import toast from 'react-hot-toast';

export default function BookFood({ onSuccess }) {
  const [restaurantName,  setRestaurantName]  = useState('');
  const [restaurantAddr,  setRestaurantAddr]  = useState(null);
  const [deliveryAddr,    setDeliveryAddr]    = useState(null);
  const [orderDesc,       setOrderDesc]       = useState('');
  const [instructions,    setInstructions]    = useState('');
  const [routeInfo,       setRouteInfo]       = useState(null);
  const [loading,         setLoading]         = useState(false);
  const [success,         setSuccess]         = useState(false);

  // Form validation
  const errors = {};
  if (restaurantName.trim().length < 2) errors.restaurantName = 'Restaurant name is required';
  if (!restaurantAddr)                   errors.restaurantAddr = 'Pick restaurant location on map';
  if (!deliveryAddr)                     errors.deliveryAddr   = 'Pick delivery location on map';
  if (orderDesc.trim().length < 5)       errors.orderDesc      = 'Please describe your order (min. 5 chars)';

  const handleSubmit = async (e) => {
    e.preventDefault();
    if (Object.keys(errors).length > 0) {
      toast.error(Object.values(errors)[0]);
      return;
    }
    try {
      validateCoimbatore(restaurantAddr.lat, restaurantAddr.lng, 'Restaurant location');
      validateCoimbatore(deliveryAddr.lat, deliveryAddr.lng, 'Delivery location');
    } catch (err) { toast.error(err.message); return; }
    setLoading(true);
    try {
      await createFoodBooking({
        restaurant_name:      restaurantName.trim(),
        restaurant_address:   restaurantAddr.address,
        restaurant_lat:       restaurantAddr.lat,
        restaurant_lng:       restaurantAddr.lng,
        delivery_address:     deliveryAddr.address,
        delivery_lat:         deliveryAddr.lat,
        delivery_lng:         deliveryAddr.lng,
        order_description:    orderDesc.trim(),
        special_instructions: instructions.trim() || null,
        distance_km:          routeInfo ? parseFloat(routeInfo.distanceKm) : null,
        estimated_fare:       routeInfo ? routeInfo.fare : null,
      });
      toast.success('🍔 Food delivery booked! Driver will pick up soon.');
      setSuccess(true);
      setTimeout(() => { setSuccess(false); onSuccess?.(); }, 2000);
      setRestaurantName(''); setRestaurantAddr(null); setDeliveryAddr(null);
      setOrderDesc(''); setInstructions(''); setRouteInfo(null);
    } catch (err) {
      toast.error(err.response?.data?.detail || 'Failed to book food delivery');
    }
    setLoading(false);
  };

  return (
    <form onSubmit={handleSubmit} className="space-y-6">
      {success && (
        <div className="flex items-center gap-3 bg-emerald-50 border border-emerald-200 rounded-xl px-4 py-3">
          <CheckCircle2 className="h-5 w-5 text-emerald-600" />
          <p className="text-emerald-700 font-medium">Food delivery booked successfully!</p>
        </div>
      )}

      {/* Restaurant Name */}
      <div>
        <label className="block text-sm font-semibold text-gray-700 mb-1.5">
          <Store className="inline h-4 w-4 mr-1 text-orange-500" />
          Restaurant Name
        </label>
        <input
          type="text"
          value={restaurantName}
          onChange={(e) => setRestaurantName(e.target.value)}
          placeholder="e.g. McDonald's, Pizza Hut, Biryani House…"
          className="w-full px-4 py-3 border border-gray-200 rounded-xl text-sm text-gray-800
            placeholder-gray-400 focus:outline-none focus:border-orange-400 focus:ring-2 focus:ring-orange-100"
        />
        {errors.restaurantName && <p className="text-xs text-red-500 mt-1">{errors.restaurantName}</p>}
      </div>

      {/* Restaurant Location */}
      <LocationPicker
        label="Restaurant / Pickup Location"
        color="green"
        value={restaurantAddr}
        onChange={setRestaurantAddr}
      />

      {/* Delivery Location */}
      <LocationPicker
        label="Delivery Address"
        color="red"
        value={deliveryAddr}
        onChange={setDeliveryAddr}
      />

      {/* Route preview */}
      {restaurantAddr && deliveryAddr && (
        <RoutePreview pickup={restaurantAddr} drop={deliveryAddr} onRouteData={setRouteInfo} />
      )}

      {/* Order Description */}
      <div>
        <label className="block text-sm font-semibold text-gray-700 mb-1.5">
          <UtensilsCrossed className="inline h-4 w-4 mr-1 text-orange-500" />
          Order Description
        </label>
        <textarea
          value={orderDesc}
          onChange={(e) => setOrderDesc(e.target.value)}
          placeholder="e.g. 2x Chicken Burger, 1x Large Fries, 2x Coke…"
          rows={3}
          className="w-full px-4 py-3 border border-gray-200 rounded-xl text-sm text-gray-800
            placeholder-gray-400 focus:outline-none focus:border-orange-400 focus:ring-2 focus:ring-orange-100 resize-none"
        />
        {errors.orderDesc && <p className="text-xs text-red-500 mt-1">{errors.orderDesc}</p>}
      </div>

      {/* Special Instructions */}
      <div>
        <label className="block text-sm font-semibold text-gray-700 mb-1.5">
          <FileText className="inline h-4 w-4 mr-1 text-gray-400" />
          Special Instructions (optional)
        </label>
        <textarea
          value={instructions}
          onChange={(e) => setInstructions(e.target.value)}
          placeholder="Leave at door, no onions, call upon arrival…"
          rows={2}
          className="w-full px-4 py-3 border border-gray-200 rounded-xl text-sm text-gray-800
            placeholder-gray-400 focus:outline-none focus:border-orange-400 focus:ring-2 focus:ring-orange-100 resize-none"
        />
      </div>

      {/* Submit */}
      <button
        type="submit"
        disabled={loading}
        className="w-full flex items-center justify-center gap-2 py-3.5 px-6 rounded-xl
          bg-gradient-to-r from-orange-500 to-red-500 text-white font-semibold text-sm
          hover:from-orange-600 hover:to-red-600 transition-all shadow-md
          disabled:opacity-50 disabled:cursor-not-allowed"
      >
        {loading ? (
          <><Loader2 className="h-4 w-4 animate-spin" /> Placing Order…</>
        ) : (
          <><UtensilsCrossed className="h-4 w-4" /> Book Food Delivery</>
        )}
      </button>
    </form>
  );
}
