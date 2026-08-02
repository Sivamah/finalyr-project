import React, { useEffect, useRef } from 'react';

/**
 * Animated SVG arc gauge showing compatibility score 0–100%.
 * Color: red < 50, amber 50–70, green >= 70.
 */
export default function CompatibilityGauge({ score = 0, size = 120 }) {
  const clampedScore = Math.max(0, Math.min(100, score));

  // Arc geometry
  const cx = size / 2;
  const cy = size / 2;
  const radius = (size / 2) - 10;
  const strokeWidth = size * 0.095;
  const circumference = Math.PI * radius;           // half-circle
  const dashOffset = circumference * (1 - clampedScore / 100);

  // Color thresholds
  let color, textColor;
  if (clampedScore >= 70) {
    color = '#22c55e'; textColor = 'text-green-400';
  } else if (clampedScore >= 50) {
    color = '#f59e0b'; textColor = 'text-amber-400';
  } else {
    color = '#ef4444'; textColor = 'text-red-400';
  }

  // Decision label
  const label = clampedScore >= 70 ? 'Compatible' : clampedScore >= 50 ? 'Marginal' : 'Incompatible';

  return (
    <div className="flex flex-col items-center gap-1">
      <svg
        width={size}
        height={size / 2 + 10}
        viewBox={`0 0 ${size} ${size / 2 + 10}`}
        className="overflow-visible"
      >
        {/* Track arc */}
        <path
          d={`M ${cx - radius} ${cy} A ${radius} ${radius} 0 0 1 ${cx + radius} ${cy}`}
          fill="none"
          stroke="#374151"
          strokeWidth={strokeWidth}
          strokeLinecap="round"
        />
        {/* Value arc */}
        <path
          d={`M ${cx - radius} ${cy} A ${radius} ${radius} 0 0 1 ${cx + radius} ${cy}`}
          fill="none"
          stroke={color}
          strokeWidth={strokeWidth}
          strokeLinecap="round"
          strokeDasharray={circumference}
          strokeDashoffset={dashOffset}
          style={{ transition: 'stroke-dashoffset 0.8s ease' }}
        />
        {/* Score text */}
        <text
          x={cx}
          y={cy - 2}
          textAnchor="middle"
          dominantBaseline="auto"
          fontSize={size * 0.22}
          fontWeight="700"
          fontFamily="monospace"
          fill={color}
        >
          {clampedScore.toFixed(1)}%
        </text>
      </svg>
      <span className={`text-[11px] font-bold ${textColor}`}>{label}</span>
    </div>
  );
}
