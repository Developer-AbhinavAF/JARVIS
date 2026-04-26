import { useState, useRef, useEffect } from 'react';
import { motion } from 'framer-motion';
import { Copy, Check, Code, Maximize2, Minimize2, Download } from 'lucide-react';

interface CodeCanvasProps {
  code: string;
  language: string;
  filename?: string;
}

export function CodeCanvas({ code, language, filename }: CodeCanvasProps) {
  const [copied, setCopied] = useState(false);
  const [isExpanded, setIsExpanded] = useState(false);
  const [isMinimized, setIsMinimized] = useState(false);
  const textareaRef = useRef<HTMLTextAreaElement>(null);

  // Auto-scroll to bottom when code changes (AI typing)
  useEffect(() => {
    if (textareaRef.current) {
      textareaRef.current.scrollTop = textareaRef.current.scrollHeight;
    }
  }, [code]);

  const handleCopy = async () => {
    try {
      await navigator.clipboard.writeText(code);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    } catch (err) {
      console.error('Failed to copy:', err);
    }
  };

  const handleDownload = () => {
    const blob = new Blob([code], { type: 'text/plain' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = filename || `code.${getExtension(language)}`;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);
  };

  const lineCount = code.split('\n').length;
  const displayCode = isExpanded ? code : code.slice(0, 2500);
  const isTruncated = code.length > 2500 && !isExpanded;
  
  // Fixed small height (200px) for preview, full height on expand
  const previewHeight = 200; // ~10-12 lines visible
  const calculatedHeight = lineCount * 20 + 32; // Full height calculation
  const displayHeight = isExpanded ? Math.min(calculatedHeight, 600) : previewHeight;

  if (isMinimized) {
    return (
      <motion.div
        initial={{ opacity: 0, scale: 0.9 }}
        animate={{ opacity: 1, scale: 1 }}
        className="bg-black/40 rounded-xl p-3 flex items-center justify-between cursor-pointer hover:bg-white/10 transition-colors border border-jarvis-accentPink/20"
        onClick={() => setIsMinimized(false)}
      >
        <div className="flex items-center gap-3">
          <div className="w-10 h-10 rounded-lg bg-jarvis-accentPink/20 flex items-center justify-center">
            <Code size={20} className="text-jarvis-accentPink" />
          </div>
          <div>
            <p className="text-sm font-medium text-jarvis-text">{filename || `${language.toUpperCase()} Code`}</p>
            <p className="text-xs text-jarvis-textMuted">{lineCount} lines • Click to expand</p>
          </div>
        </div>
        <Maximize2 size={18} className="text-jarvis-textMuted" />
      </motion.div>
    );
  }

  return (
    <motion.div
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      className={`bg-black/40 rounded-xl overflow-hidden border border-jarvis-accentPink/30 ${
        isExpanded ? 'fixed inset-4 z-50 bg-jarvis-bg' : 'relative max-h-[850px]'
      }`}
    >
      {/* Header */}
      <div className="flex items-center justify-between px-4 py-2 bg-black/40 border-b border-white/10">
        <div className="flex items-center gap-2">
          <div className="w-8 h-8 rounded-lg bg-jarvis-accentPink/20 flex items-center justify-center">
            <Code size={16} className="text-jarvis-accentPink" />
          </div>
          <div>
            <p className="text-sm font-medium text-jarvis-text">{filename || language.toUpperCase()}</p>
            <p className="text-xs text-jarvis-textMuted">{lineCount} lines</p>
          </div>
        </div>

        <div className="flex items-center gap-1">
          <button onClick={handleCopy} className="p-2 rounded-lg hover:bg-white/10 transition-colors" title="Copy code">
            {copied ? <Check size={16} className="text-green-500" /> : <Copy size={16} className="text-jarvis-textMuted" />}
          </button>
          <button onClick={handleDownload} className="p-2 rounded-lg hover:bg-white/10 transition-colors" title="Download">
            <Download size={16} className="text-jarvis-textMuted" />
          </button>
          <button onClick={() => isExpanded ? setIsExpanded(false) : setIsMinimized(true)} className="p-2 rounded-lg hover:bg-white/10 transition-colors" title={isExpanded ? 'Collapse' : 'Minimize'}>
            {isExpanded ? <Minimize2 size={16} className="text-jarvis-textMuted" /> : <Maximize2 size={16} className="text-jarvis-textMuted" />}
          </button>
        </div>
      </div>

      {/* Code content - Scrollable textarea style */}
      <div className="relative bg-black/60" style={{ height: isExpanded ? `${Math.min(calculatedHeight, 600)}px` : `${previewHeight}px` }}>
        <textarea
          ref={textareaRef}
          readOnly
          value={displayCode.split('\n').map((line, i) => `${i + 1}  ${line}`).join('\n')}
          className="w-full h-full p-4 text-sm font-mono leading-relaxed bg-transparent text-jarvis-text resize-none focus:outline-none whitespace-pre overflow-y-auto"
          spellCheck={false}
          style={{ scrollBehavior: 'smooth' }}
        />

        {/* Truncated indicator */}
        {isTruncated && (
          <div className="absolute bottom-0 left-0 right-0 p-4 bg-gradient-to-t from-black to-transparent">
            <button
              onClick={() => setIsExpanded(true)}
              className="w-full py-2 bg-jarvis-accentPink/20 hover:bg-jarvis-accentPink/30 text-jarvis-accentPink rounded-lg text-sm font-medium transition-colors"
            >
              Show all {lineCount} lines
            </button>
          </div>
        )}
      </div>

    </motion.div>
  );
}

function getExtension(language: string): string {
  const extensions: Record<string, string> = {
    javascript: 'js',
    typescript: 'ts',
    python: 'py',
    java: 'java',
    cpp: 'cpp',
    c: 'c',
    html: 'html',
    css: 'css',
    json: 'json',
    markdown: 'md',
    sql: 'sql',
    bash: 'sh',
    shell: 'sh',
    text: 'txt',
    file: 'txt',
  };
  return extensions[language.toLowerCase()] || language;
}
