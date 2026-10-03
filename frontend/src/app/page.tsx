'use client';

import { useState, useEffect, useCallback, useMemo, useRef } from 'react';
import dynamic from 'next/dynamic';
import ExperienceInput from '@/components/experience/ExperienceInput';
import NodeInspector from '@/components/memory/NodeInspector';
import ReasoningPanel from '@/components/reasoning/ReasoningPanel';
import { getExperiences } from '@/lib/api';
import { Experience } from '@/lib/types';

// BrainGraph uses ReactFlow which needs client-only
const BrainGraph = dynamic(() => import('@/components/brain/BrainGraph'), {
  ssr: false,
  loading: () => (
    <div className="flex items-center justify-center h-full">
      <span className="text-[#a1a1aa] text-[12px] font-mono animate-pulse">Initializing neural network...</span>
    </div>
  ),
});

type LeftTab = 'memory' | 'reasoning';

interface Toast {
  id: number;
  msg: string;
  type: 'success' | 'error';
}

export default function Home() {
  const [experiences, setExperiences] = useState<Experience[]>([]);
  const [selectedExperienceId, setSelectedExperienceId] = useState<string | null>(null);
  const [selectedNodeId, setSelectedNodeId] = useState<string | null>(null);
  const [activeTab, setActiveTab] = useState<LeftTab>('memory');
  const [refreshTrigger, setRefreshTrigger] = useState(0);
  const [inspectorOpen, setInspectorOpen] = useState(false);
  const [loadingExperiences, setLoadingExperiences] = useState(true);
  
  // UI States
  const [searchQuery, setSearchQuery] = useState('');
  const [isSidebarCollapsed, setIsSidebarCollapsed] = useState(false);
  const [sidebarWidth, setSidebarWidth] = useState(340);
  const [isResizing, setIsResizing] = useState(false);
  const [toasts, setToasts] = useState<Toast[]>([]);
  const [expandedCards, setExpandedCards] = useState<Record<string, boolean>>({});

  const addToast = useCallback((msg: string, type: 'success' | 'error') => {
    const id = Date.now();
    setToasts(prev => [...prev, { id, msg, type }]);
    setTimeout(() => {
      setToasts(prev => prev.filter(t => t.id !== id));
    }, 3000);
  }, []);

  const loadExperiences = useCallback(async () => {
    try {
      const data = await getExperiences();
      setExperiences(prev => {
        // Auto-select most recent experience ONLY on initial load
        if (prev.length === 0 && data.length > 0) {
          setSelectedExperienceId(current => current === null ? data[0].id : current);
        }
        return data;
      });
    } catch {
      // network error
    } finally {
      setLoadingExperiences(false);
    }
  }, []);

  useEffect(() => {
    loadExperiences();
  }, [loadExperiences]);

  // Handle Resize
  const handleMouseDown = useCallback(() => setIsResizing(true), []);
  
  useEffect(() => {
    const handleMouseMove = (e: MouseEvent) => {
      if (!isResizing) return;
      const newWidth = Math.max(280, Math.min(e.clientX - 24, 480));
      setSidebarWidth(newWidth);
    };
    const handleMouseUp = () => setIsResizing(false);
    
    if (isResizing) {
      document.addEventListener('mousemove', handleMouseMove);
      document.addEventListener('mouseup', handleMouseUp);
    }
    return () => {
      document.removeEventListener('mousemove', handleMouseMove);
      document.removeEventListener('mouseup', handleMouseUp);
    };
  }, [isResizing]);

  const handleExperienceAdded = useCallback((exp: Experience) => {
    setSelectedNodeId(null);
    setInspectorOpen(false);
    
    // Immediately update UI
    setExperiences((prev) => [exp, ...prev]);
    setSelectedExperienceId(exp.id);
    setRefreshTrigger((t) => t + 1);
  }, []);

  const handleDeleteExperience = useCallback(async (e: React.MouseEvent, id: string) => {
    e.stopPropagation(); // Prevent opening the experience
    if (!confirm('Are you sure you want to delete this memory? This will also remove any nodes/connections it created.')) return;
    
    try {
      const res = await fetch(`http://localhost:8000/experiences/${id}`, { method: 'DELETE' });
      if (!res.ok) throw new Error('Failed to delete');
      
      setExperiences((prev) => prev.filter(exp => exp.id !== id));
      if (selectedExperienceId === id) {
        setSelectedExperienceId(null);
      }
      setRefreshTrigger((t) => t + 1);
      addToast('Memory deleted successfully.', 'success');
    } catch (err) {
      console.error(err);
      addToast('Failed to delete memory.', 'error');
    }
  }, [selectedExperienceId, addToast]);

  const handleExperienceClick = useCallback((id: string) => {
    setSelectedExperienceId((prev) => (prev === id ? null : id));
    setSelectedNodeId(null);
    setInspectorOpen(false);
    setRefreshTrigger((t) => t + 1);
  }, []);

  const handleNodeClick = useCallback((id: string) => {
    setSelectedNodeId(id);
    setInspectorOpen(true);
  }, []);

  const handleCloseInspector = useCallback(() => {
    setSelectedNodeId(null);
    setInspectorOpen(false);
  }, []);
  
  const toggleCardExpand = (e: React.MouseEvent, id: string) => {
    e.stopPropagation();
    setExpandedCards(prev => ({ ...prev, [id]: !prev[id] }));
  };

  const selectedExperience = experiences.find((e) => e.id === selectedExperienceId);

  // Filter and Group Experiences
  const groupedExperiences = useMemo(() => {
    const filtered = experiences.filter(exp => 
      exp.raw_text.toLowerCase().includes(searchQuery.toLowerCase())
    );
    
    const groups: Record<string, Experience[]> = {};
    const today = new Date().toDateString();
    const yesterday = new Date(Date.now() - 86400000).toDateString();
    
    filtered.forEach(exp => {
      const dateStr = new Date(exp.created_at).toDateString();
      let label = dateStr;
      if (dateStr === today) label = 'Hari ini';
      else if (dateStr === yesterday) label = 'Kemarin';
      else label = new Date(exp.created_at).toLocaleDateString('id-ID', { day: '2-digit', month: 'short' });
      
      if (!groups[label]) groups[label] = [];
      groups[label].push(exp);
    });
    
    return Object.entries(groups).map(([label, items]) => ({ label, items }));
  }, [experiences, searchQuery]);

  return (
    <div className="flex flex-col h-screen bg-[#000000] text-[#f4f4f5] font-sans antialiased overflow-hidden relative">
      {/* ── Toasts ── */}
      <div className="fixed top-4 right-4 z-50 flex flex-col gap-2">
        {toasts.map(toast => (
          <div key={toast.id} className={`toast-enter px-4 py-2 rounded shadow-lg text-[12px] font-mono border ${toast.type === 'success' ? 'bg-[#0d9488]/10 border-[#0d9488]/30 text-[#14b8a6]' : 'bg-red-900/10 border-red-500/30 text-red-400'}`}>
            {toast.msg}
          </div>
        ))}
      </div>

      {/* ── Background Brain Graph ── */}
      <div className="absolute inset-0 z-0 flex flex-col">
        <div className="flex-1 w-full h-full">
          <BrainGraph
            experienceId={selectedExperienceId ?? undefined}
            nodeId={undefined}
            selectedNodeId={selectedNodeId ?? undefined}
            onNodeClick={handleNodeClick}
            refreshTrigger={refreshTrigger}
            memoryCount={experiences.length}
          />
        </div>
      </div>

      {/* ── Header ── */}
      <header className="relative z-10 flex items-center justify-between px-8 py-4 bg-gradient-to-b from-[#000000]/90 to-transparent pointer-events-none">
        <div className="flex items-center gap-4">
          <h1 className="text-lg font-medium text-white tracking-widest drop-shadow-md">DIGITAL SELF</h1>
          <div className="flex items-center gap-2 text-[10px] font-mono text-[#14b8a6] uppercase tracking-widest pointer-events-auto bg-[#18181b]/80 border border-[#27272a] px-2.5 py-1 rounded-full backdrop-blur-sm">
            <span className="w-1.5 h-1.5 rounded-full bg-[#14b8a6] shadow-[0_0_8px_rgba(20,184,166,0.8)] animate-pulse" />
            Neural Link Synced
          </div>
        </div>
      </header>

      {/* ── Floating Left Panel ── */}
      <aside 
        style={{ width: isSidebarCollapsed ? '48px' : `${sidebarWidth}px` }}
        className="absolute top-20 left-6 max-md:bottom-0 max-md:left-0 max-md:top-auto max-md:w-full max-md:h-[60vh] max-md:rounded-t-2xl max-md:rounded-b-none bottom-6 flex flex-col rounded-xl bg-[#09090b]/80 backdrop-blur-xl border border-[#27272a] shadow-2xl z-10 transition-[width,transform] duration-300 ease-in-out"
      >
        {/* Resize Handle (Desktop Only) */}
        {!isSidebarCollapsed && (
          <div 
            className="absolute top-0 right-0 w-1.5 h-full cursor-col-resize hover:bg-[#0d9488]/50 z-20 hidden md:block transition-colors"
            onMouseDown={handleMouseDown}
          />
        )}
        
        {/* Collapse Toggle */}
        <button 
          onClick={() => setIsSidebarCollapsed(!isSidebarCollapsed)}
          className={`absolute top-3 w-6 h-6 bg-[#18181b] border border-[#27272a] rounded-full flex items-center justify-center text-[#a1a1aa] hover:text-white z-30 transition-all duration-300 hidden md:flex cursor-pointer ${
            isSidebarCollapsed ? 'left-1/2 -translate-x-1/2' : '-right-3'
          }`}
        >
          {isSidebarCollapsed ? '›' : '‹'}
        </button>

        {!isSidebarCollapsed && (
          <>
            {/* Tabs */}
            <div className="flex border-b border-[#27272a] shrink-0 bg-[#000000]/40">
              {(['memory', 'reasoning'] as LeftTab[]).map((tab) => (
                <button
                  key={tab}
                  onClick={() => setActiveTab(tab)}
                  className={`flex-1 py-3.5 text-[10px] font-mono uppercase tracking-widest transition-all duration-200 focus:outline-none focus-visible:ring-2 focus-visible:ring-[#0d9488]/50 inset-0 ${
                    activeTab === tab
                      ? 'text-[#14b8a6] border-b-2 border-[#14b8a6] bg-[#0d9488]/10'
                      : 'text-[#a1a1aa] hover:text-[#f4f4f5] hover:bg-white/5 border-b-2 border-transparent'
                  }`}
                >
                  {tab}
                </button>
              ))}
            </div>

            {activeTab === 'memory' ? (
              <div className="flex flex-col h-full overflow-hidden relative">
                {/* Input */}
                <div className="p-5 border-b border-[#27272a] shrink-0 bg-[#000000]/20">
                  <ExperienceInput onExperienceAdded={handleExperienceAdded} onToast={addToast} />
                </div>

                {/* Filter */}
                <div className="px-5 pt-4 pb-2 shrink-0">
                  <input 
                    type="text" 
                    placeholder="Search memories..." 
                    value={searchQuery}
                    onChange={(e) => setSearchQuery(e.target.value)}
                    className="w-full bg-[#18181b] border border-[#27272a] text-[#f4f4f5] text-[12px] font-mono px-3 py-2 rounded focus:outline-none focus:border-[#0d9488] transition-colors placeholder-[#71717a]"
                  />
                </div>

                {/* Timeline */}
                <div className="flex-1 overflow-y-auto p-5 scrollbar-thin scrollbar-thumb-[#27272a] scrollbar-track-transparent scroll-fade-bottom">
                  {loadingExperiences ? (
                    <div className="flex flex-col gap-4 pl-6 relative before:absolute before:inset-y-0 before:left-2 before:w-px before:bg-[#27272a]">
                      {[1,2,3].map(i => (
                        <div key={i} className="w-full h-24 bg-[#18181b] rounded-xl animate-pulse border border-[#27272a]" />
                      ))}
                    </div>
                  ) : experiences.length === 0 ? (
                    <div className="text-center mt-8 opacity-50">
                      <p className="text-[#a1a1aa] text-[12px] font-mono">Stream empty.</p>
                    </div>
                  ) : groupedExperiences.length === 0 ? (
                    <div className="text-center mt-8 opacity-50">
                      <p className="text-[#a1a1aa] text-[12px] font-mono">No matches found.</p>
                    </div>
                  ) : (
                    <div className="flex flex-col gap-6 relative before:absolute before:inset-y-0 before:left-2 before:w-px before:bg-[#27272a]">
                      {groupedExperiences.map((group) => (
                        <div key={group.label} className="flex flex-col gap-3">
                          <div className="sticky top-0 z-10 bg-[#09090b]/90 backdrop-blur py-1 pl-6">
                            <span className="text-[10px] font-mono text-[#71717a] uppercase tracking-widest bg-[#18181b] px-2 py-0.5 rounded border border-[#27272a]">
                              {group.label}
                            </span>
                          </div>
                          
                          {group.items.map((exp) => {
                            const isSelected = exp.id === selectedExperienceId;
                            const isExpanded = expandedCards[exp.id];
                            
                            return (
                              <button
                                key={exp.id}
                                onClick={() => handleExperienceClick(exp.id)}
                                className={`ml-6 relative text-left p-4 rounded-xl border backdrop-blur-md transition-all duration-200 group focus:outline-none focus-visible:ring-2 focus-visible:ring-[#0d9488]/50 ${
                                  isSelected
                                    ? 'border-[#0d9488]/50 bg-[#0d9488]/10 text-white shadow-[0_0_15px_rgba(13,148,136,0.15)]'
                                    : 'border-[#27272a] bg-[#18181b]/50 text-[#a1a1aa] hover:border-[#3f3f46] hover:bg-[#18181b] hover:text-[#f4f4f5]'
                                }`}
                              >
                                {/* Timeline dot */}
                                <div className={`absolute -left-[1.0625rem] top-5 w-2.5 h-2.5 rounded-full border-2 z-10 transition-colors duration-300 ${
                                  isSelected ? 'bg-[#14b8a6] border-black shadow-[0_0_8px_rgba(20,184,166,0.8)]' : 'bg-black border-[#3f3f46] group-hover:border-[#71717a]'
                                }`} />
                                
                                <div className="absolute top-3 right-3 opacity-0 group-hover:opacity-100 transition-opacity focus-within:opacity-100">
                                  <button
                                    onClick={(e) => handleDeleteExperience(e, exp.id)}
                                    className="p-1.5 text-[#71717a] hover:text-red-400 hover:bg-red-400/10 transition-colors bg-[#000000]/50 rounded focus:outline-none focus-visible:ring-2 focus-visible:ring-red-500"
                                    title="Delete Memory"
                                  >
                                    <svg xmlns="http://www.w3.org/2000/svg" width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                                      <path d="M3 6h18"></path>
                                      <path d="M19 6v14c0 1-1 2-2 2H7c-1 0-2-1-2-2V6"></path>
                                      <path d="M8 6V4c0-1 1-2 2-2h4c1 0 2 1 2 2v2"></path>
                                    </svg>
                                  </button>
                                </div>
                                
                                <div className="text-[10px] font-mono uppercase tracking-widest text-[#71717a] mb-2 flex justify-between items-center pr-8">
                                  <span className={isSelected ? 'text-[#a1a1aa]' : ''}>
                                    {new Date(exp.created_at).toLocaleTimeString('id-ID', {
                                      hour: '2-digit', minute: '2-digit',
                                    })}
                                  </span>
                                  {/* Dummy chip representing nodes since we don't have accurate API data yet */}
                                  <span className="bg-[#27272a] text-[#a1a1aa] px-1.5 py-0.5 rounded text-[9px] flex items-center gap-1" title="Nodes Extracted">
                                    <span className="w-1 h-1 rounded-full bg-[#14b8a6]"></span> Nodes
                                  </span>
                                </div>
                                
                                <p className={`text-[14px] leading-relaxed font-light ${isExpanded ? '' : 'line-clamp-3'}`}>
                                  {exp.raw_text}
                                </p>
                                
                                {exp.raw_text.length > 100 && (
                                  <div 
                                    className="text-[10px] text-[#0d9488] mt-2 font-mono uppercase hover:text-[#14b8a6] inline-block"
                                    onClick={(e) => toggleCardExpand(e, exp.id)}
                                  >
                                    {isExpanded ? 'Tutup' : 'Selengkapnya'}
                                  </div>
                                )}
                              </button>
                            );
                          })}
                        </div>
                      ))}
                    </div>
                  )}
                </div>
              </div>
            ) : (
              <div className="flex-1 overflow-hidden bg-[#000000]/20">
                <ReasoningPanel />
              </div>
            )}
          </>
        )}
      </aside>

      {/* ── Context Bar (Top Center) ── */}
      <div className="absolute top-6 left-1/2 -translate-x-1/2 z-10 pointer-events-none">
        {selectedExperience && (
          <div className="flex items-center gap-4 px-6 py-2.5 rounded-full bg-[#09090b]/80 backdrop-blur-xl border border-[#27272a] shadow-lg pointer-events-auto transition-all">
            <span className="w-2 h-2 rounded-full bg-white animate-pulse" />
            <span className="text-[12px] text-white max-w-[400px] truncate font-light">
              {selectedExperience.raw_text}
            </span>
            <button
              onClick={() => { setSelectedExperienceId(null); setSelectedNodeId(null); setRefreshTrigger((t) => t + 1); }}
              className="ml-2 text-[#71717a] hover:text-white text-[10px] font-mono uppercase tracking-widest transition-colors focus:outline-none focus-visible:ring-2 focus-visible:ring-white rounded px-1"
            >
              Clear Focus
            </button>
          </div>
        )}
      </div>

      {/* ── Floating Right Panel (Node Inspector) ── */}
      {inspectorOpen && (
        <aside className="absolute top-24 right-6 bottom-6 w-[320px] max-md:bottom-0 max-md:right-0 max-md:top-auto max-md:w-full max-md:h-[50vh] max-md:rounded-t-2xl max-md:rounded-b-none flex flex-col rounded-xl bg-[#09090b]/80 backdrop-blur-xl border border-[#27272a] shadow-2xl z-10 overflow-hidden animate-in slide-in-from-right-8 duration-300">
          <div className="flex items-center justify-between px-6 py-4 border-b border-[#27272a] shrink-0 bg-[#000000]/40">
            <div className="flex items-center gap-2">
              <div className="w-1.5 h-1.5 rounded-full bg-white/50" />
              <p className="text-[10px] font-mono text-[#f4f4f5] uppercase tracking-widest">Memory Focus</p>
            </div>
            <button
              onClick={handleCloseInspector}
              className="text-[#a1a1aa] hover:text-white text-lg font-light transition-colors focus:outline-none focus-visible:ring-2 focus-visible:ring-white rounded w-6 h-6 flex items-center justify-center"
            >
              ×
            </button>
          </div>
          <div className="p-6 overflow-y-auto flex-1 scrollbar-thin scrollbar-thumb-[#27272a] scrollbar-track-transparent">
            <NodeInspector nodeId={selectedNodeId} />
          </div>
        </aside>
      )}
    </div>
  );
}
