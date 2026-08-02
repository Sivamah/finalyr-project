import React from 'react';
import { Gauge, Sparkles, Award } from 'lucide-react';

export default function CompatibilityGauge({ score = 89.5, confidence = 92 }) {
  const roundedScore = Math.round(score);
  const roundedConf = Math.round(confidence);

  // SVG Gauge calculations (semi-circle arc)
  const radius = 60;
  const circumference = Math.PI * radius;
  const strokeDashoffset = circumference - (roundedScore / 100) * circumference;

  let gaugeColor = '#6366f1'; // indigo
  if (roundedScore >= 85) gaugeColor = '#10b981'; // green
  else if (roundedScore >= 70) gaugeColor = '#f59e0b'; // amber
  else gaugeColor = '#ef4444'; // red

  return (
    <div className="bg-gray-800 border border-gray-700 rounded-xl p-5 shadow-sm flex flex-col items-center justify-between">
      <div className="w-full flex items-center justify-between border-b border-gray-700 pb-3 mb-3">
        <h3 className="text-sm font-bold text-white flex items-center gap-2">
          <Gauge className="h-4 w-4 text-cyan-400" />
          Compatibility Gauge
        </h3>
        <span className="text-xs text-gray-400 font-mono">XAI Score</span>
      </div>

      {/* Semi-circle Arc SVG Gauge */}
      <div className="relative flex flex-col items-center my-2">
        <svg className="w-40 h-24 overflow-visible">
          {/* Background Arc */}
          <path
            d="M 15 80 A 60 60 0 0 1 135 80"
            fill="none"
            stroke="#374151"
            strokeWidth="12"
            strokeLinecap="round"
          />
          {/* Active Arc */}
          <path
            d="M 15 80 A 60 60 0 0 1 135 80"
            fill="none"
            stroke={gaugeColor}
            strokeWidth="12"
            strokeLinecap="round"
            strokeDasharray={circumference}
            strokeDashoffset={strokeDashoffset}
            className="transition-all duration-700 ease-out"
          />
        </svg>

        {/* Center Text */}
        <div className="absolute top-10 text-center">
          <span className="text-3xl font-black text-white font-mono leading-none">
            {roundedScore}%
          </span>
          <span className="text-[10px] text-gray-400 font-semibold block uppercase mt-1">
            Overall Score
          </span>
        </div>
      </div>

      {/* Confidence Pill */}
      <div className="w-full bg-gray-900/80 border border-gray-700 rounded-lg p-3 flex items-center justify-between text-xs mt-2">
        <span className="text-gray-400 flex items-center gap-1.5 font-medium">
          <Sparkles className="h-3.5 w-3.5 text-amber-400" /> Model Confidence
        </span>
        <span className="font-mono font-bold text-amber-400">{roundedConf}%</span>
      </div>
    </div>
  );
}
