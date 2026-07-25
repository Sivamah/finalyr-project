import { useState } from 'react';
import { Package, Weight, User, Phone, AlertTriangle, FileText, Loader2, CheckCircle2 } from 'lucide-react';
import LocationPicker from '../../components/maps/LocationPicker';
import RoutePreview from '../../components/maps/RoutePreview';
import { createParcelBooking } from '../../services/bookingService';
import { validateCoimbatore } from '../../utils/coimbatore';
import toast from 'react-hot-toast';

const PARCEL_SIZES = [
  { id: 'Small',  label: 'Small',  desc: 'Up to 5 kg',   emoji: '📦' },
  { id: 'Medium', label: 'Medium', desc: '5 – 20 kg',     emoji: '🗃️' },
  { id: 'Large',  label: 'Large',  desc: 'Above 20 kg',   emoji: '📫' },
];

export default function BookParcel({ onSuccess }) {
  const [senderName,    setSenderName]    = useState('');
  const [senderPhone,   setSenderPhone]   = useState('');
  const [pickupAddr,    setPickupAddr]    = useState(null);
  const [recipientName, setRecipientName] = useState('');
  const [recipientPhone,setRecipientPhone]= useState('');
  const [dropAddr,      setDropAddr]      = useState(null);
  const [parcelSize,    setParcelSize]    = useState('Small');
  const [weight,        setWeight]        = useState('');
  const [description,   setDescription]  = useState('');
  const [isFragile,     setIsFragile]     = useState(false);
  const [routeInfo,     setRouteInfo]     = useState(null);
  const [loading,       setLoading]       = useState(false);
  const [success,       setSuccess]       = useState(false);

  const handleSubmit = async (e) => {
    e.preventDefault();
    if (!senderName.trim())    { toast.error('Sender name is required');     return; }
    if (!senderPhone.trim())   { toast.error('Sender phone is required');    return; }
    if (!pickupAddr)           { toast.error('Set pickup location on map');  return; }
    if (!recipientName.trim()) { toast.error('Recipient name is required');  return; }
    if (!recipientPhone.trim()){ toast.error('Recipient phone is required'); return; }
    if (!dropAddr)             { toast.error('Set drop location on map');    return; }

    try {
      validateCoimbatore(pickupAddr.lat, pickupAddr.lng, 'Pickup location');
      validateCoimbatore(dropAddr.lat, dropAddr.lng, 'Drop location');
    } catch (err) { toast.error(err.message); return; }
    setLoading(true);
    try {
      await createParcelBooking({
        sender_name:      senderName.trim(),
        sender_phone:     senderPhone.trim(),
        pickup_address:   pickupAddr.address,
        pickup_lat:       pickupAddr.lat,
        pickup_lng:       pickupAddr.lng,
        recipient_name:   recipientName.trim(),
        recipient_phone:  recipientPhone.trim(),
        drop_address:     dropAddr.address,
        drop_lat:         dropAddr.lat,
        drop_lng:         dropAddr.lng,
        parcel_size:      parcelSize,
        weight_kg:        weight ? parseFloat(weight) : null,
        description:      description.trim() || null,
        is_fragile:       isFragile,
        distance_km:      routeInfo ? parseFloat(routeInfo.distanceKm) : null,
        estimated_fare:   routeInfo ? routeInfo.fare : null,
      });
      toast.success('📦 Parcel delivery booked!');
      setSuccess(true);
      setTimeout(() => { setSuccess(false); onSuccess?.(); }, 2000);
      setSenderName(''); setSenderPhone(''); setPickupAddr(null);
      setRecipientName(''); setRecipientPhone(''); setDropAddr(null);
      setParcelSize('Small'); setWeight(''); setDescription(''); setIsFragile(false); setRouteInfo(null);
    } catch (err) {
      toast.error(err.response?.data?.detail || 'Failed to book parcel delivery');
    }
    setLoading(false);
  };

  const inputCls = "w-full px-4 py-3 border border-gray-200 rounded-xl text-sm text-gray-800 placeholder-gray-400 focus:outline-none focus:border-sky-400 focus:ring-2 focus:ring-sky-100";

  return (
    <form onSubmit={handleSubmit} className="space-y-6">
      {success && (
        <div className="flex items-center gap-3 bg-emerald-50 border border-emerald-200 rounded-xl px-4 py-3">
          <CheckCircle2 className="h-5 w-5 text-emerald-600" />
          <p className="text-emerald-700 font-medium">Parcel booked successfully!</p>
        </div>
      )}

      {/* Parcel Size */}
      <div>
        <label className="block text-sm font-semibold text-gray-700 mb-3">
          <Package className="inline h-4 w-4 mr-1 text-sky-600" /> Parcel Size
        </label>
        <div className="grid grid-cols-3 gap-3">
          {PARCEL_SIZES.map((s) => (
            <button
              key={s.id}
              type="button"
              onClick={() => setParcelSize(s.id)}
              className={`flex flex-col items-center gap-1.5 p-4 rounded-xl border-2 transition-all
                ${parcelSize === s.id
                  ? 'border-sky-500 bg-sky-50 shadow-sm'
                  : 'border-gray-100 bg-white hover:border-sky-200'
                }`}
            >
              <span className="text-2xl">{s.emoji}</span>
              <span className={`text-sm font-semibold ${parcelSize === s.id ? 'text-sky-700' : 'text-gray-600'}`}>{s.label}</span>
              <span className="text-xs text-gray-400">{s.desc}</span>
            </button>
          ))}
        </div>
      </div>

      {/* Sender details */}
      <div className="bg-gray-50 rounded-xl p-4 space-y-3">
        <h3 className="text-sm font-bold text-gray-700 flex items-center gap-1.5">
          <User className="h-4 w-4 text-sky-600" /> Sender Details
        </h3>
        <div className="grid grid-cols-2 gap-3">
          <div>
            <label className="block text-xs font-medium text-gray-500 mb-1">Full Name</label>
            <input type="text" value={senderName} onChange={(e) => setSenderName(e.target.value)}
              placeholder="Sender name" className={inputCls} />
          </div>
          <div>
            <label className="block text-xs font-medium text-gray-500 mb-1">Phone</label>
            <input type="tel" value={senderPhone} onChange={(e) => setSenderPhone(e.target.value)}
              placeholder="+91 98765 43210" className={inputCls} />
          </div>
        </div>
      </div>

      <LocationPicker label="Pickup Location" color="green" value={pickupAddr} onChange={setPickupAddr} />

      {/* Recipient details */}
      <div className="bg-gray-50 rounded-xl p-4 space-y-3">
        <h3 className="text-sm font-bold text-gray-700 flex items-center gap-1.5">
          <User className="h-4 w-4 text-sky-600" /> Recipient Details
        </h3>
        <div className="grid grid-cols-2 gap-3">
          <div>
            <label className="block text-xs font-medium text-gray-500 mb-1">Full Name</label>
            <input type="text" value={recipientName} onChange={(e) => setRecipientName(e.target.value)}
              placeholder="Recipient name" className={inputCls} />
          </div>
          <div>
            <label className="block text-xs font-medium text-gray-500 mb-1">Phone</label>
            <input type="tel" value={recipientPhone} onChange={(e) => setRecipientPhone(e.target.value)}
              placeholder="+91 98765 43210" className={inputCls} />
          </div>
        </div>
      </div>

      <LocationPicker label="Drop / Delivery Location" color="red" value={dropAddr} onChange={setDropAddr} />

      {pickupAddr && dropAddr && (
        <RoutePreview pickup={pickupAddr} drop={dropAddr} onRouteData={setRouteInfo} />
      )}

      {/* Weight & description */}
      <div className="grid grid-cols-2 gap-4">
        <div>
          <label className="block text-sm font-semibold text-gray-700 mb-1.5">
            <Weight className="inline h-4 w-4 mr-1 text-gray-400" /> Weight (kg, optional)
          </label>
          <input type="number" value={weight} onChange={(e) => setWeight(e.target.value)}
            placeholder="e.g. 2.5" step="0.1" min="0" className={inputCls} />
        </div>
        <div>
          <label className="block text-sm font-semibold text-gray-700 mb-1.5">
            <FileText className="inline h-4 w-4 mr-1 text-gray-400" /> Description (optional)
          </label>
          <input type="text" value={description} onChange={(e) => setDescription(e.target.value)}
            placeholder="e.g. Books, Electronics…" className={inputCls} />
        </div>
      </div>

      {/* Fragile toggle */}
      <label className="flex items-center gap-3 cursor-pointer select-none">
        <div
          onClick={() => setIsFragile(!isFragile)}
          className={`relative w-12 h-6 rounded-full transition-colors duration-200 ${isFragile ? 'bg-amber-500' : 'bg-gray-200'}`}
        >
          <span className={`absolute top-1 left-1 w-4 h-4 bg-white rounded-full shadow transition-transform duration-200 ${isFragile ? 'translate-x-6' : ''}`} />
        </div>
        <span className="flex items-center gap-1.5 text-sm font-medium text-gray-700">
          <AlertTriangle className={`h-4 w-4 ${isFragile ? 'text-amber-500' : 'text-gray-400'}`} />
          Fragile / Handle with Care
        </span>
      </label>

      {/* Submit */}
      <button
        type="submit"
        disabled={loading}
        className="w-full flex items-center justify-center gap-2 py-3.5 px-6 rounded-xl
          bg-gradient-to-r from-sky-500 to-blue-600 text-white font-semibold text-sm
          hover:from-sky-600 hover:to-blue-700 transition-all shadow-md
          disabled:opacity-50 disabled:cursor-not-allowed"
      >
        {loading ? (
          <><Loader2 className="h-4 w-4 animate-spin" /> Booking…</>
        ) : (
          <><Package className="h-4 w-4" /> Book Parcel Delivery</>
        )}
      </button>
    </form>
  );
}
