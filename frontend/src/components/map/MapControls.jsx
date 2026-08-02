import React from 'react';
import { Maximize2, Minimize2, Target, Plus, Minus, Compass } from 'lucide-react';

export default function MapControls({
  onFitBounds,
  onRecenter,
  onZoomIn,
  onZoomOut,
  isFullscreen,
  onToggleFullscreen,
}) {
  return (
    <div className="flex flex-col gap-2 bg-gray-800/90 backdrop-blur-md border border-gray-700/80 rounded-xl p-1.5 shadow-xl">
      {/* Fit Bounds */}
      <button
        onClick={onFitBounds}
        className="p-2 bg-indigo-600 hover:bg-indigo-700 text-white rounded-lg text-xs font-semibold flex items-center gap-1 transition-colors shadow-sm"
        title="Fit All Markers"
      >
        <Target className="h-4 w-4" />
        <span className="hidden sm:inline">Fit All</span>
      </button>

      {/* Recenter */}
      <button
        onClick={onRecenter}
        className="p-2 bg-gray-700 hover:bg-gray-600 text-gray-200 rounded-lg text-xs font-medium flex items-center gap-1 transition-colors"
        title="Recenter Map to Coimbatore"
      >
        <Compass className="h-4 w-4 text-cyan-400" />
        <span className="hidden sm:inline">Coimbatore</span>
      </button>

      <div className="h-px bg-gray-700 my-0.5" />

      {/* Zoom In */}
      <button
        onClick={onZoomIn}
        className="p-2 bg-gray-700 hover:bg-gray-600 text-gray-200 rounded-lg transition-colors"
        title="Zoom In"
      >
        <Plus className="h-4 w-4" />
      </button>

      {/* Zoom Out */}
      <button
        onClick={onZoomOut}
        className="p-2 bg-gray-700 hover:bg-gray-600 text-gray-200 rounded-lg transition-colors"
        title="Zoom Out"
      >
        <Minus className="h-4 w-4" />
      </button>

      {/* Fullscreen Toggle */}
      {onToggleFullscreen && (
        <button
          onClick={onToggleFullscreen}
          className="p-2 bg-gray-700 hover:bg-gray-600 text-gray-200 rounded-lg transition-colors mt-0.5"
          title={isFullscreen ? 'Exit Fullscreen' : 'Fullscreen'}
        >
          {isFullscreen ? <Minimize2 className="h-4 w-4" /> : <Maximize2 className="h-4 w-4" />}
        </button>
      )}
    </div>
  );
}
