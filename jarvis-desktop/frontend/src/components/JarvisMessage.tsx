import { useMemo, useState } from 'react';
import { motion } from 'framer-motion';
import { Brain, ScanSearch, Save, ChevronDown, ChevronUp } from 'lucide-react';
import { parseJarvis } from '@/lib/jarvisProtocol';
import type { JarvisBlock } from '@/lib/jarvisProtocol';
import { EnhancedMarkdown } from './EnhancedMarkdown';
import { CodeCanvas } from './CodeCanvas';
import { JarvisImage } from './JarvisImage';
import { RichInline } from './RichInline';

interface JarvisMessageProps {
  content: string;
}

/**
 * Renders assistant messages that follow the JARVIS structured-output
 * protocol. Plain markdown messages fall straight through to the
 * standard markdown renderer (backward compatible).
 */
export function JarvisMessage({ content }: JarvisMessageProps) {
  const result = useMemo(() => parseJarvis(content), [content]);

  if (!result.structured) {
    return <EnhancedMarkdown content={content} />;
  }

  return (
    <div className="space-y-2.5">
      {result.blocks.map((block, index) => (
        <BlockView key={index} block={block} streaming={result.truncated} />
      ))}
    </div>
  );
}

function BlockView({ block, streaming }: { block: JarvisBlock; streaming: boolean }) {
  switch (block.kind) {
    case 'text':
      return <EnhancedMarkdown content={block.raw} />;
    case 'think':
      return (
        <CollapseCard
          kind="think"
          content={block.raw}
          streaming={!block.closed}
          forceOpen={streaming && !block.closed}
        />
      );
    case 'analyze':
      return (
        <CollapseCard
          kind="analyze"
          content={block.raw}
          streaming={!block.closed}
          forceOpen={streaming && !block.closed}
        />
      );
    case 'saved':
      return (
        <CollapseCard
          kind="saved"
          content={block.raw}
          streaming={!block.closed}
          forceOpen={streaming && !block.closed}
        />
      );
    case 'response':
      return <EnhancedMarkdown content={block.raw} />;
    case 'code':
      return <CodeCanvas code={block.code} language={block.language} />;
    case 'canvas':
      return <EnhancedMarkdown content={block.raw} />;
    case 'image':
      return <JarvisImage src={block.src} title={block.title} />;
    default:
      return null;
  }
}

type CollapseKind = 'think' | 'analyze' | 'saved';

const COLLAPSE_CONFIG: Record<CollapseKind, { label: string; icon: typeof Brain; accent: string; bg: string }> = {
  think: {
    label: 'Thinking',
    icon: Brain,
    accent: 'text-blue-400',
    bg: 'bg-blue-500/10 border-blue-400/20',
  },
  analyze: {
    label: 'Analysis',
    icon: ScanSearch,
    accent: 'text-cyan-300',
    bg: 'bg-cyan-500/10 border-cyan-400/20',
  },
  saved: {
    label: 'Saved to memory',
    icon: Save,
    accent: 'text-emerald-400',
    bg: 'bg-emerald-500/10 border-emerald-400/20',
  },
};

interface CollapseCardProps {
  kind: CollapseKind;
  content: string;
  /** block is still being streamed (opening tag seen, closing not yet) */
  streaming: boolean;
  /** while streaming the content stays visible so the user watches it type */
  forceOpen: boolean;
}

function CollapseCard({ kind, content, streaming, forceOpen }: CollapseCardProps) {
  const [open, setOpen] = useState(false);
  const config = COLLAPSE_CONFIG[kind];
  const Icon = config.icon;
  const isOpen = forceOpen || open;
  const lines = content.split('\n').filter((line) => line.trim().length > 0);

  return (
    <motion.div
      initial={{ opacity: 0, y: 6 }}
      animate={{ opacity: 1, y: 0 }}
      className={`overflow-hidden rounded-lg border ${config.bg}`}
    >
      <button
        onClick={() => setOpen((v) => !v)}
        disabled={forceOpen}
        className="flex w-full items-center gap-2 px-2.5 py-1.5 text-left transition-colors hover:bg-white/5"
      >
        <Icon size={13} className={config.accent} />
        <span className="text-[11px] font-medium uppercase tracking-wider text-jarvis-textMuted">
          {config.label}
        </span>
        <span className="ml-auto flex items-center gap-1.5">
          {streaming && <span className="h-1 w-1 animate-pulse rounded-full bg-jarvis-accentPink" />}
          {!forceOpen &&
            (isOpen ? (
              <ChevronUp size={13} className="text-jarvis-textMuted" />
            ) : (
              <ChevronDown size={13} className="text-jarvis-textMuted" />
            ))}
        </span>
      </button>

      {isOpen && (
        <div className="max-h-64 space-y-1 overflow-y-auto px-3 pb-2.5 text-xs leading-relaxed">
          {lines.map((line, index) => (
            <p key={index} className={kind === 'saved' ? 'text-jarvis-textMuted' : 'text-jarvis-textMuted/90'}>
              <span className={config.accent}>{kind === 'saved' ? '✓ ' : ''}</span>
              <RichInline text={line} />
            </p>
          ))}
        </div>
      )}
    </motion.div>
  );
}