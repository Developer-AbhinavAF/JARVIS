package com.jarvis.mobile;

import android.content.Context;
import android.content.SharedPreferences;

import org.json.JSONArray;
import org.json.JSONException;
import org.json.JSONObject;

import java.util.HashMap;
import java.util.Map;
import java.util.UUID;

final class LocalMemory {
    private final SharedPreferences prefs;

    LocalMemory(Context context) {
        prefs = context.getSharedPreferences("jarvis_memory", Context.MODE_PRIVATE);
    }

    JSONArray notes() { return array("notes"); }
    JSONArray todos() { return array("todos"); }
    JSONArray reminders() { return array("reminders"); }
    JSONArray chat() { return array("chat"); }

    // ─── SMART MEMORY: User Preferences & Learning ───

    void addPreference(String key, String value) {
        try {
            JSONObject prefs_ = new JSONObject(prefs.getString("preferences", "{}"));
            prefs_.put(key, value);
            prefs_.put(key + "_updated", System.currentTimeMillis());
            prefs.edit().putString("preferences", prefs_.toString()).apply();
        } catch (JSONException ignored) {}
    }

    String getPreference(String key, String fallback) {
        try {
            JSONObject prefs_ = new JSONObject(prefs.getString("preferences", "{}"));
            return prefs_.optString(key, fallback);
        } catch (JSONException e) { return fallback; }
    }

    JSONObject getAllPreferences() {
        try { return new JSONObject(prefs.getString("preferences", "{}")); }
        catch (JSONException e) { return new JSONObject(); }
    }

    // Learn user's name
    void learnName(String name) {
        addPreference("user_name", name);
    }

    String getUserName() {
        return getPreference("user_name", null);
    }

    // Track frequently used commands/topics
    void trackTopic(String topic) {
        try {
            JSONObject counts = new JSONObject(prefs.getString("topic_counts", "{}"));
            int current = counts.optInt(topic, 0);
            counts.put(topic, current + 1);
            counts.put("last_" + topic, System.currentTimeMillis());
            prefs.edit().putString("topic_counts", counts.toString()).apply();
        } catch (JSONException ignored) {}
    }

    String[] getTopTopics(int limit) {
        try {
            JSONObject counts = new JSONObject(prefs.getString("topic_counts", "{}"));
            java.util.ArrayList<String> keys = new java.util.ArrayList<>();
            java.util.Iterator<String> it = counts.keys();
            while (it.hasNext()) keys.add(it.next());
            java.util.ArrayList<String> topics = new java.util.ArrayList<>();
            for (String k : keys) {
                if (!k.startsWith("last_") && counts.optInt(k, 0) > 1) topics.add(k);
            }
            int sz = Math.min(limit, topics.size());
            return topics.subList(0, sz).toArray(new String[sz]);
        } catch (JSONException e) { return new String[0]; }
    }

    // Track quiz score
    void addQuizScore(int correct, int total, String topic) {
        try {
            JSONObject scores = new JSONObject(prefs.getString("quiz_scores", "{}"));
            JSONObject entry = new JSONObject();
            entry.put("correct", correct);
            entry.put("total", total);
            entry.put("topic", topic);
            entry.put("timestamp", System.currentTimeMillis());
            JSONArray history = scores.optJSONArray("history");
            if (history == null) history = new JSONArray();
            history.put(entry);
            scores.put("history", history);
            scores.put("last_score_pct", total > 0 ? (correct * 100 / total) : 0);
            scores.put("total_correct", scores.optInt("total_correct", 0) + correct);
            scores.put("total_questions", scores.optInt("total_questions", 0) + total);
            prefs.edit().putString("quiz_scores", scores.toString()).apply();
        } catch (JSONException ignored) {}
    }

    String getQuizSummary() {
        try {
            JSONObject scores = new JSONObject(prefs.getString("quiz_scores", "{}"));
            int totalQ = scores.optInt("total_questions", 0);
            int totalC = scores.optInt("total_correct", 0);
            if (totalQ == 0) return "No quizzes attempted yet.";
            return "📊 Quiz Stats: " + totalC + "/" + totalQ + " correct (" + (totalC * 100 / totalQ) + "%)";
        } catch (JSONException e) { return "No quiz data."; }
    }

    // ─── PERSISTENT CHAT CONTEXT ───

    String getChatContextSummary() {
        JSONArray ch = chat();
        if (ch.length() == 0) return "No previous conversation.";
        StringBuilder ctx = new StringBuilder("📝 Recent conversation context:\n");
        int start = Math.max(0, ch.length() - 6);
        for (int i = start; i < ch.length(); i++) {
            JSONObject msg = ch.optJSONObject(i);
            if (msg != null) {
                String role = msg.optString("role");
                String content = msg.optString("content", "");
                if (content.length() > 60) content = content.substring(0, 60) + "...";
                ctx.append(role.equals("user") ? "👤 You: " : "🤖 AI: ").append(content).append("\n");
            }
        }
        return ctx.toString();
    }

    // ─── BASIC CRUD ───

    void addNote(String title, String body) {
        JSONObject note = baseObject();
        try {
            note.put("title", title); note.put("body", body);
            append("notes", note);
        } catch (JSONException ignored) {}
    }

    void addTodo(String task) {
        JSONObject todo = baseObject();
        try { todo.put("task", task); todo.put("done", false); append("todos", todo); }
        catch (JSONException ignored) {}
    }

    void toggleTodo(int index) {
        JSONArray todos = todos();
        if (index < 0 || index >= todos.length()) return;
        try {
            JSONObject todo = todos.getJSONObject(index);
            todo.put("done", !todo.optBoolean("done", false));
            save("todos", todos);
        } catch (JSONException ignored) {}
    }

    void addReminder(String text, long triggerAtMillis) {
        JSONObject reminder = baseObject();
        try { reminder.put("text", text); reminder.put("triggerAt", triggerAtMillis); append("reminders", reminder); }
        catch (JSONException ignored) {}
    }

    void addChat(String role, String content) {
        JSONObject message = baseObject();
        try { message.put("role", role); message.put("content", content); append("chat", message); }
        catch (JSONException ignored) {}
    }

    void clearChat() { save("chat", new JSONArray()); }

    private JSONObject baseObject() {
        JSONObject obj = new JSONObject();
        try { obj.put("id", UUID.randomUUID().toString()); obj.put("createdAt", System.currentTimeMillis()); }
        catch (JSONException ignored) {}
        return obj;
    }

    private void append(String key, JSONObject obj) {
        JSONArray arr = array(key); arr.put(obj); save(key, arr);
    }

    JSONArray array(String key) {
        try { return new JSONArray(prefs.getString(key, "[]")); }
        catch (JSONException e) { return new JSONArray(); }
    }

    private void save(String key, JSONArray array) {
        prefs.edit().putString(key, array.toString()).apply();
    }
}
