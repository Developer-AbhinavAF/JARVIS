import { useState } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import {
  Brain,
  CheckSquare,
  StickyNote,
  Bell,
  Plus,
  Trash2,
  Calendar,
  Clock,
  Edit3,
  Save,
  X,
  Search,
  Filter,
  ChevronDown,
  ChevronUp,
  Archive,
} from 'lucide-react';
import { useStore } from '@/store/useStore';
import type { Todo, Note, Reminder } from '@/types';

type TabType = 'todos' | 'notes' | 'reminders';

export default function MemorySection() {
  const { todos, notes, reminders, addTodo, toggleTodo, deleteTodo, addNote, updateNote, deleteNote, addReminder, deleteReminder } = useStore();
  const [activeTab, setActiveTab] = useState<TabType>('todos');
  const [searchQuery, setSearchQuery] = useState('');

  const tabs = [
    { id: 'todos', label: 'To-Do List', icon: CheckSquare, count: todos.filter(t => !t.completed).length },
    { id: 'notes', label: 'Notes', icon: StickyNote, count: notes.length },
    { id: 'reminders', label: 'Reminders', icon: Bell, count: reminders.length },
  ];

  return (
    <div className="h-full overflow-hidden flex flex-col">
      {/* Header */}
      <div className="p-6 border-b border-white/10">
        <div className="flex items-center justify-between mb-4">
          <h1 className="text-2xl font-bold text-jarvis-text flex items-center gap-3">
            <Brain size={28} className="text-jarvis-accentPink" />
            Memory Center
          </h1>
        </div>

        {/* Tabs */}
        <div className="flex items-center gap-2">
          {tabs.map((tab) => {
            const Icon = tab.icon;
            const isActive = activeTab === tab.id;
            return (
              <button
                key={tab.id}
                onClick={() => setActiveTab(tab.id)}
                className={`flex items-center gap-2 px-4 py-2 rounded-lg text-sm font-medium transition-all ${
                  isActive
                    ? 'bg-jarvis-accentPink/20 text-jarvis-accentPink'
                    : 'text-jarvis-textMuted hover:bg-white/5 hover:text-jarvis-text'
                }`}
              >
                <Icon size={16} />
                {tab.label}
                {tab.count > 0 && (
                  <span className={`ml-1 px-2 py-0.5 rounded-full text-xs ${
                    isActive ? 'bg-jarvis-accentPink text-white' : 'bg-white/10'
                  }`}>
                    {tab.count}
                  </span>
                )}
              </button>
            );
          })}
        </div>
      </div>

      {/* Search Bar */}
      <div className="px-6 py-3 border-b border-white/10">
        <div className="flex items-center gap-3">
          <div className="flex-1 relative">
            <Search size={16} className="absolute left-3 top-1/2 -translate-y-1/2 text-jarvis-textMuted" />
            <input
              type="text"
              placeholder={`Search ${activeTab}...`}
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              className="w-full pl-10 pr-4 py-2 bg-white/5 border border-white/10 rounded-lg text-sm text-jarvis-text placeholder-jarvis-textMuted focus:outline-none focus:border-jarvis-accentPink"
            />
          </div>
          <button className="p-2 rounded-lg hover:bg-white/5 text-jarvis-textMuted">
            <Filter size={18} />
          </button>
        </div>
      </div>

      {/* Content */}
      <div className="flex-1 overflow-y-auto p-6">
        <AnimatePresence mode="wait">
          {activeTab === 'todos' && (
            <TodosView key="todos" todos={todos} searchQuery={searchQuery} />
          )}
          {activeTab === 'notes' && (
            <NotesView key="notes" notes={notes} searchQuery={searchQuery} />
          )}
          {activeTab === 'reminders' && (
            <RemindersView key="reminders" reminders={reminders} searchQuery={searchQuery} />
          )}
        </AnimatePresence>
      </div>
    </div>
  );
}

// Todos View
function TodosView({ todos, searchQuery }: { todos: Todo[]; searchQuery: string }) {
  const { addTodo, toggleTodo, deleteTodo } = useStore();
  const [newTodo, setNewTodo] = useState('');
  const [showCompleted, setShowCompleted] = useState(true);

  const filteredTodos = todos.filter(t => 
    t.text.toLowerCase().includes(searchQuery.toLowerCase())
  );

  const pendingTodos = filteredTodos.filter(t => !t.completed);
  const completedTodos = filteredTodos.filter(t => t.completed);

  const handleAddTodo = (e: React.FormEvent) => {
    e.preventDefault();
    if (newTodo.trim()) {
      addTodo({ text: newTodo.trim(), completed: false });
      setNewTodo('');
    }
  };

  return (
    <motion.div
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      exit={{ opacity: 0, y: -20 }}
      className="space-y-4"
    >
      {/* Add Todo */}
      <form onSubmit={handleAddTodo} className="flex gap-2">
        <input
          type="text"
          value={newTodo}
          onChange={(e) => setNewTodo(e.target.value)}
          placeholder="Add a new task..."
          className="flex-1 px-4 py-3 bg-white/5 border border-white/10 rounded-lg text-sm text-jarvis-text placeholder-jarvis-textMuted focus:outline-none focus:border-jarvis-accentPink"
        />
        <button
          type="submit"
          className="px-4 py-3 bg-jarvis-accentPink text-white rounded-lg hover:bg-jarvis-accentPink/80 transition-colors"
        >
          <Plus size={20} />
        </button>
      </form>

      {/* Pending Todos */}
      <div className="space-y-2">
        <h3 className="text-sm font-medium text-jarvis-textMuted mb-2">
          Pending ({pendingTodos.length})
        </h3>
        {pendingTodos.length === 0 ? (
          <div className="text-center py-8 text-jarvis-textMuted">
            No pending tasks. Add one above!
          </div>
        ) : (
          pendingTodos.map((todo) => (
            <motion.div
              key={todo.id}
              layout
              className="flex items-center gap-3 p-3 rounded-lg glass-panel group"
            >
              <button
                onClick={() => toggleTodo(todo.id)}
                className="w-5 h-5 rounded border-2 border-jarvis-textMuted hover:border-jarvis-accentPink transition-colors flex items-center justify-center"
              />
              <span className="flex-1 text-jarvis-text">{todo.text}</span>
              <button
                onClick={() => deleteTodo(todo.id)}
                className="opacity-0 group-hover:opacity-100 p-1.5 rounded hover:bg-red-500/20 text-red-400 transition-all"
              >
                <Trash2 size={16} />
              </button>
            </motion.div>
          ))
        )}
      </div>

      {/* Completed Todos */}
      {completedTodos.length > 0 && (
        <div className="space-y-2">
          <button
            onClick={() => setShowCompleted(!showCompleted)}
            className="flex items-center gap-2 text-sm font-medium text-jarvis-textMuted hover:text-jarvis-text transition-colors"
          >
            {showCompleted ? <ChevronDown size={16} /> : <ChevronUp size={16} />}
            Completed ({completedTodos.length})
          </button>
          <AnimatePresence>
            {showCompleted && (
              <motion.div
                initial={{ height: 0, opacity: 0 }}
                animate={{ height: 'auto', opacity: 1 }}
                exit={{ height: 0, opacity: 0 }}
                className="space-y-2"
              >
                {completedTodos.map((todo) => (
                  <motion.div
                    key={todo.id}
                    layout
                    className="flex items-center gap-3 p-3 rounded-lg glass-panel opacity-60 group"
                  >
                    <button
                      onClick={() => toggleTodo(todo.id)}
                      className="w-5 h-5 rounded bg-green-500 flex items-center justify-center text-white"
                    >
                      <CheckSquare size={14} />
                    </button>
                    <span className="flex-1 text-jarvis-text line-through">{todo.text}</span>
                    <button
                      onClick={() => deleteTodo(todo.id)}
                      className="opacity-0 group-hover:opacity-100 p-1.5 rounded hover:bg-red-500/20 text-red-400 transition-all"
                    >
                      <Trash2 size={16} />
                    </button>
                  </motion.div>
                ))}
              </motion.div>
            )}
          </AnimatePresence>
        </div>
      )}
    </motion.div>
  );
}

// Notes View
function NotesView({ notes, searchQuery }: { notes: Note[]; searchQuery: string }) {
  const { addNote, updateNote, deleteNote } = useStore();
  const [editingId, setEditingId] = useState<string | null>(null);
  const [newNote, setNewNote] = useState({ title: '', content: '' });
  const [isAdding, setIsAdding] = useState(false);

  const filteredNotes = notes.filter(n => 
    n.title.toLowerCase().includes(searchQuery.toLowerCase()) ||
    n.content.toLowerCase().includes(searchQuery.toLowerCase())
  );

  const handleAddNote = () => {
    if (newNote.title.trim() || newNote.content.trim()) {
      addNote({ 
        title: newNote.title.trim() || 'Untitled', 
        content: newNote.content.trim() 
      });
      setNewNote({ title: '', content: '' });
      setIsAdding(false);
    }
  };

  return (
    <motion.div
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      exit={{ opacity: 0, y: -20 }}
      className="space-y-4"
    >
      {/* Add Note Button */}
      {!isAdding ? (
        <button
          onClick={() => setIsAdding(true)}
          className="w-full p-4 rounded-lg border-2 border-dashed border-white/20 hover:border-jarvis-accentPink/50 hover:bg-white/5 transition-all flex items-center justify-center gap-2 text-jarvis-textMuted"
        >
          <Plus size={20} />
          Create New Note
        </button>
      ) : (
        <motion.div
          initial={{ opacity: 0, scale: 0.95 }}
          animate={{ opacity: 1, scale: 1 }}
          className="glass-panel rounded-lg p-4"
        >
          <input
            type="text"
            value={newNote.title}
            onChange={(e) => setNewNote({ ...newNote, title: e.target.value })}
            placeholder="Note title..."
            className="w-full mb-3 px-3 py-2 bg-white/5 border border-white/10 rounded text-jarvis-text placeholder-jarvis-textMuted focus:outline-none focus:border-jarvis-accentPink font-medium"
          />
          <textarea
            value={newNote.content}
            onChange={(e) => setNewNote({ ...newNote, content: e.target.value })}
            placeholder="Write your note here..."
            rows={4}
            className="w-full mb-3 px-3 py-2 bg-white/5 border border-white/10 rounded text-jarvis-text placeholder-jarvis-textMuted focus:outline-none focus:border-jarvis-accentPink resize-none"
          />
          <div className="flex justify-end gap-2">
            <button
              onClick={() => setIsAdding(false)}
              className="px-3 py-1.5 rounded text-sm text-jarvis-textMuted hover:text-jarvis-text"
            >
              Cancel
            </button>
            <button
              onClick={handleAddNote}
              className="px-3 py-1.5 rounded text-sm bg-jarvis-accentPink text-white hover:bg-jarvis-accentPink/80 flex items-center gap-1"
            >
              <Save size={14} />
              Save
            </button>
          </div>
        </motion.div>
      )}

      {/* Notes Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        {filteredNotes.length === 0 ? (
          <div className="col-span-2 text-center py-8 text-jarvis-textMuted">
            No notes yet. Create your first note!
          </div>
        ) : (
          filteredNotes.map((note) => (
            <NoteCard
              key={note.id}
              note={note}
              isEditing={editingId === note.id}
              onEdit={() => setEditingId(note.id)}
              onSave={(updates) => {
                updateNote(note.id, updates);
                setEditingId(null);
              }}
              onCancel={() => setEditingId(null)}
              onDelete={() => deleteNote(note.id)}
            />
          ))
        )}
      </div>
    </motion.div>
  );
}

// Note Card Component
function NoteCard({ note, isEditing, onEdit, onSave, onCancel, onDelete }: {
  note: Note;
  isEditing: boolean;
  onEdit: () => void;
  onSave: (updates: Partial<Note>) => void;
  onCancel: () => void;
  onDelete: () => void;
}) {
  const [editData, setEditData] = useState({ title: note.title, content: note.content });

  if (isEditing) {
    return (
      <motion.div
        layout
        className="glass-panel rounded-lg p-4"
      >
        <input
          type="text"
          value={editData.title}
          onChange={(e) => setEditData({ ...editData, title: e.target.value })}
          className="w-full mb-3 px-3 py-2 bg-white/5 border border-white/10 rounded text-jarvis-text focus:outline-none focus:border-jarvis-accentPink font-medium"
        />
        <textarea
          value={editData.content}
          onChange={(e) => setEditData({ ...editData, content: e.target.value })}
          rows={4}
          className="w-full mb-3 px-3 py-2 bg-white/5 border border-white/10 rounded text-jarvis-text focus:outline-none focus:border-jarvis-accentPink resize-none"
        />
        <div className="flex justify-end gap-2">
          <button
            onClick={onCancel}
            className="p-1.5 rounded hover:bg-white/10 text-jarvis-textMuted"
          >
            <X size={16} />
          </button>
          <button
            onClick={() => onSave(editData)}
            className="p-1.5 rounded bg-jarvis-accentPink text-white hover:bg-jarvis-accentPink/80"
          >
            <Save size={16} />
          </button>
        </div>
      </motion.div>
    );
  }

  return (
    <motion.div
      layout
      className="glass-panel rounded-lg p-4 group hover:border-jarvis-accentPink/30 transition-all"
    >
      <div className="flex items-start justify-between mb-2">
        <h3 className="font-medium text-jarvis-text">{note.title}</h3>
        <div className="flex gap-1 opacity-0 group-hover:opacity-100 transition-opacity">
          <button
            onClick={onEdit}
            className="p-1.5 rounded hover:bg-white/10 text-jarvis-textMuted"
          >
            <Edit3 size={14} />
          </button>
          <button
            onClick={onDelete}
            className="p-1.5 rounded hover:bg-red-500/20 text-red-400"
          >
            <Trash2 size={14} />
          </button>
        </div>
      </div>
      <p className="text-sm text-jarvis-textMuted line-clamp-4">{note.content}</p>
      <div className="mt-3 flex items-center gap-2 text-xs text-jarvis-textMuted">
        <Clock size={12} />
        {new Date(note.updatedAt).toLocaleDateString()}
      </div>
    </motion.div>
  );
}

// Reminders View
function RemindersView({ reminders, searchQuery }: { reminders: Reminder[]; searchQuery: string }) {
  const { addReminder, deleteReminder } = useStore();
  const [newReminder, setNewReminder] = useState({ text: '', time: '' });
  const [isAdding, setIsAdding] = useState(false);

  const filteredReminders = reminders.filter(r => 
    r.text.toLowerCase().includes(searchQuery.toLowerCase())
  );

  const handleAddReminder = () => {
    if (newReminder.text.trim() && newReminder.time) {
      addReminder({ 
        text: newReminder.text.trim(), 
        time: new Date(newReminder.time).getTime(),
        completed: false 
      });
      setNewReminder({ text: '', time: '' });
      setIsAdding(false);
    }
  };

  return (
    <motion.div
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      exit={{ opacity: 0, y: -20 }}
      className="space-y-4"
    >
      {/* Add Reminder */}
      {!isAdding ? (
        <button
          onClick={() => setIsAdding(true)}
          className="w-full p-4 rounded-lg border-2 border-dashed border-white/20 hover:border-jarvis-accentPink/50 hover:bg-white/5 transition-all flex items-center justify-center gap-2 text-jarvis-textMuted"
        >
          <Plus size={20} />
          Set New Reminder
        </button>
      ) : (
        <motion.div
          initial={{ opacity: 0, scale: 0.95 }}
          animate={{ opacity: 1, scale: 1 }}
          className="glass-panel rounded-lg p-4"
        >
          <input
            type="text"
            value={newReminder.text}
            onChange={(e) => setNewReminder({ ...newReminder, text: e.target.value })}
            placeholder="What should I remind you about?"
            className="w-full mb-3 px-3 py-2 bg-white/5 border border-white/10 rounded text-jarvis-text placeholder-jarvis-textMuted focus:outline-none focus:border-jarvis-accentPink"
          />
          <input
            type="datetime-local"
            value={newReminder.time}
            onChange={(e) => setNewReminder({ ...newReminder, time: e.target.value })}
            className="w-full mb-3 px-3 py-2 bg-white/5 border border-white/10 rounded text-jarvis-text focus:outline-none focus:border-jarvis-accentPink"
          />
          <div className="flex justify-end gap-2">
            <button
              onClick={() => setIsAdding(false)}
              className="px-3 py-1.5 rounded text-sm text-jarvis-textMuted hover:text-jarvis-text"
            >
              Cancel
            </button>
            <button
              onClick={handleAddReminder}
              className="px-3 py-1.5 rounded text-sm bg-jarvis-accentPink text-white hover:bg-jarvis-accentPink/80 flex items-center gap-1"
            >
              <Bell size={14} />
              Set Reminder
            </button>
          </div>
        </motion.div>
      )}

      {/* Reminders List */}
      <div className="space-y-2">
        {filteredReminders.length === 0 ? (
          <div className="text-center py-8 text-jarvis-textMuted">
            No reminders set. Create one above!
          </div>
        ) : (
          filteredReminders.map((reminder) => (
            <motion.div
              key={reminder.id}
              layout
              className="flex items-center gap-3 p-4 rounded-lg glass-panel"
            >
              <div className="p-2 rounded-lg bg-jarvis-accentPink/20">
                <Bell size={18} className="text-jarvis-accentPink" />
              </div>
              <div className="flex-1">
                <p className="text-jarvis-text">{reminder.text}</p>
                <p className="text-xs text-jarvis-textMuted flex items-center gap-1">
                  <Calendar size={12} />
                  {new Date(reminder.time).toLocaleString()}
                </p>
              </div>
              <button
                onClick={() => deleteReminder(reminder.id)}
                className="p-1.5 rounded hover:bg-red-500/20 text-red-400 transition-colors"
              >
                <Trash2 size={16} />
              </button>
            </motion.div>
          ))
        )}
      </div>
    </motion.div>
  );
}
