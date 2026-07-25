import React, { useState, useCallback, useRef } from 'react';
import { MapContainer, TileLayer, Marker, useMapEvents, useMap } from 'react-leaflet';
import L from 'leaflet';
import { MapPin, Loader2, Search } from 'lucide-react';

delete L.Icon.Default.prototype._getIconUrl;
L.Icon.Default.mergeOptions({
  iconRetinaUrl: 'https://unpkg.com/leaflet@1.9.4/dist/images/marker-icon-2x.png',
  iconUrl: 'https://unpkg.com/leaflet@1.9.4/dist/images/marker-icon.png',
  shadowUrl: 'https://unpkg.com/leaflet@1.9.4/dist/images/marker-shadow.png',
});

const greenIcon = new L.Icon({
  iconUrl: 'https://raw.githubusercontent.com/pointhi/leaflet-color-markers/master/img/marker-icon-green.png',
  shadowUrl: 'https://unpkg.com/leaflet@1.9.4/dist/images/marker-shadow.png',
  iconSize: [25, 41],
  iconAnchor: [12, 41],
  popupAnchor: [1, -34],
  shadowSize: [41, 41],
});

const redIcon = new L.Icon({
  iconUrl: 'https://raw.githubusercontent.com/pointhi/leaflet-color-markers/master/img/marker-icon-red.png',
  shadowUrl: 'https://unpkg.com/leaflet@1.9.4/dist/images/marker-shadow.png',
  iconSize: [25, 41],
  iconAnchor: [12, 41],
  popupAnchor: [1, -34],
  shadowSize: [41, 41],
});

const COIMBATORE = [11.0168, 76.9558];

async function nominatimSearch(query) {
  const res = await fetch(
    `https://nominatim.openstreetmap.org/search?format=json&q=${encodeURIComponent(query)}&limit=5&countrycodes=in`,
    { headers: { 'Accept-Language': 'en' } }
  );
  return res.json();
}

async function nominatimReverse(lat, lng) {
  const res = await fetch(
    `https://nominatim.openstreetmap.org/reverse?format=json&lat=${lat}&lon=${lng}`,
    { headers: { 'Accept-Language': 'en' } }
  );
  return res.json();
}

function MapClickHandler({ onClick }) {
  useMapEvents({
    click(e) {
      onClick({ lat: e.latlng.lat, lng: e.latlng.lng });
    },
  });
  return null;
}

function SetViewOnChange({ value }) {
  const map = useMap();
  React.useEffect(() => {
    if (value) {
      map.setView([value.lat, value.lng], 15);
    }
  }, [value, map]);
  return null;
}

export default function LeafletLocationPicker({ label, color = 'green', value, onChange }) {
  const [searchQuery, setSearchQuery] = useState('');
  const [results, setResults] = useState([]);
  const [searching, setSearching] = useState(false);
  const [showResults, setShowResults] = useState(false);
  const debounceRef = useRef(null);

  const center = value ? [value.lat, value.lng] : COIMBATORE;

  const handleSearchInput = (e) => {
    const q = e.target.value;
    setSearchQuery(q);
    if (debounceRef.current) clearTimeout(debounceRef.current);
    if (q.length < 3) { setResults([]); return; }
    setSearching(true);
    debounceRef.current = setTimeout(async () => {
      try {
        const data = await nominatimSearch(q);
        setResults(data);
        setShowResults(true);
      } catch { setResults([]); }
      setSearching(false);
    }, 500);
  };

  const handleSelectResult = (place) => {
    const lat = parseFloat(place.lat);
    const lng = parseFloat(place.lon);
    setSearchQuery(place.display_name);
    setShowResults(false);
    onChange({ lat, lng, address: place.display_name });
  };

  const handleMapClick = async ({ lat, lng }) => {
    try {
      const data = await nominatimReverse(lat, lng);
      const address = data.display_name || `${lat.toFixed(5)}, ${lng.toFixed(5)}`;
      onChange({ lat, lng, address });
      setSearchQuery(address);
    } catch {
      onChange({ lat, lng, address: `${lat.toFixed(5)}, ${lng.toFixed(5)}` });
    }
  };

  return (
    <div className="space-y-2">
      <label className="block text-sm font-semibold text-gray-700">
        <MapPin className={`inline h-4 w-4 mr-1 ${color === 'green' ? 'text-emerald-600' : 'text-red-500'}`} />
        {label}
      </label>

      <div className="relative">
        <div className="relative">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-gray-400" />
          <input
            type="text"
            value={searchQuery}
            onChange={handleSearchInput}
            placeholder={`Search for ${label.toLowerCase()} in Coimbatore...`}
            className="w-full pl-9 pr-10 py-2.5 text-sm border border-gray-200 rounded-xl bg-white focus:outline-none focus:border-violet-400 focus:ring-2 focus:ring-violet-100"
          />
          {searching && <Loader2 className="absolute right-3 top-1/2 -translate-y-1/2 h-4 w-4 animate-spin text-gray-400" />}
        </div>

        {showResults && results.length > 0 && (
          <div className="absolute z-50 mt-1 w-full bg-white border border-gray-200 rounded-xl shadow-lg max-h-48 overflow-y-auto">
            {results.map((place, i) => (
              <button
                key={i}
                onClick={() => handleSelectResult(place)}
                className="w-full text-left px-4 py-2.5 text-sm hover:bg-violet-50 border-b border-gray-50 last:border-0"
              >
                <p className="text-gray-800 truncate">{place.display_name}</p>
                <p className="text-xs text-gray-400">{place.type}</p>
              </button>
            ))}
          </div>
        )}
      </div>

      {value && (
        <p className="text-xs text-gray-500 truncate px-1">📍 {value.address}</p>
      )}

      <div className="h-48 rounded-xl overflow-hidden border border-gray-200 relative">
        <MapContainer
          center={center}
          zoom={value ? 15 : 12}
          className="h-full w-full"
        >
          <TileLayer
            attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a>'
            url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
          />
          <MapClickHandler onClick={handleMapClick} />
          <SetViewOnChange value={value} />
          {value && (
            <Marker
              position={[value.lat, value.lng]}
              icon={color === 'green' ? greenIcon : redIcon}
            />
          )}
        </MapContainer>
      </div>
    </div>
  );
}
