package com.jarvis.mobile;

import org.json.JSONArray;
import org.json.JSONException;
import org.json.JSONObject;

import java.util.regex.Matcher;
import java.util.regex.Pattern;

final class JsonUtils {
    private static final Pattern URL = Pattern.compile("https?://\\S+");

    private JsonUtils() {
    }

    static String pretty(String raw) {
        if (raw == null) {
            return "";
        }
        String trimmed = raw.trim();
        try {
            if (trimmed.startsWith("{")) {
                return new JSONObject(trimmed).toString(2);
            }
            if (trimmed.startsWith("[")) {
                return new JSONArray(trimmed).toString(2);
            }
        } catch (JSONException ignored) {
        }
        return raw;
    }

    static String firstUrl(String text) {
        if (text == null) {
            return null;
        }
        Matcher matcher = URL.matcher(text);
        return matcher.find() ? matcher.group() : null;
    }

    static String optString(JSONObject obj, String key) {
        String value = obj.optString(key, "");
        return "null".equalsIgnoreCase(value) ? "" : value;
    }
}
