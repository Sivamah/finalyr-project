import React from 'react';
import { Clock, CheckCircle2, Circle, ArrowDown } from 'lucide-react';

export default function ExplanationTimeline({ timeline = [] }) {
  const defaultEvents = [
    { title: 'Simulation Created', timestamp: '19:40:00', status: 'completed', description: 'Request initiated by generator' },
    { title: 'Request Queued', timestamp: '19:40:02', status: 'completed', description: 'Assigned to active queue' },
    { title: 'Analysis Completed', timestamp: '19:40:05', status: 'completed', description: 'Feature vector scoring performed' },
    { title: 'Decision Generated', timestamp: '19:40:06', status: 'completed', description: 'Recommendation finalized' },
  ];

  const events = timeline.length > 0 ? timeline : defaultEvents;

  return (
    <div className="bg-gray-800 border border-gray-700 rounded-xl p-5 shadow-sm">
      <div className="flex items-center justify-between border-b border-gray-700 pb-3 mb-4">
        <h3 className="text-sm font-bold text-white flex items-center gap-2">
          <Clock className="h-4 w-4 text-yellow-400" />
          Explanation Event Timeline
        </h3>
        <span className="text-xs text-gray-400">Audit Trace</span>
      </div>

      <div className="relative pl-6 space-y-6 before:absolute before:left-2.5 before:top-2 before:bottom-2 before:w-0.5 before:bg-gray-700">
        {events.map((event, idx) => {
          const isLast = idx === events.length - 1;
          return (
            <div key={idx} className="relative flex items-start justify-between gap-4">
              {/* Dot Icon */}
              <div className={`absolute -left-6 top-0.5 w-5 h-5 rounded-full flex items-center justify-center border ${
                isLast
                  ? 'bg-indigo-600 border-indigo-400 text-white'
                  : 'bg-gray-900 border-green-500 text-green-400'
              }`}>
                {isLast ? <Circle className="h-2 w-2 fill-current" /> : <CheckCircle2 className="h-3 w-3" />}
              </div>

              <div>
                <p className={`text-sm font-bold ${isLast ? 'text-indigo-400' : 'text-white'}`}>
                  {event.title}
                </p>
                {event.description && (
                  <p className="text-xs text-gray-400 mt-0.5">{event.description}</p>
                )}
              </div>

              <span className="text-xs font-mono text-gray-400 shrink-0 bg-gray-900 px-2 py-0.5 rounded border border-gray-700">
                {event.timestamp}
              </span>
            </div>
          );
        })}
      </div>
    </div>
  );
}
