'use client';

import { useState, useEffect } from 'react';
import { getMemoryNode } from '@/lib/api';
import { MemoryNode } from '@/lib/types';

const TYPE_COLOR: Record<string, string> = {
  person:  'text-blue-400 bg-blue-950/50 border-blue-900',
  place:   'text-emerald-400 bg-emerald-950/50 border-emerald-900',
  event:   'text-amber-400 bg-amber-950/50 border-amber-900',
  emotion: 'text-pink-400 bg-pink-950/50 border-pink-900',
  thought: 'text-violet-400 bg-violet-950/50 border-violet-900',
  action:  'text-cyan-400 bg-cyan-950/50 border-cyan-900',
  concept: 'text-zinc-400 bg-zinc-900/50 border-zinc-800',
  object:  'text-lime-400 bg-lime-950/50 border-lime-900',
};

export default function NodeInspector({ nodeId }: { nodeId: string | null }) {
  const [node, setNode] = useState<MemoryNode | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');

  useEffect(() => {
    if (!nodeId) {
      setNode(null);
      return;
    }
    setLoading(true);
    setError('');
    getMemoryNode(nodeId)
      .then((data) => {
        setNode(data);
        setLoading(false);
      })
      .catch(() => {
        setError('Failed to load node.');
        setLoading(false);
      });
  }, [nodeId]);

  if (!nodeId) {
    return (
      <div className="h-full flex items-center justify-center">
        <p className="text-zinc-700 text-xs font-mono uppercase tracking-widest text-center">No node selected</p>
      </div>
    );
  }

  if (loading) return <div className="p-6 text-zinc-600 text-xs font-mono animate-pulse">Loading...</div>;
  if (error)   return <div className="p-6 text-red-400 text-xs">{error}</div>;
  if (!node)   return null;

  const typeStyle = TYPE_COLOR[node.type] ?? 'text-zinc-400 bg-zinc-900 border-zinc-800';

  return (
    <div className="flex flex-col gap-5">
      {/* Header */}
      <div>
        <h2 className="text-zinc-100 font-semibold text-base leading-tight">{node.name}</h2>
        <div className="mt-1">
          <span className={`text-[10px] font-mono uppercase tracking-widest px-2 py-0.5 rounded border ${typeStyle}`}>
            {node.type}
          </span>
        </div>
      </div>

      {/* Properties */}
      <div className="flex flex-col gap-0 text-sm divide-y divide-zinc-900 border border-zinc-900 rounded-lg overflow-hidden">
        <div className="flex justify-between items-center px-4 py-3 bg-zinc-950">
          <span className="text-zinc-500 text-[11px] uppercase tracking-widest font-mono">Associations</span>
          <span className="text-zinc-200 font-mono text-sm">{node.associations_count ?? 0}</span>
        </div>
        <div className="flex justify-between items-center px-4 py-3 bg-black">
          <span className="text-zinc-500 text-[11px] uppercase tracking-widest font-mono">Activation</span>
          <span className="text-zinc-600 text-xs italic">Not exposed by API</span>
        </div>
      </div>

      {/* UUID — below fold, small */}
      <div className="text-[10px] text-zinc-800 font-mono break-all">{node.id}</div>
    </div>
  );
}
