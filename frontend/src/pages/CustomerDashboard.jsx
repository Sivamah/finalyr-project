import { useState, useContext } from 'react';
import { Car, UtensilsCrossed, Package, Clock, Zap } from 'lucide-react';
import { AuthContext } from '../context/AuthContext';
import BookRide from './customer/BookRide';
import BookFood from './customer/BookFood';
import BookParcel from './customer/BookParcel';
import BookingHistory from './customer/BookingHistory';

const TABS = [
  {
    id: 'ride',
    label: 'Book Ride',
    icon: Car,
    gradient: 'from-violet-600 to-purple-700',
    lightBg: 'bg-violet-50',
    lightText: 'text-violet-600',
    desc: 'Quick passenger rides',
  },
  {
    id: 'food',
    label: 'Food Delivery',
    icon: UtensilsCrossed,
    gradient: 'from-orange-500 to-red-600',
    lightBg: 'bg-orange-50',
    lightText: 'text-orange-600',
    desc: 'Order from any restaurant',
  },
  {
    id: 'parcel',
    label: 'Parcel',
    icon: Package,
    gradient: 'from-sky-500 to-blue-600',
    lightBg: 'bg-sky-50',
    lightText: 'text-sky-600',
    desc: 'Send & receive parcels',
  },
  {
    id: 'history',
    label: 'My Bookings',
    icon: Clock,
    gradient: 'from-slate-600 to-gray-700',
    lightBg: 'bg-slate-50',
    lightText: 'text-slate-600',
    desc: 'View booking history',
  },
];

export default function CustomerDashboard() {
  const { user }        = useContext(AuthContext);
  const [activeTab, setActiveTab] = useState('ride');
  const [historyKey, setHistoryKey] = useState(0);

  const activeConfig = TABS.find((t) => t.id === activeTab);

  const handleBookingSuccess = () => {
    // Auto-switch to history tab after a booking
    setTimeout(() => { setActiveTab('history'); setHistoryKey((k) => k + 1); }, 1800);
  };

  return (
    <div className="flex-1 w-full space-y-6 max-w-5xl mx-auto">
      {/* Hero greeting */}
      <div className={`relative overflow-hidden rounded-2xl bg-gradient-to-r ${activeConfig.gradient} p-6 text-white shadow-lg`}>
        <div className="relative z-10">
          <div className="flex items-center gap-2 mb-1">
            <Zap className="h-5 w-5 text-white/80" />
            <span className="text-white/80 text-sm font-medium">DMFE System</span>
          </div>
          <h1 className="text-2xl font-bold">Hi, {user?.full_name?.split(' ')[0]}! 👋</h1>
          <p className="text-white/80 mt-1 text-sm">Where are you going or what do you need today?</p>
        </div>
        {/* Decorative circle */}
        <div className="absolute -right-8 -top-8 w-32 h-32 rounded-full bg-white/10" />
        <div className="absolute -right-4 -bottom-4 w-20 h-20 rounded-full bg-white/10" />
      </div>

      {/* Tab navigation */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
        {TABS.map((tab) => {
          const TIcon = tab.icon;
          const isActive = activeTab === tab.id;
          return (
            <button
              key={tab.id}
              onClick={() => setActiveTab(tab.id)}
              className={`flex flex-col items-center gap-2 p-4 rounded-xl border-2 text-left transition-all
                ${isActive
                  ? `border-transparent bg-gradient-to-br ${tab.gradient} text-white shadow-md`
                  : 'border-gray-100 bg-white text-gray-700 hover:border-gray-200 hover:shadow-sm'
                }`}
            >
              <div className={`p-2 rounded-lg ${isActive ? 'bg-white/20' : tab.lightBg}`}>
                <TIcon className={`h-5 w-5 ${isActive ? 'text-white' : tab.lightText}`} />
              </div>
              <div>
                <p className={`text-xs font-bold ${isActive ? 'text-white' : 'text-gray-800'}`}>{tab.label}</p>
                <p className={`text-xs mt-0.5 ${isActive ? 'text-white/70' : 'text-gray-400'}`}>{tab.desc}</p>
              </div>
            </button>
          );
        })}
      </div>

      {/* Tab content panel */}
      <div className="bg-white rounded-2xl border border-gray-100 shadow-sm p-6">
        <div className="flex items-center gap-2 mb-6 pb-4 border-b border-gray-100">
          {(() => { const TIcon = activeConfig.icon; return <TIcon className={`h-5 w-5 ${activeConfig.lightText}`} />; })()}
          <h2 className="text-lg font-bold text-gray-900">{activeConfig.label}</h2>
          <span className="text-gray-400 text-sm">— {activeConfig.desc}</span>
        </div>

        {activeTab === 'ride'    && <BookRide    onSuccess={handleBookingSuccess} />}
        {activeTab === 'food'    && <BookFood    onSuccess={handleBookingSuccess} />}
        {activeTab === 'parcel'  && <BookParcel  onSuccess={handleBookingSuccess} />}
        {activeTab === 'history' && <BookingHistory key={historyKey} />}
      </div>
    </div>
  );
}
