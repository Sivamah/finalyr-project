const STATUS_CONFIG = {
  Pending:     { label: 'Pending',     bg: 'bg-amber-100',   text: 'text-amber-700',   dot: 'bg-amber-500' },
  Accepted:    { label: 'Accepted',    bg: 'bg-blue-100',    text: 'text-blue-700',    dot: 'bg-blue-500' },
  In_Progress: { label: 'In Progress', bg: 'bg-purple-100',  text: 'text-purple-700',  dot: 'bg-purple-500' },
  Completed:   { label: 'Completed',   bg: 'bg-emerald-100', text: 'text-emerald-700', dot: 'bg-emerald-500' },
  Cancelled:   { label: 'Cancelled',   bg: 'bg-red-100',     text: 'text-red-700',     dot: 'bg-red-500' },
};

export default function StatusBadge({ status, size = 'md' }) {
  const cfg = STATUS_CONFIG[status] || STATUS_CONFIG.Pending;
  const textSize = size === 'sm' ? 'text-xs' : 'text-sm';

  return (
    <span className={`inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full font-medium ${cfg.bg} ${cfg.text} ${textSize}`}>
      <span className={`w-1.5 h-1.5 rounded-full ${cfg.dot} ${status === 'Pending' ? 'map-pin-pulse' : ''}`} />
      {cfg.label}
    </span>
  );
}
