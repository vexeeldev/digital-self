'use client';
import { useState } from 'react';
import { runReasoning } from '@/lib/api';
import { ReasoningResponse } from '@/lib/types';

export default function ReasoningPanel() {
  const [query, setQuery] = useState('');
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState<ReasoningResponse | null>(null);
  const [error, setError] = useState('');

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!query.trim()) return;
    setLoading(true);
    setError('');
    try {
      setResult(await runReasoning(query));
    } catch {
      setError('Reasoning failed.');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="flex flex-col gap-5 p-5 h-full overflow-y-auto">
      <form onSubmit={handleSubmit} className="flex flex-col gap-3">
        <label className="text-[10px] font-mono text-zinc-500 uppercase tracking-widest">
          Ask Digital Self
        </label>
        <div className="relative">
          <textarea
            className="w-full p-3 pb-12 border border-zinc-800 rounded-lg bg-zinc-950 text-sm text-zinc-200 placeholder-zinc-700 resize-none focus:outline-none focus:border-zinc-600 transition-colors"
            rows={5}
            placeholder="Why do I lose focus in this situation?"
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            disabled={loading}
          />
          <button
            type="submit"
            disabled={loading || !query.trim()}
            className="absolute bottom-3 right-3 px-4 py-1.5 bg-zinc-100 text-black text-xs font-bold uppercase tracking-wider rounded hover:bg-white disabled:opacity-30 disabled:pointer-events-none transition-all"
          >
            {loading ? 'Thinking...' : 'Reason'}
          </button>
        </div>
        {error && <p className="text-red-400 text-xs">{error}</p>}
      </form>

      {result && (
        <div className="flex flex-col gap-5">
          {/* Summary */}
          <div className="flex gap-4 text-xs font-mono border border-zinc-900 rounded-lg p-3 bg-zinc-950">
            <div className="flex flex-col gap-0.5">
              <span className="text-zinc-600 uppercase tracking-widest text-[9px]">Confidence</span>
              <span className="text-zinc-200">{result.confidence.toFixed(3)}</span>
            </div>
            <div className="w-px bg-zinc-900" />
            <div className="flex flex-col gap-0.5">
              <span className="text-zinc-600 uppercase tracking-widest text-[9px]">Provenance</span>
              <span className="text-zinc-200">{result.provenance.length} nodes</span>
            </div>
            <div className="w-px bg-zinc-900" />
            <div className="flex flex-col gap-0.5">
              <span className="text-zinc-600 uppercase tracking-widest text-[9px]">Conflicts</span>
              <span className={result.conflicts.length > 0 ? 'text-rose-400' : 'text-zinc-200'}>
                {result.conflicts.length}
              </span>
            </div>
          </div>

          {/* Conflicts */}
          {result.conflicts.length > 0 && (
            <div className="border border-rose-900/60 rounded-lg p-3 bg-rose-950/20">
              <p className="text-[10px] font-mono uppercase tracking-widest text-rose-500 mb-2">Conflict Detected</p>
              {result.conflicts.map((c) => (
                <p key={c.id} className="text-xs text-rose-400">
                  Beliefs {c.belief_a_id.slice(0, 8)} and {c.belief_b_id.slice(0, 8)} are in conflict. Not auto-resolved.
                </p>
              ))}
            </div>
          )}

          {/* Inferences */}
          <div className="flex flex-col gap-3">
            <p className="text-[10px] font-mono text-zinc-600 uppercase tracking-widest">
              Inferences ({result.inferences.length})
            </p>
            {result.inferences.length === 0 && (
              <p className="text-zinc-600 text-xs italic">No inferences generated.</p>
            )}
            {result.inferences.map((inf, i) => (
              <div key={i} className="border border-zinc-800 rounded-lg p-3 bg-black flex flex-col gap-3">
                <p className="text-zinc-200 text-sm leading-relaxed">{inf.statement}</p>
                <div className="text-[10px] font-mono text-zinc-600">
                  confidence: {inf.confidence.toFixed(3)}
                </div>
                {inf.supporting_evidence.length > 0 && (
                  <div>
                    <p className="text-[10px] font-mono text-emerald-500 uppercase tracking-widest mb-1">Supporting</p>
                    <div className="flex flex-col gap-1">
                      {inf.supporting_evidence.map((ev, j) => (
                        <div key={j} className="text-xs text-zinc-400 flex justify-between font-mono">
                          <span className="text-zinc-600">{ev.source_type}</span>
                          <span>{ev.relevance.toFixed(2)}</span>
                        </div>
                      ))}
                    </div>
                  </div>
                )}
                {inf.contradicting_evidence.length > 0 && (
                  <div>
                    <p className="text-[10px] font-mono text-rose-500 uppercase tracking-widest mb-1">Contradicting</p>
                    <div className="flex flex-col gap-1">
                      {inf.contradicting_evidence.map((ev, j) => (
                        <div key={j} className="text-xs text-zinc-400 font-mono">
                          <span className="text-zinc-600">{ev.source_type}</span>
                        </div>
                      ))}
                    </div>
                  </div>
                )}
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
