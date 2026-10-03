import { Handle, Position } from 'reactflow';

// Dark theme node colors
const NODE_STYLE: Record<string, { bg: string; border: string; text: string; shadow: string }> = {
  person:  { bg: '#0f172a', border: '#3b82f6', text: '#93c5fd', shadow: '#3b82f640' },
  place:   { bg: '#0f172a', border: '#10b981', text: '#6ee7b7', shadow: '#10b98140' },
  event:   { bg: '#0f172a', border: '#f59e0b', text: '#fcd34d', shadow: '#f59e0b40' },
  emotion: { bg: '#0f172a', border: '#ec4899', text: '#f9a8d4', shadow: '#ec489940' },
  thought: { bg: '#0f172a', border: '#8b5cf6', text: '#c4b5fd', shadow: '#8b5cf640' },
  action:  { bg: '#0f172a', border: '#06b6d4', text: '#67e8f9', shadow: '#06b6d440' },
  concept: { bg: '#0f172a', border: '#71717a', text: '#a1a1aa', shadow: '#71717a40' },
  object:  { bg: '#0f172a', border: '#84cc16', text: '#bef264', shadow: '#84cc1640' },
  belief:  { bg: '#0f172a', border: '#f97316', text: '#fdba74', shadow: '#f9731640' },
  pattern: { bg: '#0f172a', border: '#a855f7', text: '#d8b4fe', shadow: '#a855f740' },
  assembly:{ bg: '#0f172a', border: '#14b8a6', text: '#99f6e4', shadow: '#14b8a640' },
  conflict:{ bg: '#0f172a', border: '#ef4444', text: '#fca5a5', shadow: '#ef444440' },
};

const DEFAULT_NODE_STYLE = { bg: '#0f172a', border: '#52525b', text: '#a1a1aa', shadow: '#52525b40' };

export default function MemoryNode({ data, selected }: any) {
  const style = NODE_STYLE[data.nodeType] ?? DEFAULT_NODE_STYLE;
  
  return (
    <div
      className="relative flex items-center justify-center rounded-full transition-all duration-300 group"
      style={{
        width: 80,
        height: 80,
        backgroundColor: style.bg,
        border: `2px solid ${selected ? '#fff' : style.border}`,
        boxShadow: selected 
          ? `0 0 0 4px #fff3, 0 0 30px ${style.border}` 
          : `0 0 15px ${style.shadow}`,
        transform: selected ? 'scale(1.1)' : 'scale(1)',
        zIndex: selected ? 10 : 1
      }}
    >
      <Handle type="target" position={Position.Top} style={{ opacity: 0 }} />
      
      {/* Glow effect */}
      <div 
        className="absolute inset-0 rounded-full opacity-20 blur-md pointer-events-none transition-opacity duration-300 group-hover:opacity-50"
        style={{ backgroundColor: style.border }}
      />
      
      <div className="text-center z-10 px-2 pointer-events-none">
        <div 
          className="text-[10px] font-bold leading-tight line-clamp-3"
          style={{ color: style.text }}
        >
          {data.label}
        </div>
        <div 
          className="text-[8px] uppercase tracking-widest mt-1 opacity-70"
          style={{ color: style.text }}
        >
          {data.nodeType}
        </div>
      </div>

      <Handle type="source" position={Position.Bottom} style={{ opacity: 0 }} />
    </div>
  );
}
