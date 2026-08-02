import React, { useRef } from 'react';
import { Download, Upload, RotateCcw, ShieldAlert, FileCode } from 'lucide-react';
import toast from 'react-hot-toast';

export default function BackupRestore({ onExport, onImport, onReset }) {
  const fileInputRef = useRef(null);

  const handleFileChange = (e) => {
    const file = e.target.files?.[0];
    if (!file) return;

    const reader = new FileReader();
    reader.onload = (event) => {
      try {
        const json = JSON.parse(event.target.result);
        if (!json.configurations) {
          toast.error('Invalid configuration JSON format');
          return;
        }
        onImport(json);
      } catch (err) {
        toast.error('Failed to parse JSON file');
      }
    };
    reader.readAsText(file);
    e.target.value = ''; // Reset input
  };

  return (
    <div className="bg-gray-800 border border-gray-700 rounded-xl p-6 shadow-sm space-y-6">
      <div className="border-b border-gray-700 pb-3">
        <h3 className="text-base font-bold text-white flex items-center gap-2">
          <FileCode className="h-5 w-5 text-indigo-400" />
          Backup, Restore & Factory Reset Utilities
        </h3>
        <p className="text-xs text-gray-400 mt-0.5">
          Export system configuration state to JSON, restore settings from backup, or reset parameters to factory defaults
        </p>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
        {/* Export Card */}
        <div className="bg-gray-900 border border-gray-700 rounded-xl p-5 flex flex-col justify-between space-y-4">
          <div>
            <div className="p-3 bg-indigo-500/10 border border-indigo-500/20 text-indigo-400 rounded-lg w-fit mb-3">
              <Download className="h-5 w-5" />
            </div>
            <h4 className="text-sm font-bold text-white">Export Configuration</h4>
            <p className="text-xs text-gray-400 mt-1">
              Download a complete JSON snapshot of all system, provider, vehicle, and AI rule configurations.
            </p>
          </div>
          <button
            type="button"
            onClick={onExport}
            className="w-full flex items-center justify-center gap-2 px-4 py-2 bg-indigo-600 hover:bg-indigo-700 text-white font-bold text-xs rounded-lg transition-colors shadow-sm"
          >
            <Download className="h-4 w-4" /> Download JSON Backup
          </button>
        </div>

        {/* Import Card */}
        <div className="bg-gray-900 border border-gray-700 rounded-xl p-5 flex flex-col justify-between space-y-4">
          <div>
            <div className="p-3 bg-blue-500/10 border border-blue-500/20 text-blue-400 rounded-lg w-fit mb-3">
              <Upload className="h-5 w-5" />
            </div>
            <h4 className="text-sm font-bold text-white">Import Configuration</h4>
            <p className="text-xs text-gray-400 mt-1">
              Upload a previously exported `.json` configuration file to restore parameters.
            </p>
          </div>
          <div>
            <input
              type="file"
              accept=".json"
              ref={fileInputRef}
              onChange={handleFileChange}
              className="hidden"
            />
            <button
              type="button"
              onClick={() => fileInputRef.current?.click()}
              className="w-full flex items-center justify-center gap-2 px-4 py-2 bg-blue-600 hover:bg-blue-700 text-white font-bold text-xs rounded-lg transition-colors shadow-sm"
            >
              <Upload className="h-4 w-4" /> Upload JSON File
            </button>
          </div>
        </div>

        {/* Reset to Factory Defaults Card */}
        <div className="bg-gray-900 border border-red-500/30 rounded-xl p-5 flex flex-col justify-between space-y-4">
          <div>
            <div className="p-3 bg-red-500/10 border border-red-500/20 text-red-400 rounded-lg w-fit mb-3">
              <RotateCcw className="h-5 w-5" />
            </div>
            <h4 className="text-sm font-bold text-white">Reset to Factory Defaults</h4>
            <p className="text-xs text-gray-400 mt-1">
              Wipe custom settings and restore original platform factory parameters.
            </p>
          </div>
          <button
            type="button"
            onClick={onReset}
            className="w-full flex items-center justify-center gap-2 px-4 py-2 bg-red-600/20 hover:bg-red-600 border border-red-500/40 text-red-300 hover:text-white font-bold text-xs rounded-lg transition-colors"
          >
            <ShieldAlert className="h-4 w-4" /> Reset Factory Defaults
          </button>
        </div>
      </div>
    </div>
  );
}
