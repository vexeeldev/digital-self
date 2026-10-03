'use client';

import { useEffect, useRef, useCallback, useState } from 'react';
import ReactFlow, {
  Background,
  Controls,
  BackgroundVariant,
  applyNodeChanges,
  applyEdgeChanges,
  type Node as FlowNode,
  type Edge as FlowEdge,
  type NodeChange,
  type EdgeChange,
  Position,
  MarkerType,
  Panel,
} from 'reactflow';
import 'reactflow/dist/style.css';
import { forceSimulation, forceLink, forceManyBody, forceCenter, forceCollide } from 'd3-force';
import { getGraph } from '@/lib/api';
import { ApiGraphNode, ApiGraphEdge } from '@/lib/types';
import MemoryNode from './MemoryNode';
import Link from 'next/link';

const nodeTypes = {
  memoryNode: MemoryNode,
};

const nodeWidth = 100;
const nodeHeight = 100;

export function buildFlowNodes(
  apiNodes: ApiGraphNode[],
  apiEdges: ApiGraphEdge[],
  selectedNodeId?: string
): FlowNode[] {
  const simNodes = apiNodes.map((n) => ({ id: n.id, data: { ...n } }));
  const simLinks = apiEdges.map((e) => ({ source: e.source, target: e.target }));

  const simulation = forceSimulation(simNodes as any)
    .force('link', forceLink(simLinks).id((d: any) => d.id).distance(200))
    .force('charge', forceManyBody().strength(-1000))
    .force('center', forceCenter(0, 0))
    .force('collide', forceCollide().radius(100));

  simulation.stop();
  for (let i = 0; i < 300; ++i) {
    simulation.tick();
  }

  return simNodes.map((n: any) => ({
    id: n.id,
    type: 'memoryNode',
    position: { x: n.x - nodeWidth / 2, y: n.y - nodeHeight / 2 },
    targetPosition: Position.Top,
    sourcePosition: Position.Bottom,
    data: { label: n.data.name, nodeType: n.data.type },
    selected: n.id === selectedNodeId,
  }));
}

export function buildFlowEdges(apiEdges: ApiGraphEdge[]): FlowEdge[] {
  return apiEdges.map((e) => ({
    id: e.id || `${e.source}-${e.target}`,
    source: e.source,
    target: e.target,
    type: 'default',
    animated: true,
    style: { stroke: '#52525b', strokeWidth: 1.5, opacity: 0.6 },
    markerEnd: {
      type: MarkerType.ArrowClosed,
      color: '#52525b',
      width: 12,
      height: 12,
    },
    label: e.type,
    labelStyle: { fill: '#a1a1aa', fontSize: '9px', fontFamily: 'monospace', fontWeight: 'bold' },
    labelBgStyle: { fill: '#18181b', fillOpacity: 0.9, rx: 4, ry: 4 },
    labelBgPadding: [6, 4] as [number, number],
  }));
}

interface BrainGraphProps {
  experienceId?: string;
  nodeId?: string;
  selectedNodeId?: string;
  onNodeClick: (id: string) => void;
  refreshTrigger: number;
  memoryCount?: number;
}

export type GraphState = 'loading' | 'empty-no-filter' | 'empty-no-memory' | 'has-data';

export default function BrainGraph({
  experienceId,
  nodeId,
  selectedNodeId,
  onNodeClick,
  refreshTrigger,
  memoryCount = 0,
}: BrainGraphProps) {
  const [nodes, setNodes] = useState<FlowNode[]>([]);
  const [edges, setEdges] = useState<FlowEdge[]>([]);
  const [state, setState] = useState<GraphState>('loading');

  useEffect(() => {
    setState('loading');
    getGraph(experienceId, nodeId).then((data) => {
      if (data.nodes.length === 0) {
        setState('empty-no-memory');
        setNodes([]);
        setEdges([]);
        return;
      }
      setNodes(buildFlowNodes(data.nodes, data.edges, selectedNodeId));
      setEdges(buildFlowEdges(data.edges));
      setState('has-data');
    }).catch(() => {
      setState('empty-no-filter');
    });
  }, [refreshTrigger, experienceId, nodeId]);

  // Re-render nodes when selection changes
  useEffect(() => {
    if (state !== 'has-data') return;
    setNodes((prev) =>
      prev.map((n) => ({
        ...n,
        selected: n.id === selectedNodeId,
      }))
    );
  }, [selectedNodeId, state]);

  const onNodesChange = useCallback(
    (changes: NodeChange[]) => setNodes((nds) => applyNodeChanges(changes, nds)),
    []
  );
  const onEdgesChange = useCallback(
    (changes: EdgeChange[]) => setEdges((eds) => applyEdgeChanges(changes, eds)),
    []
  );

  if (state === 'loading') {
    return (
      <div className="flex items-center justify-center h-full bg-black">
        <div className="text-zinc-600 text-xs font-mono uppercase tracking-widest animate-pulse">Loading memory...</div>
      </div>
    );
  }

  if (state === 'empty-no-filter') {
    return (
      <div className="flex items-center justify-center h-full flex-col gap-3 text-center px-8 bg-black">
        <p className="text-zinc-600 text-xs font-mono uppercase tracking-widest">No memory nodes exist yet. Add an experience!</p>
      </div>
    );
  }

  if (state === 'empty-no-memory') {
    return (
      <div className="flex items-center justify-center h-full flex-col gap-3 text-center px-8 bg-black">
        <p className="text-zinc-400 text-sm">Experience recorded.</p>
        <p className="text-zinc-600 text-xs">Memory structures are not available for visualization yet.</p>
      </div>
    );
  }

  return (
    <div style={{ height: '100%', width: '100%' }} className="relative bg-black">
      <ReactFlow
        nodes={nodes}
        edges={edges}
        nodeTypes={nodeTypes}
        onNodesChange={onNodesChange}
        onEdgesChange={onEdgesChange}
        onNodeClick={(_, node) => onNodeClick(node.id)}
        fitView
        fitViewOptions={{ padding: 0.5, maxZoom: 1.5 }}
        minZoom={0.1}
        maxZoom={3}
        className="bg-[#000000]"
        proOptions={{ hideAttribution: true }}
      >
        <Background
          variant={BackgroundVariant.Dots}
          gap={32}
          size={1}
          color="#27272a"
        />
        <Controls position="bottom-right" />
        <Panel position="top-right" className="flex items-center gap-3">
          {/* Link to 3D Skull Design Studio */}
          <Link
            href="/desain"
            className="bg-cyan-950/80 hover:bg-cyan-900 border border-cyan-500/40 text-cyan-300 px-3 py-2 rounded-lg shadow-xl flex items-center gap-2 text-[10px] font-mono uppercase tracking-widest transition-all cursor-pointer"
          >
            <span className="w-2 h-2 rounded-full bg-cyan-400 animate-ping"></span>
            STUDIO 3D SKULL (/desain)
          </Link>

          {/* Stats Panel */}
          <div className="bg-[#09090b]/80 backdrop-blur border border-[#27272a] px-5 py-3 rounded-lg shadow-xl flex items-center gap-6 text-[10px] font-mono uppercase tracking-widest text-[#a1a1aa]">
            <div className="flex flex-col items-center gap-1 group cursor-default">
              <span>Memories</span>
              <span className="text-[14px] text-white font-bold group-hover:text-[#0d9488] transition-colors">{memoryCount}</span>
            </div>
            <div className="w-px h-8 bg-[#27272a]"></div>
            <div className="flex flex-col items-center gap-1 group cursor-default">
              <span>Nodes</span>
              <span className="text-[14px] text-white font-bold group-hover:text-[#0d9488] transition-colors">{nodes.length}</span>
            </div>
            <div className="w-px h-8 bg-[#27272a]"></div>
            <div className="flex flex-col items-center gap-1 group cursor-default">
              <span>Edges</span>
              <span className="text-[14px] text-white font-bold group-hover:text-[#0d9488] transition-colors">{edges.length}</span>
            </div>
          </div>
        </Panel>
      </ReactFlow>
    </div>
  );
}
