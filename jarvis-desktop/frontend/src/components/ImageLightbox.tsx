import { useEffect, useState } from 'react';
import { motion } from 'framer-motion';
import { X, ImageOff, ZoomIn } from 'lucide-react';

interface ImageLightboxProps {
  src: string;
  title?: string;
  onClose: () => void;
}

/**
 * Fullscreen image viewer. Closes via the X button (top-right),
 * the Escape key, or clicking outside the image. Scroll is locked
 * while open.
 */
export function ImageLightbox({ src, title, onClose }: ImageLightboxProps) {
  const [failed, setFailed] = useState(false);

  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      if (e.key === 'Escape') onClose();
    };
    window.addEventListener('keydown', onKey);
    const prevOverflow = document.body.style.overflow;
    document.body.style.overflow = 'hidden';
    return () => {
      window.removeEventListener('keydown', onKey);
      document.body.style.overflow = prevOverflow;
    };
  }, [onClose]);

  return (
    <motion.div
      initial={{ opacity: 0 }}
      animate={{ opacity: 1 }}
      exit={{ opacity: 0 }}
      transition={{ duration: 0.15 }}
      className="fixed inset-0 z-[100] flex items-center justify-center bg-black/90 backdrop-blur-sm"
      onClick={onClose}
      role="dialog"
      aria-modal="true"
      aria-label={title || 'Image preview'}
    >
      <button
        onClick={onClose}
        aria-label="Close image"
        className="absolute top-4 right-4 z-10 rounded-full bg-white/10 p-2.5 text-white/90 transition-colors hover:bg-white/20 hover:text-white"
      >
        <X size={22} />
      </button>

      <div
        className="flex max-h-[90vh] max-w-[92vw] flex-col items-center gap-3 px-6"
        onClick={(e) => e.stopPropagation()}
      >
        {failed ? (
          <div className="flex aspect-video w-[min(80vw,640px)] flex-col items-center justify-center gap-3 rounded-xl border border-white/10 bg-black/40 text-jarvis-textMuted">
            <ImageOff size={40} />
            <span className="text-sm">This image could not be loaded.</span>
          </div>
        ) : (
          <img
            src={src}
            alt={title || 'Preview'}
            className="max-h-[80vh] max-w-full rounded-lg object-contain shadow-2xl shadow-black/60"
            onError={() => setFailed(true)}
          />
        )}
        <div className="flex items-center gap-2 text-[11px] text-jarvis-textMuted">
          <ZoomIn size={12} />
          {title && <span className="truncate max-w-[50vw]">{title}</span>}
          <span className="opacity-70">· Esc to close</span>
        </div>
      </div>
    </motion.div>
  );
}