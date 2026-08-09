import React, { useContext, useState } from 'react';
import { useNavigate, Navigate } from 'react-router-dom';
import { AuthContext } from '../context/AuthContext';
import { Cpu, Eye, EyeOff, ShieldCheck, Activity } from 'lucide-react';
import { motion } from 'framer-motion';
import toast from 'react-hot-toast';

export default function Login() {
  const { user, login } = useContext(AuthContext);
  const navigate = useNavigate();
  const [email, setEmail] = useState('admin@aiorch.com');
  const [password, setPassword] = useState('admin123');
  const [showPassword, setShowPassword] = useState(false);
  const [loading, setLoading] = useState(false);

  if (user) return <Navigate to="/dashboard" replace />;

  const handleSubmit = async (e) => {
    e.preventDefault();
    setLoading(true);
    try {
      await login(email, password);
      toast.success('Welcome, Operator');
      navigate('/dashboard');
    } catch (err) {
      toast.error(err.response?.data?.detail || 'Login failed');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen relative flex items-center justify-center p-6 overflow-hidden">
      {/* Ambient accents behind the glass */}
      <div className="absolute pointer-events-none top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2">
        <div className="w-[720px] h-[720px] rounded-full bg-brand-primary/15 blur-[140px] mix-blend-screen animate-aurora" />
        <div className="absolute inset-8 rounded-full bg-brand-accent/14 blur-[120px] mix-blend-screen animate-aurora" style={{ animationDelay: '4s' }} />
      </div>

      <motion.div
        initial={{ opacity: 0, y: 24, scale: 0.98 }}
        animate={{ opacity: 1, y: 0, scale: 1 }}
        transition={{ duration: 0.7, ease: [0.22, 1, 0.36, 1] }}
        className="relative w-full max-w-[420px]"
      >
        {/* Brand */}
        <div className="flex flex-col items-center text-center mb-9">
          <div className="relative mb-5">
            <div className="absolute inset-0 rounded-[22px] bg-gradient-to-br from-brand-primary/70 to-brand-accent/70 blur-lg opacity-70" />
            <div className="relative h-16 w-16 rounded-[22px] bg-gradient-to-br from-brand-primary to-brand-accent border border-white/25 flex items-center justify-center glass-reflect">
              <Cpu className="h-7 w-7 text-white drop-shadow-[0_2px_8px_rgba(0,0,0,0.4)]" />
            </div>
          </div>
          <h1 className="text-[26px] font-semibold text-white tracking-tight">A·DMFE</h1>
          <p className="mt-1.5 text-[12px] text-brand-text-muted uppercase tracking-[0.22em] font-semibold">
            Unified Mobility Platform
          </p>
          <div className="mt-4 inline-flex items-center gap-2 rounded-full border border-white/[0.08] bg-white/[0.03] px-3.5 py-1.5 backdrop-blur-md">
            <span className="relative flex h-1.5 w-1.5">
              <span className="absolute inline-flex h-full w-full rounded-full bg-brand-success opacity-60 animate-ping" />
              <span className="relative inline-flex rounded-full h-1.5 w-1.5 bg-brand-success" />
            </span>
            <span className="text-[11px] font-semibold text-brand-text-secondary tracking-wide">Adaptive engine online</span>
          </div>
        </div>

        {/* Glass form */}
        <div className="glass-panel-strong rounded-[28px] p-8 glass-reflect">
          <form onSubmit={handleSubmit} className="space-y-5">
            <div>
              <label className="block text-[12px] font-semibold text-brand-text-secondary mb-2">Email</label>
              <input
                type="email"
                required
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                className="input-glass"
                placeholder="operator@platform.ai"
              />
            </div>
            <div>
              <label className="block text-[12px] font-semibold text-brand-text-secondary mb-2">Password</label>
              <div className="relative">
                <input
                  type={showPassword ? 'text' : 'password'}
                  required
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  className="input-glass pr-11"
                  placeholder="••••••••"
                />
                <button
                  type="button"
                  onClick={() => setShowPassword((v) => !v)}
                  className="absolute right-3.5 top-1/2 -translate-y-1/2 text-brand-text-muted hover:text-white transition-colors"
                  aria-label="Toggle password visibility"
                >
                  {showPassword ? <EyeOff className="h-4 w-4" /> : <Eye className="h-4 w-4" />}
                </button>
              </div>
            </div>

            <button
              type="submit"
              disabled={loading}
              className="btn-primary w-full justify-center !py-3 mt-2"
            >
              {loading ? (
                <>
                  <span className="h-4 w-4 border-2 border-white/30 border-t-white rounded-full animate-spin" />
                  Connecting…
                </>
              ) : (
                'Enter Platform'
              )}
            </button>
          </form>

          <div className="mt-6 pt-6 border-t border-white/[0.06] flex items-center justify-center gap-2 text-brand-text-muted">
            <ShieldCheck className="h-3.5 w-3.5" />
            <span className="text-[11px] font-medium tracking-wide">Secure operator access · v1.0</span>
          </div>
        </div>

        <p className="text-center mt-7 flex items-center justify-center gap-2 text-[11px] text-brand-text-muted">
          <Activity className="h-3 w-3" />
          Adaptive Dynamic Feasibility Engine · Admin Console
        </p>
      </motion.div>
    </div>
  );
}