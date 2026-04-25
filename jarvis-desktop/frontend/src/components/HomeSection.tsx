import { motion } from 'framer-motion';
import {
  MessageSquare,
  Zap,
  Cpu,
  Globe,
  Calculator,
  Cloud,
  Smile,
  Quote,
  Brain,
  Terminal,
  Settings,
  BookOpen,
  Sparkles,
  Command,
  FileImage,
  Crown,
} from 'lucide-react';
import { useStore } from '@/store/useStore';
import FeaturesHub from './FeaturesHub';
import { useState, useEffect } from 'react';

const quickCards = [
  { id: 'features', label: 'Features Hub', icon: Crown, color: 'from-yellow-500 to-amber-500', desc: '60+ powerful features' },
  { id: 'chat', label: 'Chat with JARVIS', icon: MessageSquare, color: 'from-pink-500 to-rose-500', desc: 'Ask anything' },
  { id: 'upload', label: 'Upload & Analyze', icon: FileImage, color: 'from-orange-500 to-amber-500', desc: 'Images, PDFs, Files' },
  { id: 'system', label: 'System Status', icon: Cpu, color: 'from-blue-500 to-cyan-500', desc: 'CPU, RAM, Battery' },
  { id: 'network', label: 'Network Info', icon: Globe, color: 'from-green-500 to-emerald-500', desc: 'WiFi, IP, Data' },
  { id: 'docs', label: 'Documentation', icon: BookOpen, color: 'from-indigo-500 to-purple-500', desc: 'Help & Guides' },
  { id: 'settings', label: 'Settings', icon: Settings, color: 'from-gray-500 to-slate-500', desc: 'Customize JARVIS' },
];

const aiFeatures = [
  { id: 'vision', label: 'Image Analysis', icon: FileImage, desc: 'Upload images for AI analysis', color: 'from-violet-500 to-purple-500' },
  { id: 'chat', label: 'Smart Chat', icon: Sparkles, desc: 'Natural conversations with AI', color: 'from-pink-500 to-rose-500' },
  { id: 'commands', label: 'Voice Commands', icon: Command, desc: '25+ system commands', color: 'from-cyan-500 to-blue-500' },
];

const funCards = [
  { id: 'joke', label: 'Tell a Joke', icon: Smile, command: 'tell me a joke' },
  { id: 'quote', label: 'Inspiration', icon: Quote, command: 'quote' },
  { id: 'fact', label: 'Random Fact', icon: Brain, command: 'random fact' },
  { id: 'calc', label: 'Calculator', icon: Calculator, command: 'calculate ' },
  { id: 'weather', label: 'Weather', icon: Cloud, command: 'weather' },
  { id: 'logs', label: 'System Logs', icon: Terminal, command: 'show logs' },
];

export default function HomeSection() {
  const { setActiveTab, setInput } = useStore();
  const [showFeaturesHub, setShowFeaturesHub] = useState(false);

  useEffect(() => {
    const handleOpenFeaturesHub = () => setShowFeaturesHub(true);
    window.addEventListener('open-features-hub', handleOpenFeaturesHub);
    return () => window.removeEventListener('open-features-hub', handleOpenFeaturesHub);
  }, []);

  const handleCardClick = (id: string) => {
    if (id === 'features') {
      setShowFeaturesHub(true);
      return;
    }
    if (id === 'chat') {
      setActiveTab('assistant');
    } else if (id === 'upload') {
      setActiveTab('assistant');
      // Trigger file upload via the chat panel would need a store state
      setInput('Upload a file to analyze');
    } else if (id === 'system') {
      setActiveTab('assistant');
      setInput('system status');
    } else if (id === 'network') {
      setActiveTab('assistant');
      setInput('network status');
    } else if (id === 'pc') {
      setActiveTab('pc-control');
    } else if (id === 'docs') {
      setActiveTab('help');
    } else if (id === 'settings') {
      setActiveTab('settings');
    }
  };

  const handleFunCard = (command: string) => {
    setActiveTab('assistant');
    setInput(command);
  };

  return (
    <div className="flex-1 h-full overflow-y-auto p-8">
      {/* Welcome Header */}
      <motion.div
        initial={{ opacity: 0, y: -20 }}
        animate={{ opacity: 1, y: 0 }}
        className="text-center mb-10"
      >
        <h1 className="text-4xl font-bold mb-3">
          <span className="gradient-text">Welcome to JARVIS</span>
        </h1>
        <p className="text-jarvis-textMuted text-lg">
          Your Ultimate AI Desktop Assistant
        </p>
        <div className="flex items-center justify-center gap-2 mt-4">
          <div className="w-2 h-2 rounded-full bg-green-500 animate-pulse" />
          <span className="text-sm text-jarvis-textMuted">Online and Ready</span>
        </div>
      </motion.div>

      {/* Quick Access Cards */}
      <motion.div
        initial={{ opacity: 0 }}
        animate={{ opacity: 1 }}
        transition={{ delay: 0.1 }}
        className="mb-8"
      >
        <h2 className="text-sm font-semibold text-jarvis-textMuted uppercase tracking-wider mb-4">
          Quick Access
        </h2>
        <div className="grid grid-cols-2 lg:grid-cols-3 gap-4">
          {quickCards.map((card, index) => {
            const Icon = card.icon;
            return (
              <motion.button
                key={card.id}
                initial={{ opacity: 0, y: 20 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ delay: index * 0.05 }}
                whileHover={{ scale: 1.02, y: -2 }}
                whileTap={{ scale: 0.98 }}
                onClick={() => handleCardClick(card.id)}
                className={`p-5 rounded-2xl glass-panel text-left group hover:bg-white/10 transition-all duration-300`}
              >
                <div className={`w-12 h-12 rounded-xl bg-gradient-to-br ${card.color} flex items-center justify-center mb-3 group-hover:shadow-lg transition-shadow`}>
                  <Icon size={24} className="text-white" />
                </div>
                <h3 className="font-semibold text-jarvis-text mb-1">{card.label}</h3>
                <p className="text-xs text-jarvis-textMuted">{card.desc}</p>
              </motion.button>
            );
          })}
        </div>
      </motion.div>

      {/* AI Features Section */}
      <motion.div
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ delay: 0.15 }}
        className="mb-8"
      >
        <h2 className="text-sm font-semibold text-jarvis-textMuted uppercase tracking-wider mb-4 flex items-center gap-2">
          <Sparkles size={16} className="text-jarvis-accentPink" />
          AI Features
        </h2>
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          {aiFeatures.map((feature, index) => {
            const Icon = feature.icon;
            return (
              <motion.div
                key={feature.id}
                initial={{ opacity: 0, scale: 0.9 }}
                animate={{ opacity: 1, scale: 1 }}
                transition={{ delay: 0.15 + index * 0.08 }}
                whileHover={{ scale: 1.03, y: -3 }}
                className={`p-4 rounded-xl bg-gradient-to-br ${feature.color} bg-opacity-10 border border-white/10`}
              >
                <div className="flex items-center gap-3">
                  <div className="p-2.5 rounded-xl bg-white/20 backdrop-blur-sm">
                    <Icon size={22} className="text-white" />
                  </div>
                  <div>
                    <h3 className="font-semibold text-jarvis-text">{feature.label}</h3>
                    <p className="text-xs text-jarvis-text/70">{feature.desc}</p>
                  </div>
                </div>
              </motion.div>
            );
          })}
        </div>
      </motion.div>

      {/* Fun & Utilities */}
      <motion.div
        initial={{ opacity: 0 }}
        animate={{ opacity: 1 }}
        transition={{ delay: 0.2 }}
        className="mb-8"
      >
        <h2 className="text-sm font-semibold text-jarvis-textMuted uppercase tracking-wider mb-4">
          Fun & Utilities
        </h2>
        <div className="grid grid-cols-3 lg:grid-cols-6 gap-3">
          {funCards.map((card, index) => {
            const Icon = card.icon;
            return (
              <motion.button
                key={card.id}
                initial={{ opacity: 0, scale: 0.9 }}
                animate={{ opacity: 1, scale: 1 }}
                transition={{ delay: 0.2 + index * 0.03 }}
                whileHover={{ scale: 1.05 }}
                whileTap={{ scale: 0.95 }}
                onClick={() => handleFunCard(card.command)}
                className="p-4 rounded-xl glass-panel text-center hover:bg-white/10 transition-colors group"
              >
                <Icon size={20} className="mx-auto mb-2 text-jarvis-accentPink group-hover:text-jarvis-accentRed transition-colors" />
                <span className="text-xs text-jarvis-textMuted group-hover:text-jarvis-text transition-colors">{card.label}</span>
              </motion.button>
            );
          })}
        </div>
      </motion.div>

      {/* Recent Activity / Tips */}
      <motion.div
        initial={{ opacity: 0 }}
        animate={{ opacity: 1 }}
        transition={{ delay: 0.3 }}
        className="grid grid-cols-1 lg:grid-cols-2 gap-4"
      >
        {/* Tips Card */}
        <div className="p-5 rounded-2xl glass-panel">
          <h3 className="font-semibold text-jarvis-text mb-3 flex items-center gap-2">
            <Zap size={18} className="text-yellow-400" />
            Quick Tips
          </h3>
          <ul className="space-y-2 text-sm text-jarvis-textMuted">
            <li className="flex items-start gap-2">
              <span className="text-jarvis-accentPink">→</span>
              Try voice mode for hands-free control
            </li>
            <li className="flex items-start gap-2">
              <span className="text-jarvis-accentPink">→</span>
              Say &quot;system status&quot; for real-time stats
            </li>
            <li className="flex items-start gap-2">
              <span className="text-jarvis-accentPink">→</span>
              Use &quot;open [app]&quot; to launch applications
            </li>
            <li className="flex items-start gap-2">
              <span className="text-jarvis-accentPink">→</span>
              Add todos with &quot;add todo [task]&quot;
            </li>
          </ul>
        </div>

        {/* Stats Preview */}
        <div className="p-5 rounded-2xl glass-panel">
          <h3 className="font-semibold text-jarvis-text mb-3 flex items-center gap-2">
            <Cpu size={18} className="text-blue-400" />
            At a Glance
          </h3>
          <div className="grid grid-cols-2 gap-3">
            <div className="p-3 rounded-lg bg-white/5">
              <div className="text-xs text-jarvis-textMuted mb-1">Mode</div>
              <div className="text-sm font-medium text-green-400">Active</div>
            </div>
            <div className="p-3 rounded-lg bg-white/5">
              <div className="text-xs text-jarvis-textMuted mb-1">Connection</div>
              <div className="text-sm font-medium text-green-400">Connected</div>
            </div>
            <div className="p-3 rounded-lg bg-white/5">
              <div className="text-xs text-jarvis-textMuted mb-1">Voice</div>
              <div className="text-sm font-medium text-jarvis-accentPink">Supported</div>
            </div>
            <div className="p-3 rounded-lg bg-white/5">
              <div className="text-xs text-jarvis-textMuted mb-1">Version</div>
              <div className="text-sm font-medium text-jarvis-text">Ultimate</div>
            </div>
          </div>
        </div>
      </motion.div>

      {/* Footer */}
      <motion.div
        initial={{ opacity: 0 }}
        animate={{ opacity: 1 }}
        transition={{ delay: 0.4 }}
        className="text-center mt-10 pb-4"
      >
        <p className="text-xs text-jarvis-textMuted">
          Press <kbd className="px-2 py-1 rounded bg-white/10 text-jarvis-text">Ctrl+J</kbd> to toggle JARVIS from anywhere
        </p>
      </motion.div>

      {/* Features Hub Modal */}
      {showFeaturesHub && <FeaturesHub onClose={() => setShowFeaturesHub(false)} />}
    </div>
  );
}
