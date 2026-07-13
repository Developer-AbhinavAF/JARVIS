import { useEffect, useCallback } from 'react';
import { useStore } from '@/store/useStore';

interface FormatEventDetail {
  format: 'bold' | 'italic' | 'bullet' | 'numbered' | 'check' | 'quote' | 'code';
}

function dispatchFormat(format: FormatEventDetail['format']) {
  window.dispatchEvent(new CustomEvent<FormatEventDetail>('format-chat', { detail: { format } }));
}

export function useChatShortcuts() {
  const { activeTab } = useStore();

  const handler = useCallback((e: KeyboardEvent) => {
    if (activeTab !== 'assistant') return;

    const target = e.target as HTMLElement;
    const isInput = target.tagName === 'TEXTAREA' || target.tagName === 'INPUT' || target.isContentEditable;

    // Ctrl+B → Bold
    if (e.ctrlKey && e.key === 'b') {
      e.preventDefault();
      dispatchFormat('bold');
      return;
    }

    // Ctrl+I → Italic
    if (e.ctrlKey && e.key === 'i') {
      e.preventDefault();
      dispatchFormat('italic');
      return;
    }

    // Ctrl+Shift+L → Bullet list
    if (e.ctrlKey && e.shiftKey && e.key === 'L') {
      e.preventDefault();
      dispatchFormat('bullet');
      return;
    }

    // Ctrl+Shift+O → Numbered list
    if (e.ctrlKey && e.shiftKey && e.key === 'O') {
      e.preventDefault();
      dispatchFormat('numbered');
      return;
    }

    // Ctrl+Shift+T → Task list
    if (e.ctrlKey && e.shiftKey && e.key === 'T') {
      e.preventDefault();
      dispatchFormat('check');
      return;
    }

    // Ctrl+E → Inline code (only when not in input to avoid conflict with Emacs)
    if (e.ctrlKey && e.key === 'e' && !isInput) {
      e.preventDefault();
      dispatchFormat('code');
      return;
    }

    // Ctrl+Shift+Q → Blockquote
    if (e.ctrlKey && e.shiftKey && e.key === 'Q') {
      e.preventDefault();
      dispatchFormat('quote');
      return;
    }

    // Quick action shortcuts: Ctrl+1-9
    if (e.ctrlKey && e.key >= '1' && e.key <= '9') {
      e.preventDefault();
      const quickActions = [
        'take screenshot',
        'open youtube',
        'system status',
        'network status',
        'calculate 15 * 23',
        'open notepad',
        'tell me a joke',
        'quote',
        'random fact',
      ];
      const idx = parseInt(e.key) - 1;
      if (idx < quickActions.length) {
        window.dispatchEvent(new CustomEvent<string>('quick-action', { detail: quickActions[idx] }));
      }
      return;
    }
  }, [activeTab]);

  useEffect(() => {
    window.addEventListener('keydown', handler);
    return () => window.removeEventListener('keydown', handler);
  }, [handler]);
}
