/**
 * Shared basemap tile configuration.
 *
 * Mirrors the defaults once defined inside LiveMapContainer.jsx so every
 * Leaflet map in the app (LiveMapContainer, VehicleLocationMap,
 * OrchestrationDetailsDrawer) resolves its basemap from the same source.
 *
 * Default is keyless OpenStreetMap. Point VITE_MAP_TILE_URL at a keyed
 * provider to swap every map at once (see .env.example). CARTO's raster
 * basemaps watermark anonymous requests with "API KEY REQUIRED", so do not
 * use those without a key.
 */
const TILE_URL = import.meta.env.VITE_MAP_TILE_URL
  || 'https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png';
const TILE_ATTRIBUTION = import.meta.env.VITE_MAP_TILE_ATTRIBUTION
  || '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a>';
const TILE_SUBDOMAINS = import.meta.env.VITE_MAP_TILE_SUBDOMAINS || 'abc';

export { TILE_URL, TILE_ATTRIBUTION, TILE_SUBDOMAINS };