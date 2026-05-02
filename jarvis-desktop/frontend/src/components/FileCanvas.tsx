import { useEffect, useMemo, useRef, useState } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import {
  Copy,
  Check,
  FileText,
  Maximize2,
  Minimize2,
  Download,
  PenSquare,
  Eye,
  RotateCcw,
  Search,
  WrapText,
  Bold,
  Italic,
  Heading1,
  List,
  ListOrdered,
  Quote,
  CheckSquare,
  Code2,
  Strikethrough,
} from 'lucide-react';

interface FileCanvasProps {
  content: string;
  filename?: string;
  fileType?: string;
}

export function FileCanvas({ content, filename, fileType }: FileCanvasProps) {
  const [copied, setCopied] = useState(false);
  const [isExpanded, setIsExpanded] = useState(false);
  const [isMinimized, setIsMinimized] = useState(false);
  const [isEditing, setIsEditing] = useState(false);
  const [isPreview, setIsPreview] = useState(false);
  const [wrapText, setWrapText] = useState(true);
  const [searchQuery, setSearchQuery] = useState('');
  const [draft, setDraft] = useState(content);
  const textareaRef = useRef<HTMLTextAreaElement>(null);

  useEffect(() => {
    setDraft(content);
  }, [content]);

  const lineCount = draft.split('\n').length;
  const wordCount = useMemo(() => draft.trim().split(/\s+/).filter(Boolean).length, [draft]);
  const charCount = draft.length;
  const visibleContent = isExpanded ? draft : draft.slice(0, 3500);
  const isTruncated = draft.length > 3500 && !isExpanded;
  const previewHeight = isExpanded ? 'min(72vh, 820px)' : '300px';
  const searchMatches = searchQuery
    ? (draft.toLowerCase().match(new RegExp(escapeRegExp(searchQuery.toLowerCase()), 'g')) ?? []).length
    : 0;

  const handleCopy = async () => {
    try {
      await navigator.clipboard.writeText(draft);
      setCopied(true);
      window.setTimeout(() => setCopied(false), 2000);
    } catch (err) {
      console.error('Failed to copy:', err);
    }
  };

  const handleDownload = () => {
    const blob = new Blob([draft], { type: 'text/plain' });
    const url = URL.createObjectURL(blob);
    const anchor = document.createElement('a');
    anchor.href = url;
    anchor.download = filename || 'file.txt';
    document.body.appendChild(anchor);
    anchor.click();
    document.body.removeChild(anchor);
    URL.revokeObjectURL(url);
  };

  const applyFormat = (type: FormatType) => {
    if (!textareaRef.current) {
      return;
    }

    const textarea = textareaRef.current;
    const selectionStart = textarea.selectionStart;
    const selectionEnd = textarea.selectionEnd;
    const selectedText = draft.slice(selectionStart, selectionEnd);
    const { nextText, nextSelectionStart, nextSelectionEnd } = formatSelection(
      draft,
      selectionStart,
      selectionEnd,
      selectedText,
      type
    );

    setDraft(nextText);
    setIsEditing(true);

    requestAnimationFrame(() => {
      textarea.focus();
      textarea.setSelectionRange(nextSelectionStart, nextSelectionEnd);
    });
  };

  const resetDraft = () => {
    setDraft(content);
  };

  if (isMinimized) {
    return (
      <motion.div
        initial={{ opacity: 0, scale: 0.9 }}
        animate={{ opacity: 1, scale: 1 }}
        className="cursor-pointer rounded-xl border border-white/10 bg-white/5 p-3 transition-colors hover:bg-white/10"
        onClick={() => setIsMinimized(false)}
      >
        <div className="flex items-center justify-between gap-3">
          <div className="flex items-center gap-3">
            <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-jarvis-accentPink/20">
              <FileText size={20} className="text-jarvis-accentPink" />
            </div>
            <div>
              <p className="text-sm font-medium text-jarvis-text">{filename || 'File Content'}</p>
              <p className="text-xs text-jarvis-textMuted">{lineCount} lines • Click to expand</p>
            </div>
          </div>
          <Maximize2 size={18} className="text-jarvis-textMuted" />
        </div>
      </motion.div>
    );
  }

  return (
    <>
      <AnimatePresence>
        {isExpanded && (
          <motion.div
            className="fixed inset-0 z-40 bg-black/50 backdrop-blur-sm"
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            onClick={() => setIsExpanded(false)}
          />
        )}
      </AnimatePresence>

      <motion.div
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        className={`overflow-hidden rounded-xl border border-white/10 bg-white/5 ${
          isExpanded ? 'fixed inset-4 z-50 bg-jarvis-bg shadow-2xl shadow-jarvis-accentPink/10' : 'relative'
        }`}
      >
        <div className="border-b border-white/10 bg-[linear-gradient(90deg,rgba(255,110,199,0.08),rgba(59,130,246,0.06),rgba(255,255,255,0.04))] px-4 py-3">
          <div className="flex flex-wrap items-center justify-between gap-3">
            <div className="flex min-w-0 items-center gap-3">
              <div className="flex h-9 w-9 items-center justify-center rounded-lg bg-jarvis-accentPink/20">
                <FileText size={18} className="text-jarvis-accentPink" />
              </div>
              <div className="min-w-0">
                <p className="truncate text-sm font-medium text-jarvis-text">{filename || 'File Content'}</p>
                <div className="mt-1 flex flex-wrap items-center gap-3 text-xs text-jarvis-textMuted">
                  <span>{lineCount} lines</span>
                  <span>{wordCount} words</span>
                  <span>{charCount} chars</span>
                  <span>{fileType || 'text'}</span>
                </div>
              </div>
            </div>

            <div className="flex flex-wrap items-center gap-1">
              <button
                onClick={() => setIsEditing((value) => !value)}
                className={`rounded-lg p-2 transition-colors ${isEditing ? 'bg-jarvis-accentPink/20 text-jarvis-accentPink' : 'hover:bg-white/10 text-jarvis-textMuted'}`}
                title="Toggle edit mode"
              >
                <PenSquare size={16} />
              </button>
              <button
                onClick={() => setIsPreview((value) => !value)}
                className={`rounded-lg p-2 transition-colors ${isPreview ? 'bg-cyan-400/15 text-cyan-300' : 'hover:bg-white/10 text-jarvis-textMuted'}`}
                title="Toggle preview"
              >
                <Eye size={16} />
              </button>
              <button
                onClick={() => setWrapText((value) => !value)}
                className={`rounded-lg p-2 transition-colors ${wrapText ? 'bg-white/10 text-jarvis-text' : 'hover:bg-white/10 text-jarvis-textMuted'}`}
                title="Toggle line wrap"
              >
                <WrapText size={16} />
              </button>
              <button onClick={handleCopy} className="rounded-lg p-2 transition-colors hover:bg-white/10" title="Copy content">
                {copied ? <Check size={16} className="text-green-500" /> : <Copy size={16} className="text-jarvis-textMuted" />}
              </button>
              <button onClick={handleDownload} className="rounded-lg p-2 transition-colors hover:bg-white/10" title="Download file">
                <Download size={16} className="text-jarvis-textMuted" />
              </button>
              <button onClick={resetDraft} className="rounded-lg p-2 transition-colors hover:bg-white/10" title="Reset changes">
                <RotateCcw size={16} className="text-jarvis-textMuted" />
              </button>
              <button
                onClick={() => (isExpanded ? setIsExpanded(false) : setIsMinimized(true))}
                className="rounded-lg p-2 transition-colors hover:bg-white/10"
                title={isExpanded ? 'Collapse' : 'Minimize'}
              >
                {isExpanded ? <Minimize2 size={16} className="text-jarvis-textMuted" /> : <Maximize2 size={16} className="text-jarvis-textMuted" />}
              </button>
            </div>
          </div>

          <div className="mt-3 flex flex-wrap items-center gap-2">
            <div className="relative min-w-[220px] flex-1 max-w-sm">
              <Search size={14} className="absolute left-3 top-1/2 -translate-y-1/2 text-jarvis-textMuted" />
              <input
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                placeholder="Search inside text canvas..."
                className="w-full rounded-lg border border-white/10 bg-black/30 py-2 pl-9 pr-3 text-sm text-jarvis-text outline-none transition-colors focus:border-jarvis-accentPink/40"
              />
            </div>
            <span className="rounded-full border border-white/10 bg-black/20 px-3 py-1 text-xs text-jarvis-textMuted">
              {searchQuery ? `${searchMatches} matches` : 'Search ready'}
            </span>
          </div>

          <div className="mt-3 flex flex-wrap gap-2">
            {[
              { type: 'bold' as const, icon: Bold, label: 'Bold' },
              { type: 'italic' as const, icon: Italic, label: 'Italic' },
              { type: 'strike' as const, icon: Strikethrough, label: 'Strike' },
              { type: 'heading' as const, icon: Heading1, label: 'Heading' },
              { type: 'bullet' as const, icon: List, label: 'Bullet' },
              { type: 'number' as const, icon: ListOrdered, label: 'Numbered' },
              { type: 'quote' as const, icon: Quote, label: 'Quote' },
              { type: 'checkbox' as const, icon: CheckSquare, label: 'Checklist' },
              { type: 'code' as const, icon: Code2, label: 'Inline Code' },
            ].map((tool) => {
              const Icon = tool.icon;
              return (
                <button
                  key={tool.type}
                  onClick={() => applyFormat(tool.type)}
                  className="flex items-center gap-2 rounded-lg border border-white/10 bg-black/25 px-3 py-2 text-xs text-jarvis-textMuted transition-colors hover:border-jarvis-accentPink/30 hover:bg-white/10 hover:text-jarvis-text"
                  title={`Apply ${tool.label}`}
                >
                  <Icon size={14} />
                  {tool.label}
                </button>
              );
            })}
          </div>
        </div>

        <div className="relative" style={{ height: previewHeight }}>
          {isPreview ? (
            <div className="h-full overflow-auto bg-black/25 p-5">
              <div className="mx-auto max-w-4xl">
                <SimpleMarkdownPreview content={highlightMatches(visibleContent, searchQuery)} />
              </div>
            </div>
          ) : (
            <textarea
              ref={textareaRef}
              readOnly={!isEditing}
              value={highlightPlaceholder(visibleContent, searchQuery)}
              onChange={(e) => setDraft(e.target.value)}
              className={`h-full w-full resize-none bg-black/30 p-4 text-sm leading-relaxed text-jarvis-text focus:outline-none ${
                wrapText ? 'whitespace-pre-wrap' : 'whitespace-pre font-mono'
              } ${isEditing ? 'cursor-text' : 'cursor-default'}`}
              spellCheck={isEditing}
            />
          )}

          {isTruncated && (
            <div className="absolute inset-x-0 bottom-0 p-3 bg-gradient-to-t from-black to-transparent">
              <button
                onClick={() => setIsExpanded(true)}
                className="w-full rounded-lg bg-jarvis-accentPink/20 py-2 text-sm font-medium text-jarvis-accentPink transition-colors hover:bg-jarvis-accentPink/30"
              >
                Show all {lineCount} lines
              </button>
            </div>
          )}
        </div>
      </motion.div>
    </>
  );
}

type FormatType = 'bold' | 'italic' | 'strike' | 'heading' | 'bullet' | 'number' | 'quote' | 'checkbox' | 'code';

function formatSelection(
  source: string,
  selectionStart: number,
  selectionEnd: number,
  selectedText: string,
  type: FormatType
) {
  const before = source.slice(0, selectionStart);
  const after = source.slice(selectionEnd);
  const fallback = selectedText || getPlaceholder(type);

  switch (type) {
    case 'bold': {
      const wrapped = `**${fallback}**`;
      return replaceSelection(before, after, wrapped, selectionStart + 2, selectionStart + 2 + fallback.length);
    }
    case 'italic': {
      const wrapped = `*${fallback}*`;
      return replaceSelection(before, after, wrapped, selectionStart + 1, selectionStart + 1 + fallback.length);
    }
    case 'strike': {
      const wrapped = `~~${fallback}~~`;
      return replaceSelection(before, after, wrapped, selectionStart + 2, selectionStart + 2 + fallback.length);
    }
    case 'heading': {
      const wrapped = `# ${fallback}`;
      return replaceSelection(before, after, wrapped, selectionStart + 2, selectionStart + 2 + fallback.length);
    }
    case 'bullet': {
      const lines = fallback.split('\n').map((line) => `- ${line}`).join('\n');
      return replaceSelection(before, after, lines, selectionStart, selectionStart + lines.length);
    }
    case 'number': {
      const lines = fallback.split('\n').map((line, index) => `${index + 1}. ${line}`).join('\n');
      return replaceSelection(before, after, lines, selectionStart, selectionStart + lines.length);
    }
    case 'quote': {
      const lines = fallback.split('\n').map((line) => `> ${line}`).join('\n');
      return replaceSelection(before, after, lines, selectionStart, selectionStart + lines.length);
    }
    case 'checkbox': {
      const lines = fallback.split('\n').map((line) => `- [ ] ${line}`).join('\n');
      return replaceSelection(before, after, lines, selectionStart, selectionStart + lines.length);
    }
    case 'code': {
      const wrapped = `\`${fallback}\``;
      return replaceSelection(before, after, wrapped, selectionStart + 1, selectionStart + 1 + fallback.length);
    }
  }
}

function replaceSelection(
  before: string,
  after: string,
  inserted: string,
  nextSelectionStart: number,
  nextSelectionEnd: number
) {
  return {
    nextText: `${before}${inserted}${after}`,
    nextSelectionStart,
    nextSelectionEnd,
  };
}

function getPlaceholder(type: FormatType) {
  switch (type) {
    case 'heading':
      return 'Heading';
    case 'code':
      return 'code';
    case 'checkbox':
      return 'Task';
    default:
      return 'text';
  }
}

function escapeRegExp(value: string) {
  return value.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
}

function highlightPlaceholder(content: string, searchQuery: string) {
  if (!searchQuery) {
    return content;
  }

  return content;
}

function highlightMatches(content: string, searchQuery: string) {
  if (!searchQuery) {
    return content;
  }

  const regex = new RegExp(`(${escapeRegExp(searchQuery)})`, 'gi');
  return content.replace(regex, '==$1==');
}

function SimpleMarkdownPreview({ content }: { content: string }) {
  const lines = content.split('\n');
  const elements: React.ReactNode[] = [];
  let key = 0;

  for (const line of lines) {
    const trimmed = line.trim();

    if (!trimmed) {
      elements.push(<div key={key++} className="h-3" />);
      continue;
    }

    if (trimmed.startsWith('# ')) {
      elements.push(
        <h1 key={key++} className="mb-3 text-2xl font-bold gradient-text">
          {renderInline(trimmed.slice(2))}
        </h1>
      );
      continue;
    }

    if (trimmed.startsWith('## ')) {
      elements.push(
        <h2 key={key++} className="mb-3 text-xl font-semibold text-jarvis-text">
          {renderInline(trimmed.slice(3))}
        </h2>
      );
      continue;
    }

    if (trimmed.startsWith('> ')) {
      elements.push(
        <blockquote key={key++} className="my-2 rounded-r-lg border-l-4 border-jarvis-accentPink bg-white/5 px-4 py-2 text-jarvis-text italic">
          {renderInline(trimmed.slice(2))}
        </blockquote>
      );
      continue;
    }

    if (trimmed.startsWith('- [ ] ') || trimmed.startsWith('- [x] ')) {
      const checked = trimmed.startsWith('- [x] ');
      const text = trimmed.slice(6);
      elements.push(
        <div key={key++} className="flex items-center gap-3 py-1 text-sm text-jarvis-text">
          <span className={`flex h-5 w-5 items-center justify-center rounded border text-xs ${checked ? 'border-jarvis-accentPink bg-jarvis-accentPink text-white' : 'border-white/30'}`}>
            {checked ? '✓' : ''}
          </span>
          <span className={checked ? 'line-through opacity-60' : ''}>{renderInline(text)}</span>
        </div>
      );
      continue;
    }

    if (trimmed.startsWith('- ')) {
      elements.push(
        <div key={key++} className="flex items-start gap-3 py-1">
          <span className="mt-1 text-jarvis-accentPink">•</span>
          <span className="text-sm text-jarvis-text">{renderInline(trimmed.slice(2))}</span>
        </div>
      );
      continue;
    }

    const numbered = trimmed.match(/^(\d+)\.\s(.+)$/);
    if (numbered) {
      elements.push(
        <div key={key++} className="flex items-start gap-3 py-1">
          <span className="mt-0.5 text-sm font-semibold text-jarvis-accentPink">{numbered[1]}.</span>
          <span className="text-sm text-jarvis-text">{renderInline(numbered[2])}</span>
        </div>
      );
      continue;
    }

    elements.push(
      <p key={key++} className="py-1 text-sm leading-relaxed text-jarvis-text">
        {renderInline(line)}
      </p>
    );
  }

  return <div>{elements}</div>;
}

function renderInline(text: string): React.ReactNode {
  const parts: React.ReactNode[] = [];
  const pattern = /(\*\*.+?\*\*|\*.+?\*|~~.+?~~|`.+?`|==.+?==)/g;
  const segments = text.split(pattern).filter(Boolean);

  segments.forEach((segment, index) => {
    if (segment.startsWith('**') && segment.endsWith('**')) {
      parts.push(<strong key={index} className="font-semibold text-white">{segment.slice(2, -2)}</strong>);
    } else if (segment.startsWith('*') && segment.endsWith('*')) {
      parts.push(<em key={index} className="italic text-slate-100">{segment.slice(1, -1)}</em>);
    } else if (segment.startsWith('~~') && segment.endsWith('~~')) {
      parts.push(<span key={index} className="line-through opacity-60">{segment.slice(2, -2)}</span>);
    } else if (segment.startsWith('`') && segment.endsWith('`')) {
      parts.push(<code key={index} className="rounded bg-black/40 px-1.5 py-0.5 font-mono text-xs text-cyan-300">{segment.slice(1, -1)}</code>);
    } else if (segment.startsWith('==') && segment.endsWith('==')) {
      parts.push(<span key={index} className="rounded bg-yellow-500/20 px-1 text-yellow-100">{segment.slice(2, -2)}</span>);
    } else {
      parts.push(<span key={index}>{segment}</span>);
    }
  });

  return <>{parts}</>;
}
