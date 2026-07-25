import { useState, useEffect, useCallback, useContext } from 'react';
import {
  Car, UtensilsCrossed, Package, MapPin, IndianRupee, RefreshCw,
  Loader2, CheckCircle2, ChevronRight, Power, Star, Navigation, Clock, Trophy
} from 'lucide-react';
import { AuthContext } from '../context/AuthContext';
import StatusBadge from '../components/bookings/StatusBadge';
import {
  getDriverProfile, createDriverProfile, updateDriverProfile,
  toggleAvailability, getPendingRequests, getActiveBooking,
  getCompletedBookings, acceptRequest, updateBookingStatus,
} from '../services/driverService';
import { dmfeService } from '../services/dmfeService';
import schedulerService from '../services/schedulerService';
import api from '../services/api';
import { Layers, Map, Check, X, MapPin as MapPinIcon } from 'lucide-react';
import toast from 'react-hot-toast';
import TripRouteView from '../components/maps/TripRouteView';

const TYPE_CONFIG = {
  ride:   { icon: Car,             label: 'Ride',   color: 'text-violet-600', bg: 'bg-violet-50' },
  food:   { icon: UtensilsCrossed, label: 'Food',   color: 'text-orange-600', bg: 'bg-orange-50' },
  parcel: { icon: Package,         label: 'Parcel', color: 'text-sky-600',    bg: 'bg-sky-50'    },
};

const STATUS_SEQUENCE = {
  Accepted:    { nextStatus: 'In_Progress', nextLabel: 'Start Trip', btnColor: 'bg-blue-600 hover:bg-blue-700' },
  In_Progress: { nextStatus: 'Completed',  nextLabel: 'Mark Complete', btnColor: 'bg-emerald-600 hover:bg-emerald-700' },
};

// ─────────────────────────────────────────────
// Profile Setup Modal (shown if no profile)
// ─────────────────────────────────────────────
function ProfileSetup({ onDone }) {
  const [vehicleType,   setVehicleType]   = useState('Bike');
  const [vehicleNumber, setVehicleNumber] = useState('');
  const [vehicleModel,  setVehicleModel]  = useState('');
  const [saving,        setSaving]        = useState(false);

  const handleCreate = async (e) => {
    e.preventDefault();
    if (!vehicleNumber.trim()) { toast.error('Vehicle number is required'); return; }
    setSaving(true);
    try {
      await createDriverProfile({ vehicle_type: vehicleType, vehicle_number: vehicleNumber.trim(), vehicle_model: vehicleModel.trim() || null });
      toast.success('Driver profile created!');
      onDone();
    } catch (err) {
      toast.error(err.response?.data?.detail || 'Failed to create profile');
    }
    setSaving(false);
  };

  return (
    <div className="max-w-md mx-auto mt-10">
      <div className="bg-white rounded-2xl shadow-lg p-8 border border-gray-100">
        <div className="text-center mb-6">
          <div className="w-16 h-16 bg-violet-100 rounded-full flex items-center justify-center mx-auto mb-4">
            <Car className="h-8 w-8 text-violet-600" />
          </div>
          <h2 className="text-xl font-bold text-gray-900">Set Up Driver Profile</h2>
          <p className="text-gray-500 text-sm mt-1">Add your vehicle details to start accepting rides</p>
        </div>
        <form onSubmit={handleCreate} className="space-y-4">
          <div>
            <label className="block text-sm font-semibold text-gray-700 mb-2">Vehicle Type</label>
            <select value={vehicleType} onChange={(e) => setVehicleType(e.target.value)}
              className="w-full px-4 py-3 border border-gray-200 rounded-xl text-sm focus:outline-none focus:border-violet-400">
              {['Bike', 'Auto', 'Car', 'Van', 'Truck'].map((v) => <option key={v}>{v}</option>)}
            </select>
          </div>
          <div>
            <label className="block text-sm font-semibold text-gray-700 mb-2">Vehicle Number</label>
            <input type="text" value={vehicleNumber} onChange={(e) => setVehicleNumber(e.target.value)}
              placeholder="e.g. KA 01 AB 1234"
              className="w-full px-4 py-3 border border-gray-200 rounded-xl text-sm focus:outline-none focus:border-violet-400" />
          </div>
          <div>
            <label className="block text-sm font-semibold text-gray-700 mb-2">Vehicle Model (optional)</label>
            <input type="text" value={vehicleModel} onChange={(e) => setVehicleModel(e.target.value)}
              placeholder="e.g. Honda Activa, Maruti Swift"
              className="w-full px-4 py-3 border border-gray-200 rounded-xl text-sm focus:outline-none focus:border-violet-400" />
          </div>
          <button type="submit" disabled={saving}
            className="w-full py-3 rounded-xl bg-gradient-to-r from-violet-600 to-purple-600 text-white font-semibold text-sm hover:from-violet-700 hover:to-purple-700 flex items-center justify-center gap-2 disabled:opacity-50">
            {saving ? <Loader2 className="h-4 w-4 animate-spin" /> : <CheckCircle2 className="h-4 w-4" />}
            Save Profile
          </button>
        </form>
      </div>
    </div>
  );
}

// ─────────────────────────────────────────────
// Main Driver Dashboard
// ─────────────────────────────────────────────
export default function DriverDashboard() {
  const { user }          = useContext(AuthContext);
  const [profile,         setProfile]         = useState(null);
  const [profileLoading,  setProfileLoading]  = useState(true);
  const [requests,        setRequests]        = useState([]);
  const [batches,         setBatches]         = useState([]);
  const [activeBooking,   setActiveBooking]   = useState(null);
  const [completed,       setCompleted]       = useState([]);
  const [reqLoading,      setReqLoading]      = useState(false);
  const [accepting,       setAccepting]       = useState(null);
  const [updating,        setUpdating]        = useState(false);
  const [activeTab,       setActiveTab]       = useState('requests');
  const [assignments,     setAssignments]     = useState([]);

  const loadProfile = useCallback(async () => {
    try {
      const res = await getDriverProfile();
      setProfile(res.data);
    } catch {
      setProfile(null);
    }
    setProfileLoading(false);
  }, []);

  const loadRequests = useCallback(async () => {
    setReqLoading(true);
    try {
      const [reqRes, activeRes, compRes, batchRes, assignmentRes] = await Promise.all([
        getPendingRequests(),
        getActiveBooking(),
        getCompletedBookings(),
        dmfeService.getBatches(),
        schedulerService.getPendingAssignments()
      ]);
      setRequests(reqRes.data);
      setActiveBooking(activeRes.data);
      setCompleted(compRes.data);
      setBatches(batchRes);
      setAssignments(assignmentRes);
    } catch { toast.error('Failed to load requests'); }
    setReqLoading(false);
  }, []);

  useEffect(() => { loadProfile(); }, [loadProfile]);
  useEffect(() => { if (profile) loadRequests(); }, [profile, loadRequests]);

  // Auto-refresh every 30 sec
  useEffect(() => {
    if (!profile) return;
    const id = setInterval(loadRequests, 30000);
    return () => clearInterval(id);
  }, [profile, loadRequests]);

  const handleToggleAvailability = async () => {
    try {
      const res = await toggleAvailability();
      setProfile((p) => ({ ...p, is_available: res.data.is_available }));
      toast.success(res.data.is_available ? '✅ You are now Online' : '⏸️ You are now Offline');
    } catch { toast.error('Failed to update availability'); }
  };

  const handleAccept = async (req) => {
    if (req.is_batch) {
      setAccepting(`batch-${req.id}`);
      try {
        await dmfeService.acceptBatch(req.id);
        toast.success('✅ Batched Trip accepted!');
        loadRequests();
      } catch (err) {
        toast.error(err.response?.data?.detail || 'Failed to accept batch');
      }
      setAccepting(null);
      return;
    }

    setAccepting(`${req.type}-${req.id}`);
    try {
      await acceptRequest(req.type, req.id);
      toast.success('✅ Booking accepted!');
      loadRequests();
    } catch (err) {
      toast.error(err.response?.data?.detail || 'Failed to accept');
    }
    setAccepting(null);
  };

  const handleAssignmentRespond = async (assignmentId, action) => {
    try {
      await schedulerService.respondToAssignment(assignmentId, action);
      toast.success(`Assignment ${action}ed`);
      loadRequests();
    } catch (err) {
      toast.error(err.response?.data?.detail || `Failed to ${action} assignment`);
    }
  };

  const handleStatusUpdate = async () => {
    if (!activeBooking) return;
    const cfg = STATUS_SEQUENCE[activeBooking.status];
    if (!cfg) return;
    setUpdating(true);
    try {
      if (activeBooking.is_batch) {
        await dmfeService.updateBatchStatus(activeBooking.id, cfg.nextStatus);
      } else {
        await updateBookingStatus(activeBooking.type, activeBooking.id, cfg.nextStatus);
      }
      toast.success(`Status → ${cfg.nextStatus.replace('_', ' ')}`);
      loadRequests();
    } catch (err) {
      toast.error(err.response?.data?.detail || 'Update failed');
    }
    setUpdating(false);
  };

  const handleSimulateDriving = async () => {
    if (!activeBooking) return;
    toast.success('Started simulated driving...');
    // Simulated path
    const mockPath = [
      { lat: 11.0168, lng: 76.9558 },
      { lat: 11.0180, lng: 76.9570 },
      { lat: 11.0190, lng: 76.9585 },
      { lat: 11.0200, lng: 76.9600 },
    ];
    let step = 0;
    const interval = setInterval(async () => {
      if (step >= mockPath.length) {
        clearInterval(interval);
        toast.success('Simulation complete');
        return;
      }
      try {
        await api.post('/tracking/location', {
          lat: mockPath[step].lat,
          lng: mockPath[step].lng,
          trip_id: activeBooking.is_batch ? activeBooking.id : null
        });
      } catch (err) {
        console.error('Failed to post location', err);
      }
      step++;
    }, 2000);
  };

  if (profileLoading) return (
    <div className="flex items-center justify-center py-24">
      <Loader2 className="h-8 w-8 animate-spin text-violet-500" />
    </div>
  );

  if (!profile) return <ProfileSetup onDone={loadProfile} />;

  return (
    <div className="flex-1 w-full space-y-6 max-w-5xl mx-auto">
      {/* Header card */}
      <div className="bg-gradient-to-r from-slate-800 to-slate-900 rounded-2xl p-6 text-white shadow-lg">
        <div className="flex items-center justify-between">
          <div>
            <h1 className="text-xl font-bold">Driver Dashboard</h1>
            <p className="text-slate-400 text-sm mt-0.5">{user?.full_name} · {profile.vehicle_type} · {profile.vehicle_number}</p>
          </div>
          {/* Online/offline toggle */}
          <button
            onClick={handleToggleAvailability}
            className={`flex items-center gap-2 px-4 py-2 rounded-full text-sm font-semibold border-2 transition-all
              ${profile.is_available
                ? 'border-emerald-400 bg-emerald-400/20 text-emerald-300'
                : 'border-slate-600 bg-slate-700 text-slate-400'
              }`}
          >
            <Power className="h-4 w-4" />
            {profile.is_available ? 'Online' : 'Offline'}
          </button>
        </div>

        {/* Stats row */}
        <div className="grid grid-cols-3 gap-4 mt-6">
          <div className="bg-slate-700/50 rounded-xl p-3 text-center">
            <Trophy className="h-5 w-5 text-amber-400 mx-auto mb-1" />
            <p className="text-2xl font-bold">{profile.total_trips}</p>
            <p className="text-slate-400 text-xs">Completed</p>
          </div>
          <div className="bg-slate-700/50 rounded-xl p-3 text-center">
            <Star className="h-5 w-5 text-yellow-400 mx-auto mb-1" />
            <p className="text-2xl font-bold">{profile.rating.toFixed(1)}</p>
            <p className="text-slate-400 text-xs">Rating</p>
          </div>
          <div className="bg-slate-700/50 rounded-xl p-3 text-center">
            <Navigation className="h-5 w-5 text-violet-400 mx-auto mb-1" />
            <p className="text-2xl font-bold">{requests.length}</p>
            <p className="text-slate-400 text-xs">Pending</p>
          </div>
        </div>
      </div>

      {/* Pending Assignments Banner (Phase 4) */}
      {assignments.length > 0 && !activeBooking && (
        <div className="space-y-3">
          {assignments.map(assignment => (
            <div key={assignment.id} className="bg-gradient-to-r from-amber-500 to-orange-500 rounded-2xl p-5 text-white shadow-lg animate-pulse-slow border border-amber-400">
              <div className="flex items-center justify-between mb-3">
                <div className="flex items-center gap-2">
                  <Map className="h-5 w-5 text-amber-100" />
                  <span className="font-bold text-lg">New Trip Offer!</span>
                </div>
                <span className="text-xs bg-amber-900/40 px-2 py-1 rounded-md font-medium">Expires soon</span>
              </div>
              <p className="text-sm text-amber-50 mb-4">You have been allocated Trip #{assignment.trip_id} based on your current location and availability.</p>
              
              <div className="flex gap-3">
                <button
                  onClick={() => handleAssignmentRespond(assignment.id, 'Accept')}
                  className="flex-1 py-2.5 rounded-xl bg-white text-orange-600 font-bold text-sm flex items-center justify-center gap-2 hover:bg-orange-50 transition-colors shadow-sm"
                >
                  <Check className="h-5 w-5" /> Accept
                </button>
                <button
                  onClick={() => handleAssignmentRespond(assignment.id, 'Reject')}
                  className="px-5 py-2.5 rounded-xl bg-orange-600/30 text-white font-semibold text-sm flex items-center justify-center gap-2 hover:bg-orange-600/50 transition-colors border border-orange-400/50"
                >
                  <X className="h-5 w-5" /> Reject
                </button>
              </div>
            </div>
          ))}
        </div>
      )}

      {/* Active booking banner */}
      {activeBooking && (
        <div className="bg-gradient-to-r from-blue-600 to-violet-600 rounded-2xl p-5 text-white shadow-lg">
          <div className="flex items-center justify-between mb-3">
            <div className="flex items-center gap-2">
              <div className="w-2 h-2 bg-white rounded-full animate-pulse" />
              <span className="font-semibold text-sm">Active Booking</span>
            </div>
            <StatusBadge status={activeBooking.status} />
          </div>
          <div className="space-y-1.5 mb-4">
            <div className="flex items-center gap-2 text-sm text-blue-100">
              <MapPin className="h-4 w-4 text-emerald-300" />
              <span className="truncate">{activeBooking.pickup_address}</span>
            </div>
            <div className="flex items-center gap-2 text-sm text-blue-100">
              <MapPin className="h-4 w-4 text-red-300" />
              <span className="truncate">{activeBooking.drop_address}</span>
            </div>
          </div>
          
          {activeBooking.is_batch && (
            <div className="mb-4 bg-white/10 rounded-xl p-2">
               <TripRouteView tripId={activeBooking.id} />
            </div>
          )}

          <div className="flex gap-2">
            {STATUS_SEQUENCE[activeBooking.status] && (
              <button
                onClick={handleStatusUpdate}
                disabled={updating}
                className={`flex-1 py-2.5 rounded-xl text-white font-semibold text-sm flex items-center justify-center gap-2
                  ${STATUS_SEQUENCE[activeBooking.status].btnColor} transition-colors disabled:opacity-50`}
              >
                {updating
                  ? <><Loader2 className="h-4 w-4 animate-spin" /> Updating…</>
                  : <><ChevronRight className="h-4 w-4" /> {STATUS_SEQUENCE[activeBooking.status].nextLabel}</>
                }
              </button>
            )}
            {activeBooking.is_batch && (
              <button
                onClick={handleSimulateDriving}
                className="px-4 py-2.5 rounded-xl bg-slate-800 text-white font-semibold text-sm hover:bg-slate-900 transition-colors"
                title="Simulate driving to test live tracking"
              >
                <MapPinIcon className="h-4 w-4" />
              </button>
            )}
          </div>
        </div>
      )}

      {/* Tabs */}
      <div className="flex gap-2">
        {[
          { id: 'requests',  label: `Requests (${requests.length + batches.length})` },
          { id: 'completed', label: `Completed (${completed.length})` },
        ].map((t) => (
          <button
            key={t.id}
            onClick={() => setActiveTab(t.id)}
            className={`px-5 py-2 rounded-full text-sm font-medium transition-all
              ${activeTab === t.id
                ? 'bg-violet-600 text-white shadow-sm'
                : 'bg-white text-gray-600 border border-gray-200 hover:border-violet-300'
              }`}
          >
            {t.label}
          </button>
        ))}
        <button
          onClick={loadRequests}
          disabled={reqLoading}
          className="ml-auto text-sm text-violet-600 flex items-center gap-1 hover:text-violet-800"
        >
          <RefreshCw className={`h-4 w-4 ${reqLoading ? 'animate-spin' : ''}`} /> Refresh
        </button>
      </div>

      {/* Requests feed */}
      {activeTab === 'requests' && (
        reqLoading ? (
          <div className="flex items-center justify-center py-16">
            <Loader2 className="h-8 w-8 animate-spin text-violet-500" />
          </div>
        ) : requests.length === 0 && batches.length === 0 ? (
          <div className="text-center py-16 bg-white rounded-2xl border border-gray-100">
            <Clock className="h-12 w-12 text-gray-300 mx-auto mb-3" />
            <p className="text-gray-500 font-medium">No pending requests right now</p>
            <p className="text-gray-400 text-sm">New requests will appear here automatically</p>
          </div>
        ) : (
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            {batches.map((batch) => {
              const key = `batch-${batch.id}`;
              const isAccepting = accepting === key;
              const routeStops = JSON.parse(batch.optimized_route_json || '[]');
              return (
                <div key={key} className="bg-white rounded-xl border border-emerald-200 shadow-md hover:shadow-lg transition-shadow p-5 relative overflow-hidden">
                  <div className="absolute top-0 right-0 bg-emerald-500 text-white text-xs font-bold px-3 py-1 rounded-bl-xl">DMFE BATCHED</div>
                  <div className="flex items-start justify-between mb-3 mt-2">
                    <div className="flex items-center gap-3">
                      <div className="p-2.5 rounded-xl bg-emerald-100">
                        <Layers className="h-5 w-5 text-emerald-600" />
                      </div>
                      <div>
                        <p className="text-xs font-semibold uppercase tracking-wide text-emerald-700">Combined Trip</p>
                        <p className="text-xs text-gray-400">Batch #{batch.id} • {routeStops.length} Stops</p>
                      </div>
                    </div>
                    {batch.total_estimated_fare > 0 && (
                      <span className="flex items-center text-sm font-bold text-emerald-700 bg-emerald-50 px-2 py-1 rounded-lg">
                        <IndianRupee className="h-3.5 w-3.5" /> {batch.total_estimated_fare}
                      </span>
                    )}
                  </div>
                  <div className="space-y-1.5 mb-4 text-sm text-gray-600">
                    <p>🛣️ Total Distance: {batch.total_distance_km?.toFixed(1) || 0} km</p>
                    <p>📍 {routeStops.length / 2} Orders (Pickup & Drop)</p>
                  </div>
                  <button
                    onClick={() => handleAccept({ ...batch, is_batch: true })}
                    disabled={isAccepting || !!activeBooking}
                    className="w-full py-2.5 rounded-xl bg-gradient-to-r from-emerald-500 to-teal-500 text-white font-semibold text-sm hover:from-emerald-600 hover:to-teal-600 flex items-center justify-center gap-2 transition-all disabled:opacity-40 disabled:cursor-not-allowed"
                  >
                    {isAccepting ? <><Loader2 className="h-4 w-4 animate-spin" /> Accepting…</> : activeBooking ? 'Complete active booking first' : <><CheckCircle2 className="h-4 w-4" /> Accept Batch</>}
                  </button>
                </div>
              );
            })}
            
            {requests.map((req) => {
              const cfg  = TYPE_CONFIG[req.type] || TYPE_CONFIG.ride;
              const Icon = cfg.icon;
              const key  = `${req.type}-${req.id}`;
              const isAccepting = accepting === key;
              return (
                <div key={key}
                  className="bg-white rounded-xl border border-gray-100 shadow-sm hover:shadow-md transition-shadow p-5">
                  <div className="flex items-start justify-between mb-3">
                    <div className="flex items-center gap-3">
                      <div className={`p-2.5 rounded-xl ${cfg.bg}`}>
                        <Icon className={`h-5 w-5 ${cfg.color}`} />
                      </div>
                      <div>
                        <p className={`text-xs font-semibold uppercase tracking-wide ${cfg.color}`}>{cfg.label}</p>
                        <p className="text-xs text-gray-400">#{req.id}</p>
                      </div>
                    </div>
                    {req.estimated_fare && (
                      <span className="flex items-center text-sm font-bold text-emerald-700 bg-emerald-50 px-2 py-1 rounded-lg">
                        <IndianRupee className="h-3.5 w-3.5" /> {req.estimated_fare}
                      </span>
                    )}
                  </div>

                  <div className="space-y-1.5 mb-4">
                    <div className="flex items-start gap-2 text-sm text-gray-700">
                      <MapPin className="h-4 w-4 text-emerald-500 mt-0.5 shrink-0" />
                      <span className="line-clamp-1">{req.pickup_address}</span>
                    </div>
                    <div className="flex items-start gap-2 text-sm text-gray-700">
                      <MapPin className="h-4 w-4 text-red-500 mt-0.5 shrink-0" />
                      <span className="line-clamp-1">{req.drop_address}</span>
                    </div>
                  </div>

                  {req.restaurant_name && (
                    <p className="text-xs text-gray-500 mb-3">🍽️ {req.restaurant_name}</p>
                  )}
                  {req.distance_km && (
                    <p className="text-xs text-gray-500 mb-3">📏 {req.distance_km} km away</p>
                  )}
                  {req.is_fragile && (
                    <p className="text-xs text-amber-600 mb-3">⚠️ Fragile — Handle with Care</p>
                  )}

                  <button
                    onClick={() => handleAccept(req)}
                    disabled={isAccepting || !!activeBooking}
                    className="w-full py-2.5 rounded-xl bg-gradient-to-r from-violet-600 to-purple-600 text-white font-semibold text-sm
                      hover:from-violet-700 hover:to-purple-700 flex items-center justify-center gap-2 transition-all
                      disabled:opacity-40 disabled:cursor-not-allowed"
                  >
                    {isAccepting
                      ? <><Loader2 className="h-4 w-4 animate-spin" /> Accepting…</>
                      : activeBooking
                        ? 'Complete active booking first'
                        : <><CheckCircle2 className="h-4 w-4" /> Accept</>
                    }
                  </button>
                </div>
              );
            })}
          </div>
        )
      )}

      {/* Completed trips */}
      {activeTab === 'completed' && (
        completed.length === 0 ? (
          <div className="text-center py-16 bg-white rounded-2xl border border-gray-100">
            <Trophy className="h-12 w-12 text-gray-300 mx-auto mb-3" />
            <p className="text-gray-500 font-medium">No completed trips yet</p>
          </div>
        ) : (
          <div className="space-y-3">
            {completed.map((trip, i) => (
              <div key={i} className="bg-white rounded-xl border border-gray-100 p-4 flex items-center justify-between">
                <div>
                  <p className="text-sm font-semibold text-gray-800 capitalize">
                    {trip.type} · #{trip.id}
                  </p>
                  <p className="text-xs text-gray-500 truncate max-w-xs">{trip.from} → {trip.to}</p>
                  {trip.completed_at && (
                    <p className="text-xs text-gray-400 mt-0.5">
                      {new Date(trip.completed_at).toLocaleDateString('en-IN')}
                    </p>
                  )}
                </div>
                {trip.fare && (
                  <span className="flex items-center text-sm font-bold text-emerald-700">
                    <IndianRupee className="h-3.5 w-3.5" /> {trip.fare}
                  </span>
                )}
              </div>
            ))}
          </div>
        )
      )}
    </div>
  );
}
