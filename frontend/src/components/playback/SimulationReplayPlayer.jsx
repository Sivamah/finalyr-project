import React, { useState, useEffect, useRef } from 'react';
import { Play, Pause, Square, FastForward, X, Activity, Layers } from 'lucide-react';

export default function SimulationReplayPlayer({ simulation, onClose }) {
  const [isPlaying, setIsPlaying] = useState(false);
  const [currentFrameIndex, setCurrentFrameIndex] = useState(0);
  const [speedMultiplier, setSpeedMultiplier] = useState(1); // 1x, 2x, 5x

  const frames = simulation?.events_timeline || [];
  const totalFrames = frames.length || 1;

  const timerRef = useRef(null);

  useEffect(() => {
    if (isPlaying) {
      const intervalMs = Math.max(200, 1000 / speedMultiplier);
      timerRef.current = setInterval(() => {
        setCurrentFrameIndex((prev) => {
          if (prev >= totalFrames - 1) {
            setIsPlaying(false);
            return prev;
          }
          return prev + 1;
        });
      }, intervalMs);
    } else {
      clearInterval(timerRef.current);
    }
    return () => clearInterval(timerRef.current);
  }, [isPlaying, speedMultiplier, totalFrames]);

  if (!simulation) return null;

  const currentFrame = frames[currentFrameIndex] || {
    frame: 1,
    timestamp: '00:00:00',
    active_requests: 0,
    completed_requests: 0,
    completion_rate: simulation.completion_rate,
  };

  const handlePlay = () => setIsPlaying(true);
  const handlePause = () => setIsPlaying(false);
  const handleStop = () => {
    setIsPlaying(false);
    setCurrentFrameIndex(0);
  };

  const handleScrubberChange = (e) => {
    setCurrentFrameIndex(parseInt(e.target.value));
  };

  return (
    <div className="fixed inset-0 bg-black/75 z-50 flex items-center justify-center p-4">
      <div className="bg-gray-800 border border-gray-700 rounded-2xl w-full max-w-4xl shadow-2xl overflow-hidden flex flex-col max-h-[90vh]">
        {/* Modal Header */}
        <div className="flex items-center justify-between px-6 py-4 border-b border-gray-700 bg-gray-850">
          <div>
            <h3 className="text-lg font-bold text-white flex items-center gap-2">
              <Activity className="h-5 w-5 text-indigo-400 animate-pulse" />
              Replaying Historical Run: {simulation.name}
            </h3>
            <p className="text-xs text-gray-400 mt-0.5">
              Scenario: <span className="text-indigo-300 font-bold">{simulation.scenario_name}</span> • Saved on {simulation.created_at}
            </p>
          </div>

          <button
            onClick={onClose}
            className="p-2 text-gray-400 hover:text-white hover:bg-gray-700 rounded-lg transition-colors"
          >
            <X className="h-5 w-5" />
          </button>
        </div>

        {/* Telemetry Display Stage */}
        <div className="p-6 space-y-6 overflow-y-auto flex-1 bg-gray-900/50">
          {/* Top Live Overlay Metrics */}
          <div className="grid grid-cols-1 sm:grid-cols-4 gap-4">
            <div className="bg-gray-800 border border-gray-700 rounded-xl p-4 text-center">
              <span className="text-xs text-gray-400 font-medium">Replay Time</span>
              <p className="text-xl font-bold font-mono text-indigo-400 mt-1">{currentFrame.timestamp}</p>
            </div>
            <div className="bg-gray-800 border border-gray-700 rounded-xl p-4 text-center">
              <span className="text-xs text-gray-400 font-medium">Active Queue</span>
              <p className="text-xl font-bold font-mono text-amber-400 mt-1">{currentFrame.active_requests} reqs</p>
            </div>
            <div className="bg-gray-800 border border-gray-700 rounded-xl p-4 text-center">
              <span className="text-xs text-gray-400 font-medium">Completed Reqs</span>
              <p className="text-xl font-bold font-mono text-green-400 mt-1">{currentFrame.completed_requests} reqs</p>
            </div>
            <div className="bg-gray-800 border border-gray-700 rounded-xl p-4 text-center">
              <span className="text-xs text-gray-400 font-medium">Completion Rate</span>
              <p className="text-xl font-bold font-mono text-blue-400 mt-1">{currentFrame.completion_rate}%</p>
            </div>
          </div>

          {/* Provider Breakdown Cards */}
          <div className="bg-gray-800 border border-gray-700 rounded-xl p-5">
            <h4 className="text-xs font-bold text-gray-300 uppercase tracking-wider mb-3 flex items-center gap-2">
              <Layers className="h-4 w-4 text-indigo-400" /> Provider Request Utilization
            </h4>
            <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
              {Object.entries(simulation.provider_stats || {}).map(([pName, pCount]) => (
                <div key={pName} className="bg-gray-900 border border-gray-700 rounded-lg p-3 flex justify-between items-center">
                  <span className="text-xs font-bold text-white">{pName}</span>
                  <span className="text-xs font-mono font-bold text-indigo-400">{pCount} reqs</span>
                </div>
              ))}
            </div>
          </div>

          {/* Timeline Scrubber */}
          <div className="space-y-2 pt-2">
            <div className="flex justify-between text-xs font-mono text-gray-400">
              <span>Frame {currentFrameIndex + 1} of {totalFrames}</span>
              <span>{Math.round(((currentFrameIndex + 1) / totalFrames) * 100)}% Progress</span>
            </div>
            <input
              type="range"
              min="0"
              max={totalFrames - 1}
              value={currentFrameIndex}
              onChange={handleScrubberChange}
              className="w-full accent-indigo-500 cursor-pointer h-2 bg-gray-700 rounded-lg"
            />
          </div>
        </div>

        {/* Player Controls Toolbar */}
        <div className="px-6 py-4 border-t border-gray-700 bg-gray-850 flex flex-wrap items-center justify-between gap-4">
          {/* Main Controls */}
          <div className="flex items-center gap-2">
            {!isPlaying ? (
              <button
                type="button"
                onClick={handlePlay}
                className="flex items-center gap-1.5 px-4 py-2 bg-indigo-600 hover:bg-indigo-700 text-white font-bold text-xs rounded-lg transition-colors shadow"
              >
                <Play className="h-4 w-4" /> Play
              </button>
            ) : (
              <button
                type="button"
                onClick={handlePause}
                className="flex items-center gap-1.5 px-4 py-2 bg-amber-600 hover:bg-amber-700 text-white font-bold text-xs rounded-lg transition-colors shadow"
              >
                <Pause className="h-4 w-4" /> Pause
              </button>
            )}

            <button
              type="button"
              onClick={handleStop}
              className="flex items-center gap-1.5 px-3 py-2 bg-gray-700 hover:bg-gray-600 text-gray-300 font-bold text-xs rounded-lg transition-colors"
            >
              <Square className="h-4 w-4" /> Stop
            </button>
          </div>

          {/* Speed Selector */}
          <div className="flex items-center gap-2">
            <span className="text-xs font-medium text-gray-400 flex items-center gap-1">
              <FastForward className="h-3.5 w-3.5 text-indigo-400" /> Replay Speed:
            </span>
            {[1, 2, 5].map((s) => (
              <button
                key={s}
                type="button"
                onClick={() => setSpeedMultiplier(s)}
                className={`px-3 py-1 rounded text-xs font-bold font-mono transition-colors border ${
                  speedMultiplier === s
                    ? 'bg-indigo-600 border-indigo-500 text-white'
                    : 'bg-gray-900 border-gray-700 text-gray-400 hover:text-white'
                }`}
              >
                {s}x
              </button>
            ))}
          </div>
        </div>
      </div>
    </div>
  );
}
