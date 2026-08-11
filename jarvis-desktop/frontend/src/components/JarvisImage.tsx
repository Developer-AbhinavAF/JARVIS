import { useState } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { Maximize2, ImageOff } from 'lucide-react';
import { isSafeUrl } from '@/lib/jarvisProtocol';
import { ImageLightbox } from './ImageLightbox';

interface JarvisImageProps {
  src: string;
  title?: string;
}

/**
 * Renders a <image> protocol block: an inline preview that opens a
 * fullscreen lightbox (X / Esc / outside-click / scroll-lock) on click.
 * Non-http(s) sources are never rendered as images.
 */
export function JarvisImage({ src, title }: JarvisImageProps) {
  const [open, setOpen] = useState(false);
  const [failed, setFailed] = useState(false);

  if (!isSafeUrl(src)) {
    return <p className="text-xs italic text-jarvis-textMuted">[image omitted — unsupported source]</p>;
  }

  return (
    <>
      <motion.button
        initial={{ opacity: 0, y: 8 }}
        animate={{ opacity: 1, y: 0 }}
        className="group block max-w-full"
        onClick={() => setOpen(true)}
        aria-label={title || 'Open image fullscreen'}
      >
        {failed ? (
          <div className="flex aspect-video w-full max-w-md items-center justify-center gap-2 rounded-lg border border-white/10 bg-black/40 text-jarvis-textMuted">
            <ImageOff size={22} />
            <span className="text-xs">Image unavailable</span>
          </div>
        ) : (
          <img
            src={src}
            alt={title || 'JARVIS image'}
            className="max-h-80 w-auto max-w-full rounded-lg border border-white/10 object-contain shadow-lg shadow-black/40 transition-opacity group-hover:opacity-90"
            loading="lazy"
            onError={() => setFailed(true)}
          />
        )}
        <span className="mt-1.5 inline-flex items-center gap-1.5 text-[10px] font-medium text-jarvis-textMuted transition-colors group-hover:text-jarvis-accentPink">
          <Maximize2 size={12} />
          Click to view fullscreen
        </span>
      </motion.button>

      <AnimatePresence>
        {open && <ImageLightbox src={src} title={title} onClose={() => setOpen(false)} />}
      </AnimatePresence>
    </>
  );
}