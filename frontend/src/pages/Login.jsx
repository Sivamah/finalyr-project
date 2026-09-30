import React, { useContext, useState } from 'react';
import { useNavigate, Navigate } from 'react-router-dom';
import { AuthContext } from '../context/AuthContext';
import {
  User, Lock, Eye, EyeOff, ArrowRight, ShieldCheck,
  Users, Cpu, TrendingUp
} from 'lucide-react';
import { motion } from 'framer-motion';
import toast from 'react-hot-toast';

export default function Login() {
  const { user, login } = useContext(AuthContext);
  const navigate = useNavigate();
  const [email, setEmail] = useState('admin@aiorch.com');
  const [password, setPassword] = useState('admin123');
  const [showPassword, setShowPassword] = useState(false);
  const [rememberMe, setRememberMe] = useState(true);
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
    <div className="min-h-screen relative flex items-center justify-center p-4 sm:p-6 lg:p-12 overflow-hidden bg-[#050B17] text-white">
      {/* ── Background: Deep Atmosphere & Glowing Telemetry Network ─────── */}
      <div className="absolute inset-0 pointer-events-none overflow-hidden select-none" aria-hidden="true">
        {/* Soft radial blue and cyan ambient glows */}
        <div className="absolute top-0 left-1/4 w-[800px] h-[600px] bg-gradient-to-br from-[#1677FF]/20 via-[#00F0FF]/10 to-transparent blur-[140px] rounded-full mix-blend-screen" />
        <div className="absolute bottom-0 right-1/4 w-[700px] h-[500px] bg-gradient-to-tl from-[#7C3AED]/15 via-[#1677FF]/10 to-transparent blur-[130px] rounded-full mix-blend-screen" />
        
        {/* Horizon twilight gradient */}
        <div className="absolute inset-x-0 bottom-0 h-[45%] bg-gradient-to-t from-[#02050E] via-[#071329]/80 to-transparent" />

        {/* Abstract Vector Map & Route Telemetry Layer */}
        <svg
          className="absolute inset-0 w-full h-full opacity-40 md:opacity-50"
          xmlns="http://www.w3.org/2000/svg"
        >
          <defs>
            <linearGradient id="routeGlow1" x1="0%" y1="0%" x2="100%" y2="100%">
              <stop offset="0%" stopColor="#00F0FF" stopOpacity="0.8" />
              <stop offset="50%" stopColor="#3B82F6" stopOpacity="0.9" />
              <stop offset="100%" stopColor="#10B981" stopOpacity="0.8" />
            </linearGradient>
            <linearGradient id="routeGlow2" x1="0%" y1="100%" x2="100%" y2="0%">
              <stop offset="0%" stopColor="#3B82F6" stopOpacity="0.6" />
              <stop offset="70%" stopColor="#A855F7" stopOpacity="0.8" />
              <stop offset="100%" stopColor="#00F0FF" stopOpacity="0.7" />
            </linearGradient>
            <filter id="glowFilter" x="-30%" y="-30%" width="160%" height="160%">
              <feGaussianBlur stdDeviation="4" result="blur" />
              <feMerge>
                <feMergeNode in="blur" />
                <feMergeNode in="SourceGraphic" />
              </feMerge>
            </filter>
          </defs>

          {/* Secondary road grid traces */}
          <path
            d="M 50 180 Q 280 260 520 200 T 950 310 T 1400 240"
            fill="none"
            stroke="rgba(255,255,255,0.06)"
            strokeWidth="1.5"
            strokeDasharray="4 6"
          />
          <path
            d="M 120 400 Q 420 320 740 450 T 1200 420"
            fill="none"
            stroke="rgba(255,255,255,0.05)"
            strokeWidth="1.5"
          />
          <path
            d="M 200 120 L 380 340 L 600 280 L 820 490"
            fill="none"
            stroke="rgba(255,255,255,0.04)"
            strokeWidth="1.2"
          />

          {/* Primary Glowing Arterial Routes */}
          <path
            d="M 80 520 C 260 480, 390 320, 520 260 S 780 180, 920 120"
            fill="none"
            stroke="url(#routeGlow1)"
            strokeWidth="2.5"
            filter="url(#glowFilter)"
          />
          <path
            d="M 320 620 C 440 510, 560 410, 680 370 S 960 430, 1180 340"
            fill="none"
            stroke="url(#routeGlow2)"
            strokeWidth="2"
            filter="url(#glowFilter)"
          />

          {/* Map Nodes & Telemetry Pins */}
          {/* Node 1: North */}
          <circle cx="920" cy="120" r="4" fill="#00F0FF" />
          <circle cx="920" cy="120" r="10" fill="none" stroke="#00F0FF" strokeOpacity="0.4" strokeWidth="1" />
          {/* Node 2: Central East */}
          <circle cx="780" cy="180" r="3.5" fill="#38BDF8" />
          {/* Node 3: Coimbatore Hub */}
          <circle cx="680" cy="370" r="5" fill="#A855F7" filter="url(#glowFilter)" />
          <circle cx="680" cy="370" r="14" fill="none" stroke="#A855F7" strokeOpacity="0.3" strokeWidth="1.5" />
          <text x="698" y="374" fill="rgba(255,255,255,0.75)" fontSize="11" fontFamily="sans-serif" fontWeight="500" letterSpacing="0.05em">
            Coimbatore
          </text>
          {/* Node 4: West Waypoint */}
          <circle cx="520" cy="260" r="4" fill="#10B981" />
          <circle cx="520" cy="260" r="11" fill="none" stroke="#10B981" strokeOpacity="0.4" strokeWidth="1" />
          {/* Node 5: Highway Hub */}
          <circle cx="390" cy="320" r="3.5" fill="#F59E0B" />
          {/* Node 6: South Corridor */}
          <circle cx="440" cy="510" r="4" fill="#00F0FF" />
          <circle cx="440" cy="510" r="12" fill="none" stroke="#00F0FF" strokeOpacity="0.3" strokeWidth="1" />
        </svg>

        {/* Lower Roadway / Perspective Highway Trails */}
        <div className="absolute inset-x-0 bottom-0 h-44 overflow-hidden pointer-events-none">
          <svg className="w-full h-full" preserveAspectRatio="none" viewBox="0 0 1440 180" xmlns="http://www.w3.org/2000/svg">
            {/* Road ribbon */}
            <path d="M 0 180 Q 420 150 780 160 T 1440 175 L 1440 180 L 0 180 Z" fill="rgba(6, 14, 30, 0.9)" />
            {/* Illuminated highway guide lines */}
            <path d="M 0 170 Q 420 142 800 152 T 1440 168" fill="none" stroke="#00F0FF" strokeWidth="2.5" opacity="0.8" filter="drop-shadow(0 0 8px rgba(0,240,255,0.7))" />
            <path d="M 0 164 Q 400 138 780 148 T 1440 162" fill="none" stroke="#3B82F6" strokeWidth="1.2" opacity="0.6" strokeDasharray="16 12" />
            <path d="M 0 178 Q 440 154 820 162 T 1440 178" fill="none" stroke="#00F0FF" strokeWidth="1" opacity="0.4" />
          </svg>
        </div>
      </div>

      {/* ── Main Two-Column Container ───────────────────────────────────── */}
      <div className="relative z-10 w-full max-w-[1240px] mx-auto grid grid-cols-1 lg:grid-cols-12 gap-8 lg:gap-14 items-center">
        
        {/* ── LEFT COLUMN: Brand Identity & Subsystem Highlights ─────────── */}
        <motion.div
          initial={{ opacity: 0, x: -24 }}
          animate={{ opacity: 1, x: 0 }}
          transition={{ duration: 0.7, ease: [0.22, 1, 0.36, 1] }}
          className="lg:col-span-6 flex flex-col items-center lg:items-start text-center lg:text-left pt-2 lg:pt-0"
        >
          {/* Custom A-DMFE Heart + Vehicle Glow Emblem */}
          <div className="relative mb-5 group">
            <div className="absolute -inset-1.5 rounded-[26px] bg-gradient-to-r from-[#00F0FF] to-[#3B82F6] opacity-70 blur-md group-hover:opacity-100 transition-opacity duration-500" />
            <div className="relative h-20 w-20 rounded-[22px] bg-gradient-to-br from-[#09152D] via-[#0E2046] to-[#07132B] border border-[#00F0FF]/50 flex items-center justify-center shadow-[0_10px_30px_rgba(0,240,255,0.25)]">
              {/* Stylized SVG emblem matching the approved heart + mobility design */}
              <svg className="h-11 w-11" viewBox="0 0 48 48" fill="none" xmlns="http://www.w3.org/2000/svg">
                {/* Heart perimeter */}
                <path
                  d="M 24 39 C 14 30 7 24 7 16.5 C 7 11.5 10.5 8 15.5 8 C 19 8 22 10 24 12.5 C 26 10 29 8 32.5 8 C 37.5 8 41 11.5 41 16.5 C 41 20 38.5 24 35 27.5"
                  stroke="#00F0FF"
                  strokeWidth="2.4"
                  strokeLinecap="round"
                  strokeLinejoin="round"
                />
                {/* People silhouettes inside heart */}
                <circle cx="16" cy="18" r="2.2" fill="#00F0FF" />
                <path d="M 12 26 C 12 23 14 22 16 22 C 18 22 20 23 20 26" stroke="#00F0FF" strokeWidth="1.8" strokeLinecap="round" />
                <circle cx="23" cy="17" r="2.2" fill="#38BDF8" />
                <path d="M 19.5 25 C 19.5 22.2 21.2 21.2 23 21.2 C 24.8 21.2 26.5 22.2 26.5 25" stroke="#38BDF8" strokeWidth="1.8" strokeLinecap="round" />
                {/* Integrated delivery van on bottom right */}
                <path
                  d="M 28 32 L 39 32 L 41 35 L 41 39 L 28 39 Z"
                  fill="#00F0FF"
                  fillOpacity="0.25"
                  stroke="#00F0FF"
                  strokeWidth="1.8"
                  strokeLinejoin="round"
                />
                <circle cx="31.5" cy="39" r="1.8" fill="#00F0FF" />
                <circle cx="37.5" cy="39" r="1.8" fill="#00F0FF" />
                <path d="M 37 32 L 37 36 L 41 36" stroke="#00F0FF" strokeWidth="1.4" />
              </svg>
            </div>
          </div>

          {/* Primary Branding */}
          <h1 className="text-3xl sm:text-4xl lg:text-[42px] font-display font-extrabold tracking-tight text-white leading-tight">
            A-DMFE
          </h1>
          <p className="mt-2 text-base sm:text-lg font-semibold text-transparent bg-clip-text bg-gradient-to-r from-white via-cyan-100 to-sky-300 max-w-md">
            AI-Powered Unified Mobility &amp; Delivery Platform
          </p>
          <p className="mt-1 text-xs sm:text-sm font-medium text-cyan-300/80 tracking-wide">
            People &bull; Food &bull; Parcels &nbsp;|&nbsp; Smarter Cities
          </p>

          {/* Engine Status Pill */}
          <div className="mt-4 inline-flex items-center gap-2 rounded-full border border-emerald-500/30 bg-emerald-500/10 px-3.5 py-1.5 backdrop-blur-md">
            <span className="relative flex h-2 w-2">
              <span className="absolute inline-flex h-full w-full rounded-full bg-emerald-400 opacity-75 animate-ping" />
              <span className="relative inline-flex rounded-full h-2 w-2 bg-emerald-400 shadow-[0_0_8px_rgba(52,211,153,0.9)]" />
            </span>
            <span className="text-[11.5px] font-semibold text-emerald-300 tracking-wide">Adaptive engine online</span>
          </div>

          {/* 3 Grounded Supporting Pillars */}
          <div className="mt-8 grid grid-cols-3 gap-3 sm:gap-4 w-full max-w-[480px]">
            {/* Pillar 1 */}
            <div className="flex flex-col items-center p-3 rounded-2xl bg-[#09152B]/60 border border-white/[0.08] backdrop-blur-md transition-transform hover:-translate-y-0.5">
              <div className="h-9 w-9 rounded-xl bg-blue-500/15 border border-blue-400/30 flex items-center justify-center text-blue-400 mb-2 shadow-[0_0_12px_rgba(59,130,246,0.3)]">
                <Users className="h-4 w-4" />
              </div>
              <span className="text-[11px] font-semibold text-white/90 text-center leading-tight">
                Unified Mobility Services
              </span>
            </div>

            {/* Pillar 2 */}
            <div className="flex flex-col items-center p-3 rounded-2xl bg-[#09152B]/60 border border-white/[0.08] backdrop-blur-md transition-transform hover:-translate-y-0.5">
              <div className="h-9 w-9 rounded-xl bg-purple-500/15 border border-purple-400/30 flex items-center justify-center text-purple-300 mb-2 shadow-[0_0_12px_rgba(168,85,247,0.3)]">
                <Cpu className="h-4 w-4" />
              </div>
              <span className="text-[11px] font-semibold text-white/90 text-center leading-tight">
                AI-driven Optimization
              </span>
            </div>

            {/* Pillar 3 */}
            <div className="flex flex-col items-center p-3 rounded-2xl bg-[#09152B]/60 border border-white/[0.08] backdrop-blur-md transition-transform hover:-translate-y-0.5">
              <div className="h-9 w-9 rounded-xl bg-emerald-500/15 border border-emerald-400/30 flex items-center justify-center text-emerald-400 mb-2 shadow-[0_0_12px_rgba(16,185,129,0.3)]">
                <TrendingUp className="h-4 w-4" />
              </div>
              <span className="text-[11px] font-semibold text-white/90 text-center leading-tight">
                Efficient Fleet Operations
              </span>
            </div>
          </div>
        </motion.div>

        {/* ── RIGHT COLUMN: Centered Frosted-Glass Login Card ────────────── */}
        <motion.div
          initial={{ opacity: 0, x: 24, scale: 0.98 }}
          animate={{ opacity: 1, x: 0, scale: 1 }}
          transition={{ duration: 0.7, ease: [0.22, 1, 0.36, 1] }}
          className="lg:col-span-6 flex justify-center lg:justify-end"
        >
          <div className="relative w-full max-w-[450px]">
            {/* Luminous aura behind login card */}
            <div className="absolute -inset-1 rounded-[32px] bg-gradient-to-br from-[#00F0FF]/30 via-[#1677FF]/20 to-[#7C3AED]/20 blur-xl opacity-60" />

            {/* Frosted Glass Container */}
            <div className="relative rounded-[28px] bg-[#071329]/80 backdrop-blur-2xl border border-white/[0.12] p-7 sm:p-9 shadow-[0_24px_64px_rgba(0,0,0,0.65),0_0_35px_rgba(0,240,255,0.12)]">
              {/* Header */}
              <div className="mb-7 text-center">
                <h2 className="text-2xl sm:text-[28px] font-bold text-white tracking-tight">
                  Welcome Back
                </h2>
                <p className="mt-1.5 text-xs sm:text-[13px] text-white/60">
                  Sign in to continue to A-DMFE
                </p>
              </div>

              {/* Form */}
              <form onSubmit={handleSubmit} className="space-y-4">
                {/* Username / Operator Field */}
                <div>
                  <div className="relative">
                    <User className="absolute left-3.5 top-1/2 -translate-y-1/2 h-4 w-4 text-cyan-400/80 pointer-events-none" />
                    <input
                      type="text"
                      required
                      id="username"
                      name="username"
                      autoComplete="username"
                      value={email}
                      onChange={(e) => setEmail(e.target.value)}
                      className="w-full pl-10 pr-4 py-3 rounded-xl bg-[#0B1A36]/80 border border-white/10 text-white placeholder-white/40 text-sm focus:outline-none focus:ring-2 focus:ring-[#00D2FF]/50 focus:border-[#00D2FF]/80 transition-all shadow-inner"
                      placeholder="Username"
                    />
                  </div>
                </div>

                {/* Password Field */}
                <div>
                  <div className="relative">
                    <Lock className="absolute left-3.5 top-1/2 -translate-y-1/2 h-4 w-4 text-cyan-400/80 pointer-events-none" />
                    <input
                      type={showPassword ? 'text' : 'password'}
                      required
                      id="password"
                      name="password"
                      autoComplete="current-password"
                      value={password}
                      onChange={(e) => setPassword(e.target.value)}
                      className="w-full pl-10 pr-11 py-3 rounded-xl bg-[#0B1A36]/80 border border-white/10 text-white placeholder-white/40 text-sm focus:outline-none focus:ring-2 focus:ring-[#00D2FF]/50 focus:border-[#00D2FF]/80 transition-all shadow-inner"
                      placeholder="Password"
                    />
                    <button
                      type="button"
                      onClick={() => setShowPassword((v) => !v)}
                      className="absolute right-3.5 top-1/2 -translate-y-1/2 text-white/40 hover:text-white transition-colors"
                      aria-label="Toggle password visibility"
                    >
                      {showPassword ? <EyeOff className="h-4 w-4" /> : <Eye className="h-4 w-4" />}
                    </button>
                  </div>
                </div>

                {/* Remember Me Option */}
                <div className="flex items-center justify-between pt-1">
                  <label className="flex items-center gap-2.5 text-xs text-white/70 cursor-pointer select-none">
                    <input
                      type="checkbox"
                      id="rememberMe"
                      checked={rememberMe}
                      onChange={(e) => setRememberMe(e.target.checked)}
                      className="h-4 w-4 rounded border-white/20 bg-white/5 text-brand-primary focus:ring-[#00D2FF]/40 focus:ring-offset-0 cursor-pointer accent-[#1677FF]"
                    />
                    <span>Remember me</span>
                  </label>
                </div>

                {/* Submit Action */}
                <button
                  type="submit"
                  disabled={loading}
                  className="w-full mt-2 py-3.5 px-6 rounded-xl font-semibold text-sm text-white bg-gradient-to-r from-[#1677FF] via-[#0284C7] to-[#00D2FF] hover:from-[#2563EB] hover:to-[#38BDF8] shadow-[0_0_24px_rgba(0,210,255,0.4)] hover:shadow-[0_0_32px_rgba(0,210,255,0.6)] active:scale-[0.99] transition-all flex items-center justify-center gap-2 disabled:opacity-50 disabled:cursor-not-allowed"
                >
                  {loading ? (
                    <>
                      <span className="h-4 w-4 border-2 border-white/30 border-t-white rounded-full animate-spin" />
                      <span>Signing In&hellip;</span>
                    </>
                  ) : (
                    <>
                      <span>Sign In</span>
                      <ArrowRight className="h-4 w-4" />
                    </>
                  )}
                </button>
              </form>

              {/* Card Footer Security Indicator */}
              <div className="mt-6 pt-5 border-t border-white/[0.08] flex items-center justify-center gap-2 text-white/50 text-[11.5px]">
                <ShieldCheck className="h-3.5 w-3.5 text-cyan-400/90" />
                <span>Your data is protected and encrypted</span>
              </div>
            </div>
          </div>
        </motion.div>
      </div>
    </div>
  );
}