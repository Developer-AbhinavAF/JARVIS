package com.jarvis.mobile;

import android.content.Context;
import android.content.SharedPreferences;

import java.util.LinkedHashMap;
import java.util.Map;

final class ApiKeys {
    static final String[] NAMES = {
            "GROQ_API_KEY",
            "GROQ_API_KEY2",
            "GROQ_API_KEY3",
            "GROQ_API_KEY4",
            "TAVILY_API_KEY",
            "OPENROUTER_API_KEY",
            "GEMINI_API_KEY",
            "OPENWEATHER_API_KEY",
            "NEWSAPI_KEY",
            "ALPHA_VANTAGE_KEY",
            "YOUTUBE_API_KEY",
            "ELEVENLABS_API_KEY",
            "SERPAPI_KEY",
            "RESEND_API_KEY",
            "TMDB_API_KEY",
            "NASA_API_KEY",
            "FINNHUB_API_KEY",
            "API_NINJAS_KEY",
            "CALENDARIFIC_API_KEY"
    };

    private final SharedPreferences prefs;

    ApiKeys(Context context) {
        prefs = context.getSharedPreferences("jarvis_api_keys", Context.MODE_PRIVATE);
    }

    String get(String name) {
        String override = prefs.getString(name, "");
        if (override != null && !override.trim().isEmpty()) {
            return override.trim();
        }
        return buildConfigValue(name);
    }

    boolean has(String name) {
        return !get(name).isEmpty();
    }

    void save(String name, String value) {
        prefs.edit().putString(name, value == null ? "" : value.trim()).apply();
    }

    void importEnvText(String text) {
        SharedPreferences.Editor editor = prefs.edit();
        String[] lines = text == null ? new String[0] : text.split("\\r?\\n");
        for (String raw : lines) {
            String line = raw.trim();
            if (line.isEmpty() || line.startsWith("#") || !line.contains("=")) {
                continue;
            }
            int idx = line.indexOf('=');
            String key = line.substring(0, idx).trim();
            String value = line.substring(idx + 1).trim();
            if ((value.startsWith("\"") && value.endsWith("\""))
                    || (value.startsWith("'") && value.endsWith("'"))) {
                value = value.substring(1, value.length() - 1);
            }
            for (String known : NAMES) {
                if (known.equals(key)) {
                    editor.putString(key, value);
                    break;
                }
            }
        }
        editor.apply();
    }

    Map<String, String> snapshotMasked() {
        Map<String, String> map = new LinkedHashMap<>();
        for (String name : NAMES) {
            String value = get(name);
            map.put(name, mask(value));
        }
        return map;
    }

    private String mask(String value) {
        if (value == null || value.isEmpty()) {
            return "not set";
        }
        if (value.length() <= 8) {
            return "set";
        }
        return value.substring(0, 4) + "..." + value.substring(value.length() - 4);
    }

    private String buildConfigValue(String name) {
        switch (name) {
            case "GROQ_API_KEY":
                return BuildConfig.GROQ_API_KEY;
            case "GROQ_API_KEY2":
                return BuildConfig.GROQ_API_KEY2;
            case "GROQ_API_KEY3":
                return BuildConfig.GROQ_API_KEY3;
            case "GROQ_API_KEY4":
                return BuildConfig.GROQ_API_KEY4;
            case "TAVILY_API_KEY":
                return BuildConfig.TAVILY_API_KEY;
            case "OPENROUTER_API_KEY":
                return BuildConfig.OPENROUTER_API_KEY;
            case "GEMINI_API_KEY":
                return BuildConfig.GEMINI_API_KEY;
            case "OPENWEATHER_API_KEY":
                return BuildConfig.OPENWEATHER_API_KEY;
            case "NEWSAPI_KEY":
                return BuildConfig.NEWSAPI_KEY;
            case "ALPHA_VANTAGE_KEY":
                return BuildConfig.ALPHA_VANTAGE_KEY;
            case "YOUTUBE_API_KEY":
                return BuildConfig.YOUTUBE_API_KEY;
            case "ELEVENLABS_API_KEY":
                return BuildConfig.ELEVENLABS_API_KEY;
            case "SERPAPI_KEY":
                return BuildConfig.SERPAPI_KEY;
            case "RESEND_API_KEY":
                return BuildConfig.RESEND_API_KEY;
            case "TMDB_API_KEY":
                return BuildConfig.TMDB_API_KEY;
            case "NASA_API_KEY":
                return BuildConfig.NASA_API_KEY;
            case "FINNHUB_API_KEY":
                return BuildConfig.FINNHUB_API_KEY;
            case "API_NINJAS_KEY":
                return BuildConfig.API_NINJAS_KEY;
            case "CALENDARIFIC_API_KEY":
                return BuildConfig.CALENDARIFIC_API_KEY;
            default:
                return "";
        }
    }
}
