import { useMemo } from 'react';
import type { ReactNode } from 'react';
import { motion } from 'framer-motion';
import { ExternalLink } from 'lucide-react';
import { parseInline, isSafeUrl } from '@/lib/jarvisProtocol';
import type { JarvisInlineNode } from '@/lib/jarvisProtocol';

interface RichInlineProps {
  text: string;
}

/**
 * Renders inline text with BOTH JARVIS formatting tags
 * (<b>, <i>, <u>, <lthrough>, <color name="...">) and standard
 * markdown inline styles (**bold**, *italic*, `code`, ~~strike~~,
 * ==highlight==, [links](url)). Links are only rendered for http(s)
 * URLs; anything else stays plain text.
 */
export function RichInline({ text }: RichInlineProps) {
  const nodes = useMemo(() => parseInline(text), [text]);
  return <>{nodes.map((node, index) => <InlineNode key={index} node={node} />)}</>;
}

function InlineNode({ node }: { node: JarvisInlineNode }) {
  switch (node.type) {
    case 'text':
      return <MarkdownSegment text={node.text} />;
    case 'bold':
      return <strong className="font-semibold text-jarvis-text">{renderChildren(node.children)}</strong>;
    case 'italic':
      return <em className="italic">{renderChildren(node.children)}</em>;
    case 'underline':
      return <span className="underline underline-offset-2">{renderChildren(node.children)}</span>;
    case 'strikethrough':
      return <span className="line-through opacity-60">{renderChildren(node.children)}</span>;
    case 'color':
      return (
        <span style={{ color: node.color || undefined }}>{renderChildren(node.children)}</span>
      );
    default:
      return null;
  }
}

function renderChildren(children: JarvisInlineNode[]): ReactNode {
  return children.map((child, index) => <InlineNode key={index} node={child} />);
}

interface SegmentStyle {
  type: 'plain' | 'bold' | 'italic' | 'code' | 'strike' | 'highlight' | 'link';
  content: ReactNode;
  url?: string;
}

const MARKDOWN_PATTERNS: Array<{ type: SegmentStyle['type']; regex: RegExp }> = [
  { type: 'link', regex: /\[([^\]]+)\]\(([^)]+)\)/ },
  { type: 'bold', regex: /\*\*(.+?)\*\*/ },
  { type: 'italic', regex: /\*(.+?)\*/ },
  { type: 'code', regex: /`(.+?)`/ },
  { type: 'strike', regex: /~~(.+?)~~/ },
  { type: 'highlight', regex: /==(.+?)==/ },
];

function MarkdownSegment({ text }: { text: string }) {
  const parts = useMemo(() => segmentMarkdown(text), [text]);
  return (
    <>
      {parts.map((part, index) => {
        switch (part.type) {
          case 'link':
            return part.url && isSafeUrl(part.url) ? (
              <motion.a
                key={index}
                href={part.url}
                target="_blank"
                rel="noopener noreferrer"
                className="inline-flex items-center gap-1 rounded-md border border-jarvis-accentPink/30 bg-jarvis-accentPink/15 px-2 py-0.5 text-sm font-medium text-jarvis-accentPink transition-colors hover:bg-jarvis-accentPink/25"
                whileHover={{ scale: 1.01 }}
                whileTap={{ scale: 0.98 }}
                onClick={(e) => e.stopPropagation()}
              >
                <ExternalLink size={13} />
                {part.content}
              </motion.a>
            ) : (
              <span key={index} className="text-jarvis-textMuted underline">{part.content}</span>
            );
          case 'bold':
            return <strong key={index} className="font-semibold text-jarvis-text">{part.content}</strong>;
          case 'italic':
            return <em key={index} className="italic">{part.content}</em>;
          case 'code':
            return (
              <code key={index} className="font-mono bg-black/30 px-1.5 py-0.5 rounded text-[0.85em] text-jarvis-accentPink">
                {part.content}
              </code>
            );
          case 'strike':
            return <span key={index} className="line-through opacity-60">{part.content}</span>;
          case 'highlight':
            return <mark key={index} className="rounded bg-yellow-500/20 px-1 text-jarvis-text">{part.content}</mark>;
          default:
            return <span key={index}>{part.content}</span>;
        }
      })}
    </>
  );
}

function segmentMarkdown(text: string): MarkdownStyle[] {
  const parts: MarkdownStyle[] = [];
  let remaining = text;

  while (remaining) {
    let earliest: { pattern: (typeof MARKDOWN_PATTERNS)[0]; match: RegExpMatchArray; index: number } | null = null;

    for (const pattern of MARKDOWN_PATTERNS) {
      const match = remaining.match(pattern.regex);
      if (match && (!earliest || remaining.indexOf(match[0]) < earliest.index)) {
        earliest = { pattern, match, index: remaining.indexOf(match[0]) };
      }
    }

    if (!earliest || earliest.index === -1) {
      parts.push({ type: 'plain', content: remaining });
      break;
    }

    if (earliest.index > 0) {
      parts.push({ type: 'plain', content: remaining.slice(0, earliest.index) });
    }

    const { pattern, match } = earliest;
    if (pattern.type === 'link') {
      parts.push({ type: 'link', content: match[1], url: match[2] });
    } else {
      parts.push({ type: pattern.type, content: match[1] });
    }

    remaining = remaining.slice(earliest.index + match[0].length);
  }

  return parts;
}

type MarkdownStyle =
  | { type: 'plain'; content: string }
  | { type: 'bold' | 'italic' | 'code' | 'strike' | 'highlight'; content: string }
  | { type: 'link'; content: string; url: string };