import { useState } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import {
  User,
  Bell,
  Shield,
  Palette,
  Volume2,
  Mic,
  Globe,
  Keyboard,
  Database,
  Save,
  RefreshCw,
  Check,
  AlertTriangle,
  Zap,
  Moon,
  Sun,
  Monitor,
  Wifi,
  Bluetooth,
  Power,
  ChevronRight,
  ToggleLeft,
  ToggleRight,
  Sliders,
  Cpu,
  HardDrive,
  Sparkles,
} from 'lucide-react';
import { useStore } from '@/store/useStore';

const containerVariants = {
  hidden: { opacity: 0 },
  visible: {
    opacity: 1,
    transition: {
      staggerChildren: 0.05,
      delayChildren: 0.1,
    },
  },
};

const itemVariants = {
  hidden: { opacity: 0, y: 20 },
  visible: {
    opacity: 1,
    y: 0,
    transition: {
      type: 'spring',
      stiffness: 100,
      damping: 15,
    },
  },
};

const cardHoverVariants = {
  rest: { scale: 1 },
  hover: { 
    scale: 1.02,
    transition: {
      type: 'spring',
      stiffness: 400,
      damping: 25,
    }
  },
};

interface SettingItemProps {
  icon: React.ReactNode;
  title: string;
  description: string;
  control: React.ReactNode;
  danger?: boolean;
}

function SettingItem({ icon, title, description, control, danger }: SettingItemProps) {
  return (
    <motion.div
      variants={itemVariants}
      whileHover="hover"
      initial="rest"
      animate="rest"
      className={`glass-panel rounded-xl p-4 flex items-center gap-4 transition-colors ${
        danger ? 'border-red-500/30 hover:border-red-500/50' : 'hover:border-jarvis-accentPink/30'
      }`}
    >
      <motion.div 
        className={`p-3 rounded-lg ${danger ? 'bg-red-500/10 text-red-400' : 'bg-jarvis-accentPink/10 text-jarvis-accentPink'}`}
        whileHover={{ rotate: 5 }}
      >
        {icon}
      </motion.div>
      <div className="flex-1 min-w-0">
        <h3 className={`font-medium ${danger ? 'text-red-400' : 'text-jarvis-text'}`}>{title}</h3>
        <p className="text-sm text-jarvis-textMuted truncate">{description}</p>
      </div>
      <div className="flex-shrink-0">{control}</div>
    </motion.div>
  );
}

function ToggleSwitch({ checked, onChange }: { checked: boolean; onChange: (v: boolean) => void }) {
  return (
    <motion.button
      onClick={() => onChange(!checked)}
      className={`relative w-14 h-7 rounded-full transition-colors ${
        checked ? 'bg-jarvis-accentPink' : 'bg-white/10'
      }`}
      whileTap={{ scale: 0.95 }}
    >
      <motion.div
        className="absolute top-1 w-5 h-5 rounded-full bg-white shadow-lg"
        animate={{ left: checked ? '28px' : '4px' }}
        transition={{ type: 'spring', stiffness: 500, damping: 30 }}
      />
    </motion.button>
  );
}

export default function SettingsSection() {
  const { isConnected } = useStore();
  const [activeTab, setActiveTab] = useState('general');
  const [saved, setSaved] = useState(false);

  // Settings state
  const [settings, setSettings] = useState({
    voiceMode: true,
    soundEffects: true,
    notifications: true,
    autoStart: false,
    darkMode: true,
    compactMode: false,
    dataCollection: false,
    cloudSync: true,
    keyboardShortcuts: true,
    animations: true,
    highPerformance: false,
    offlineMode: false,
  });

  const handleSave = () => {
    setSaved(true);
    setTimeout(() => setSaved(false), 2000);
  };

  const tabs = [
    { id: 'general', label: 'General', icon: Sliders },
    { id: 'voice', label: 'Voice & Audio', icon: Mic },
    { id: 'appearance', label: 'Appearance', icon: Palette },
    { id: 'privacy', label: 'Privacy & Data', icon: Shield },
    { id: 'advanced', label: 'Advanced', icon: Cpu },
  ];

  return (
    <motion.div
      initial={{ opacity: 0 }}
      animate={{ opacity: 1 }}
      exit={{ opacity: 0 }}
      className="h-full flex flex-col overflow-hidden"
    >
      {/* Header */}
      <motion.div 
        className="p-6 border-b border-white/10"
        initial={{ y: -20, opacity: 0 }}
        animate={{ y: 0, opacity: 1 }}
        transition={{ duration: 0.3 }}
      >
        <div className="flex items-center justify-between">
          <div>
            <motion.h2 
              className="text-2xl font-bold text-jarvis-text"
              initial={{ x: -20, opacity: 0 }}
              animate={{ x: 0, opacity: 1 }}
              transition={{ delay: 0.1 }}
            >
              Settings
            </motion.h2>
            <motion.p 
              className="text-sm text-jarvis-textMuted mt-1"
              initial={{ x: -20, opacity: 0 }}
              animate={{ x: 0, opacity: 1 }}
              transition={{ delay: 0.15 }}
            >
              Customize your JARVIS experience
            </motion.p>
          </div>
          <motion.button
            onClick={handleSave}
            className={`flex items-center gap-2 px-4 py-2 rounded-lg font-medium transition-all ${
              saved
                ? 'bg-green-500/20 text-green-400'
                : 'bg-jarvis-accentPink/20 text-jarvis-accentPink hover:bg-jarvis-accentPink/30'
            }`}
            whileHover={{ scale: 1.05 }}
            whileTap={{ scale: 0.95 }}
            initial={{ scale: 0 }}
            animate={{ scale: 1 }}
            transition={{ delay: 0.2 }}
          >
            {saved ? <Check size={18} /> : <Save size={18} />}
            {saved ? 'Saved!' : 'Save Changes'}
          </motion.button>
        </div>
      </motion.div>

      {/* Tabs */}
      <motion.div 
        className="flex gap-1 p-2 border-b border-white/10 overflow-x-auto scrollbar-hide"
        initial={{ opacity: 0 }}
        animate={{ opacity: 1 }}
        transition={{ delay: 0.2 }}
      >
        {tabs.map((tab, index) => {
          const Icon = tab.icon;
          const isActive = activeTab === tab.id;
          return (
            <motion.button
              key={tab.id}
              onClick={() => setActiveTab(tab.id)}
              className={`flex items-center gap-2 px-4 py-2 rounded-lg text-sm font-medium whitespace-nowrap transition-all ${
                isActive
                  ? 'bg-jarvis-accentPink/20 text-jarvis-accentPink'
                  : 'text-jarvis-textMuted hover:text-jarvis-text hover:bg-white/5'
              }`}
              initial={{ opacity: 0, y: -10 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: 0.25 + index * 0.05 }}
              whileHover={{ scale: 1.02 }}
              whileTap={{ scale: 0.98 }}
            >
              <Icon size={16} />
              {tab.label}
            </motion.button>
          );
        })}
      </motion.div>

      {/* Content */}
      <div className="flex-1 overflow-y-auto p-6 scrollbar-hide">
        <AnimatePresence mode="wait">
          {activeTab === 'general' && (
            <motion.div
              key="general"
              variants={containerVariants}
              initial="hidden"
              animate="visible"
              exit={{ opacity: 0, y: -20 }}
              className="space-y-4 max-w-2xl"
            >
              <motion.div variants={itemVariants} className="mb-6">
                <h3 className="text-lg font-semibold text-jarvis-text mb-1">General Settings</h3>
                <p className="text-sm text-jarvis-textMuted">Basic preferences for JARVIS</p>
              </motion.div>

              <SettingItem
                icon={<Zap size={20} />}
                title="Auto-start on boot"
                description="Launch JARVIS when your computer starts"
                control={<ToggleSwitch checked={settings.autoStart} onChange={(v) => setSettings({ ...settings, autoStart: v })} />}
              />

              <SettingItem
                icon={<Bell size={20} />}
                title="Notifications"
                description="Show desktop notifications for alerts"
                control={<ToggleSwitch checked={settings.notifications} onChange={(v) => setSettings({ ...settings, notifications: v })} />}
              />

              <SettingItem
                icon={<Keyboard size={20} />}
                title="Keyboard Shortcuts"
                description="Enable global hotkeys (Ctrl+Shift+J)"
                control={<ToggleSwitch checked={settings.keyboardShortcuts} onChange={(v) => setSettings({ ...settings, keyboardShortcuts: v })} />}
              />

              <SettingItem
                icon={<Globe size={20} />}
                title="Language"
                description="English (US) - More languages coming soon"
                control={<span className="text-sm text-jarvis-textMuted">English</span>}
              />
            </motion.div>
          )}

          {activeTab === 'voice' && (
            <motion.div
              key="voice"
              variants={containerVariants}
              initial="hidden"
              animate="visible"
              exit={{ opacity: 0, y: -20 }}
              className="space-y-4 max-w-2xl"
            >
              <motion.div variants={itemVariants} className="mb-6">
                <h3 className="text-lg font-semibold text-jarvis-text mb-1">Voice & Audio</h3>
                <p className="text-sm text-jarvis-textMuted">Configure speech and sound settings</p>
              </motion.div>

              <SettingItem
                icon={<Mic size={20} />}
                title="Voice Mode"
                description="Enable speech-to-speech conversation"
                control={<ToggleSwitch checked={settings.voiceMode} onChange={(v) => setSettings({ ...settings, voiceMode: v })} />}
              />

              <SettingItem
                icon={<Volume2 size={20} />}
                title="Sound Effects"
                description="Play audio feedback for actions"
                control={<ToggleSwitch checked={settings.soundEffects} onChange={(v) => setSettings({ ...settings, soundEffects: v })} />}
              />

              <motion.div variants={itemVariants} className="glass-panel rounded-xl p-4">
                <div className="flex items-center gap-4">
                  <div className="p-3 rounded-lg bg-jarvis-accentPink/10 text-jarvis-accentPink">
                    <Sparkles size={20} />
                  </div>
                  <div className="flex-1">
                    <h3 className="font-medium text-jarvis-text">Voice Speed</h3>
                    <p className="text-sm text-jarvis-textMuted">Adjust AI speech rate</p>
                  </div>
                  <div className="flex items-center gap-2">
                    <span className="text-xs text-jarvis-textMuted">Slow</span>
                    <div className="w-32 h-2 bg-white/10 rounded-full overflow-hidden">
                      <div className="w-3/5 h-full bg-jarvis-accentPink rounded-full" />
                    </div>
                    <span className="text-xs text-jarvis-textMuted">Fast</span>
                  </div>
                </div>
              </motion.div>
            </motion.div>
          )}

          {activeTab === 'appearance' && (
            <motion.div
              key="appearance"
              variants={containerVariants}
              initial="hidden"
              animate="visible"
              exit={{ opacity: 0, y: -20 }}
              className="space-y-4 max-w-2xl"
            >
              <motion.div variants={itemVariants} className="mb-6">
                <h3 className="text-lg font-semibold text-jarvis-text mb-1">Appearance</h3>
                <p className="text-sm text-jarvis-textMuted">Customize the visual experience</p>
              </motion.div>

              <SettingItem
                icon={<Moon size={20} />}
                title="Dark Mode"
                description="Use dark theme (always on for now)"
                control={<ToggleSwitch checked={settings.darkMode} onChange={(v) => setSettings({ ...settings, darkMode: v })} />}
              />

              <SettingItem
                icon={<Monitor size={20} />}
                title="Compact Mode"
                description="Reduce UI spacing for smaller screens"
                control={<ToggleSwitch checked={settings.compactMode} onChange={(v) => setSettings({ ...settings, compactMode: v })} />}
              />

              <SettingItem
                icon={<Zap size={20} />}
                title="Animations"
                description="Enable smooth transitions and effects"
                control={<ToggleSwitch checked={settings.animations} onChange={(v) => setSettings({ ...settings, animations: v })} />}
              />
            </motion.div>
          )}

          {activeTab === 'privacy' && (
            <motion.div
              key="privacy"
              variants={containerVariants}
              initial="hidden"
              animate="visible"
              exit={{ opacity: 0, y: -20 }}
              className="space-y-4 max-w-2xl"
            >
              <motion.div variants={itemVariants} className="mb-6">
                <h3 className="text-lg font-semibold text-jarvis-text mb-1">Privacy & Data</h3>
                <p className="text-sm text-jarvis-textMuted">Control your data and privacy</p>
              </motion.div>

              <SettingItem
                icon={<Database size={20} />}
                title="Cloud Sync"
                description="Sync settings across devices"
                control={<ToggleSwitch checked={settings.cloudSync} onChange={(v) => setSettings({ ...settings, cloudSync: v })} />}
              />

              <SettingItem
                icon={<HardDrive size={20} />}
                title="Data Collection"
                description="Help improve JARVIS with usage data"
                control={<ToggleSwitch checked={settings.dataCollection} onChange={(v) => setSettings({ ...settings, dataCollection: v })} />}
              />

              <motion.div variants={itemVariants} className="glass-panel rounded-xl p-4 border-red-500/30">
                <div className="flex items-center gap-4">
                  <div className="p-3 rounded-lg bg-red-500/10 text-red-400">
                    <AlertTriangle size={20} />
                  </div>
                  <div className="flex-1">
                    <h3 className="font-medium text-red-400">Clear All Data</h3>
                    <p className="text-sm text-jarvis-textMuted">Delete all conversations and settings</p>
                  </div>
                  <motion.button
                    className="px-4 py-2 bg-red-500/20 text-red-400 rounded-lg text-sm font-medium hover:bg-red-500/30 transition-colors"
                    whileHover={{ scale: 1.05 }}
                    whileTap={{ scale: 0.95 }}
                  >
                    Clear
                  </motion.button>
                </div>
              </motion.div>
            </motion.div>
          )}

          {activeTab === 'advanced' && (
            <motion.div
              key="advanced"
              variants={containerVariants}
              initial="hidden"
              animate="visible"
              exit={{ opacity: 0, y: -20 }}
              className="space-y-4 max-w-2xl"
            >
              <motion.div variants={itemVariants} className="mb-6">
                <h3 className="text-lg font-semibold text-jarvis-text mb-1">Advanced</h3>
                <p className="text-sm text-jarvis-textMuted">Power user settings</p>
              </motion.div>

              <SettingItem
                icon={<Cpu size={20} />}
                title="High Performance Mode"
                description="Use more resources for faster responses"
                control={<ToggleSwitch checked={settings.highPerformance} onChange={(v) => setSettings({ ...settings, highPerformance: v })} />}
              />

              <SettingItem
                icon={<Wifi size={20} />}
                title="Offline Mode"
                description="Work without internet (limited features)"
                control={<ToggleSwitch checked={settings.offlineMode} onChange={(v) => setSettings({ ...settings, offlineMode: v })} />}
              />

              <motion.div variants={itemVariants} className="glass-panel rounded-xl p-4">
                <div className="flex items-center gap-4">
                  <div className="p-3 rounded-lg bg-jarvis-accentPink/10 text-jarvis-accentPink">
                    <RefreshCw size={20} />
                  </div>
                  <div className="flex-1">
                    <h3 className="font-medium text-jarvis-text">Check for Updates</h3>
                    <p className="text-sm text-jarvis-textMuted">Version 2.0.1 - Latest</p>
                  </div>
                  <motion.button
                    className="px-4 py-2 bg-jarvis-accentPink/20 text-jarvis-accentPink rounded-lg text-sm font-medium hover:bg-jarvis-accentPink/30 transition-colors"
                    whileHover={{ scale: 1.05 }}
                    whileTap={{ scale: 0.95 }}
                  >
                    Check
                  </motion.button>
                </div>
              </motion.div>

              <motion.div variants={itemVariants} className="glass-panel rounded-xl p-4">
                <div className="flex items-center gap-4">
                  <div className="p-3 rounded-lg bg-jarvis-accentPink/10 text-jarvis-accentPink">
                    <Database size={20} />
                  </div>
                  <div className="flex-1">
                    <h3 className="font-medium text-jarvis-text">Export Data</h3>
                    <p className="text-sm text-jarvis-textMuted">Download all your data as JSON</p>
                  </div>
                  <motion.button
                    className="px-4 py-2 bg-jarvis-accentPink/20 text-jarvis-accentPink rounded-lg text-sm font-medium hover:bg-jarvis-accentPink/30 transition-colors"
                    whileHover={{ scale: 1.05 }}
                    whileTap={{ scale: 0.95 }}
                  >
                    Export
                  </motion.button>
                </div>
              </motion.div>
            </motion.div>
          )}
        </AnimatePresence>
      </div>
    </motion.div>
  );
}
