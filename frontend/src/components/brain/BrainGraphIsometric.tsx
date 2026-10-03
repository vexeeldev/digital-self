'use client';

import { useState, useMemo, useRef } from 'react';
import { ApiGraphNode, ApiGraphEdge } from '@/lib/types';
import { forceSimulation, forceLink, forceManyBody, forceCenter, forceCollide } from 'd3-force';

interface BrainGraphIsometricProps {
  apiNodes: ApiGraphNode[];
  apiEdges: ApiGraphEdge[];
  selectedNodeId?: string;
  onNodeClick: (id: string) => void;
}

const TYPE_BADGES: Record<string, { bg: string; border: string; text: string }> = {
  person: { bg: 'bg-cyan-950/60', border: 'border-cyan-500/50', text: 'text-cyan-400' },
  concept: { bg: 'bg-emerald-950/60', border: 'border-emerald-500/50', text: 'text-emerald-400' },
  action: { bg: 'bg-purple-950/60', border: 'border-purple-500/50', text: 'text-purple-400' },
  object: { bg: 'bg-amber-950/60', border: 'border-amber-500/50', text: 'text-amber-400' },
  emotion: { bg: 'bg-rose-950/60', border: 'border-rose-500/50', text: 'text-rose-400' },
  event: { bg: 'bg-indigo-950/60', border: 'border-indigo-500/50', text: 'text-indigo-400' },
  place: { bg: 'bg-sky-950/60', border: 'border-sky-500/50', text: 'text-sky-400' },
  default: { bg: 'bg-teal-950/60', border: 'border-teal-500/50', text: 'text-teal-400' },
};

export default function BrainGraphIsometric({
  apiNodes,
  apiEdges,
  selectedNodeId,
  onNodeClick,
}: BrainGraphIsometricProps) {
  const [tiltX, setTiltX] = useState(30);
  const [tiltZ, setTiltZ] = useState(-15);
  const [zoom, setZoom] = useState(0.85);

  // Compute 2.5D positions using force simulation
  const layout = useMemo(() => {
    const degrees: Record<string, number> = {};
    apiEdges.forEach((e) => {
      degrees[e.source] = (degrees[e.source] || 0) + 1;
      degrees[e.target] = (degrees[e.target] || 0) + 1;
    });

    const simNodes = apiNodes.map((n) => ({
      id: n.id,
      name: n.name,
      type: n.type,
      deg: degrees[n.id] || 0,
      isAku: n.name.toLowerCase() === 'aku',
    }));

    const simLinks = apiEdges.map((e) => ({ source: e.source, target: e.target, type: e.type }));

    const simulation = forceSimulation(simNodes as any)
      .force('link', forceLink(simLinks).id((d: any) => d.id).distance(220))
      .force('charge', forceManyBody().strength(-1400))
      .force('center', forceCenter(0, 0))
      .force('collide', forceCollide().radius(110));

    simulation.stop();
    for (let i = 0; i < 300; ++i) {
      simulation.tick();
    }

    const nodePosMap = new Map<string, { x: number; y: number; z: number; node: typeof simNodes[0] }>();
    simNodes.forEach((n: any) => {
      // Elevate 'aku' and highly connected nodes in Z height
      const zOffset = n.isAku ? 80 : Math.min(60, 10 + n.deg * 5);
      nodePosMap.set(n.id, { x: n.x, y: n.y, z: zOffset, node: n });
    });

    const calculatedEdges = simLinks.map((l: any, i) => {
      const src = nodePosMap.get(typeof l.source === 'object' ? l.source.id : l.source);
      const tgt = nodePosMap.get(typeof l.target === 'object' ? l.target.id : l.target);
      return {
        id: `iso-edge-${i}`,
        src,
        tgt,
        type: l.type,
      };
    });

    return { nodes: Array.from(nodePosMap.values()), edges: calculatedEdges };
  }, [apiNodes, apiEdges]);

  return (
    <div className="w-full h-full relative bg-[#030712] overflow-hidden select-none flex flex-col justify-between">
      {/* Top Controller Bar */}
      <div className="absolute top-4 left-4 z-20 flex items-center gap-3 bg-[#09090b]/80 backdrop-blur border border-[#27272a] px-4 py-2 rounded-lg text-[10px] font-mono text-zinc-400">
        <span className="text-white font-bold tracking-wider uppercase">Isometric HUD Controls:</span>
        <div className="flex items-center gap-2">
          <span>Tilt X:</span>
          <input
            type="range"
            min="0"
            max="60"
            value={tiltX}
            onChange={(e) => setTiltX(Number(e.target.value))}
            className="w-20 accent-teal-400 cursor-pointer"
          />
        </div>
        <div className="flex items-center gap-2">
          <span>Rotate Z:</span>
          <input
            type="range"
            min="-45"
            max="45"
            value={tiltZ}
            onChange={(e) => setTiltZ(Number(e.target.value))}
            className="w-20 accent-teal-400 cursor-pointer"
          />
        </div>
        <div className="flex items-center gap-2">
          <span>Zoom:</span>
          <button
            onClick={() => setZoom((z) => Math.min(1.5, z + 0.1))}
            className="px-2 py-0.5 bg-zinc-800 hover:bg-zinc-700 text-white rounded cursor-pointer"
          >
            +
          </button>
          <button
            onClick={() => setZoom((z) => Math.max(0.4, z - 0.1))}
            className="px-2 py-0.5 bg-zinc-800 hover:bg-zinc-700 text-white rounded cursor-pointer"
          >
            -
          </button>
        </div>
      </div>

      {/* 3D Isometric Projection Stage */}
      <div className="w-full h-full flex items-center justify-center relative overflow-hidden" style={{ perspective: '1200px' }}>
        <div
          className="transition-transform duration-300 ease-out relative flex items-center justify-center"
          style={{
            transform: `rotateX(${tiltX}deg) rotateZ(${tiltZ}deg) scale(${zoom})`,
            transformStyle: 'preserve-3d',
            width: '2000px',
            height: '2000px',
          }}
        >
          {/* Cybernetic Hologram Floor Plate Grid */}
          <div
            className="absolute inset-0 border border-teal-500/20 rounded-3xl"
            style={{
              backgroundImage: 'radial-gradient(#14b8a6 1px, transparent 1px), radial-gradient(#27272a 1px, transparent 1px)',
              backgroundSize: '40px 40px',
              backgroundPosition: '0 0, 20px 20px',
              boxShadow: '0 0 100px rgba(20, 184, 166, 0.08) inset',
            }}
          ></div>

          {/* SVG Connection Laser Beams */}
          <svg
            className="absolute inset-0 w-full h-full pointer-events-none"
            style={{ transform: 'translateZ(10px)', transformStyle: 'preserve-3d' }}
          >
            {layout.edges.map((e) => {
              if (!e.src || !e.tgt) return null;
              const x1 = 1000 + e.src.x;
              const y1 = 1000 + e.src.y;
              const x2 = 1000 + e.tgt.x;
              const y2 = 1000 + e.tgt.y;
              const isSelectedEdge = e.src.node.id === selectedNodeId || e.tgt.node.id === selectedNodeId;

              return (
                <g key={e.id}>
                  <line
                    x1={x1}
                    y1={y1}
                    x2={x2}
                    y2={y2}
                    stroke={isSelectedEdge ? '#2dd4bf' : '#3f3f46'}
                    strokeWidth={isSelectedEdge ? 2.5 : 1.2}
                    strokeOpacity={isSelectedEdge ? 0.9 : 0.4}
                    strokeDasharray={isSelectedEdge ? '6 3' : 'none'}
                    className={isSelectedEdge ? 'animate-pulse' : ''}
                  />
                </g>
              );
            })}
          </svg>

          {/* Floating 3D Isometric Cards */}
          {layout.nodes.map(({ x, y, z, node }) => {
            const isSelected = node.id === selectedNodeId;
            const badge = TYPE_BADGES[node.type.toLowerCase()] || TYPE_BADGES.default;

            return (
              <div
                key={node.id}
                onClick={() => onNodeClick(node.id)}
                className={`absolute cursor-pointer transition-all duration-300 group ${
                  node.isAku ? 'z-50' : 'z-10'
                }`}
                style={{
                  transform: `translate3d(${1000 + x - 80}px, ${1000 + y - 40}px, ${z}px) rotateZ(${-tiltZ}deg) rotateX(${-tiltX}deg)`,
                  transformStyle: 'preserve-3d',
                }}
              >
                {/* Elevation Light Pillar / Beam beneath the node */}
                <div
                  className="absolute left-1/2 bottom-0 -translate-x-1/2 w-0.5 bg-gradient-to-t from-teal-500/0 via-teal-500/30 to-teal-400/80 pointer-events-none"
                  style={{
                    height: `${z}px`,
                    transform: 'rotateX(90deg)',
                    transformOrigin: 'bottom center',
                  }}
                ></div>

                {/* Card Container */}
                <div
                  className={`w-44 px-3 py-2.5 rounded-xl backdrop-blur-md border transition-all duration-300 shadow-2xl flex flex-col gap-1.5 ${
                    node.isAku
                      ? 'bg-teal-950/90 border-teal-400 ring-2 ring-teal-400/50 shadow-teal-500/30 shadow-2xl scale-110'
                      : isSelected
                      ? 'bg-zinc-900/90 border-white ring-2 ring-white/50 scale-105'
                      : 'bg-[#09090b]/85 border-[#27272a] hover:border-teal-500/50 hover:bg-zinc-900/90 hover:scale-105'
                  }`}
                >
                  {/* Top Badge & Connections Count */}
                  <div className="flex items-center justify-between">
                    <span className={`text-[9px] font-mono uppercase font-bold tracking-wider px-1.5 py-0.5 rounded border ${badge.bg} ${badge.border} ${badge.text}`}>
                      {node.type}
                    </span>
                    <span className="text-[9px] font-mono text-zinc-500 group-hover:text-teal-400">
                      {node.deg} rel
                    </span>
                  </div>

                  {/* Node Name */}
                  <div className={`text-xs font-mono font-bold truncate leading-tight ${
                    node.isAku ? 'text-teal-300 text-sm' : isSelected ? 'text-white' : 'text-zinc-200'
                  }`}>
                    {node.name}
                  </div>
                </div>
              </div>
            );
          })}
        </div>
      </div>

      {/* Legend & Instructions */}
      <div className="absolute bottom-4 left-4 z-10 bg-[#09090b]/80 backdrop-blur border border-[#27272a] px-4 py-2.5 rounded-lg text-[10px] font-mono text-zinc-400 flex items-center gap-4">
        <span className="text-white font-bold tracking-wider">3D ISOMETRIC MATRIX:</span>
        <span className="text-teal-400">Elevated glassmorphic cards for maximum text readability</span>
        <span className="text-zinc-600">|</span>
        <span>Use sliders at top to rotate angle</span>
      </div>
    </div>
  );
}
