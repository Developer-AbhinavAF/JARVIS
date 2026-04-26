import { useState } from 'react';
import { motion } from 'framer-motion';
import { Copy, Check, Code, FileText, Maximize2, Minimize2, ExternalLink } from 'lucide-react';
import { CodeCanvas } from './CodeCanvas';
import { FileCanvas } from './FileCanvas';

interface EnhancedMarkdownProps {
  content: string;
  className?: string;
}

export function EnhancedMarkdown({ content, className = '' }: EnhancedMarkdownProps) {
  return (
    <div className={`enhanced-markdown space-y-3 ${className}`}>
      <MarkdownContent content={content} />
    </div>
  );
}

function MarkdownContent({ content }: { content: string }) {
  const lines = content.split('\n');
  const elements: React.ReactNode[] = [];
  let key = 0;

  for (let i = 0; i < lines.length; i++) {
    const line = lines[i];
    const trimmed = line.trim();

    // Code blocks
    if (trimmed.startsWith('```')) {
      const language = trimmed.slice(3).trim();
      let code = '';
      i++;
      while (i < lines.length && !lines[i].trim().startsWith('```')) {
        code += lines[i] + '\n';
        i++;
      }
      elements.push(
        <CodeCanvas key={key++} code={code.trim()} language={language || 'text'} />
      );
      continue;
    }

    // File canvas blocks
    if (trimmed.startsWith('~~~')) {
      const fileInfo = trimmed.slice(3).trim();
      let fileContent = '';
      i++;
      while (i < lines.length && !lines[i].trim().startsWith('~~~')) {
        fileContent += lines[i] + '\n';
        i++;
      }
      elements.push(
        <FileCanvas key={key++} content={fileContent.trim()} filename={fileInfo} />
      );
      continue;
    }

    // Headings
    if (trimmed.startsWith('# ')) {
      elements.push(
        <h1 key={key++} className="text-2xl font-bold text-jarvis-text mt-6 mb-4 gradient-text">
          {parseInlineStyles(trimmed.slice(2))}
        </h1>
      );
      continue;
    }
    if (trimmed.startsWith('## ')) {
      elements.push(
        <h2 key={key++} className="text-xl font-semibold text-jarvis-text mt-5 mb-3 border-b border-white/10 pb-2">
          {parseInlineStyles(trimmed.slice(3))}
        </h2>
      );
      continue;
    }
    if (trimmed.startsWith('### ')) {
      elements.push(
        <h3 key={key++} className="text-lg font-medium mt-4 mb-2 text-jarvis-accentPink">
          {parseInlineStyles(trimmed.slice(4))}
        </h3>
      );
      continue;
    }

    // Numbered lists with colored bullets
    const numberedMatch = trimmed.match(/^(\d+)[.)]\s*(.+)$/);
    if (numberedMatch) {
      const num = parseInt(numberedMatch[1]);
      const text = numberedMatch[2];
      const bulletColors = ['⏺️', '🔴', '🟠', '🟡', '🟢', '🔵', '🟣'];
      const bullet = bulletColors[(num - 1) % bulletColors.length];
      
      elements.push(
        <motion.div
          key={key++}
          initial={{ opacity: 0, x: -20 }}
          animate={{ opacity: 1, x: 0 }}
          transition={{ delay: num * 0.05 }}
          className="flex items-start gap-3 py-2"
        >
          <span className="text-lg shrink-0">{bullet}</span>
          <span className="text-jarvis-text mt-0.5">{parseInlineStyles(text)}</span>
        </motion.div>
      );
      continue;
    }

    // Bullet lists
    if (trimmed.startsWith('- ') || trimmed.startsWith('• ') || trimmed.startsWith('* ')) {
      const text = trimmed.slice(2);
      const bullets = ['⏺️', '◆', '▸', '•'];
      const bullet = bullets[key % bullets.length];
      
      elements.push(
        <motion.div
          key={key++}
          initial={{ opacity: 0, x: -10 }}
          animate={{ opacity: 1, x: 0 }}
          className="flex items-start gap-3 py-1.5 pl-4"
        >
          <span className="text-jarvis-accentPink shrink-0 mt-1">{bullet}</span>
          <span className="text-jarvis-text">{parseInlineStyles(text)}</span>
        </motion.div>
      );
      continue;
    }

    // Checkboxes
    if (trimmed.startsWith('- [ ] ') || trimmed.startsWith('- [x] ')) {
      const isChecked = trimmed.startsWith('- [x] ');
      const text = trimmed.slice(6);
      
      elements.push(
        <div key={key++} className="flex items-center gap-3 py-1.5 pl-4">
          <span className={`w-5 h-5 rounded border-2 flex items-center justify-center text-xs ${
            isChecked ? 'bg-jarvis-accentPink border-jarvis-accentPink text-white' : 'border-white/30'
          }`}>
            {isChecked && '✓'}
          </span>
          <span className={`text-jarvis-text ${isChecked ? 'line-through opacity-50' : ''}`}>
            {parseInlineStyles(text)}
          </span>
        </div>
      );
      continue;
    }

    // Horizontal rule
    if (trimmed === '---' || trimmed === '***' || trimmed === '___') {
      elements.push(
        <hr key={key++} className="my-6 border-white/10" />
      );
      continue;
    }

    // Blockquote
    if (trimmed.startsWith('> ')) {
      elements.push(
        <blockquote key={key++} className="border-l-4 border-jarvis-accentPink pl-4 py-2 my-3 bg-white/5 rounded-r-lg">
          <p className="text-jarvis-text italic">{parseInlineStyles(trimmed.slice(2))}</p>
        </blockquote>
      );
      continue;
    }

    // Regular text
    if (trimmed) {
      elements.push(
        <p key={key++} className="text-jarvis-text leading-relaxed py-1">
          {parseInlineStyles(line)}
        </p>
      );
    } else {
      elements.push(<div key={key++} className="h-2" />);
    }
  }

  return <>{elements}</>;
}

function parseInlineStyles(text: string): React.ReactNode {
  // Parse **bold**, *italic*, `code`, ~~strikethrough~~, ==highlight==, ^superscript^, [links](url)
  const parts: React.ReactNode[] = [];
  let remaining = text;
  let key = 0;

  const patterns = [
    { regex: /\[([^\]]+)\]\(([^)]+)\)/, type: 'link', class: '' }, // [text](url) - must be first
    { regex: /\*\*(.+?)\*\* /, type: 'bold', class: 'font-bold text-lg' },
    { regex: /\*(.+?)\* /, type: 'italic', class: 'italic' },
    { regex: /`(.+?)`/, type: 'code', class: 'font-mono bg-black/30 px-1.5 py-0.5 rounded text-sm text-jarvis-accentPink' },
    { regex: /~~(.+?)~~/, type: 'strike', class: 'line-through opacity-50' },
    { regex: /==(.+?)==/, type: 'highlight', class: 'bg-yellow-500/20 px-1 rounded' },
    { regex: /\^(.+?)\^/, type: 'sup', class: 'text-xs align-super text-jarvis-accentPink' },
    { regex: /~(.+?)~/, type: 'sub', class: 'text-xs align-sub' },
  ];

  while (remaining) {
    let earliestMatch: { pattern: typeof patterns[0], match: RegExpMatchArray, index: number } | null = null;

    for (const pattern of patterns) {
      const match = remaining.match(pattern.regex);
      if (match && (!earliestMatch || (remaining.indexOf(match[0]) < earliestMatch.index))) {
        earliestMatch = { pattern, match, index: remaining.indexOf(match[0]) };
      }
    }

    if (earliestMatch && earliestMatch.index !== -1) {
      if (earliestMatch.index > 0) {
        parts.push(<span key={key++}>{remaining.slice(0, earliestMatch.index)}</span>);
      }

      const { pattern, match } = earliestMatch;
      
      // Handle links specially - render as clickable button
      if (pattern.type === 'link') {
        const linkText = match[1];
        const linkUrl = match[2];
        parts.push(
          <motion.a
            key={key++}
            href={linkUrl}
            target="_blank"
            rel="noopener noreferrer"
            className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-jarvis-accentPink/20 hover:bg-jarvis-accentPink/30 border border-jarvis-accentPink/40 text-jarvis-accentPink text-sm font-medium transition-all group"
            whileHover={{ scale: 1.02 }}
            whileTap={{ scale: 0.98 }}
            onClick={(e) => {
              e.stopPropagation();
              window.open(linkUrl, '_blank');
            }}
          >
            <ExternalLink size={14} className="group-hover:rotate-12 transition-transform" />
            {linkText}
          </motion.a>
        );
      } else {
        parts.push(
          <span key={key++} className={pattern.class}>
            {match[1]}
          </span>
        );
      }

      remaining = remaining.slice(earliestMatch.index + match[0].length);
    } else {
      parts.push(<span key={key++}>{remaining}</span>);
      break;
    }
  }

  return <>{parts}</>;
}
