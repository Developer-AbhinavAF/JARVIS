package com.jarvis.mobile;

import android.content.Context;
import android.content.SharedPreferences;

import org.json.JSONArray;
import org.json.JSONException;
import org.json.JSONObject;

import java.util.UUID;

final class LocalMemory {
    private final SharedPreferences prefs;

    LocalMemory(Context context) {
        prefs = context.getSharedPreferences("jarvis_memory", Context.MODE_PRIVATE);
    }

    JSONArray notes() {
        return array("notes");
    }

    JSONArray todos() {
        return array("todos");
    }

    JSONArray reminders() {
        return array("reminders");
    }

    JSONArray chat() {
        return array("chat");
    }

    void addNote(String title, String body) {
        JSONObject note = baseObject();
        try {
            note.put("title", title);
            note.put("body", body);
            append("notes", note);
        } catch (JSONException ignored) {
        }
    }

    void addTodo(String task) {
        JSONObject todo = baseObject();
        try {
            todo.put("task", task);
            todo.put("done", false);
            append("todos", todo);
        } catch (JSONException ignored) {
        }
    }

    void toggleTodo(int index) {
        JSONArray todos = todos();
        if (index < 0 || index >= todos.length()) {
            return;
        }
        try {
            JSONObject todo = todos.getJSONObject(index);
            todo.put("done", !todo.optBoolean("done", false));
            save("todos", todos);
        } catch (JSONException ignored) {
        }
    }

    void addReminder(String text, long triggerAtMillis) {
        JSONObject reminder = baseObject();
        try {
            reminder.put("text", text);
            reminder.put("triggerAt", triggerAtMillis);
            append("reminders", reminder);
        } catch (JSONException ignored) {
        }
    }

    void addChat(String role, String content) {
        JSONObject message = baseObject();
        try {
            message.put("role", role);
            message.put("content", content);
            append("chat", message);
        } catch (JSONException ignored) {
        }
    }

    void clearChat() {
        save("chat", new JSONArray());
    }

    private JSONObject baseObject() {
        JSONObject obj = new JSONObject();
        try {
            obj.put("id", UUID.randomUUID().toString());
            obj.put("createdAt", System.currentTimeMillis());
        } catch (JSONException ignored) {
        }
        return obj;
    }

    private void append(String key, JSONObject obj) {
        JSONArray arr = array(key);
        arr.put(obj);
        save(key, arr);
    }

    private JSONArray array(String key) {
        try {
            return new JSONArray(prefs.getString(key, "[]"));
        } catch (JSONException e) {
            return new JSONArray();
        }
    }

    private void save(String key, JSONArray array) {
        prefs.edit().putString(key, array.toString()).apply();
    }
}
