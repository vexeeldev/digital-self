'use client';
import { useState, useRef, useEffect } from 'react';
import { createExperience } from '@/lib/api';

import { Experience } from '@/lib/types';

interface Props {
  onExperienceAdded: (exp: Experience) => void;
  onToast: (msg: string, type: 'success' | 'error') => void;
}

export default function ExperienceInput({ onExperienceAdded, onToast }: Props) {
  const [text, setText] = useState('');
  const [loading, setLoading] = useState(false);
  const textareaRef = useRef<HTMLTextAreaElement>(null);

  // Auto-grow textarea
  useEffect(() => {
    if (textareaRef.current) {
      textareaRef.current.style.height = 'auto';
      textareaRef.current.style.height = `${Math.min(textareaRef.current.scrollHeight, 200)}px`;
    }
  }, [text]);

  const handleSubmit = async (e?: React.FormEvent) => {
    if (e) e.preventDefault();
    if (!text.trim() || loading) return;
    setLoading(true);
    try {
      const exp = await createExperience(text);
      setText('');
      onExperienceAdded(exp);
      onToast('Memory stored successfully.', 'success');
    } catch {
      onToast('Could not remember this experience.', 'error');
    } finally {
      setLoading(false);
    }
  };

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if ((e.ctrlKey || e.metaKey) && e.key === 'Enter') {
      handleSubmit();
    }
  };

  return (
    <form onSubmit={handleSubmit} className="flex flex-col gap-3">
      <div className="flex justify-between items-center">
        <label className="text-[12px] font-mono text-[#a1a1aa] uppercase tracking-widest">
          What happened?
        </label>
        <span className="text-[10px] font-mono text-[#71717a]">
          {text.length} chars
        </span>
      </div>
      <div className="relative group">
        <textarea
          ref={textareaRef}
          className="w-full p-3 border border-[#27272a] rounded-lg bg-[#09090b] text-[14px] text-[#f4f4f5] placeholder-[#a1a1aa] resize-none focus:outline-none focus:border-[#0d9488] focus:ring-2 focus:ring-[#0d9488]/20 transition-all duration-200"
          rows={3}
          style={{ minHeight: '80px', maxHeight: '200px' }}
          placeholder="Tadi di kantor aku bertemu Budi..."
          value={text}
          onChange={(e) => setText(e.target.value)}
          onKeyDown={handleKeyDown}
          disabled={loading}
        />
      </div>
      <button
        type="submit"
        disabled={loading || !text.trim()}
        className="w-full flex items-center justify-center gap-2 px-4 py-2.5 bg-[#0d9488] text-white text-[12px] font-bold uppercase tracking-wider rounded-lg hover:bg-[#14b8a6] disabled:opacity-50 disabled:bg-[#27272a] disabled:text-[#71717a] disabled:cursor-not-allowed transition-all duration-200 focus:outline-none focus:ring-2 focus:ring-[#0d9488]/50"
      >
        {loading ? (
          <>
            <svg className="animate-spin -ml-1 mr-2 h-4 w-4 text-white" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
              <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
              <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
            </svg>
            Remembering...
          </>
        ) : (
          <>
            Remember
            <span className="text-[10px] opacity-70 font-normal tracking-normal ml-1 hidden sm:inline">(Ctrl+Enter)</span>
          </>
        )}
      </button>
    </form>
  );
}
