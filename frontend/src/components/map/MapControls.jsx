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
  const baseBtn =
    'flex items-center justify-center gap-1.5 rounded-xl text-brand-text-secondary hover:text-white hover:bg-white/[0.08] transition-all duration-300';
  return (
    <div className="flex flex-col gap-1 glass-panel-strong rounded-2xl p-1.5 backdrop-blur-xl">
      <button
        onClick={onFitBounds}
        className={`${baseBtn} h-9 px-2.5 text-[11px] font-semibold text-white bg-gradient-to-br from-brand-primary to-brand-secondary/80 border border-white/15 shadow-[0_4px_16px_rgba(59,130,246,0.35)]`}
        title="Fit All Markers"
      >
        <Target className="h-3.5 w-3.5" />
        <span className="hidden sm:inline">Fit</span>
      </button>

      <button onClick={onRecenter} className={`${baseBtn} h-9 px-2.5 text-[11px]`} title="Recenter Map to Coimbatore">
        <Compass className="h-3.5 w-3.5 text-brand-secondary" />
        <span className="hidden sm:inline">Center</span>
      </button>

      <div className="h-px bg-white/[0.07] my-0.5 mx-1" />

      <button onClick={onZoomIn} className={`${baseBtn} h-9 w-9`} title="Zoom In">
        <Plus className="h-4 w-4" />
      </button>
      <button onClick={onZoomOut} className={`${baseBtn} h-9 w-9`} title="Zoom Out">
        <Minus className="h-4 w-4" />
      </button>

      {onToggleFullscreen && (
        <button onClick={onToggleFullscreen} className={`${baseBtn} h-9 w-9`} title={isFullscreen ? 'Exit Fullscreen' : 'Fullscreen'}>
          {isFullscreen ? <Minimize2 className="h-4 w-4" /> : <Maximize2 className="h-4 w-4" />}
        </button>
      )}
    </div>
  );
}