import React, { useMemo } from 'react';
import { motion } from 'framer-motion';

export default function AnimatedBackground() {
  const particles = useMemo(
    () =>
      Array.from({ length: 22 }, () => ({
        x: Math.random() * 100,
        y: Math.random() * 100,
        size: Math.random() * 2.4 + 0.8,
        duration: Math.random() * 18 + 18,
        driftX: Math.random() * 12 - 6,
        driftY: Math.random() * 14 - 8,
        delay: Math.random() * 12,
        opacity: Math.random() * 0.5 + 0.15,
        cyan: Math.random() > 0.5,
      })),
    []
  );

  return (
    <div className="fixed inset-0 z-[-1] overflow-hidden bg-[#050816]" aria-hidden>
      {/* Base volumetric blue bloom */}
      <div className="absolute inset-0 bg-[radial-gradient(ellipse_70%_60%_at_50%_-10%,_rgba(59,130,246,0.14)_0%,_rgba(5,8,22,1)_65%)]" />

      {/* Aurora — slowly shifting blue field */}
      <div
        className="absolute left-[8%] top-[14%] w-[46vw] h-[46vw] bg-brand-primary/14 rounded-full blur-[120px] mix-blend-screen animate-aurora"
        style={{ willChange: 'transform' }}
      />
      {/* Aurora — purple field, counterweight */}
      <div
        className="absolute right-[2%] bottom-[6%] w-[52vw] h-[52vw] bg-brand-accent/12 rounded-full blur-[140px] mix-blend-screen animate-aurora"
        style={{ animationDelay: '5s', willChange: 'transform' }}
      />
      {/* Fine cyan secondary light */}
      <div
        className="absolute top-[55%] left-[55%] w-[26vw] h-[26vw] bg-brand-secondary/8 rounded-full blur-[110px] animate-float-slow"
        style={{ willChange: 'transform' }}
      />

      {/* Drifting embers */}
      {particles.map((p, i) => (
        <motion.div
          key={i}
          className="absolute rounded-full"
          style={{
            left: `${p.x}%`,
            top: `${p.y}%`,
            width: `${p.size}px`,
            height: `${p.size}px`,
            background: p.cyan ? 'rgba(6,182,212,0.7)' : 'rgba(139,92,246,0.7)',
            boxShadow: p.cyan
              ? '0 0 8px rgba(6,182,212,0.5)'
              : '0 0 8px rgba(139,92,246,0.5)',
            willChange: 'transform, opacity',
          }}
          initial={{ opacity: 0 }}
          animate={{
            opacity: [0, p.opacity, 0],
            x: [0, p.driftX, 0],
            y: [0, p.driftY, 0],
          }}
          transition={{
            duration: p.duration,
            repeat: Infinity,
            ease: 'easeInOut',
            delay: p.delay,
          }}
        />
      ))}

      {/* Soft vignette to keep edges calm */}
      <div className="absolute inset-0 bg-[radial-gradient(ellipse_at_center,transparent_55%,rgba(2,4,12,0.55)_100%)]" />
    </div>
  );
}