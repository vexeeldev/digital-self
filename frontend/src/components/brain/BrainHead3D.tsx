'use client';

import { useEffect, useRef, useState, useMemo } from 'react';
import dynamic from 'next/dynamic';
import { ApiGraphNode, ApiGraphEdge } from '@/lib/types';
import * as THREE from 'three';
import SpriteText from 'three-spritetext';

// Dynamically import ForceGraph3D for SSR compatibility in Next.js
const ForceGraph3D = dynamic(() => import('react-force-graph-3d'), {
  ssr: false,
  loading: () => (
    <div className="flex items-center justify-center h-full bg-black">
      <div className="text-cyan-400 text-xs font-mono uppercase tracking-widest animate-pulse">
        Constructing 3D Holographic Head Matrix...
      </div>
    </div>
  ),
});

interface BrainHead3DProps {
  apiNodes: ApiGraphNode[];
  apiEdges: ApiGraphEdge[];
  selectedNodeId?: string;
  onNodeClick: (id: string) => void;
}

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

export default function BrainHead3D({
  apiNodes,
  apiEdges,
  selectedNodeId,
  onNodeClick,
}: BrainHead3DProps) {
  const fgRef = useRef<any>(null);
  const [dimensions, setDimensions] = useState({ width: 800, height: 600 });
  const containerRef = useRef<HTMLDivElement>(null);
  const headGroupRef = useRef<THREE.Group | null>(null);

  // Resize listener
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

  // Format data for 3D force graph
  const graphData = useMemo(() => {
    const degrees: Record<string, number> = {};
    apiEdges.forEach((e) => {
      degrees[e.source] = (degrees[e.source] || 0) + 1;
      degrees[e.target] = (degrees[e.target] || 0) + 1;
    });

    const nodes = apiNodes.map((n) => {
      const isAku = n.name.toLowerCase() === 'aku';
      const deg = degrees[n.id] || 1;
      const baseVal = isAku ? 22 : Math.min(14, 4 + deg * 0.7);
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

  // Inject 3D Holographic Head Mesh into Three.js Scene
  useEffect(() => {
    if (!fgRef.current) return;
    const scene = fgRef.current.scene();
    if (!scene) return;

    // Remove old head group if re-rendering
    if (headGroupRef.current) {
      scene.remove(headGroupRef.current);
    }

    const headGroup = new THREE.Group();

    // 1. Holographic Head Cranium Mesh (Outer Contour)
    const headGeo = new THREE.IcosahedronGeometry(220, 3);
    headGeo.scale(1.0, 1.25, 1.1); // Anatomical head shape ratio
    const headMat = new THREE.MeshBasicMaterial({
      color: '#06b6d4',
      wireframe: true,
      transparent: true,
      opacity: 0.12,
    });
    const headMesh = new THREE.Mesh(headGeo, headMat);
    headGroup.add(headMesh);

    // 2. Left Brain Hemisphere
    const leftHemGeo = new THREE.SphereGeometry(140, 24, 24);
    leftHemGeo.scale(0.85, 0.95, 1.25);
    const hemMat = new THREE.MeshBasicMaterial({
      color: '#14b8a6',
      wireframe: true,
      transparent: true,
      opacity: 0.08,
    });
    const leftHem = new THREE.Mesh(leftHemGeo, hemMat);
    leftHem.position.set(-65, 30, 0);
    headGroup.add(leftHem);

    // 3. Right Brain Hemisphere
    const rightHem = new THREE.Mesh(leftHemGeo, hemMat);
    rightHem.position.set(65, 30, 0);
    headGroup.add(rightHem);

    // 4. Outer Holographic Shield Halo Grid
    const haloGeo = new THREE.RingGeometry(260, 262, 64);
    const haloMat = new THREE.MeshBasicMaterial({
      color: '#2dd4bf',
      side: THREE.DoubleSide,
      transparent: true,
      opacity: 0.25,
    });
    const haloMesh = new THREE.Mesh(haloGeo, haloMat);
    haloMesh.rotation.x = Math.PI / 2;
    haloMesh.position.y = -50;
    headGroup.add(haloMesh);

    scene.add(headGroup);
    headGroupRef.current = headGroup;

    // Apply bounding forces to keep nodes inside head volume
    fgRef.current.d3Force('charge').strength(-800);
    fgRef.current.d3Force('link').distance(140);

    return () => {
      if (headGroupRef.current && scene) {
        scene.remove(headGroupRef.current);
      }
    };
  }, [graphData]);

  // Center camera on selected node
  useEffect(() => {
    if (selectedNodeId && fgRef.current) {
      const node = graphData.nodes.find((n) => n.id === selectedNodeId);
      if (node && (node as any).x !== undefined) {
        const distance = 140;
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
    <div ref={containerRef} className="w-full h-full relative bg-[#030712] overflow-hidden select-none">
      <ForceGraph3D
        ref={fgRef}
        width={dimensions.width}
        height={dimensions.height}
        graphData={graphData}
        backgroundColor="#030712"
        showNavInfo={false}
        // Custom 3D Node Rendering
        nodeThreeObject={(node: any) => {
          const group = new THREE.Group();
          const isSelected = node.id === selectedNodeId;

          // Sphere Mesh
          const radius = Math.sqrt(node.val) * 2.2;
          const geometry = new THREE.SphereGeometry(radius, 24, 24);
          const material = new THREE.MeshStandardMaterial({
            color: isSelected ? '#ffffff' : node.color,
            emissive: node.color,
            emissiveIntensity: isSelected ? 1.4 : node.isAku ? 1.0 : 0.5,
            roughness: 0.15,
            metalness: 0.85,
          });
          const sphere = new THREE.Mesh(geometry, material);
          group.add(sphere);

          // Glowing Outer Halo for 'aku' core or selected node
          if (node.isAku || isSelected) {
            const glowGeo = new THREE.SphereGeometry(radius * 1.5, 16, 16);
            const glowMat = new THREE.MeshBasicMaterial({
              color: node.isAku ? '#2dd4bf' : '#ffffff',
              transparent: true,
              opacity: 0.35,
              wireframe: true,
            });
            group.add(new THREE.Mesh(glowGeo, glowMat));
          }

          // Floating 3D Text Label
          const sprite = new SpriteText(node.name);
          sprite.color = isSelected ? '#ffffff' : '#e4e4e7';
          sprite.textHeight = node.isAku ? 5.5 : 3.8;
          sprite.fontFace = 'Monospace';
          sprite.fontWeight = isSelected || node.isAku ? 'bold' : 'normal';
          sprite.position.set(0, radius + 4, 0);
          group.add(sprite);

          return group;
        }}
        onNodeClick={(node: any) => {
          onNodeClick(node.id);
        }}
        // Link beam styling & particle flow inside head
        linkColor={() => '#27272a'}
        linkWidth={1.5}
        linkDirectionalParticles={3}
        linkDirectionalParticleWidth={2.5}
        linkDirectionalParticleSpeed={0.007}
        linkDirectionalParticleColor={(link: any) => '#06b6d4'}
        d3VelocityDecay={0.25}
      />

      {/* Control Overlay & Instructions */}
      <div className="absolute bottom-4 left-4 z-10 bg-[#09090b]/85 backdrop-blur border border-[#27272a] px-4 py-3 rounded-lg text-[10px] font-mono text-zinc-400 flex flex-wrap items-center gap-4 shadow-2xl">
        <span className="text-cyan-400 font-bold tracking-wider uppercase flex items-center gap-2">
          <span className="w-2 h-2 rounded-full bg-cyan-400 animate-ping"></span>
          3D BRAIN HOLOGRAM:
        </span>
        <span className="text-zinc-200">Drag mouse to rotate head 360°</span>
        <span className="text-zinc-600">|</span>
        <span className="text-zinc-200">Scroll to zoom in/out inside cerebral lobes</span>
        <span className="text-zinc-600">|</span>
        <div className="flex items-center gap-1.5"><span className="w-2.5 h-2.5 rounded-full bg-[#2dd4bf]"></span><span className="text-teal-300 font-bold">Aku (Core)</span></div>
      </div>
    </div>
  );
}
