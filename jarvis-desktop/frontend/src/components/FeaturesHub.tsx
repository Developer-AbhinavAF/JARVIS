import { useState } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import {
  Wand2, Languages, Mic, BookOpen, Image, Search, Newspaper, Cloud,
  TrendingUp, DollarSign, ChefHat, Youtube, Film, Sparkles,
  Zap, Crown, X, Copy, RefreshCw, Github, MapPin, QrCode, MessageCircle,
  Gamepad2, Quote, Laugh, HelpCircle, AlertCircle, ExternalLink,
  Music, LayoutGrid, Folder, Clipboard, Camera, Video, Plane, ShoppingCart,
  Radio, Bell, CheckSquare, Calendar, Target, StickyNote, Palette,
  Gauge, Terminal, Braces, Coins, Dices,
  CircleDot, Code, FileText, Mail, Clock, Lock, Database,
  Shield, BarChart, Mic2, AlignLeft, Users, Repeat,
  Timer, Cpu
} from 'lucide-react';

interface Feature {
  id: string;
  name: string;
  icon: React.ReactNode;
  color: string;
  description: string;
  category: string;
  endpoint?: string;
}

const features: Feature[] = [
  // ===== 🤖 AI FEATURES (1-7) =====
  { id: 'ai-openrouter', name: 'OpenRouter AI', icon: <Wand2 size={20} />, color: 'from-purple-500 to-pink-500', description: 'GPT-4, Llama, Mixtral access', category: 'AI', endpoint: '/api/real/openrouter?prompt=Hello&model=openai/gpt-3.5-turbo' },
  { id: 'ai-gemini', name: 'Google Gemini', icon: <Sparkles size={20} />, color: 'from-blue-500 to-cyan-500', description: 'Google AI 60 req/min', category: 'AI', endpoint: '/api/real/gemini?prompt=Explain+AI' },
  { id: 'ai-image-gen', name: 'AI Image Generation', icon: <Image size={20} />, color: 'from-violet-500 to-purple-500', description: 'Generate images FREE', category: 'AI', endpoint: '/api/ai/generate-image?prompt=futuristic+city' },
  { id: 'ai-code-assist', name: 'AI Code Assistant', icon: <Code size={20} />, color: 'from-green-500 to-emerald-500', description: 'Explain, debug, optimize code', category: 'AI', endpoint: '/api/ai/code-assist?code=print(hello)&action=explain' },
  { id: 'ai-summarize', name: 'AI Summarizer', icon: <FileText size={20} />, color: 'from-orange-500 to-amber-500', description: 'Summarize long documents', category: 'AI', endpoint: '/api/ai/summarize?text=Long+text+here&max_length=200' },
  { id: 'ai-translate', name: 'AI Translator', icon: <Languages size={20} />, color: 'from-pink-500 to-rose-500', description: 'Hindi, English, Hinglish support', category: 'AI', endpoint: '/api/ai/translate?text=Hello&target_lang=hi' },
  { id: 'ai-write-email', name: 'AI Email Writer', icon: <Mail size={20} />, color: 'from-indigo-500 to-purple-500', description: 'Professional email drafts', category: 'AI', endpoint: '/api/ai/write-email?subject=Meeting&recipient=boss@company.com' },
  { id: 'ai-meeting-notes', name: 'Meeting Notes', icon: <StickyNote size={20} />, color: 'from-yellow-500 to-orange-500', description: 'Notes from voice transcript', category: 'AI', endpoint: '/api/ai/meeting-notes?transcript=Meeting+discussion' },
  { id: 'ai-write-story', name: 'Story Writer', icon: <BookOpen size={20} />, color: 'from-teal-500 to-cyan-500', description: 'AI story/script generation', category: 'AI', endpoint: '/api/ai/write-story?genre=sci-fi&theme=adventure' },
  
  // ===== 🎙️ VOICE FEATURES (11-14) =====
  { id: 'voice-wake-word', name: 'Wake Word Detection', icon: <Mic size={20} />, color: 'from-blue-400 to-cyan-400', description: '"Hey JARVIS" activation', category: 'Voice', endpoint: '/api/voice/wake-word' },
  { id: 'voice-profiles', name: 'Voice Profiles', icon: <Users size={20} />, color: 'from-green-400 to-emerald-400', description: 'Multiple user voice profiles', category: 'Voice', endpoint: '/api/voice/profiles' },
  { id: 'voice-speed', name: 'Voice Speed Control', icon: <Gauge size={20} />, color: 'from-purple-400 to-violet-400', description: '0.5x to 2.0x speed', category: 'Voice', endpoint: '/api/voice/speed?speed=1.2' },
  { id: 'voice-continuous', name: 'Continuous Mode', icon: <Repeat size={20} />, color: 'from-orange-400 to-amber-400', description: 'Non-stop conversation', category: 'Voice', endpoint: '/api/voice/continuous?enable=true' },
  
  // ===== 💻 SYSTEM CONTROL (15-20) =====
  { id: 'system-window', name: 'Window Manager', icon: <LayoutGrid size={20} />, color: 'from-blue-500 to-indigo-500', description: 'Minimize, tile, switch windows', category: 'System', endpoint: '/api/system/window?action=minimize' },
  { id: 'system-apps', name: 'App Launcher', icon: <Zap size={20} />, color: 'from-green-500 to-emerald-500', description: 'Launch recent apps', category: 'System', endpoint: '/api/system/apps' },
  { id: 'system-files', name: 'File Manager', icon: <Folder size={20} />, color: 'from-yellow-500 to-amber-500', description: 'Browse files & folders', category: 'System', endpoint: '/api/system/files?path=Downloads' },
  { id: 'system-clipboard', name: 'Clipboard Manager', icon: <Clipboard size={20} />, color: 'from-pink-500 to-rose-500', description: 'Clipboard history', category: 'System', endpoint: '/api/system/clipboard' },
  { id: 'system-screenshot', name: 'Screenshot + OCR', icon: <Camera size={20} />, color: 'from-purple-500 to-violet-500', description: 'Capture & read text from screen', category: 'System', endpoint: '/api/system/screenshot' },
  { id: 'system-record', name: 'Screen Recording', icon: <Video size={20} />, color: 'from-red-500 to-rose-500', description: 'Record screen activity', category: 'System', endpoint: '/api/system/record?action=start' },
  
  // ===== 🌐 WEB & INFO (21-31) =====
  { id: 'web-smart-search', name: 'Smart Web Search', icon: <Search size={20} />, color: 'from-blue-500 to-cyan-500', description: 'Multi-engine search', category: 'Web', endpoint: '/api/web/search?query=python+tutorial&engine=google' },
  { id: 'web-news', name: 'News Reader', icon: <Newspaper size={20} />, color: 'from-sky-500 to-blue-500', description: 'Latest headlines', category: 'Web', endpoint: '/api/web/news?category=technology' },
  { id: 'web-weather', name: 'Weather Forecast', icon: <Cloud size={20} />, color: 'from-cyan-400 to-blue-400', description: '7-day weather forecast', category: 'Web', endpoint: '/api/web/weather?city=Mumbai' },
  { id: 'web-stocks', name: 'Stock Tracker', icon: <TrendingUp size={20} />, color: 'from-green-500 to-emerald-500', description: 'Real-time stock prices', category: 'Web', endpoint: '/api/web/stocks?symbol=AAPL' },
  { id: 'web-currency', name: 'Currency Converter', icon: <DollarSign size={20} />, color: 'from-yellow-500 to-amber-500', description: 'Live exchange rates', category: 'Web', endpoint: '/api/web/currency?amount=100&from_curr=USD&to_curr=INR' },
  { id: 'web-flight', name: 'Flight Tracker', icon: <Plane size={20} />, color: 'from-blue-400 to-indigo-400', description: 'PNR/Flight status', category: 'Web', endpoint: '/api/web/flight?pnr=ABC123' },
  { id: 'web-recipe', name: 'Recipe Finder', icon: <ChefHat size={20} />, color: 'from-orange-400 to-amber-400', description: 'Find recipes by dish', category: 'Web', endpoint: '/api/web/recipe?dish=biryani' },
  { id: 'web-shopping', name: 'Shopping Compare', icon: <ShoppingCart size={20} />, color: 'from-pink-400 to-rose-400', description: 'Price comparison', category: 'Web', endpoint: '/api/web/shopping?product=iPhone+15' },
  
  // ===== 🎵 MEDIA CONTROL (32-35) =====
  { id: 'media-spotify', name: 'Spotify Control', icon: <Music size={20} />, color: 'from-green-500 to-emerald-500', description: 'Play/Pause/Skip tracks', category: 'Media', endpoint: '/api/media/spotify?action=play' },
  { id: 'media-youtube', name: 'YouTube Player', icon: <Youtube size={20} />, color: 'from-red-600 to-rose-600', description: 'Search & play videos', category: 'Media', endpoint: '/api/media/youtube?query=lofi+music' },
  { id: 'media-music-recognize', name: 'Music Recognition', icon: <Mic2 size={20} />, color: 'from-purple-500 to-violet-500', description: 'Shazam-like song ID', category: 'Media', endpoint: '/api/media/music-recognize' },
  { id: 'media-podcast', name: 'Podcast Player', icon: <Radio size={20} />, color: 'from-orange-500 to-amber-500', description: 'Listen to podcasts', category: 'Media', endpoint: '/api/media/podcast?action=list' },
  { id: 'media-movies', name: 'Movie Recommendations', icon: <Film size={20} />, color: 'from-pink-600 to-rose-600', description: 'Movies by genre & mood', category: 'Media', endpoint: '/api/media/movies?genre=action&mood=excited' },
  
  // ===== 🧠 KNOWLEDGE (36-39) =====
  { id: 'knowledge-wikipedia', name: 'Wikipedia', icon: <BookOpen size={20} />, color: 'from-gray-500 to-slate-500', description: 'Instant knowledge lookup', category: 'Knowledge', endpoint: '/api/real/wikipedia?query=India&sentences=3' },
  { id: 'knowledge-dictionary', name: 'Dictionary', icon: <AlignLeft size={20} />, color: 'from-blue-400 to-indigo-400', description: 'Word definitions', category: 'Knowledge', endpoint: '/api/knowledge/dictionary?word=serendipity' },
  { id: 'knowledge-fact', name: 'Random Facts', icon: <HelpCircle size={20} />, color: 'from-purple-400 to-violet-400', description: 'Interesting facts', category: 'Knowledge', endpoint: '/api/knowledge/fact' },
  { id: 'knowledge-joke', name: 'Jokes', icon: <Laugh size={20} />, color: 'from-yellow-400 to-orange-400', description: 'Programming jokes', category: 'Knowledge', endpoint: '/api/real/joke?category=Programming' },
  { id: 'knowledge-quote', name: 'Quotes', icon: <Quote size={20} />, color: 'from-pink-400 to-rose-400', description: 'Inspirational quotes', category: 'Knowledge', endpoint: '/api/real/quote' },
  { id: 'knowledge-coin-flip', name: 'Coin Flip', icon: <CircleDot size={20} />, color: 'from-yellow-500 to-amber-500', description: 'Heads or tails', category: 'Knowledge', endpoint: '/api/knowledge/coin-flip' },
  { id: 'knowledge-dice-roll', name: 'Dice Roll', icon: <Dices size={20} />, color: 'from-red-500 to-rose-500', description: 'Roll the dice', category: 'Knowledge', endpoint: '/api/knowledge/dice-roll?sides=6' },
  
  // ===== 🛠️ PRODUCTIVITY (40-46) =====
  { id: 'productivity-todo', name: 'Smart To-Do', icon: <CheckSquare size={20} />, color: 'from-green-500 to-emerald-500', description: 'AI-powered task list', category: 'Productivity', endpoint: '/api/productivity/todo' },
  { id: 'productivity-calendar', name: 'Calendar View', icon: <Calendar size={20} />, color: 'from-blue-500 to-cyan-500', description: 'Schedule & events', category: 'Productivity', endpoint: '/api/productivity/calendar?view=month' },
  { id: 'productivity-notes', name: 'Smart Notes', icon: <StickyNote size={20} />, color: 'from-yellow-500 to-amber-500', description: 'AI note-taking', category: 'Productivity', endpoint: '/api/productivity/notes?action=list' },
  { id: 'productivity-reminder', name: 'Reminders', icon: <Bell size={20} />, color: 'from-red-500 to-rose-500', description: 'Set alarms & reminders', category: 'Productivity', endpoint: '/api/productivity/reminder?action=set&time=14:00' },
  { id: 'productivity-pomodoro', name: 'Pomodoro Timer', icon: <Timer size={20} />, color: 'from-orange-500 to-red-500', description: 'Focus timer', category: 'Productivity', endpoint: '/api/productivity/pomodoro?action=start' },
  { id: 'productivity-clipboard', name: 'Clipboard History', icon: <Clipboard size={20} />, color: 'from-pink-500 to-rose-500', description: 'Advanced clipboard', category: 'Productivity', endpoint: '/api/productivity/clipboard?action=history' },
  { id: 'productivity-focus', name: 'Focus Mode', icon: <Target size={20} />, color: 'from-purple-500 to-violet-500', description: 'Block distractions', category: 'Productivity', endpoint: '/api/productivity/focus?enable=true' },
  
  // ===== 🔒 SECURITY (47-50) =====
  { id: 'security-password', name: 'Password Generator', icon: <Lock size={20} />, color: 'from-green-500 to-emerald-500', description: 'Strong passwords', category: 'Security', endpoint: '/api/security/password?length=16' },
  { id: 'security-check', name: 'Security Check', icon: <Shield size={20} />, color: 'from-blue-500 to-cyan-500', description: 'System security scan', category: 'Security', endpoint: '/api/security/check' },
  { id: 'security-encrypt', name: 'File Encryption', icon: <FileText size={20} />, color: 'from-purple-500 to-violet-500', description: 'Encrypt sensitive files', category: 'Security', endpoint: '/api/security/encrypt?action=encrypt' },
  { id: 'security-vault', name: 'Password Vault', icon: <Database size={20} />, color: 'from-orange-500 to-amber-500', description: 'Secure password storage', category: 'Security', endpoint: '/api/security/vault?action=list' },
  
  // ===== 🎮 GAMING (51-54) =====
  { id: 'gaming-quick-launch', name: 'Game Launcher', icon: <Gamepad2 size={20} />, color: 'from-purple-500 to-violet-500', description: 'Launch installed games', category: 'Gaming', endpoint: '/api/gaming/quick-launch' },
  { id: 'gaming-stats', name: 'Gaming Stats', icon: <BarChart size={20} />, color: 'from-green-500 to-emerald-500', description: 'Track play time', category: 'Gaming', endpoint: '/api/gaming/stats?game=all' },
  { id: 'gaming-optimize', name: 'Gaming Mode', icon: <Zap size={20} />, color: 'from-blue-500 to-cyan-500', description: 'Optimize for gaming', category: 'Gaming', endpoint: '/api/gaming/optimize?enable=true' },
  { id: 'gaming-stream', name: 'Stream Overlay', icon: <Video size={20} />, color: 'from-red-500 to-rose-500', description: 'Streaming tools', category: 'Gaming', endpoint: '/api/gaming/stream?platform=twitch' },
  
  // ===== 📊 DEV TOOLS (55-60) =====
  { id: 'dev-api-tester', name: 'API Tester', icon: <Terminal size={20} />, color: 'from-green-500 to-emerald-500', description: 'Test REST APIs', category: 'Dev', endpoint: '/api/dev/api-tester?method=GET&url=https://api.github.com' },
  { id: 'dev-regex', name: 'Regex Tester', icon: <Search size={20} />, color: 'from-blue-500 to-cyan-500', description: 'Test regular expressions', category: 'Dev', endpoint: '/api/dev/regex?pattern=test&text=testing' },
  { id: 'dev-json', name: 'JSON Formatter', icon: <Braces size={20} />, color: 'from-yellow-500 to-amber-500', description: 'Format & validate JSON', category: 'Dev', endpoint: '/api/dev/json?action=format' },
  { id: 'dev-base64', name: 'Base64 Tool', icon: <Code size={20} />, color: 'from-purple-500 to-violet-500', description: 'Encode/decode Base64', category: 'Dev', endpoint: '/api/dev/base64?action=encode&text=hello' },
  { id: 'dev-timestamp', name: 'Unix Timestamp', icon: <Clock size={20} />, color: 'from-gray-500 to-slate-500', description: 'Convert timestamps', category: 'Dev', endpoint: '/api/dev/timestamp?convert=now' },
  { id: 'dev-color', name: 'Color Tool', icon: <Palette size={20} />, color: 'from-pink-500 to-rose-500', description: 'HEX/RGB converter', category: 'Dev', endpoint: '/api/dev/color?hex=FF5733' },
  
  // ===== 🌤️ REAL APIs =====
  { id: 'real-weather', name: 'Live Weather', icon: <Cloud size={20} />, color: 'from-cyan-400 to-blue-400', description: 'Real-time weather API', category: 'Real APIs', endpoint: '/api/real/weather?city=Mumbai' },
  { id: 'real-crypto', name: 'Crypto Prices', icon: <Coins size={20} />, color: 'from-green-500 to-emerald-500', description: 'Live BTC, ETH prices', category: 'Real APIs', endpoint: '/api/real/crypto?coin=bitcoin' },
  { id: 'real-news', name: 'Live News', icon: <Newspaper size={20} />, color: 'from-sky-500 to-blue-500', description: 'Latest headlines', category: 'Real APIs', endpoint: '/api/real/news?category=technology' },
  { id: 'real-youtube', name: 'YouTube Search', icon: <Youtube size={20} />, color: 'from-red-600 to-rose-600', description: 'Find videos', category: 'Real APIs', endpoint: '/api/real/youtube?query=programming' },
  { id: 'real-github', name: 'GitHub Stats', icon: <Github size={20} />, color: 'from-gray-700 to-gray-900', description: 'Profile & repo info', category: 'Real APIs', endpoint: '/api/real/github/user?username=torvalds' },
  { id: 'real-reddit', name: 'Reddit Posts', icon: <MessageCircle size={20} />, color: 'from-orange-600 to-red-600', description: 'Hot posts', category: 'Real APIs', endpoint: '/api/real/reddit?subreddit=technology' },
  { id: 'real-recipe', name: 'Recipes', icon: <ChefHat size={20} />, color: 'from-orange-400 to-amber-400', description: 'Meal recipes', category: 'Real APIs', endpoint: '/api/real/recipe?ingredient=chicken' },
  { id: 'real-location', name: 'My Location', icon: <MapPin size={20} />, color: 'from-green-500 to-emerald-500', description: 'IP geolocation', category: 'Real APIs', endpoint: '/api/real/location' },
  { id: 'real-qr', name: 'QR Generator', icon: <QrCode size={20} />, color: 'from-gray-500 to-slate-500', description: 'Create QR codes', category: 'Real APIs', endpoint: '/api/real/qr?data=hello' },
  { id: 'real-games', name: 'Game Deals', icon: <Gamepad2 size={20} />, color: 'from-purple-500 to-violet-500', description: 'Steam prices', category: 'Real APIs', endpoint: '/api/real/games/search?query=witcher' },
  { id: 'real-movies', name: 'Movie Search', icon: <Film size={20} />, color: 'from-pink-600 to-rose-600', description: 'TMDB movies', category: 'Real APIs', endpoint: '/api/real/movies/search?query=Inception' },
  { id: 'real-tts', name: 'Text to Speech', icon: <Mic size={20} />, color: 'from-green-500 to-emerald-500', description: 'Hindi/English voice', category: 'Real APIs', endpoint: '/api/real/tts?text=Hello&lang=en' },
  { id: 'real-translate', name: 'Translator', icon: <Languages size={20} />, color: 'from-orange-500 to-red-500', description: '100+ languages', category: 'Real APIs', endpoint: '/api/real/translate?text=Hello&target=hi' },
  { id: 'real-stocks', name: 'Stock Prices', icon: <DollarSign size={20} />, color: 'from-blue-500 to-indigo-500', description: 'Market data', category: 'Real APIs', endpoint: '/api/real/stock?symbol=AAPL' },
  { id: 'real-web-search', name: 'Web Search', icon: <Search size={20} />, color: 'from-blue-500 to-indigo-500', description: 'DuckDuckGo search', category: 'Real APIs', endpoint: '/api/real/web-search?query=AI' },
];

const categories = ['All', 'AI', 'Voice', 'System', 'Web', 'Media', 'Knowledge', 'Productivity', 'Security', 'Gaming', 'Dev', 'Real APIs'];

export default function FeaturesHub({ onClose }: { onClose: () => void }) {
  const [activeCategory, setActiveCategory] = useState('All');
  const [searchQuery, setSearchQuery] = useState('');
  const [selectedFeature, setSelectedFeature] = useState<Feature | null>(null);
  const [loading, setLoading] = useState<string | null>(null);
  const [result, setResult] = useState<any>(null);

  const filteredFeatures = features.filter(f => {
    const matchesCategory = activeCategory === 'All' || f.category === activeCategory;
    const matchesSearch = f.name.toLowerCase().includes(searchQuery.toLowerCase()) ||
                         f.description.toLowerCase().includes(searchQuery.toLowerCase());
    return matchesCategory && matchesSearch;
  });

  const handleFeatureClick = async (feature: Feature) => {
    if (!feature.endpoint) return;
    
    setSelectedFeature(feature);
    setLoading(feature.id);
    setResult(null);

    try {
      // Determine if endpoint needs POST based on path
      const postEndpoints = ['/api/ai/', '/api/system/window', '/api/system/screenshot', '/api/system/record', 
        '/api/media/spotify', '/api/media/youtube', '/api/media/music-recognize',
        '/api/productivity/', '/api/security/', '/api/gaming/', '/api/dev/'];
      const needsPost = postEndpoints.some(ep => feature.endpoint?.startsWith(ep));
      
      const url = `http://localhost:8001${feature.endpoint}`;
      
      let response;
      if (needsPost) {
        // For POST endpoints, extract query params and send as body
        const [path, queryString] = url.split('?');
        const params = new URLSearchParams(queryString || '');
        const body: any = {};
        params.forEach((value, key) => body[key] = value);
        
        response = await fetch(path, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: Object.keys(body).length > 0 ? JSON.stringify(body) : undefined,
        });
      } else {
        response = await fetch(url, {
          method: 'GET',
          headers: { 'Content-Type': 'application/json' },
        });
      }
      
      if (!response.ok) {
        const errorData = await response.json().catch(() => ({}));
        throw new Error(errorData.detail || `HTTP ${response.status}: Feature endpoint not implemented yet`);
      }
      
      const data = await response.json();
      setResult(data);
    } catch (error: any) {
      setResult({ 
        error: error.message || 'Feature not available',
        tip: 'Try using the AI chat instead! Just type your request naturally like "play music" or "open calculator"'
      });
    } finally {
      setLoading(null);
    }
  };

  return (
    <motion.div
      initial={{ opacity: 0, scale: 0.95 }}
      animate={{ opacity: 1, scale: 1 }}
      exit={{ opacity: 0, scale: 0.95 }}
      className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/80 backdrop-blur-sm"
    >
      <motion.div
        className="w-full max-w-6xl h-[90vh] bg-jarvis-dark/95 rounded-2xl border border-white/10 overflow-hidden flex flex-col"
        initial={{ y: 20 }}
        animate={{ y: 0 }}
      >
        {/* Header */}
        <div className="p-6 border-b border-white/10 flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className="p-2 rounded-xl bg-gradient-to-br from-jarvis-accentPink to-jarvis-accentRed">
              <Crown size={24} className="text-white" />
            </div>
            <div>
              <h2 className="text-2xl font-bold text-jarvis-text">Features Hub</h2>
              <p className="text-sm text-jarvis-textMuted">60+ powerful features at your command</p>
            </div>
          </div>
          <button
            onClick={onClose}
            className="p-2 rounded-lg hover:bg-white/10 transition-colors"
          >
            <X size={24} className="text-jarvis-text" />
          </button>
        </div>

        {/* Search & Categories */}
        <div className="p-4 border-b border-white/10 space-y-4">
          <div className="relative">
            <Search className="absolute left-4 top-1/2 -translate-y-1/2 text-jarvis-textMuted" size={20} />
            <input
              type="text"
              placeholder="Search 60+ features..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              className="w-full pl-12 pr-4 py-3 bg-white/5 rounded-xl text-jarvis-text placeholder:text-jarvis-textMuted focus:outline-none focus:ring-2 focus:ring-jarvis-accentPink/50"
            />
          </div>
          
          <div className="flex gap-2 overflow-x-auto scrollbar-hide pb-2">
            {categories.map(cat => (
              <button
                key={cat}
                onClick={() => setActiveCategory(cat)}
                className={`px-4 py-2 rounded-lg text-sm font-medium whitespace-nowrap transition-all ${
                  activeCategory === cat
                    ? 'bg-jarvis-accentPink text-white'
                    : 'bg-white/5 text-jarvis-textMuted hover:bg-white/10'
                }`}
              >
                {cat}
              </button>
            ))}
          </div>
        </div>

        {/* Features Grid */}
        <div className="flex-1 overflow-y-auto p-4">
          <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 lg:grid-cols-5 xl:grid-cols-6 gap-3">
            {filteredFeatures.map((feature, index) => (
              <motion.button
                key={feature.id}
                initial={{ opacity: 0, y: 20 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ delay: index * 0.02 }}
                onClick={() => handleFeatureClick(feature)}
                whileHover={{ scale: 1.05 }}
                whileTap={{ scale: 0.95 }}
                className="p-4 rounded-xl bg-white/5 hover:bg-white/10 border border-white/5 hover:border-jarvis-accentPink/30 transition-all text-left group"
              >
                <div className={`w-10 h-10 rounded-lg bg-gradient-to-br ${feature.color} flex items-center justify-center mb-3 group-hover:scale-110 transition-transform`}>
                  <span className="text-white">{feature.icon}</span>
                </div>
                <h3 className="font-medium text-jarvis-text text-sm mb-1">{feature.name}</h3>
                <p className="text-xs text-jarvis-textMuted line-clamp-2">{feature.description}</p>
                <span className="text-[10px] text-jarvis-accentPink mt-2 inline-block">{feature.category}</span>
              </motion.button>
            ))}
          </div>
        </div>

        {/* Feature Result Modal */}
        <AnimatePresence>
          {selectedFeature && (
            <motion.div
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              exit={{ opacity: 0 }}
              className="absolute inset-0 bg-black/60 backdrop-blur-sm flex items-center justify-center p-4"
              onClick={() => setSelectedFeature(null)}
            >
              <motion.div
                initial={{ scale: 0.9, opacity: 0 }}
                animate={{ scale: 1, opacity: 1 }}
                exit={{ scale: 0.9, opacity: 0 }}
                className="bg-jarvis-dark rounded-2xl border border-white/10 p-6 max-w-md w-full max-h-[70vh] overflow-y-auto"
                onClick={e => e.stopPropagation()}
              >
                <div className="flex items-center gap-3 mb-4">
                  <div className={`w-12 h-12 rounded-xl bg-gradient-to-br ${selectedFeature.color} flex items-center justify-center`}>
                    {selectedFeature.icon}
                  </div>
                  <div>
                    <h3 className="text-xl font-bold text-jarvis-text">{selectedFeature.name}</h3>
                    <p className="text-sm text-jarvis-textMuted">{selectedFeature.description}</p>
                  </div>
                </div>

                {loading === selectedFeature.id ? (
                  <div className="flex items-center justify-center py-8">
                    <motion.div
                      animate={{ rotate: 360 }}
                      transition={{ duration: 1, repeat: Infinity, ease: "linear" }}
                    >
                      <RefreshCw size={32} className="text-jarvis-accentPink" />
                    </motion.div>
                  </div>
                ) : result ? (
                  <div className="bg-white/5 rounded-lg p-4 max-h-[50vh] overflow-y-auto">
                    {result.error ? (
                      <div className="space-y-3">
                        <div className="text-red-400 text-sm">
                          <AlertCircle size={16} className="inline mr-2" />
                          {result.error}
                        </div>
                        {result.tip && (
                          <div className="p-3 bg-jarvis-accentPink/10 rounded-lg border border-jarvis-accentPink/30">
                            <p className="text-sm text-jarvis-accentPink">
                              <Sparkles size={14} className="inline mr-2" />
                              {result.tip}
                            </p>
                          </div>
                        )}
                      </div>
                    ) : (
                      <div className="space-y-3">
                        {result.title && (
                          <h4 className="font-semibold text-jarvis-text">{result.title}</h4>
                        )}
                        {result.content && (
                          <p className="text-sm text-jarvis-text leading-relaxed">{result.content}</p>
                        )}
                        {result.summary && (
                          <p className="text-sm text-jarvis-text leading-relaxed">{result.summary}</p>
                        )}
                        {result.text && (
                          <p className="text-sm text-jarvis-text leading-relaxed">{result.text}</p>
                        )}
                        {result.translated && (
                          <div className="p-3 bg-green-500/10 rounded-lg border border-green-500/20">
                            <span className="text-xs text-green-400 uppercase tracking-wide">Translation</span>
                            <p className="text-sm text-jarvis-text mt-1">{result.translated}</p>
                          </div>
                        )}
                        {result.temperature !== undefined && (
                          <div className="flex items-center gap-3 p-3 bg-blue-500/10 rounded-lg">
                            <Cloud size={24} className="text-blue-400" />
                            <div>
                              <div className="text-2xl font-bold text-jarvis-text">{result.temperature}°C</div>
                              <div className="text-xs text-jarvis-textMuted">{result.description}</div>
                            </div>
                          </div>
                        )}
                        {result.price && (
                          <div className="text-xl font-bold text-green-400">${result.price}</div>
                        )}
                        {result.rate && (
                          <div className="text-lg font-semibold text-jarvis-text">{result.rate}</div>
                        )}
                        {result.articles && (
                          <div className="space-y-2">
                            <h4 className="font-semibold text-jarvis-text text-sm">Latest Headlines</h4>
                            {result.articles.slice(0, 5).map((article: any, idx: number) => (
                              <div key={idx} className="p-2 bg-white/5 rounded-lg hover:bg-white/10 transition-colors cursor-pointer"
                                onClick={() => article.url && window.open(article.url, '_blank')}>
                                <div className="text-sm text-jarvis-text font-medium line-clamp-2">{article.title}</div>
                                <div className="text-xs text-jarvis-textMuted mt-1">{article.source}</div>
                              </div>
                            ))}
                          </div>
                        )}
                        {result.movies && (
                          <div className="grid grid-cols-1 gap-2">
                            {result.movies.map((movie: any, idx: number) => (
                              <div key={idx} className="flex gap-3 p-2 bg-white/5 rounded-lg">
                                {movie.poster && (
                                  <img src={movie.poster} alt={movie.title} className="w-12 h-16 object-cover rounded" />
                                )}
                                <div className="flex-1">
                                  <div className="text-sm font-medium text-jarvis-text">{movie.title}</div>
                                  <div className="text-xs text-jarvis-textMuted">{movie.year} • ★ {movie.rating}</div>
                                </div>
                              </div>
                            ))}
                          </div>
                        )}
                        {result.recipes && (
                          <div className="space-y-3">
                            {result.recipes.map((recipe: any, idx: number) => (
                              <div key={idx} className="p-3 bg-white/5 rounded-lg">
                                <div className="text-sm font-semibold text-jarvis-text">{recipe.name}</div>
                                <div className="text-xs text-jarvis-textMuted">{recipe.category} • {recipe.area}</div>
                                {recipe.ingredients && (
                                  <div className="flex flex-wrap gap-1 mt-2">
                                    {recipe.ingredients.slice(0, 5).map((ing: string, i: number) => (
                                      <span key={i} className="text-[10px] px-1.5 py-0.5 bg-orange-500/20 text-orange-300 rounded">{ing}</span>
                                    ))}
                                  </div>
                                )}
                              </div>
                            ))}
                          </div>
                        )}
                        {result.posts && (
                          <div className="space-y-2">
                            {result.posts.map((post: any, idx: number) => (
                              <div key={idx} className="p-2 bg-white/5 rounded-lg hover:bg-white/10 transition-colors cursor-pointer"
                                onClick={() => post.url && window.open(post.url, '_blank')}>
                                <div className="text-sm text-jarvis-text line-clamp-2">{post.title}</div>
                                <div className="text-xs text-jarvis-textMuted mt-1 flex items-center gap-2">
                                  <span>↑ {post.score}</span>
                                  <span>💬 {post.comments}</span>
                                </div>
                              </div>
                            ))}
                          </div>
                        )}
                        {result.games && (
                          <div className="space-y-2">
                            {result.games.map((game: any, idx: number) => (
                              <div key={idx} className="flex items-center gap-3 p-2 bg-white/5 rounded-lg">
                                {game.thumb && (
                                  <img src={game.thumb} alt={game.name} className="w-16 h-10 object-cover rounded" />
                                )}
                                <div className="flex-1">
                                  <div className="text-sm font-medium text-jarvis-text">{game.name}</div>
                                  <div className="text-xs text-green-400">{game.cheapest_price}</div>
                                </div>
                              </div>
                            ))}
                          </div>
                        )}
                        {result.joke && (
                          <div className="p-3 bg-yellow-500/10 rounded-lg border border-yellow-500/20">
                            <p className="text-sm text-jarvis-text italic">{result.joke}</p>
                          </div>
                        )}
                        {result.quote && (
                          <div className="p-3 bg-blue-500/10 rounded-lg border border-blue-500/20">
                            <Quote size={16} className="text-blue-400 mb-2" />
                            <p className="text-sm text-jarvis-text italic">{result.quote}</p>
                            {result.author && <p className="text-xs text-jarvis-textMuted mt-2">— {result.author}</p>}
                          </div>
                        )}
                        {result.qr_code && (
                          <div className="flex justify-center">
                            <img src={`data:image/png;base64,${result.qr_code}`} alt="QR Code" className="rounded-lg" />
                          </div>
                        )}
                        {result.ip && (
                          <div className="grid grid-cols-2 gap-2 text-sm">
                            <div className="p-2 bg-white/5 rounded"><span className="text-jarvis-textMuted">IP:</span> {result.ip}</div>
                            <div className="p-2 bg-white/5 rounded"><span className="text-jarvis-textMuted">City:</span> {result.city}</div>
                            <div className="p-2 bg-white/5 rounded"><span className="text-jarvis-textMuted">Region:</span> {result.region}</div>
                            <div className="p-2 bg-white/5 rounded"><span className="text-jarvis-textMuted">Country:</span> {result.country}</div>
                          </div>
                        )}
                        {result.url && (
                          <a href={result.url} target="_blank" rel="noopener noreferrer" 
                            className="inline-flex items-center gap-1 text-sm text-jarvis-accentPink hover:underline">
                            <ExternalLink size={14} /> Open Link
                          </a>
                        )}
                        {result.trending && (
                          <div className="space-y-2">
                            {result.trending.map((coin: any, idx: number) => (
                              <div key={idx} className="flex justify-between items-center p-2 bg-white/5 rounded-lg">
                                <span className="text-sm text-jarvis-text">#{coin.rank} {coin.name}</span>
                                <span className="text-sm text-green-400">{coin.price}</span>
                              </div>
                            ))}
                          </div>
                        )}
                        {/* Fallback for unhandled response formats */}
                        {!result.title && !result.content && !result.text && !result.translated && 
                         result.temperature === undefined && !result.articles && !result.movies && 
                         !result.recipes && !result.posts && !result.games && !result.joke && 
                         !result.quote && !result.qr_code && !result.ip && !result.trending && (
                          <pre className="text-sm text-jarvis-text overflow-x-auto">
                            {JSON.stringify(result, null, 2)}
                          </pre>
                        )}
                      </div>
                    )}
                  </div>
                ) : null}

                <div className="flex gap-2 mt-4">
                  <button
                    onClick={() => setSelectedFeature(null)}
                    className="flex-1 py-2 rounded-lg bg-white/10 text-jarvis-text hover:bg-white/20 transition-colors"
                  >
                    Close
                  </button>
                  {result && (
                    <button
                      onClick={() => navigator.clipboard.writeText(JSON.stringify(result, null, 2))}
                      className="px-4 py-2 rounded-lg bg-jarvis-accentPink/20 text-jarvis-accentPink hover:bg-jarvis-accentPink/30 transition-colors"
                    >
                      <Copy size={18} />
                    </button>
                  )}
                </div>
              </motion.div>
            </motion.div>
          )}
        </AnimatePresence>

        {/* Footer Stats */}
        <div className="p-4 border-t border-white/10 bg-white/5">
          <div className="flex items-center justify-between text-sm text-jarvis-textMuted">
            <span>Showing {filteredFeatures.length} of {features.length} features</span>
            <div className="flex gap-4">
              <span className="flex items-center gap-1">
                <Cpu size={14} /> AI Powered
              </span>
              <span className="flex items-center gap-1">
                <Zap size={14} /> Instant
              </span>
            </div>
          </div>
        </div>
      </motion.div>
    </motion.div>
  );
}
