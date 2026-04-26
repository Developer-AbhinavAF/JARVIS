import { useState } from 'react';
import { motion } from 'framer-motion';
import { Copy, Check, FileText, Maximize2, Minimize2, Download } from 'lucide-react';

interface FileCanvasProps {
  content: string;
  filename?: string;
  fileType?: string;
}

export function FileCanvas({ content, filename, fileType }: FileCanvasProps) {
  const [copied, setCopied] = useState(false);
  const [isExpanded, setIsExpanded] = useState(false);
  const [isMinimized, setIsMinimized] = useState(false);

  const handleCopy = async () => {
    try {
      await navigator.clipboard.writeText(content);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    } catch (err) {
      console.error('Failed to copy:', err);
    }
  };

  const handleDownload = () => {
    const blob = new Blob([content], { type: 'text/plain' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = filename || 'file.txt';
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);
  };

  const lineCount = content.split('\n').length;
  const displayContent = isExpanded ? content : content.slice(0, 3000);
  const isTruncated = content.length > 3000 && !isExpanded;

  if (isMinimized) {
    return (
      <motion.div
        initial={{ opacity: 0, scale: 0.9 }}
        animate={{ opacity: 1, scale: 1 }}
        className="bg-white/5 rounded-xl p-3 flex items-center justify-between cursor-pointer hover:bg-white/10 transition-colors border border-white/10"
        onClick={() => setIsMinimized(false)}
      >
        <div className="flex items-center gap-3">
          <div className="w-10 h-10 rounded-lg bg-jarvis-accentPink/20 flex items-center justify-center">
            <FileText size={20} className="text-jarvis-accentPink" />
          </div>
          <div>
            <p className="text-sm font-medium text-jarvis-text">{filename || 'File Content'}</p>
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
      className={`bg-white/5 rounded-xl overflow-hidden border border-white/10 ${
        isExpanded ? 'fixed inset-4 z-50 bg-jarvis-bg' : 'relative max-h-80'
      }`}
    >
      {/* Header */}
      <div className="flex items-center justify-between px-4 py-2 bg-black/40 border-b border-white/10">
        <div className="flex items-center gap-2">
          <div className="w-8 h-8 rounded-lg bg-jarvis-accentPink/20 flex items-center justify-center">
            <FileText size={16} className="text-jarvis-accentPink" />
          </div>
          <div>
            <p className="text-sm font-medium text-jarvis-text">
              {filename || 'File Content'}
            </p>
            <p className="text-xs text-jarvis-textMuted">{lineCount} lines • {fileType || 'text'}</p>
          </div>
        </div>

        <div className="flex items-center gap-1">
          {/* Copy button */}
          <button
            onClick={handleCopy}
            className="p-2 rounded-lg hover:bg-white/10 transition-colors group relative"
            title="Copy content"
          >
            {copied ? (
              <Check size={16} className="text-green-500" />
            ) : (
              <Copy size={16} className="text-jarvis-textMuted group-hover:text-jarvis-text" />
            )}
            {copied && (
              <span className="absolute -top-8 left-1/2 -translate-x-1/2 text-xs bg-green-500 text-white px-2 py-1 rounded whitespace-nowrap">
                Copied!
              </span>
            )}
          </button>

          {/* Download button */}
          <button
            onClick={handleDownload}
            className="p-2 rounded-lg hover:bg-white/10 transition-colors group"
            title="Download file"
          >
            <Download size={16} className="text-jarvis-textMuted group-hover:text-jarvis-text" />
          </button>

          {/* Expand/Minimize */}
          <button
            onClick={() => isExpanded ? setIsExpanded(false) : setIsMinimized(true)}
            className="p-2 rounded-lg hover:bg-white/10 transition-colors group"
            title={isExpanded ? 'Collapse' : 'Minimize'}
          >
            {isExpanded ? (
              <Minimize2 size={16} className="text-jarvis-textMuted group-hover:text-jarvis-text" />
            ) : (
              <Maximize2 size={16} className="text-jarvis-textMuted group-hover:text-jarvis-text" />
            )}
          </button>
        </div>
      </div>

      {/* Content - Scrollable textarea style */}
      <div className={`relative bg-black/30 ${isExpanded ? 'h-[calc(100%-60px)]' : 'max-h-64'}`}>
        <textarea
          readOnly
          value={displayContent}
          className="w-full h-full p-4 text-sm font-mono leading-relaxed bg-transparent text-jarvis-text resize-none focus:outline-none whitespace-pre-wrap"
          spellCheck={false}
        />

        {/* Truncated indicator */}
        {isTruncated && (
          <div className="absolute bottom-0 left-0 right-0 p-3 bg-gradient-to-t from-black to-transparent">
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
