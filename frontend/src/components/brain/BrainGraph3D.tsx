'use client';

import { useEffect, useRef, useState, useMemo } from 'react';
import dynamic from 'next/dynamic';
import { ApiGraphNode, ApiGraphEdge } from '@/lib/types';
import * as THREE from 'three';
import SpriteText from 'three-spritetext';

// Dynamically import ForceGraph3D to prevent SSR window/document reference errors in Next.js
const ForceGraph3D = dynamic(() => import('react-force-graph-3d'), {
  ssr: false,
  loading: () => (
    <div className="flex items-center justify-center h-full bg-black">
      <div className="text-teal-500 text-xs font-mono uppercase tracking-widest animate-pulse">
        Initializing 3D Neural Galaxy...
      </div>
    </div>
  ),
});

interface BrainGraph3DProps {
  apiNodes: ApiGraphNode[];
  apiEdges: ApiGraphEdge[];
  selectedNodeId?: string;
  onNodeClick: (id: string) => void;
}

// Type accent colors for 3D spheres
const TYPE_COLORS: Record<string, string> = {
  person: '#06b6d4',   // cyan
  concept: '#10b981',  // emerald
  action: '#8b5cf6',   // violet
  object: '#f59e0b',   // amber
  emotion: '#f43f5e',  // rose
  event: '#6366f1',    // indigo
  place: '#0ea5e9',    // sky
  default: '#14b8a6',  // teal default
};

export default function BrainGraph3D({
  apiNodes,
  apiEdges,
  selectedNodeId,
  onNodeClick,
}: BrainGraph3DProps) {
  const fgRef = useRef<any>(null);
  const [dimensions, setDimensions] = useState({ width: 800, height: 600 });
  const containerRef = useRef<HTMLDivElement>(null);

  // Resize handler
  useEffect(() => {
    const updateSize = () => {
      if (containerRef.current) {
        setDimensions({
          width: containerRef.current.clientWidth,
          height: containerRef.current.clientHeight,
        });
      }
    };
    updateSize();
    window.addEventListener('resize', updateSize);
    return () => window.removeEventListener('resize', updateSize);
  }, []);

  // Format data for 3d force graph
  const graphData = useMemo(() => {
    // Count degrees (associations) for scaling node size
    const degrees: Record<string, number> = {};
    apiEdges.forEach((e) => {
      degrees[e.source] = (degrees[e.source] || 0) + 1;
      degrees[e.target] = (degrees[e.target] || 0) + 1;
    });

    const nodes = apiNodes.map((n) => {
      const isAku = n.name.toLowerCase() === 'aku';
      const deg = degrees[n.id] || 1;
      const baseVal = isAku ? 24 : Math.min(16, 4 + deg * 0.8);
      return {
        id: n.id,
        name: n.name,
        type: n.type,
        val: baseVal,
        color: isAku ? '#2dd4bf' : TYPE_COLORS[n.type.toLowerCase()] || TYPE_COLORS.default,
        isAku,
      };
    });

    const links = apiEdges.map((e) => ({
      source: e.source,
      target: e.target,
      type: e.type,
    }));

    return { nodes, links };
  }, [apiNodes, apiEdges]);

  // Center on selected node when selection changes
  useEffect(() => {
    if (selectedNodeId && fgRef.current) {
      const node = graphData.nodes.find((n) => n.id === selectedNodeId);
      if (node && (node as any).x !== undefined) {
        const distance = 120;
        const distRatio = 1 + distance / Math.hypot((node as any).x, (node as any).y, (node as any).z);
        fgRef.current.cameraPosition(
          { x: (node as any).x * distRatio, y: (node as any).y * distRatio, z: (node as any).z * distRatio },
          { x: (node as any).x, y: (node as any).y, z: (node as any).z },
          2000
        );
      }
    }
  }, [selectedNodeId, graphData]);

  return (
    <div ref={containerRef} className="w-full h-full relative bg-black overflow-hidden">
      <ForceGraph3D
        ref={fgRef}
        width={dimensions.width}
        height={dimensions.height}
        graphData={graphData}
        backgroundColor="#030712"
        showNavInfo={false}
        // Custom Node 3D Object
        nodeThreeObject={(node: any) => {
          const group = new THREE.Group();
          const isSelected = node.id === selectedNodeId;

          // Sphere Mesh
          const radius = Math.sqrt(node.val) * 2;
          const geometry = new THREE.SphereGeometry(radius, 24, 24);
          const material = new THREE.MeshStandardMaterial({
            color: isSelected ? '#ffffff' : node.color,
            emissive: node.color,
            emissiveIntensity: isSelected ? 1.2 : node.isAku ? 0.8 : 0.4,
            roughness: 0.2,
            metalness: 0.8,
          });
          const sphere = new THREE.Mesh(geometry, material);
          group.add(sphere);

          // Outer Glow Ring for 'aku' or selected node
          if (node.isAku || isSelected) {
            const glowGeo = new THREE.SphereGeometry(radius * 1.4, 16, 16);
            const glowMat = new THREE.MeshBasicMaterial({
              color: node.isAku ? '#2dd4bf' : '#ffffff',
              transparent: true,
              opacity: 0.25,
              wireframe: true,
            });
            group.add(new THREE.Mesh(glowGeo, glowMat));
          }

          // 3D Text Label
          const sprite = new SpriteText(node.name);
          sprite.color = isSelected ? '#ffffff' : '#e4e4e7';
          sprite.textHeight = node.isAku ? 5 : 3.5;
          sprite.fontFace = 'Monospace';
          sprite.fontWeight = isSelected || node.isAku ? 'bold' : 'normal';
          sprite.position.set(0, radius + 4, 0);
          group.add(sprite);

          return group;
        }}
        // Node interaction
        onNodeClick={(node: any) => {
          onNodeClick(node.id);
        }}
        // Link styling & particle effects
        linkColor={() => '#3f3f46'}
        linkWidth={1.2}
        linkDirectionalParticles={2}
        linkDirectionalParticleWidth={2}
        linkDirectionalParticleSpeed={0.006}
        linkDirectionalParticleColor={(link: any) => '#14b8a6'}
        // D3 Force settings
        d3VelocityDecay={0.3}
      />

      {/* 3D Legend & Controls Overlay */}
      <div className="absolute bottom-4 left-4 z-10 bg-[#09090b]/80 backdrop-blur border border-[#27272a] px-4 py-3 rounded-lg shadow-xl text-[10px] font-mono text-[#a1a1aa] flex flex-wrap items-center gap-3">
        <span className="text-white font-bold tracking-wider">3D GALAXY LEGEND:</span>
        <div className="flex items-center gap-1.5"><span className="w-2.5 h-2.5 rounded-full bg-[#2dd4bf] animate-pulse"></span><span className="text-zinc-200">Aku (Core)</span></div>
        <div className="flex items-center gap-1.5"><span className="w-2.5 h-2.5 rounded-full bg-[#06b6d4]"></span><span>Person</span></div>
        <div className="flex items-center gap-1.5"><span className="w-2.5 h-2.5 rounded-full bg-[#10b981]"></span><span>Concept</span></div>
        <div className="flex items-center gap-1.5"><span className="w-2.5 h-2.5 rounded-full bg-[#8b5cf6]"></span><span>Action</span></div>
        <div className="flex items-center gap-1.5"><span className="w-2.5 h-2.5 rounded-full bg-[#f59e0b]"></span><span>Object</span></div>
        <div className="flex items-center gap-1.5"><span className="w-2.5 h-2.5 rounded-full bg-[#f43f5e]"></span><span>Emotion</span></div>
      </div>
    </div>
  );
}
