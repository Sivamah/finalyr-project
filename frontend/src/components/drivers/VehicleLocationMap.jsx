import React, { useState } from 'react';
import { MapContainer, TileLayer, Marker as LeafletMarker, Popup as LeafletPopup } from 'react-leaflet';
import L from 'leaflet';
import { Navigation, Truck, RefreshCw } from 'lucide-react';
import 'leaflet/dist/leaflet.css';

import { COIMBATORE_CENTER as _CBE } from '../../utils/coimbatore';
import { TILE_URL, TILE_ATTRIBUTION, TILE_SUBDOMAINS } from '../../utils/tileConfig';

const COIMBATORE_CENTER = [_CBE.lat, _CBE.lng];
const DEFAULT_ZOOM = 12;

// Custom SVG Icons for Vehicle Statuses
function createVehicleIcon(status, selected = false) {
  let color = '#10B981'; // Available: Green
  if (status === 'Busy') color = '#3B82F6'; // Busy: Blue
  if (status === 'Maintenance') color = '#F59E0B'; // Maintenance: Amber
  if (status === 'Offline') color = '#6B7280'; // Offline: Gray

  const size = selected ? 40 : 28;
  const stroke = selected ? '#FFFFFF' : '#111827';
  const strokeWidth = selected ? 2.5 : 1.5;

  const svg = `<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="${color}" width="${size}" height="${size}" stroke="${stroke}" stroke-width="${strokeWidth}">
    <path d="M12 2C8.13 2 5 5.13 5 9c0 5.25 7 13 7 13s7-7.75 7-13c0-3.87-3.13-7-7-7zm0 9.5a2.5 2.5 0 1 1 0-5 2.5 2.5 0 0 1 0 5z"/>
  </svg>`;

  return L.divIcon({
    html: svg,
    className: selected ? 'custom-vehicle-marker custom-vehicle-marker--selected' : 'custom-vehicle-marker',
    iconSize: [size, size],
    iconAnchor: [size / 2, size],
    popupAnchor: [0, -size],
  });
}

export default function VehicleLocationMap({ locations = [], onRefresh }) {
  const [selectedVehicle, setSelectedVehicle] = useState(null);
  return (
    <div className="glass-panel rounded-[20px] p-4 lg:p-5 shadow-sm space-y-4">
      {/* Map Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2 border-b border-white/10 pb-4">
        <div>
          <h3 className="text-base font-display font-semibold text-white flex items-center gap-2">
            <Navigation className="h-5 w-5 text-brand-primary" />
            Vehicle Location Map <span className="text-brand-text-muted text-sm font-medium">({locations.length} Fleet Markers)</span>
          </h3>
          <p className="text-xs text-brand-text-muted mt-0.5">
            Simulated / last-known positions — no live GPS feed connected
          </p>
        </div>

        {/* Legend & Refresh */}
        <div className="flex items-center gap-4">
          <div className="flex items-center gap-3 text-[11px] font-medium">
            <span className="flex items-center gap-1 text-green-400">
              <span className="w-2 h-2 rounded-full bg-green-500" /> Available
            </span>
            <span className="flex items-center gap-1 text-blue-400">
              <span className="w-2 h-2 rounded-full bg-blue-500" /> Busy
            </span>
            <span className="flex items-center gap-1 text-amber-400">
              <span className="w-2 h-2 rounded-full bg-amber-500" /> Maintenance
            </span>
          </div>

          <button
            onClick={onRefresh}
            className="btn-ghost py-1.5 px-3 text-xs"
          >
            <RefreshCw className="h-3.5 w-3.5" /> Refresh
          </button>
        </div>
      </div>

      {/* Map View */}
      <div className="relative h-[480px] w-full rounded-[16px] overflow-hidden border border-white/10 bg-gray-900/50 z-0">
        <MapContainer
          center={COIMBATORE_CENTER}
          zoom={DEFAULT_ZOOM}
          scrollWheelZoom={true}
          style={{ width: '100%', height: '100%' }}
        >
          <TileLayer
            attribution={TILE_ATTRIBUTION}
            url={TILE_URL}
            subdomains={TILE_SUBDOMAINS}
          />

          {locations.map((loc) => {
            const isSelected = selectedVehicle?.vehicle_id === loc.vehicle_id;
            const icon = createVehicleIcon(loc.status, isSelected);
            return (
              <LeafletMarker
                key={loc.vehicle_id}
                position={[loc.lat, loc.lng]}
                icon={icon}
                zIndexOffset={isSelected ? 300 : 0}
                eventHandlers={{
                  click: () => {
                    setSelectedVehicle(loc);
                  },
                }}
              >
                <LeafletPopup autoPan={true}>
                  <div className="p-2 min-w-[200px] text-xs">
                    <div className="flex items-center justify-between border-b pb-1.5 mb-2">
                      <span className="font-bold text-gray-900 flex items-center gap-1">
                        <Truck className="h-3.5 w-3.5 text-indigo-600" />
                        {loc.vehicle_name}
                      </span>
                      <span className={`px-2 py-0.5 rounded text-[10px] font-bold ${
                        loc.status === 'Available' ? 'bg-green-100 text-green-800' : 'bg-blue-100 text-blue-800'
                      }`}>
                        {loc.status}
                      </span>
                    </div>

                    <div className="space-y-1 text-gray-700">
                      <p><strong>Registration:</strong> {loc.registration_number}</p>
                      <p><strong>Type:</strong> {loc.vehicle_type}</p>
                      <p><strong>Provider:</strong> {loc.provider_name}</p>
                      <p><strong>Driver:</strong> {loc.driver_name}</p>
                      <p className="font-mono text-[10px] text-gray-500 pt-1 border-t">
                        Pos (simulated): {loc.lat && loc.lat.toFixed ? loc.lat.toFixed(4) : loc.lat}, {loc.lng && loc.lng.toFixed ? loc.lng.toFixed(4) : loc.lng}
                      </p>
                    </div>
                  </div>
                </LeafletPopup>
              </LeafletMarker>
            );
          })}
        </MapContainer>
      </div>
    </div>
  );
}
