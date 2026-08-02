import React, { useState } from 'react';
import { Download, FileSpreadsheet, FileText, Printer, CheckCircle, X } from 'lucide-react';
import toast from 'react-hot-toast';

export default function ReportExport({ analyticsData = {}, filters = {} }) {
  const [modalOpen, setModalOpen] = useState(false);

  const timestamp = analyticsData.timestamp
    ? new Date(analyticsData.timestamp).toLocaleString()
    : new Date().toLocaleString();

  const kpi = analyticsData.kpi || {};
  const reqAnalytics = analyticsData.request_analytics || {};
  const providerStats = analyticsData.provider_analytics?.provider_stats || [];

  // 1. CSV Export
  const handleExportCSV = () => {
    try {
      let csvContent = "data:text/csv;charset=utf-8,";
      csvContent += `AI ORCHESTRATION PLATFORM - OPERATIONAL ANALYTICS REPORT\n`;
      csvContent += `Report Generated At,${timestamp}\n`;
      csvContent += `Filter Preset,${filters.preset || 'All'}\n`;
      csvContent += `Filter Type,${filters.requestType || 'All'}\n`;
      csvContent += `Filter Status,${filters.status || 'All'}\n\n`;

      csvContent += `--- SUMMARY KPIS ---\n`;
      csvContent += `Metric,Value\n`;
      csvContent += `Total Requests Generated,${kpi.total_requests || 0}\n`;
      csvContent += `Active Requests,${kpi.active_requests || 0}\n`;
      csvContent += `Pending Requests,${kpi.pending_requests || 0}\n`;
      csvContent += `Completed Requests,${kpi.completed_requests || 0}\n`;
      csvContent += `Requests Per Minute (RPM),${kpi.requests_per_minute || 0}\n`;
      csvContent += `Avg Processing Time (sec),${kpi.avg_processing_time_sec || 0}\n`;
      csvContent += `Total Providers,${kpi.total_providers || 0}\n`;
      csvContent += `Active Providers,${kpi.active_providers || 0}\n\n`;

      csvContent += `--- SERVICE ANALYTICS ---\n`;
      csvContent += `Ride Requests,${reqAnalytics.total_ride_requests || 0}\n`;
      csvContent += `Food Requests,${reqAnalytics.total_food_requests || 0}\n`;
      csvContent += `Parcel Requests,${reqAnalytics.total_parcel_requests || 0}\n`;
      csvContent += `Avg Estimated Distance (km),${reqAnalytics.avg_estimated_distance_km || 0}\n`;
      csvContent += `Avg Travel Time (min),${reqAnalytics.avg_estimated_travel_time_min || 0}\n`;
      csvContent += `Completion Rate (%),${reqAnalytics.completion_rate_pct || 0}%\n`;
      csvContent += `Pending Rate (%),${reqAnalytics.pending_rate_pct || 0}%\n\n`;

      csvContent += `--- PROVIDER PERFORMANCE ---\n`;
      csvContent += `Provider ID,Provider Name,Total Requests,Completed,Pending,Utilization Rate (%),Avg Distance (km)\n`;
      providerStats.forEach((p) => {
        csvContent += `${p.provider_id || ''},"${p.provider_name}",${p.total_requests},${p.completed_requests},${p.pending_requests},${p.utilization_pct}%,${p.avg_distance_km}\n`;
      });

      const encodedUri = encodeURI(csvContent);
      const link = document.createElement("a");
      link.setAttribute("href", encodedUri);
      link.setAttribute("download", `analytics_report_${Date.now()}.csv`);
      document.body.appendChild(link);
      link.click();
      document.body.removeChild(link);

      toast.success("CSV Report Exported Successfully");
      setModalOpen(false);
    } catch (err) {
      toast.error("Failed to export CSV report");
    }
  };

  // 2. Excel Export (.xlsx / XML formatted)
  const handleExportExcel = () => {
    try {
      let excelContent = `
        <html xmlns:o="urn:schemas-microsoft-com:office:office" xmlns:x="urn:schemas-microsoft-com:office:excel" xmlns="http://www.w3.org/TR/REC-html40">
        <head><meta charset="UTF-8"><!--[if gte mso 9]><xml><x:ExcelWorkbook><x:ExcelWorksheets><x:ExcelWorksheet><x:Name>Analytics Report</x:Name><x:WorksheetOptions><x:DisplayGridlines/></x:WorksheetOptions></x:ExcelWorksheet></x:ExcelWorksheets></x:ExcelWorkbook></xml><![endif]--></head>
        <body style="font-family: Arial, sans-serif;">
          <h2>AI Orchestration Platform — Analytics & Operational Report</h2>
          <p><b>Generated At:</b> ${timestamp}</p>
          <hr/>
          <h3>Summary KPIs</h3>
          <table border="1" cellspacing="0" cellpadding="5">
            <tr style="background-color: #4f46e5; color: #ffffff;"><th>Metric</th><th>Value</th></tr>
            <tr><td>Total Requests Generated</td><td>${kpi.total_requests || 0}</td></tr>
            <tr><td>Active Requests</td><td>${kpi.active_requests || 0}</td></tr>
            <tr><td>Pending Requests</td><td>${kpi.pending_requests || 0}</td></tr>
            <tr><td>Completed Requests</td><td>${kpi.completed_requests || 0}</td></tr>
            <tr><td>Requests Per Minute (RPM)</td><td>${kpi.requests_per_minute || 0}</td></tr>
            <tr><td>Avg Processing Time (sec)</td><td>${kpi.avg_processing_time_sec || 0}</td></tr>
            <tr><td>Completion Rate</td><td>${reqAnalytics.completion_rate_pct || 0}%</td></tr>
          </table>

          <h3>Provider Performance Summary</h3>
          <table border="1" cellspacing="0" cellpadding="5">
            <tr style="background-color: #ea580c; color: #ffffff;">
              <th>Provider Name</th>
              <th>Total Requests</th>
              <th>Completed</th>
              <th>Pending</th>
              <th>Utilization Rate</th>
              <th>Avg Distance (km)</th>
            </tr>
            ${providerStats.map(p => `
              <tr>
                <td>${p.provider_name}</td>
                <td>${p.total_requests}</td>
                <td>${p.completed_requests}</td>
                <td>${p.pending_requests}</td>
                <td>${p.utilization_pct}%</td>
                <td>${p.avg_distance_km}</td>
              </tr>
            `).join('')}
          </table>
        </body>
        </html>
      `;

      const blob = new Blob([excelContent], { type: 'application/vnd.ms-excel;charset=utf-8' });
      const link = document.createElement("a");
      link.href = URL.createObjectURL(blob);
      link.download = `analytics_report_${Date.now()}.xlsx`;
      document.body.appendChild(link);
      link.click();
      document.body.removeChild(link);

      toast.success("Excel Report (.xlsx) Exported Successfully");
      setModalOpen(false);
    } catch (err) {
      toast.error("Failed to export Excel report");
    }
  };

  // 3. PDF Export (Print / Printable Window)
  const handleExportPDF = () => {
    try {
      const printWindow = window.open('', '_blank');
      if (!printWindow) {
        toast.error("Please allow popups to generate PDF report");
        return;
      }

      printWindow.document.write(`
        <!DOCTYPE html>
        <html>
        <head>
          <title>AI Orchestration Analytics Executive Report</title>
          <style>
            body { font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; color: #111827; padding: 30px; line-height: 1.5; }
            .header { border-bottom: 2px solid #4f46e5; padding-bottom: 15px; margin-bottom: 20px; display: flex; justify-content: space-between; align-items: center; }
            .title { font-size: 24px; font-weight: bold; color: #1e1b4b; margin: 0; }
            .subtitle { font-size: 13px; color: #6b7280; margin-top: 4px; }
            .badge { background: #e0e7ff; color: #3730a3; padding: 4px 10px; border-radius: 9999px; font-size: 12px; font-weight: bold; }
            .grid { display: grid; grid-template-columns: repeat(4, 1fr); gap: 15px; margin-bottom: 25px; }
            .card { background: #f9fafb; border: 1px solid #e5e7eb; border-radius: 8px; padding: 12px; }
            .card-label { font-size: 11px; color: #6b7280; font-weight: 600; text-transform: uppercase; }
            .card-value { font-size: 20px; font-weight: bold; color: #111827; margin-top: 4px; }
            table { width: 100%; border-collapse: collapse; margin-top: 15px; margin-bottom: 25px; }
            th, td { border: 1px solid #e5e7eb; padding: 10px; text-align: left; font-size: 13px; }
            th { background-color: #f3f4f6; color: #374151; font-weight: 600; }
            .footer { border-top: 1px solid #e5e7eb; padding-top: 15px; font-size: 11px; color: #9ca3af; text-align: center; }
          </style>
        </head>
        <body>
          <div class="header">
            <div>
              <h1 class="title">AI Orchestration Platform</h1>
              <div class="subtitle">Operational Analytics & System Performance Report</div>
            </div>
            <div class="badge">Timestamp: ${timestamp}</div>
          </div>

          <h3>System Key Performance Indicators</h3>
          <div class="grid">
            <div class="card"><div class="card-label">Total Requests</div><div class="card-value">${kpi.total_requests || 0}</div></div>
            <div class="card"><div class="card-label">Active / Pending</div><div class="card-value">${kpi.active_requests || 0}</div></div>
            <div class="card"><div class="card-label">Completed</div><div class="card-value">${kpi.completed_requests || 0}</div></div>
            <div class="card"><div class="card-label">Requests / Min</div><div class="card-value">${kpi.requests_per_minute || 0}</div></div>
          </div>

          <h3>Service Breakdown</h3>
          <div class="grid">
            <div class="card"><div class="card-label">Ride Requests</div><div class="card-value">${reqAnalytics.total_ride_requests || 0}</div></div>
            <div class="card"><div class="card-label">Food Requests</div><div class="card-value">${reqAnalytics.total_food_requests || 0}</div></div>
            <div class="card"><div class="card-label">Parcel Requests</div><div class="card-value">${reqAnalytics.total_parcel_requests || 0}</div></div>
            <div class="card"><div class="card-label">Completion Rate</div><div class="card-value">${reqAnalytics.completion_rate_pct || 0}%</div></div>
          </div>

          <h3>Provider Performance Comparison</h3>
          <table>
            <thead>
              <tr>
                <th>Provider Name</th>
                <th>Total Requests</th>
                <th>Completed</th>
                <th>Pending</th>
                <th>Utilization Rate</th>
                <th>Avg Distance</th>
              </tr>
            </thead>
            <tbody>
              ${providerStats.map(p => `
                <tr>
                  <td><b>${p.provider_name}</b></td>
                  <td>${p.total_requests}</td>
                  <td>${p.completed_requests}</td>
                  <td>${p.pending_requests}</td>
                  <td>${p.utilization_pct}%</td>
                  <td>${p.avg_distance_km} km</td>
                </tr>
              `).join('')}
            </tbody>
          </table>

          <div class="footer">
            Report generated by AI Orchestration Admin Dashboard • ${timestamp}
          </div>

          <script>
            window.onload = function() {
              window.print();
            }
          </script>
        </body>
        </html>
      `);
      printWindow.document.close();
      toast.success("Printable PDF Report Generated");
      setModalOpen(false);
    } catch (err) {
      toast.error("Failed to generate PDF report");
    }
  };

  return (
    <>
      {/* Export Button */}
      <button
        onClick={() => setModalOpen(true)}
        className="flex items-center gap-2 px-4 py-2 bg-indigo-600 hover:bg-indigo-700 text-white font-medium rounded-lg text-sm transition-colors shadow-sm"
      >
        <Download className="h-4 w-4" />
        Export Report
      </button>

      {/* Modal */}
      {modalOpen && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 backdrop-blur-sm p-4">
          <div className="bg-gray-800 border border-gray-700 rounded-xl w-full max-w-md p-6 shadow-2xl relative animate-in fade-in zoom-in duration-200">
            {/* Close Button */}
            <button
              onClick={() => setModalOpen(false)}
              className="absolute top-4 right-4 text-gray-400 hover:text-white"
            >
              <X className="h-5 w-5" />
            </button>

            <div className="mb-6">
              <h3 className="text-lg font-bold text-white flex items-center gap-2">
                <Download className="h-5 w-5 text-indigo-400" />
                Export Operational Report
              </h3>
              <p className="text-xs text-gray-400 mt-1">
                Select your preferred format to download summary KPIs, statistics, and provider performance data.
              </p>
            </div>

            {/* Export Format Options */}
            <div className="space-y-3 mb-6">
              {/* CSV Option */}
              <button
                onClick={handleExportCSV}
                className="w-full flex items-center justify-between p-4 bg-gray-900/80 hover:bg-gray-700/60 border border-gray-700 rounded-xl transition-all text-left group"
              >
                <div className="flex items-center gap-3">
                  <div className="p-2.5 bg-blue-500/10 rounded-lg text-blue-400 group-hover:scale-105 transition-transform">
                    <FileText className="h-5 w-5" />
                  </div>
                  <div>
                    <p className="text-sm font-bold text-white">CSV Format (.csv)</p>
                    <p className="text-xs text-gray-400">Raw tabular data suitable for custom data tools</p>
                  </div>
                </div>
                <Download className="h-4 w-4 text-gray-400 group-hover:text-blue-400 transition-colors" />
              </button>

              {/* Excel Option */}
              <button
                onClick={handleExportExcel}
                className="w-full flex items-center justify-between p-4 bg-gray-900/80 hover:bg-gray-700/60 border border-gray-700 rounded-xl transition-all text-left group"
              >
                <div className="flex items-center gap-3">
                  <div className="p-2.5 bg-emerald-500/10 rounded-lg text-emerald-400 group-hover:scale-105 transition-transform">
                    <FileSpreadsheet className="h-5 w-5" />
                  </div>
                  <div>
                    <p className="text-sm font-bold text-white">Excel Document (.xlsx)</p>
                    <p className="text-xs text-gray-400">Formatted tables with styled headers for spreadsheet analysis</p>
                  </div>
                </div>
                <Download className="h-4 w-4 text-gray-400 group-hover:text-emerald-400 transition-colors" />
              </button>

              {/* PDF Option */}
              <button
                onClick={handleExportPDF}
                className="w-full flex items-center justify-between p-4 bg-gray-900/80 hover:bg-gray-700/60 border border-gray-700 rounded-xl transition-all text-left group"
              >
                <div className="flex items-center gap-3">
                  <div className="p-2.5 bg-purple-500/10 rounded-lg text-purple-400 group-hover:scale-105 transition-transform">
                    <Printer className="h-5 w-5" />
                  </div>
                  <div>
                    <p className="text-sm font-bold text-white">PDF Executive Document (.pdf)</p>
                    <p className="text-xs text-gray-400">Clean printable layout with executive summary & timestamp</p>
                  </div>
                </div>
                <Printer className="h-4 w-4 text-gray-400 group-hover:text-purple-400 transition-colors" />
              </button>
            </div>

            <div className="text-[11px] text-gray-500 text-center">
              Timestamp: {timestamp}
            </div>
          </div>
        </div>
      )}
    </>
  );
}
