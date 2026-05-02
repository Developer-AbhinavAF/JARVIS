import { useState, useRef, useEffect, useMemo } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import {
  Copy,
  Check,
  Code,
  Maximize2,
  Minimize2,
  Download,
  Sparkles,
  Search,
  WrapText,
  ScanSearch,
  Focus,
} from 'lucide-react';

interface CodeCanvasProps {
  code: string;
  language: string;
  filename?: string;
}

interface Token {
  text: string;
  className: string;
}

export function CodeCanvas({ code, language, filename }: CodeCanvasProps) {
  const [copied, setCopied] = useState(false);
  const [isExpanded, setIsExpanded] = useState(false);
  const [isMinimized, setIsMinimized] = useState(false);
  const [wrapLines, setWrapLines] = useState(false);
  const [plainMode, setPlainMode] = useState(false);
  const [searchQuery, setSearchQuery] = useState('');
  const [activeLine, setActiveLine] = useState<number | null>(null);
  const scrollRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (scrollRef.current) {
      scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
    }
  }, [code]);

  const handleCopy = async () => {
    try {
      await navigator.clipboard.writeText(code);
      setCopied(true);
      window.setTimeout(() => setCopied(false), 2000);
    } catch (err) {
      console.error('Failed to copy:', err);
    }
  };

  const handleDownload = () => {
    const blob = new Blob([code], { type: 'text/plain' });
    const url = URL.createObjectURL(blob);
    const anchor = document.createElement('a');
    anchor.href = url;
    anchor.download = filename || `code.${getExtension(language)}`;
    document.body.appendChild(anchor);
    anchor.click();
    document.body.removeChild(anchor);
    URL.revokeObjectURL(url);
  };

  const lineCount = code.split('\n').length;
  const charCount = code.length;
  const displayCode = isExpanded ? code : code.slice(0, 2500);
  const isTruncated = code.length > 2500 && !isExpanded;
  const previewHeight = 240;
  const calculatedHeight = lineCount * 24 + 48;
  const displayLines = displayCode.split('\n');
  const matchCount = useMemo(() => {
    if (!searchQuery) return 0;
    return (code.toLowerCase().match(new RegExp(escapeRegExp(searchQuery.toLowerCase()), 'g')) ?? []).length;
  }, [code, searchQuery]);

  if (isMinimized) {
    return (
      <motion.div
        initial={{ opacity: 0, scale: 0.9 }}
        animate={{ opacity: 1, scale: 1 }}
        className="cursor-pointer rounded-xl border border-jarvis-accentPink/20 bg-black/40 p-3 transition-colors hover:bg-white/10"
        onClick={() => setIsMinimized(false)}
      >
        <div className="flex items-center justify-between gap-3">
          <div className="flex items-center gap-3">
            <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-jarvis-accentPink/20">
              <Code size={20} className="text-jarvis-accentPink" />
            </div>
            <div>
              <p className="text-sm font-medium text-jarvis-text">{filename || `${language.toUpperCase()} Code`}</p>
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
        className={`overflow-hidden rounded-xl border border-jarvis-accentPink/30 bg-black/40 ${
          isExpanded ? 'fixed inset-4 z-50 bg-jarvis-bg shadow-2xl shadow-jarvis-accentPink/10' : 'relative max-h-[900px]'
        }`}
      >
        <div className="relative overflow-hidden border-b border-white/10 bg-[linear-gradient(90deg,rgba(255,110,199,0.08),rgba(255,59,59,0.06),rgba(59,130,246,0.06))] px-4 py-3">
          <motion.div
            className="absolute inset-y-0 left-[-30%] w-[30%] bg-gradient-to-r from-transparent via-white/10 to-transparent"
            animate={{ x: ['0%', '520%'] }}
            transition={{ duration: 5.2, repeat: Infinity, ease: 'linear' }}
          />
          <div className="relative flex flex-wrap items-center justify-between gap-3">
            <div className="flex min-w-0 items-center gap-3">
              <div className="flex h-9 w-9 items-center justify-center rounded-lg bg-jarvis-accentPink/20">
                <Code size={18} className="text-jarvis-accentPink" />
              </div>
              <div className="min-w-0">
                <div className="flex flex-wrap items-center gap-2">
                  <p className="truncate text-sm font-medium text-jarvis-text">{filename || language.toUpperCase()}</p>
                  <span className="rounded-full border border-cyan-400/20 bg-cyan-400/10 px-2 py-0.5 text-[10px] font-medium uppercase tracking-[0.2em] text-cyan-300">
                    {language}
                  </span>
                </div>
                <div className="mt-1 flex flex-wrap items-center gap-3 text-xs text-jarvis-textMuted">
                  <span>{lineCount} lines</span>
                  <span>{charCount} chars</span>
                  <span className="flex items-center gap-1 text-amber-300/90">
                    <Sparkles size={12} />
                    Syntax colored
                  </span>
                  {activeLine && <span className="text-jarvis-accentPink">Focused line {activeLine}</span>}
                </div>
              </div>
            </div>

            <div className="flex flex-wrap items-center gap-1">
              <button
                onClick={() => setWrapLines((value) => !value)}
                className={`rounded-lg p-2 transition-colors ${wrapLines ? 'bg-white/10 text-jarvis-text' : 'hover:bg-white/10 text-jarvis-textMuted'}`}
                title="Toggle wrap"
              >
                <WrapText size={16} />
              </button>
              <button
                onClick={() => setPlainMode((value) => !value)}
                className={`rounded-lg p-2 transition-colors ${plainMode ? 'bg-cyan-400/15 text-cyan-300' : 'hover:bg-white/10 text-jarvis-textMuted'}`}
                title="Toggle plain mode"
              >
                <ScanSearch size={16} />
              </button>
              <button
                onClick={() => setActiveLine(null)}
                className="rounded-lg p-2 transition-colors hover:bg-white/10 text-jarvis-textMuted"
                title="Clear line focus"
              >
                <Focus size={16} />
              </button>
              <button onClick={handleCopy} className="rounded-lg p-2 transition-colors hover:bg-white/10" title="Copy code">
                {copied ? <Check size={16} className="text-green-500" /> : <Copy size={16} className="text-jarvis-textMuted" />}
              </button>
              <button onClick={handleDownload} className="rounded-lg p-2 transition-colors hover:bg-white/10" title="Download">
                <Download size={16} className="text-jarvis-textMuted" />
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

          <div className="relative mt-3 max-w-sm">
            <Search size={14} className="absolute left-3 top-1/2 -translate-y-1/2 text-jarvis-textMuted" />
            <input
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              placeholder="Search inside code..."
              className="w-full rounded-lg border border-white/10 bg-black/30 py-2 pl-9 pr-3 text-sm text-jarvis-text outline-none transition-colors focus:border-jarvis-accentPink/40"
            />
            {searchQuery && (
              <span className="absolute right-3 top-1/2 -translate-y-1/2 text-[11px] text-jarvis-textMuted">
                {matchCount} matches
              </span>
            )}
          </div>
        </div>

        <div
          ref={scrollRef}
          className="relative overflow-auto bg-[radial-gradient(circle_at_top_right,rgba(255,110,199,0.08),transparent_35%),linear-gradient(180deg,rgba(3,7,18,0.95),rgba(2,6,23,0.98))]"
          style={{ height: isExpanded ? `${Math.min(calculatedHeight, 720)}px` : `${previewHeight}px` }}
        >
          <div className="pointer-events-none absolute inset-x-0 top-0 h-12 bg-gradient-to-b from-white/5 to-transparent" />
          <div className={`flex min-w-max font-mono text-sm leading-6 ${wrapLines ? 'items-start' : ''}`}>
            <div className="sticky left-0 z-10 flex flex-col border-r border-white/10 bg-slate-950/90 px-3 py-4 text-right text-xs text-slate-500 backdrop-blur">
              {displayLines.map((_, index) => (
                <button
                  key={`line-${index}`}
                  className={`h-6 select-none text-right transition-colors ${
                    activeLine === index + 1 ? 'text-jarvis-accentPink' : 'hover:text-slate-300'
                  }`}
                  onClick={() => setActiveLine(index + 1)}
                >
                  {index + 1}
                </button>
              ))}
            </div>

            <pre className={`m-0 min-w-full flex-1 px-4 py-4 text-jarvis-text ${wrapLines ? 'whitespace-pre-wrap break-words' : ''}`}>
              {displayLines.map((line, index) => (
                <div
                  key={`${index}-${line}`}
                  className={`min-h-6 ${wrapLines ? 'whitespace-pre-wrap break-words' : 'whitespace-pre'} ${
                    activeLine === index + 1 ? 'rounded bg-jarvis-accentPink/10 ring-1 ring-jarvis-accentPink/20' : ''
                  }`}
                >
                  {(plainMode ? [{ text: line, className: 'text-slate-200' }] : tokenizeLine(line, language)).map((token, tokenIndex) => (
                    <HighlightedToken
                      key={`${index}-${tokenIndex}`}
                      text={token.text}
                      className={token.className}
                      query={searchQuery}
                    />
                  ))}
                </div>
              ))}
            </pre>
          </div>

          {isTruncated && (
            <div className="absolute inset-x-0 bottom-0 p-4 bg-gradient-to-t from-slate-950 via-slate-950/90 to-transparent">
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

function HighlightedToken({ text, className, query }: { text: string; className: string; query: string }) {
  if (!query) {
    return <span className={className}>{text || ' '}</span>;
  }

  const regex = new RegExp(`(${escapeRegExp(query)})`, 'gi');
  const parts = text.split(regex);

  return (
    <>
      {parts.map((part, index) =>
        part.toLowerCase() === query.toLowerCase() ? (
          <mark key={`${part}-${index}`} className="rounded bg-yellow-400/30 px-0.5 text-yellow-100">
            {part}
          </mark>
        ) : (
          <span key={`${part}-${index}`} className={className}>
            {part || ' '}
          </span>
        )
      )}
    </>
  );
}

function tokenizeLine(line: string, language: string): Token[] {
  if (!line) {
    return [{ text: '', className: '' }];
  }

  const lang = language.toLowerCase();
  const commentPattern = getCommentPattern(lang);
  const stringPattern = /("(?:[^"\\]|\\.)*"|'(?:[^'\\]|\\.)*'|`(?:[^`\\]|\\.)*`)/g;
  const numberPattern = /\b\d+(?:\.\d+)?\b/g;
  const functionPattern = /\b([A-Za-z_]\w*)(?=\s*\()/g;
  const keywordPattern = new RegExp(`\\b(${getKeywords(lang).join('|')})\\b`, 'g');
  const constantPattern = /\b(true|false|null|undefined|None|True|False)\b/g;

  const tokens: Array<{ start: number; end: number; className: string }> = [];

  collectMatches(tokens, line, commentPattern, 'text-slate-500 italic');
  collectMatches(tokens, line, stringPattern, 'text-emerald-300');
  collectMatches(tokens, line, numberPattern, 'text-orange-300');
  collectMatches(tokens, line, constantPattern, 'text-fuchsia-300');
  collectMatches(tokens, line, keywordPattern, 'text-sky-300 font-semibold');
  collectMatches(tokens, line, functionPattern, 'text-amber-300');

  tokens.sort((a, b) => a.start - b.start || a.end - b.end);

  const result: Token[] = [];
  let cursor = 0;

  for (const token of tokens) {
    if (token.start < cursor) {
      continue;
    }

    if (token.start > cursor) {
      result.push({
        text: line.slice(cursor, token.start),
        className: 'text-slate-200',
      });
    }

    result.push({
      text: line.slice(token.start, token.end),
      className: token.className,
    });

    cursor = token.end;
  }

  if (cursor < line.length) {
    result.push({
      text: line.slice(cursor),
      className: 'text-slate-200',
    });
  }

  return result.length > 0 ? result : [{ text: line, className: 'text-slate-200' }];
}

function collectMatches(
  tokens: Array<{ start: number; end: number; className: string }>,
  line: string,
  pattern: RegExp | null,
  className: string
) {
  if (!pattern) {
    return;
  }

  const regex = new RegExp(pattern.source, pattern.flags);
  let match = regex.exec(line);

  while (match) {
    const text = match[0];
    const start = match.index;
    const end = start + text.length;

    if (!tokens.some((token) => start < token.end && end > token.start)) {
      tokens.push({ start, end, className });
    }

    if (!regex.global) {
      break;
    }

    match = regex.exec(line);
  }
}

function getCommentPattern(language: string): RegExp | null {
  if (['python', 'bash', 'shell', 'sql', 'yaml'].includes(language)) {
    return /#.*/g;
  }

  if (language === 'html') {
    return /<!--.*?-->/g;
  }

  return /\/\/.*/g;
}

function getKeywords(language: string): string[] {
  const shared = ['return', 'if', 'else', 'for', 'while', 'switch', 'case', 'break', 'continue'];

  if (['javascript', 'typescript', 'js', 'ts', 'jsx', 'tsx'].includes(language)) {
    return [...shared, 'const', 'let', 'var', 'function', 'async', 'await', 'import', 'from', 'export', 'class', 'new', 'try', 'catch', 'finally', 'typeof', 'instanceof'];
  }

  if (language === 'python') {
    return ['def', 'class', 'return', 'if', 'elif', 'else', 'for', 'while', 'async', 'await', 'import', 'from', 'as', 'try', 'except', 'finally', 'with', 'lambda', 'pass', 'yield'];
  }

  if (['html', 'xml'].includes(language)) {
    return ['div', 'span', 'script', 'style', 'head', 'body', 'html', 'section', 'button'];
  }

  if (language === 'css') {
    return ['display', 'position', 'color', 'background', 'border', 'padding', 'margin', 'flex', 'grid', 'transition', 'transform'];
  }

  if (language === 'json') {
    return [];
  }

  if (['bash', 'shell'].includes(language)) {
    return ['if', 'then', 'else', 'fi', 'for', 'do', 'done', 'case', 'esac', 'function'];
  }

  if (language === 'sql') {
    return ['select', 'from', 'where', 'join', 'left', 'right', 'insert', 'update', 'delete', 'group', 'by', 'order', 'limit', 'into', 'values'];
  }

  return shared;
}

function escapeRegExp(value: string) {
  return value.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
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
