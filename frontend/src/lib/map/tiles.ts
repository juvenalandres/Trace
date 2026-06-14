export interface TileProvider {
  key: string;
  name: string;
  url: string;
  attribution: string;
  maxZoom: number;
}

export const tileProviders: Record<string, TileProvider> = {
  esri_topo: {
    key: 'esri_topo',
    name: 'Topo Map',
    url: 'https://server.arcgisonline.com/ArcGIS/rest/services/World_Topo_Map/MapServer/tile/{z}/{y}/{x}',
    attribution: '&copy; Esri',
    maxZoom: 19,
  },
  opentopomap: {
    key: 'opentopomap',
    name: 'OpenTopoMap',
    url: 'https://{s}.tile.opentopomap.org/{z}/{x}/{y}.png',
    attribution: '&copy; OpenTopoMap',
    maxZoom: 17,
  },
  openstreetmap: {
    key: 'openstreetmap',
    name: 'Street Map',
    url: 'https://tile.openstreetmap.org/{z}/{x}/{y}.png',
    attribution: '&copy; OpenStreetMap',
    maxZoom: 19,
  },
  voyager: {
    key: 'voyager',
    name: 'Voyager',
    url: 'https://{s}.basemaps.cartocdn.com/rastertiles/voyager/{z}/{x}/{y}.png',
    attribution: '&copy; CARTO',
    maxZoom: 19,
  },
  esri_imagery: {
    key: 'esri_imagery',
    name: 'Satellite',
    url: 'https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}',
    attribution: '&copy; Esri',
    maxZoom: 19,
  },
};

const STORAGE_KEY = 'trace_tile_provider';
const DEFAULT_KEY = 'esri_topo';

export function getSelectedTile(): TileProvider {
  if (typeof window === 'undefined') return tileProviders[DEFAULT_KEY];
  const saved = localStorage.getItem(STORAGE_KEY);
  return tileProviders[saved] ?? tileProviders[DEFAULT_KEY];
}

export function setSelectedTile(key: string): void {
  if (typeof window === 'undefined') return;
  localStorage.setItem(STORAGE_KEY, key);
}

export function getTileList(): TileProvider[] {
  return Object.values(tileProviders);
}
