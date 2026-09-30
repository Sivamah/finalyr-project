/**
 * Indian Rupee (INR) currency formatting utility.
 * Formats numerical values with standard Indian number grouping and ₹ symbol.
 * Example: 155.24 -> ₹155.24, 1250.5 -> ₹1,250.50, 12500 -> ₹12,500.00
 */
export function formatINR(val) {
  if (val === null || val === undefined || isNaN(val)) return '—';
  const num = Number(val);
  return '₹' + num.toLocaleString('en-IN', {
    minimumFractionDigits: 2,
    maximumFractionDigits: 2,
  });
}
