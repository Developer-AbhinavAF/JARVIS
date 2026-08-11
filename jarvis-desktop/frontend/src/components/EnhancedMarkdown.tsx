import type { ReactNode } from 'react';
import { useState } from 'react';
import { AnimatePresence } from 'framer-motion';
import { CodeCanvas } from './CodeCanvas';
import { FileCanvas } from './FileCanvas';
import { RichInline } from './RichInline';
import { ImageLightbox } from './ImageLightbox';

interface EnhancedMarkdownProps {
  content: string;
  className?: string;
}

type ListItem = {
  text: string;
  checked?: boolean;
};

export function EnhancedMarkdown({ content, className = '' }: EnhancedMarkdownProps) {
  return (
    <div className={`enhanced-markdown space-y-3 text-sm leading-relaxed ${className}`}>
      <MarkdownContent content={content} />
    </div>
  );
}

function MarkdownContent({ content }: { content: string }) {
  const lines = content.split('\n');
  const elements: ReactNode[] = [];
  const [lightboxUrl, setLightboxUrl] = useState<string | null>(null);
  let key = 0;

  const readList = (start: number, type: 'ul' | 'ol' | 'check') => {
    const items: ListItem[] = [];
    let i = start;

    while (i < lines.length) {
      const trimmed = lines[i].trim();
      const checkboxMatch = trimmed.match(/^[-*]\s+\[( |x|X)\]\s+(.+)$/);
      const bulletMatch = trimmed.match(/^[-*]\s+(.+)$/);
      const numberedMatch = trimmed.match(/^\d+[.)]\s+(.+)$/);

      if (type === 'check' && checkboxMatch) {
        items.push({ text: checkboxMatch[2], checked: checkboxMatch[1].toLowerCase() === 'x' });
      } else if (type === 'ul' && bulletMatch && !checkboxMatch) {
        items.push({ text: bulletMatch[1] });
      } else if (type === 'ol' && numberedMatch) {
        items.push({ text: numberedMatch[1] });
      } else {
        break;
      }
      i++;
    }

    return { items, nextIndex: i - 1 };
  };

  for (let i = 0; i < lines.length; i++) {
    const line = lines[i];
    const trimmed = line.trim();

    if (trimmed.startsWith('```')) {
      const language = trimmed.slice(3).trim();
      let code = '';
      i++;
      while (i < lines.length && !lines[i].trim().startsWith('```')) {
        code += lines[i] + '\n';
        i++;
      }
      elements.push(<CodeCanvas key={key++} code={code.trim()} language={language || 'text'} />);
      continue;
    }

    if (trimmed.startsWith('~~~')) {
      const fileInfo = trimmed.slice(3).trim();
      let fileContent = '';
      i++;
      while (i < lines.length && !lines[i].trim().startsWith('~~~')) {
        fileContent += lines[i] + '\n';
        i++;
      }
      elements.push(<FileCanvas key={key++} content={fileContent.trim()} filename={fileInfo} />);
      continue;
    }

    if (trimmed.startsWith('# ')) {
      elements.push(
        <h1 key={key++} className="text-xl font-semibold text-jarvis-text mt-5 mb-3">
          {parseInlineStyles(trimmed.slice(2))}
        </h1>
      );
      continue;
    }

    if (trimmed.startsWith('## ')) {
      elements.push(
        <h2 key={key++} className="text-lg font-semibold text-jarvis-text mt-4 mb-2 border-b border-white/10 pb-2">
          {parseInlineStyles(trimmed.slice(3))}
        </h2>
      );
      continue;
    }

    if (trimmed.startsWith('### ')) {
      elements.push(
        <h3 key={key++} className="text-base font-semibold mt-3 mb-2 text-jarvis-accentPink">
          {parseInlineStyles(trimmed.slice(4))}
        </h3>
      );
      continue;
    }

    if (/^[-*]\s+\[( |x|X)\]\s+/.test(trimmed)) {
      const result = readList(i, 'check');
      elements.push(
        <ul key={key++} className="space-y-2 py-1">
          {result.items.map((item, idx) => (
            <li key={idx} className="flex items-start gap-3">
              <span
                className={`mt-0.5 flex h-4 w-4 shrink-0 items-center justify-center rounded border text-[10px] ${
                  item.checked
                    ? 'border-jarvis-accentPink bg-jarvis-accentPink text-white'
                    : 'border-white/30'
                }`}
              >
                {item.checked ? '✓' : ''}
              </span>
              <span className={item.checked ? 'text-jarvis-textMuted line-through' : 'text-jarvis-text'}>
                {parseInlineStyles(item.text)}
              </span>
            </li>
          ))}
        </ul>
      );
      i = result.nextIndex;
      continue;
    }

    if (/^[-*]\s+/.test(trimmed)) {
      const result = readList(i, 'ul');
      elements.push(
        <ul key={key++} className="list-disc space-y-1.5 py-1 pl-5 marker:text-jarvis-accentPink">
          {result.items.map((item, idx) => (
            <li key={idx} className="pl-1 text-jarvis-text">
              {parseInlineStyles(item.text)}
            </li>
          ))}
        </ul>
      );
      i = result.nextIndex;
      continue;
    }

    if (/^\d+[.)]\s+/.test(trimmed)) {
      const result = readList(i, 'ol');
      elements.push(
        <ol key={key++} className="list-decimal space-y-1.5 py-1 pl-5 marker:text-jarvis-accentPink marker:font-semibold">
          {result.items.map((item, idx) => (
            <li key={idx} className="pl-1 text-jarvis-text">
              {parseInlineStyles(item.text)}
            </li>
          ))}
        </ol>
      );
      i = result.nextIndex;
      continue;
    }

    if (trimmed === '---' || trimmed === '***' || trimmed === '___') {
      elements.push(<hr key={key++} className="my-5 border-white/10" />);
      continue;
    }

    if (trimmed.startsWith('> ')) {
      elements.push(
        <blockquote key={key++} className="my-3 rounded-r-lg border-l-4 border-jarvis-accentPink bg-white/5 py-2 pl-4">
          <p className="text-jarvis-text italic">{parseInlineStyles(trimmed.slice(2))}</p>
        </blockquote>
      );
      continue;
    }

    // Image detection: standalone image URL or "Image: <url>" line
    const imageMatch = trimmed.match(/^(?:image:\s*)?(https?:\/\/[^\s]+\.(?:jpg|jpeg|png|gif|webp|svg|bmp|tiff)(?:\?[^\s]*)?)$/i);
    if (imageMatch) {
      const imgUrl = imageMatch[1];
      elements.push(
        <div key={key++} className="my-3">
          <button
            onClick={() => setLightboxUrl(imgUrl)}
            className="group block cursor-pointer max-w-full"
            aria-label="Open image fullscreen"
          >
            <img
              src={imgUrl}
              alt="Generated image"
              className="max-w-full max-h-96 rounded-lg border border-white/10 object-contain transition-opacity group-hover:opacity-90"
              loading="lazy"
            />
            <span className="mt-1 inline-block text-[10px] text-jarvis-textMuted group-hover:text-jarvis-accentPink">
              ⤢ View fullscreen
            </span>
          </button>
        </div>
      );
      continue;
    }

    if (trimmed) {
      elements.push(
        <p key={key++} className="text-jarvis-text">
          {parseInlineStyles(line)}
        </p>
      );
    } else {
      elements.push(<div key={key++} className="h-1" />);
    }
  }

  return (
    <>
      {elements}
      <AnimatePresence>
        {lightboxUrl && <ImageLightbox src={lightboxUrl} onClose={() => setLightboxUrl(null)} />}
      </AnimatePresence>
    </>
  );
}

function parseInlineStyles(text: string): ReactNode {
  return <RichInline text={text} />;
}
