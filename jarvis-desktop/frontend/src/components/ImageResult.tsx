import { motion } from 'framer-motion';
import { ExternalLink, Image as ImageIcon } from 'lucide-react';

export interface ImageResultData {
  source: string;
  title: string;
  description: string;
  image_url: string;
  thumbnail_url: string;
  source_url: string;
  media_type: string;
  metadata?: Record<string, any>;
}

interface ImageResultCardProps {
  result: ImageResultData;
  compact?: boolean;
}

export function ImageResultCard({ result, compact = false }: ImageResultCardProps) {
  const imgSrc = result.thumbnail_url || result.image_url;
  const handleClick = () => {
    if (result.source_url) {
      window.open(result.source_url, '_blank', 'noopener,noreferrer');
    } else if (result.image_url) {
      window.open(result.image_url, '_blank', 'noopener,noreferrer');
    }
  };

  if (compact) {
    return (
      <motion.div
        initial={{ opacity: 0, scale: 0.95 }}
        animate={{ opacity: 1, scale: 1 }}
        className="flex-shrink-0 w-48 rounded-xl overflow-hidden bg-black/30 border border-white/10 cursor-pointer hover:border-jarvis-accentPink/50 transition-colors"
        onClick={handleClick}
      >
        <div className="relative aspect-video bg-black/50">
          {imgSrc ? (
            <img
              src={imgSrc}
              alt={result.title}
              className="w-full h-full object-cover"
              loading="lazy"
              onError={(e) => {
                (e.target as HTMLImageElement).style.display = 'none';
              }}
            />
          ) : (
            <div className="w-full h-full flex items-center justify-center">
              <ImageIcon size={24} className="text-jarvis-textMuted" />
            </div>
          )}
          <div className="absolute top-1 right-1 px-1.5 py-0.5 rounded text-[9px] bg-black/60 text-white/80">
            {result.source}
          </div>
        </div>
        <div className="p-2">
          <p className="text-[11px] font-medium text-jarvis-text truncate">{result.title}</p>
          {result.description && (
            <p className="text-[9px] text-jarvis-textMuted mt-0.5 line-clamp-2">{result.description}</p>
          )}
        </div>
      </motion.div>
    );
  }

  return (
    <motion.div
      initial={{ opacity: 0, y: 10 }}
      animate={{ opacity: 1, y: 0 }}
      className="rounded-xl overflow-hidden bg-black/30 border border-white/10 max-w-md"
    >
      <div className="relative aspect-video bg-black/50">
        {imgSrc ? (
          <img
            src={imgSrc}
            alt={result.title}
            className="w-full h-full object-cover"
            loading="lazy"
            onError={(e) => {
              (e.target as HTMLImageElement).style.display = 'none';
            }}
          />
        ) : (
          <div className="w-full h-full flex items-center justify-center">
            <ImageIcon size={32} className="text-jarvis-textMuted" />
          </div>
        )}
        <div className="absolute top-2 left-2 px-2 py-1 rounded-md text-[10px] font-medium bg-black/60 text-white/90">
          {result.source}
        </div>
      </div>
      <div className="p-3">
        <h4 className="text-sm font-semibold text-jarvis-text">{result.title}</h4>
        {result.description && (
          <p className="text-xs text-jarvis-textMuted mt-1 line-clamp-3">{result.description}</p>
        )}
        <button
          onClick={handleClick}
          className="mt-2 flex items-center gap-1.5 text-[10px] text-jarvis-accentPink hover:text-jarvis-accentPink/80 transition-colors"
        >
          <ExternalLink size={10} />
          View source
        </button>
      </div>
    </motion.div>
  );
}

interface ImageGalleryProps {
  source: string;
  query: string;
  results: ImageResultData[];
  count: number;
}

export function ImageGallery({ source, query, results, count }: ImageGalleryProps) {
  return (
    <motion.div
      initial={{ opacity: 0, y: 10 }}
      animate={{ opacity: 1, y: 0 }}
      className="space-y-2"
    >
      <div className="flex items-center gap-2 mb-2">
        <span className="text-[10px] px-2 py-0.5 rounded-full bg-jarvis-accentPink/20 text-jarvis-accentPink font-medium">
          {source}
        </span>
        <span className="text-xs text-jarvis-textMuted">
          {count} result{count !== 1 ? 's' : ''} for "{query}"
        </span>
      </div>
      <div className="flex gap-2 overflow-x-auto pb-2 scrollbar-thin">
        {results.slice(0, 6).map((result, idx) => (
          <ImageResultCard key={idx} result={result} compact />
        ))}
      </div>
    </motion.div>
  );
}
