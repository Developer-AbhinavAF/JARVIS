import { useState } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import {
  BookOpen,
  Code,
  Terminal,
  Cpu,
  Mic,
  Keyboard,
  Zap,
  Shield,
  HelpCircle,
  ChevronRight,
  ChevronDown,
  ExternalLink,
  Github,
  Twitter,
  MessageCircle,
  Mail,
  Sparkles,
  FileText,
  Play,
  Lightbulb,
  AlertCircle,
  CheckCircle,
  Info,
  Search,
  Command,
  MousePointer,
  Globe,
  Settings,
  Download,
  Upload,
  Image,
  MessageSquare,
  Bot,
  Brain,
  Wand2,
  Volume2,
  Monitor,
  Database,
  Lock,
  Eye,
  FileCode,
  Layers,
  Puzzle,
  Rocket,
  Star,
  Heart,
} from 'lucide-react';

const containerVariants = {
  hidden: { opacity: 0 },
  visible: {
    opacity: 1,
    transition: {
      staggerChildren: 0.03,
      delayChildren: 0.1,
    },
  },
};

const itemVariants = {
  hidden: { opacity: 0, x: -10 },
  visible: {
    opacity: 1,
    x: 0,
    transition: {
      type: 'spring',
      stiffness: 100,
      damping: 15,
    },
  },
};

const cardVariants = {
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

interface DocSection {
  id: string;
  title: string;
  icon: React.ReactNode;
  content: React.ReactNode;
}

function FeatureCard({ icon, title, description, color = 'pink' }: { 
  icon: React.ReactNode; 
  title: string; 
  description: string;
  color?: 'pink' | 'blue' | 'green' | 'purple' | 'orange';
}) {
  const colorClasses = {
    pink: 'from-jarvis-accentPink/20 to-jarvis-accentPink/5 border-jarvis-accentPink/30',
    blue: 'from-blue-500/20 to-blue-500/5 border-blue-500/30',
    green: 'from-green-500/20 to-green-500/5 border-green-500/30',
    purple: 'from-purple-500/20 to-purple-500/5 border-purple-500/30',
    orange: 'from-orange-500/20 to-orange-500/5 border-orange-500/30',
  };

  const iconColors = {
    pink: 'text-jarvis-accentPink bg-jarvis-accentPink/10',
    blue: 'text-blue-400 bg-blue-500/10',
    green: 'text-green-400 bg-green-500/10',
    purple: 'text-purple-400 bg-purple-500/10',
    orange: 'text-orange-400 bg-orange-500/10',
  };

  return (
    <motion.div
      variants={cardVariants}
      whileHover={{ scale: 1.02, y: -2 }}
      className={`glass-panel rounded-xl p-5 bg-gradient-to-br ${colorClasses[color]} border hover:shadow-lg transition-all`}
    >
      <div className={`w-12 h-12 rounded-xl ${iconColors[color]} flex items-center justify-center mb-4`}>
        {icon}
      </div>
      <h3 className="text-lg font-semibold text-jarvis-text mb-2">{title}</h3>
      <p className="text-sm text-jarvis-textMuted leading-relaxed">{description}</p>
    </motion.div>
  );
}

function CommandExample({ command, description }: { command: string; description: string }) {
  return (
    <motion.div 
      variants={itemVariants}
      className="flex items-start gap-3 p-3 rounded-lg bg-white/5 hover:bg-white/10 transition-colors"
    >
      <div className="p-2 rounded-lg bg-jarvis-accentPink/10 text-jarvis-accentPink flex-shrink-0">
        <Terminal size={16} />
      </div>
      <div className="flex-1 min-w-0">
        <code className="text-sm text-jarvis-accentPink font-mono block mb-1">"{command}"</code>
        <p className="text-xs text-jarvis-textMuted">{description}</p>
      </div>
    </motion.div>
  );
}

export default function DocsSection() {
  const [activeSection, setActiveSection] = useState('getting-started');
  const [searchQuery, setSearchQuery] = useState('');

  const sidebarItems = [
    { id: 'getting-started', label: 'Getting Started', icon: <Rocket size={18} /> },
    { id: 'features', label: 'Features Overview', icon: <Sparkles size={18} /> },
    { id: 'commands', label: 'Voice Commands', icon: <Mic size={18} /> },
    { id: 'ai-capabilities', label: 'AI Capabilities', icon: <Brain size={18} /> },
    { id: 'file-upload', label: 'File Upload & Analysis', icon: <Upload size={18} /> },
    { id: 'shortcuts', label: 'Keyboard Shortcuts', icon: <Keyboard size={18} /> },
    { id: 'system', label: 'System Integration', icon: <Monitor size={18} /> },
    { id: 'privacy', label: 'Privacy & Security', icon: <Shield size={18} /> },
    { id: 'troubleshooting', label: 'Troubleshooting', icon: <HelpCircle size={18} /> },
    { id: 'api', label: 'API Reference', icon: <Code size={18} /> },
    { id: 'about', label: 'About Abhinav', icon: <Heart size={18} /> },
  ];

  return (
    <motion.div
      initial={{ opacity: 0 }}
      animate={{ opacity: 1 }}
      exit={{ opacity: 0 }}
      className="h-full flex overflow-hidden"
    >
      {/* Sidebar */}
      <motion.div 
        className="w-72 h-full glass-panel border-r border-white/10 flex flex-col overflow-hidden"
        initial={{ x: -50, opacity: 0 }}
        animate={{ x: 0, opacity: 1 }}
        transition={{ duration: 0.3 }}
      >
        {/* Header */}
        <div className="p-4 border-b border-white/10">
          <div className="flex items-center gap-3 mb-4">
            <div className="p-2 rounded-xl bg-jarvis-accentPink/10 text-jarvis-accentPink">
              <BookOpen size={24} />
            </div>
            <div>
              <h2 className="font-bold text-jarvis-text">Documentation</h2>
              <p className="text-xs text-jarvis-textMuted">JARVIS Ultimate v2.0</p>
            </div>
          </div>

          {/* Search */}
          <div className="relative">
            <Search className="absolute left-3 top-1/2 -translate-y-1/2 text-jarvis-textMuted" size={16} />
            <input
              type="text"
              placeholder="Search docs..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              className="w-full pl-10 pr-4 py-2 bg-white/5 border border-white/10 rounded-lg text-sm text-jarvis-text placeholder-jarvis-textMuted focus:outline-none focus:border-jarvis-accentPink/50 transition-colors"
            />
          </div>
        </div>

        {/* Navigation */}
        <nav className="flex-1 overflow-y-auto p-3 space-y-1 scrollbar-hide">
          {sidebarItems.map((item, index) => {
            const isActive = activeSection === item.id;
            return (
              <motion.button
                key={item.id}
                onClick={() => setActiveSection(item.id)}
                className={`w-full flex items-center gap-3 px-3 py-2.5 rounded-lg text-sm font-medium transition-all ${
                  isActive
                    ? 'bg-jarvis-accentPink/20 text-jarvis-accentPink'
                    : 'text-jarvis-textMuted hover:text-jarvis-text hover:bg-white/5'
                }`}
                initial={{ opacity: 0, x: -20 }}
                animate={{ opacity: 1, x: 0 }}
                transition={{ delay: index * 0.03 }}
                whileHover={{ x: 4 }}
                whileTap={{ scale: 0.98 }}
              >
                {item.icon}
                <span>{item.label}</span>
                {isActive && <ChevronRight size={16} className="ml-auto" />}
              </motion.button>
            );
          })}
        </nav>

        {/* Footer */}
        <div className="p-4 border-t border-white/10">
          <div className="flex items-center gap-2 text-xs text-jarvis-textMuted">
            <span>Made with</span>
            <Heart size={12} className="text-red-400 fill-red-400" />
            <span>by Abhinav</span>
          </div>
        </div>
      </motion.div>

      {/* Content */}
      <div className="flex-1 overflow-y-auto scrollbar-hide">
        <AnimatePresence mode="wait">
          {activeSection === 'getting-started' && (
            <motion.div
              key="getting-started"
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0, y: -20 }}
              className="p-8 max-w-4xl"
            >
              <motion.div 
                className="mb-8"
                initial={{ opacity: 0, y: 20 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ delay: 0.1 }}
              >
                <div className="flex items-center gap-3 mb-4">
                  <div className="p-3 rounded-2xl bg-jarvis-accentPink/10 text-jarvis-accentPink">
                    <Rocket size={32} />
                  </div>
                  <div>
                    <h1 className="text-3xl font-bold text-jarvis-text">Getting Started</h1>
                    <p className="text-jarvis-textMuted">Welcome to JARVIS Ultimate - Your AI Assistant</p>
                  </div>
                </div>
              </motion.div>

              <motion.div variants={containerVariants} initial="hidden" animate="visible" className="space-y-6">
                <motion.div variants={itemVariants} className="glass-panel rounded-xl p-6">
                  <h2 className="text-xl font-semibold text-jarvis-text mb-4 flex items-center gap-2">
                    <Sparkles size={20} className="text-jarvis-accentPink" />
                    What is JARVIS?
                  </h2>
                  <p className="text-jarvis-textMuted leading-relaxed mb-4">
                    JARVIS Ultimate is your personal AI assistant that combines powerful system control, 
                    intelligent conversations, file analysis, and voice interaction - all in one beautiful interface. 
                    Built with love by Abhinav for ultimate productivity.
                  </p>
                  <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mt-6">
                    <FeatureCard 
                      icon={<Brain size={24} />}
                      title="AI Powered"
                      description="Advanced language model for intelligent conversations"
                      color="purple"
                    />
                    <FeatureCard 
                      icon={<Mic size={24} />}
                      title="Voice Control"
                      description="Hands-free operation with speech-to-speech"
                      color="pink"
                    />
                    <FeatureCard 
                      icon={<Zap size={24} />}
                      title="System Control"
                      description="Control your PC with natural language"
                      color="blue"
                    />
                  </div>
                </motion.div>

                <motion.div variants={itemVariants} className="glass-panel rounded-xl p-6">
                  <h2 className="text-xl font-semibold text-jarvis-text mb-4 flex items-center gap-2">
                    <Play size={20} className="text-green-400" />
                    Quick Start Guide
                  </h2>
                  <div className="space-y-4">
                    {[
                      { step: 1, title: 'Launch JARVIS', desc: 'Start the application and wait for the "Online" indicator' },
                      { step: 2, title: 'Choose Your Mode', desc: 'Switch between Text Mode (typing) or Voice Mode (speaking)' },
                      { step: 3, title: 'Try a Command', desc: 'Say "volume up" or type "open chrome" to see JARVIS in action' },
                      { step: 4, title: 'Explore Features', desc: 'Check out the Dashboard, Memory Center, and all other sections' },
                    ].map((item) => (
                      <div key={item.step} className="flex items-start gap-4">
                        <div className="w-8 h-8 rounded-full bg-jarvis-accentPink/20 text-jarvis-accentPink flex items-center justify-center font-bold text-sm flex-shrink-0">
                          {item.step}
                        </div>
                        <div>
                          <h3 className="font-medium text-jarvis-text">{item.title}</h3>
                          <p className="text-sm text-jarvis-textMuted">{item.desc}</p>
                        </div>
                      </div>
                    ))}
                  </div>
                </motion.div>
              </motion.div>
            </motion.div>
          )}

          {activeSection === 'features' && (
            <motion.div
              key="features"
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0, y: -20 }}
              className="p-8 max-w-5xl"
            >
              <h1 className="text-3xl font-bold text-jarvis-text mb-2">Features Overview</h1>
              <p className="text-jarvis-textMuted mb-8">Discover everything JARVIS can do for you</p>

              <motion.div 
                variants={containerVariants}
                initial="hidden"
                animate="visible"
                className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4"
              >
                <FeatureCard icon={<MessageSquare size={24} />} title="Smart Chat" description="Natural conversations with context awareness" color="pink" />
                <FeatureCard icon={<Upload size={24} />} title="File Analysis" description="Upload images, PDFs, documents for AI analysis" color="blue" />
                <FeatureCard icon={<Image size={24} />} title="Image Understanding" description="AI can see and describe images, extract text" color="purple" />
                <FeatureCard icon={<Monitor size={24} />} title="System Control" description="Volume, brightness, shutdown, lock screen" color="green" />
                <FeatureCard icon={<Volume2 size={24} />} title="Media Controls" description="Play, pause, skip tracks with voice" color="orange" />
                <FeatureCard icon={<Database size={24} />} title="Memory Center" description="Todos, notes, reminders with persistence" color="blue" />
                <FeatureCard icon={<Search size={24} />} title="Web Search" description="Google searches and website opening" color="pink" />
                <FeatureCard icon={<Terminal size={24} />} title="System Logs" description="Real-time system monitoring" color="green" />
                <FeatureCard icon={<Wand2 size={24} />} title="25+ Commands" description="Calculator, weather, jokes, quotes, and more" color="purple" />
              </motion.div>
            </motion.div>
          )}

          {activeSection === 'commands' && (
            <motion.div
              key="commands"
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0, y: -20 }}
              className="p-8 max-w-4xl"
            >
              <h1 className="text-3xl font-bold text-jarvis-text mb-2">Voice Commands</h1>
              <p className="text-jarvis-textMuted mb-8">Just say these commands to control your system</p>

              <motion.div variants={containerVariants} initial="hidden" animate="visible" className="space-y-6">
                <motion.div variants={itemVariants} className="glass-panel rounded-xl p-6">
                  <h2 className="text-lg font-semibold text-jarvis-text mb-4 flex items-center gap-2">
                    <Volume2 size={20} className="text-jarvis-accentPink" />
                    Volume & Media
                  </h2>
                  <div className="space-y-2">
                    <CommandExample command="volume up" description="Increase system volume by 5 steps" />
                    <CommandExample command="volume down" description="Decrease system volume by 5 steps" />
                    <CommandExample command="mute" description="Toggle mute on/off" />
                    <CommandExample command="play" description="Play or pause media" />
                    <CommandExample command="next track" description="Skip to next song" />
                    <CommandExample command="previous track" description="Go to previous song" />
                  </div>
                </motion.div>

                <motion.div variants={itemVariants} className="glass-panel rounded-xl p-6">
                  <h2 className="text-lg font-semibold text-jarvis-text mb-4 flex items-center gap-2">
                    <Power size={20} className="text-red-400" />
                    System Power
                  </h2>
                  <div className="space-y-2">
                    <CommandExample command="shutdown" description="Shutdown computer in 60 seconds" />
                    <CommandExample command="restart" description="Restart computer in 60 seconds" />
                    <CommandExample command="sleep" description="Put computer to sleep" />
                    <CommandExample command="lock" description="Lock the screen" />
                    <CommandExample command="cancel shutdown" description="Abort pending shutdown" />
                  </div>
                </motion.div>

                <motion.div variants={itemVariants} className="glass-panel rounded-xl p-6">
                  <h2 className="text-lg font-semibold text-jarvis-text mb-4 flex items-center gap-2">
                    <Globe size={20} className="text-blue-400" />
                    Web & Apps
                  </h2>
                  <div className="space-y-2">
                    <CommandExample command="open chrome" description="Launch Google Chrome" />
                    <CommandExample command="open youtube" description="Open YouTube in browser" />
                    <CommandExample command="search python tutorials" description="Search Google for anything" />
                    <CommandExample command="open gmail" description="Open Gmail" />
                  </div>
                </motion.div>

                <motion.div variants={itemVariants} className="glass-panel rounded-xl p-6">
                  <h2 className="text-lg font-semibold text-jarvis-text mb-4 flex items-center gap-2">
                    <Zap size={20} className="text-yellow-400" />
                    Utilities
                  </h2>
                  <div className="space-y-2">
                    <CommandExample command="calculate 15 times 23" description="Math calculations" />
                    <CommandExample command="what time is it" description="Get current time" />
                    <CommandExample command="take screenshot" description="Capture screen" />
                    <CommandExample command="tell me a joke" description="Get a random joke" />
                    <CommandExample command="system status" description="Check CPU, RAM, battery" />
                  </div>
                </motion.div>
              </motion.div>
            </motion.div>
          )}

          {activeSection === 'file-upload' && (
            <motion.div
              key="file-upload"
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0, y: -20 }}
              className="p-8 max-w-4xl"
            >
              <h1 className="text-3xl font-bold text-jarvis-text mb-2">File Upload & Analysis</h1>
              <p className="text-jarvis-textMuted mb-8">Upload files and let JARVIS analyze them</p>

              <motion.div variants={containerVariants} initial="hidden" animate="visible" className="space-y-6">
                <motion.div variants={itemVariants} className="glass-panel rounded-xl p-6">
                  <h2 className="text-xl font-semibold text-jarvis-text mb-4 flex items-center gap-2">
                    <Image size={24} className="text-jarvis-accentPink" />
                    Supported File Types
                  </h2>
                  <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                    {[
                      { icon: <Image size={20} />, label: 'Images', types: 'PNG, JPG, WebP, GIF' },
                      { icon: <FileText size={20} />, label: 'Documents', types: 'PDF, DOCX, TXT' },
                      { icon: <Code size={20} />, label: 'Code', types: 'JS, PY, HTML, CSS' },
                      { icon: <Database size={20} />, label: 'Data', types: 'CSV, JSON, XML' },
                    ].map((item) => (
                      <div key={item.label} className="p-4 rounded-lg bg-white/5 text-center">
                        <div className="text-jarvis-accentPink mb-2 flex justify-center">{item.icon}</div>
                        <div className="font-medium text-jarvis-text text-sm">{item.label}</div>
                        <div className="text-xs text-jarvis-textMuted">{item.types}</div>
                      </div>
                    ))}
                  </div>
                </motion.div>

                <motion.div variants={itemVariants} className="glass-panel rounded-xl p-6">
                  <h2 className="text-xl font-semibold text-jarvis-text mb-4">How to Upload</h2>
                  <div className="space-y-4">
                    <div className="flex items-start gap-4">
                      <div className="w-8 h-8 rounded-full bg-jarvis-accentPink/20 text-jarvis-accentPink flex items-center justify-center font-bold text-sm">1</div>
                      <div>
                        <h3 className="font-medium text-jarvis-text">Click Upload Button</h3>
                        <p className="text-sm text-jarvis-textMuted">In the Smart Assistant chat, click the paperclip icon</p>
                      </div>
                    </div>
                    <div className="flex items-start gap-4">
                      <div className="w-8 h-8 rounded-full bg-jarvis-accentPink/20 text-jarvis-accentPink flex items-center justify-center font-bold text-sm">2</div>
                      <div>
                        <h3 className="font-medium text-jarvis-text">Select File</h3>
                        <p className="text-sm text-jarvis-textMuted">Choose an image, PDF, or document from your computer</p>
                      </div>
                    </div>
                    <div className="flex items-start gap-4">
                      <div className="w-8 h-8 rounded-full bg-jarvis-accentPink/20 text-jarvis-accentPink flex items-center justify-center font-bold text-sm">3</div>
                      <div>
                        <h3 className="font-medium text-jarvis-text">Ask Questions</h3>
                        <p className="text-sm text-jarvis-textMuted">"What's in this image?" or "Summarize this PDF"</p>
                      </div>
                    </div>
                  </div>
                </motion.div>

                <motion.div variants={itemVariants} className="glass-panel rounded-xl p-6">
                  <h2 className="text-xl font-semibold text-jarvis-text mb-4">Example Queries</h2>
                  <div className="space-y-2">
                    <CommandExample command="What's in this image?" description="Describe image contents" />
                    <CommandExample command="Extract text from this document" description="OCR text extraction" />
                    <CommandExample command="Summarize this PDF" description="Get document summary" />
                    <CommandExample command="Is there a cat in this photo?" description="Object detection questions" />
                  </div>
                </motion.div>
              </motion.div>
            </motion.div>
          )}

          {activeSection === 'about' && (
            <motion.div
              key="about"
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0, y: -20 }}
              className="p-8 max-w-3xl"
            >
              <div className="text-center mb-8">
                <motion.div 
                  className="w-24 h-24 mx-auto mb-4 rounded-2xl bg-gradient-to-br from-jarvis-accentPink to-jarvis-accentRed flex items-center justify-center"
                  animate={{ rotate: [0, 5, -5, 0] }}
                  transition={{ duration: 4, repeat: Infinity }}
                >
                  <Bot size={48} className="text-white" />
                </motion.div>
                <h1 className="text-3xl font-bold text-jarvis-text mb-2">About Abhinav</h1>
                <p className="text-jarvis-textMuted">Creator of JARVIS Ultimate</p>
              </div>

              <motion.div 
                variants={containerVariants}
                initial="hidden"
                animate="visible"
                className="space-y-6"
              >
                <motion.div variants={itemVariants} className="glass-panel rounded-xl p-6 text-center">
                  <p className="text-jarvis-text leading-relaxed mb-4">
                    Hi! I'm <span className="text-jarvis-accentPink font-semibold">Abhinav</span>, a passionate developer 
                    who loves building cool things with AI and code.
                  </p>
                  <p className="text-jarvis-textMuted leading-relaxed">
                    JARVIS Ultimate is my dream project - an AI assistant that actually helps you 
                    get things done. From controlling your PC to analyzing files, I wanted to create 
                    something that's both powerful and beautiful.
                  </p>
                </motion.div>

                <motion.div variants={itemVariants} className="grid grid-cols-2 gap-4">
                  <a href="#" className="glass-panel rounded-xl p-4 flex items-center gap-3 hover:border-jarvis-accentPink/30 transition-colors">
                    <Github size={24} className="text-jarvis-textMuted" />
                    <div>
                      <div className="font-medium text-jarvis-text">GitHub</div>
                      <div className="text-xs text-jarvis-textMuted">@abhinav-af</div>
                    </div>
                  </a>
                  <a href="#" className="glass-panel rounded-xl p-4 flex items-center gap-3 hover:border-jarvis-accentPink/30 transition-colors">
                    <Twitter size={24} className="text-blue-400" />
                    <div>
                      <div className="font-medium text-jarvis-text">Twitter</div>
                      <div className="text-xs text-jarvis-textMuted">@abhinavbuilds</div>
                    </div>
                  </a>
                </motion.div>

                <motion.div variants={itemVariants} className="glass-panel rounded-xl p-6">
                  <div className="flex items-center justify-between">
                    <div>
                      <h3 className="font-semibold text-jarvis-text">Support the Project</h3>
                      <p className="text-sm text-jarvis-textMuted">Star on GitHub if you love JARVIS!</p>
                    </div>
                    <motion.button
                      className="flex items-center gap-2 px-4 py-2 bg-jarvis-accentPink/20 text-jarvis-accentPink rounded-lg font-medium"
                      whileHover={{ scale: 1.05 }}
                      whileTap={{ scale: 0.95 }}
                    >
                      <Star size={18} />
                      Star
                    </motion.button>
                  </div>
                </motion.div>
              </motion.div>
            </motion.div>
          )}

          {/* Other sections placeholder */}
          {!['getting-started', 'features', 'commands', 'file-upload', 'about'].includes(activeSection) && (
            <motion.div
              key={activeSection}
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0, y: -20 }}
              className="p-8 max-w-4xl"
            >
              <div className="glass-panel rounded-xl p-12 text-center">
                <HelpCircle size={48} className="mx-auto text-jarvis-textMuted mb-4" />
                <h2 className="text-xl font-semibold text-jarvis-text mb-2">Coming Soon</h2>
                <p className="text-jarvis-textMuted">This documentation section is being written by Abhinav.</p>
                <p className="text-sm text-jarvis-textMuted mt-2">Check back for updates!</p>
              </div>
            </motion.div>
          )}
        </AnimatePresence>
      </div>
    </motion.div>
  );
}
