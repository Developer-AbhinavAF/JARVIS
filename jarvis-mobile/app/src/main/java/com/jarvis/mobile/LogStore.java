package com.jarvis.mobile;

import android.content.Context;
import android.content.SharedPreferences;

import org.json.JSONArray;
import org.json.JSONException;
import org.json.JSONObject;

import java.text.SimpleDateFormat;
import java.util.Date;
import java.util.Locale;

final class LogStore {
    private static final int MAX_LOGS = 200;
    private final SharedPreferences prefs;
    private final SimpleDateFormat clock = new SimpleDateFormat("HH:mm:ss", Locale.US);

    LogStore(Context context) {
        prefs = context.getSharedPreferences("jarvis_logs", Context.MODE_PRIVATE);
    }

    synchronized void add(String level, String message) {
        JSONArray logs = getArray();
        JSONObject item = new JSONObject();
        try {
            item.put("time", clock.format(new Date()));
            item.put("level", level);
            item.put("message", message);
            logs.put(item);
            while (logs.length() > MAX_LOGS) {
                logs.remove(0);
            }
            prefs.edit().putString("items", logs.toString()).apply();
        } catch (JSONException ignored) {
        }
    }

    synchronized JSONArray all() {
        return getArray();
    }

    synchronized void clear() {
        prefs.edit().remove("items").apply();
    }

    private JSONArray getArray() {
        String raw = prefs.getString("items", "[]");
        try {
            return new JSONArray(raw);
        } catch (JSONException e) {
            return new JSONArray();
        }
    }
}
