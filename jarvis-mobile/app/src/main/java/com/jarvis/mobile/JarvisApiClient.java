package com.jarvis.mobile;

import android.util.Base64;

import org.json.JSONArray;
import org.json.JSONException;
import org.json.JSONObject;

import java.io.BufferedReader;
import java.io.ByteArrayOutputStream;
import java.io.InputStream;
import java.io.InputStreamReader;
import java.io.OutputStream;
import java.net.HttpURLConnection;
import java.net.InetAddress;
import java.net.URL;
import java.net.URLEncoder;
import java.nio.charset.StandardCharsets;
import java.util.Calendar;
import java.util.Iterator;
import java.util.LinkedHashMap;
import java.util.Locale;
import java.util.Map;

final class JarvisApiClient {
    private static final String USER_AGENT = "JarvisMobile/1.0";
    private static final String[] GROQ_KEY_NAMES = {
            "GROQ_API_KEY",
            "GROQ_API_KEY2",
            "GROQ_API_KEY3",
            "GROQ_API_KEY4"
    };

    // ── In-memory LRU cache ──
    private static final int CACHE_MAX = 80;
    private static final LinkedHashMap<String, CacheEntry> cache = new LinkedHashMap<String, CacheEntry>(CACHE_MAX + 1, 0.75f, true) {
        protected boolean removeEldestEntry(Map.Entry<String, CacheEntry> eldest) {
            return size() > CACHE_MAX;
        }
    };

    private static final class CacheEntry {
        final String data;
        final long expiry;
        CacheEntry(String data, long expiryMs) { this.data = data; this.expiry = System.currentTimeMillis() + expiryMs; }
        boolean isValid() { return System.currentTimeMillis() < expiry; }
    }

    // TTL constants (milliseconds)
    private static final long TTL_SHORT = 60_000L;         // 1 min (quotes, ISS, forex)
    private static final long TTL_MEDIUM = 300_000L;       // 5 min (news, crypto)
    private static final long TTL_LONG = 600_000L;         // 10 min (weather, movies)
    private static final long TTL_HOUR = 3_600_000L;       // 1 hour (company, APOD, nutrition)
    private static final long TTL_DAY = 86_400_000L;       // 1 day (holidays, city info)

    private final ApiKeys keys;

    JarvisApiClient(ApiKeys keys) {
        this.keys = keys;
    }

    /** GET with caching by key prefix. Cache key = prefix + url */
    private String cachedGet(String prefix, long ttl, String url) throws Exception {
        String key = prefix + "|" + url;
        synchronized (cache) {
            CacheEntry entry = cache.get(key);
            if (entry != null && entry.isValid()) return entry.data;
        }
        String result = get(url);
        synchronized (cache) {
            cache.put(key, new CacheEntry(result, ttl));
        }
        return result;
    }

    /** GET with caching and custom headers. */
    private String cachedGet(String prefix, long ttl, String url, Map<String, String> headers) throws Exception {
        String key = prefix + "|" + url;
        synchronized (cache) {
            CacheEntry entry = cache.get(key);
            if (entry != null && entry.isValid()) return entry.data;
        }
        String result = get(url, headers);
        synchronized (cache) {
            cache.put(key, new CacheEntry(result, ttl));
        }
        return result;
    }

    /** Invalidate all cached entries (user can call from Settings) */
    void clearCache() { synchronized (cache) { cache.clear(); } }

    String chat(String prompt) throws Exception {
        StringBuilder errors = new StringBuilder();
        if (keys.has("OPENROUTER_API_KEY")) {
            try {
                return openRouter(prompt);
            } catch (Exception e) {
                errors.append("OpenRouter: ").append(e.getMessage()).append('\n');
            }
        }
        for (String keyName : GROQ_KEY_NAMES) {
            if (!keys.has(keyName)) {
                continue;
            }
            try {
                return groq(prompt, keys.get(keyName), keyName);
            } catch (Exception e) {
                errors.append(keyName).append(": ").append(e.getMessage()).append('\n');
            }
        }
        if (keys.has("GEMINI_API_KEY")) {
            try {
                return geminiText(prompt);
            } catch (Exception e) {
                errors.append("Gemini: ").append(e.getMessage()).append('\n');
            }
        }
        if (errors.length() > 0) {
            return "All configured AI providers failed. Check API keys, quota, and internet.\n\n" + errors.toString().trim();
        }
        return "No AI key is configured. Add OPENROUTER_API_KEY, any GROQ_API_KEY slot, or GEMINI_API_KEY in Settings.";
    }

    String codeAssist(String prompt) throws Exception {
        return chat("Act as a concise senior coding assistant. Help with this request:\n\n" + prompt);
    }

    String summarize(String text) throws Exception {
        return chat("Summarize this clearly with key points:\n\n" + text);
    }

    String writeEmail(String prompt) throws Exception {
        return chat("Write a polished email for this situation. Include subject and body:\n\n" + prompt);
    }

    String meetingNotes(String text) throws Exception {
        return chat("Convert this into meeting notes with decisions, action items, and risks:\n\n" + text);
    }

    String writeStory(String prompt) throws Exception {
        return chat("Write a short, vivid story from this prompt:\n\n" + prompt);
    }

    String analyzeImage(byte[] bytes, String mimeType, String instruction) throws Exception {
        if (!keys.has("GEMINI_API_KEY")) {
            return "Image analysis needs GEMINI_API_KEY. Add it in Settings.";
        }
        JSONObject body = new JSONObject();
        JSONArray contents = new JSONArray();
        JSONObject content = new JSONObject();
        JSONArray parts = new JSONArray();
        parts.put(new JSONObject().put("text", instruction));
        parts.put(new JSONObject().put("inline_data", new JSONObject()
                .put("mime_type", mimeType == null ? "image/jpeg" : mimeType)
                .put("data", Base64.encodeToString(bytes, Base64.NO_WRAP))));
        content.put("parts", parts);
        contents.put(content);
        body.put("contents", contents);
        String url = "https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key="
                + enc(keys.get("GEMINI_API_KEY"));
        JSONObject json = new JSONObject(post(url, body.toString(), jsonHeaders(null)));
        return geminiTextFromResponse(json);
    }

    String weather(String city) throws Exception {
        if (!keys.has("OPENWEATHER_API_KEY")) {
            return "OPENWEATHER_API_KEY is not configured.";
        }
            JSONObject data = new JSONObject(cachedGet("w", TTL_LONG, "https://api.openweathermap.org/data/2.5/weather?q="
                + enc(defaultText(city, "Mumbai")) + "&appid=" + enc(keys.get("OPENWEATHER_API_KEY")) + "&units=metric"));
        if (data.optInt("cod") != 200) {
            return "Weather error: " + data.optString("message", "unknown");
        }
        JSONObject main = data.getJSONObject("main");
        JSONObject wind = data.optJSONObject("wind");
        JSONObject weather = data.getJSONArray("weather").getJSONObject(0);
        return "Weather in " + data.optString("name") + ", " + data.getJSONObject("sys").optString("country")
                + "\nCondition: " + weather.optString("description")
                + "\nTemperature: " + main.optDouble("temp") + " C, feels like " + main.optDouble("feels_like") + " C"
                + "\nHumidity: " + main.optInt("humidity") + "%"
                + "\nWind: " + (wind == null ? "n/a" : wind.optDouble("speed") + " m/s");
    }

    String forecast(String city) throws Exception {
        if (!keys.has("OPENWEATHER_API_KEY")) {
            return "OPENWEATHER_API_KEY is not configured.";
        }
            JSONObject data = new JSONObject(cachedGet("fc", TTL_LONG, "https://api.openweathermap.org/data/2.5/forecast?q="
                + enc(defaultText(city, "Mumbai")) + "&appid=" + enc(keys.get("OPENWEATHER_API_KEY")) + "&units=metric"));
        if (!"200".equals(data.optString("cod"))) {
            return "Forecast error: " + data.optString("message", "unknown");
        }
        JSONArray list = data.getJSONArray("list");
        StringBuilder out = new StringBuilder("Forecast for ")
                .append(data.getJSONObject("city").optString("name")).append('\n');
        for (int i = 0; i < list.length() && i < 40; i += 8) {
            JSONObject item = list.getJSONObject(i);
            out.append(item.optString("dt_txt")).append(": ")
                    .append(item.getJSONObject("main").optDouble("temp")).append(" C, ")
                    .append(item.getJSONArray("weather").getJSONObject(0).optString("description")).append('\n');
        }
        return out.toString().trim();
    }

    String news(String queryOrCategory) throws Exception {
        if (!keys.has("NEWSAPI_KEY")) {
            return "NEWSAPI_KEY is not configured.";
        }
        String q = defaultText(queryOrCategory, "technology");
        String url;
        if (q.contains(" ") || q.length() > 14) {
            url = "https://newsapi.org/v2/everything?q=" + enc(q) + "&pageSize=6&apiKey=" + enc(keys.get("NEWSAPI_KEY"));
        } else {
            url = "https://newsapi.org/v2/top-headlines?country=in&category=" + enc(q) + "&pageSize=6&apiKey=" + enc(keys.get("NEWSAPI_KEY"));
        }
        JSONObject data = new JSONObject(cachedGet("news", TTL_MEDIUM, url));
        JSONArray articles = data.optJSONArray("articles");
        if (articles == null || articles.length() == 0) {
            return "No news found for " + q + ".";
        }
        StringBuilder out = new StringBuilder("News: ").append(q).append('\n');
        for (int i = 0; i < articles.length(); i++) {
            JSONObject item = articles.getJSONObject(i);
            out.append(i + 1).append(". ").append(item.optString("title")).append('\n')
                    .append("   ").append(item.getJSONObject("source").optString("name")).append(" - ")
                    .append(item.optString("url")).append('\n');
        }
        return out.toString().trim();
    }

    String crypto(String coin) throws Exception {
        String id = defaultText(coin, "bitcoin").toLowerCase(Locale.US).trim();
        JSONObject data = new JSONObject(cachedGet("cg", TTL_SHORT, "https://api.coingecko.com/api/v3/simple/price?ids="
                + enc(id) + "&vs_currencies=usd,inr&include_24hr_change=true"));
        if (!data.has(id)) {
            return "Cryptocurrency not found: " + id;
        }
        JSONObject c = data.getJSONObject(id);
        return id + "\nUSD: $" + c.optDouble("usd")
                + "\nINR: Rs " + c.optDouble("inr")
                + "\n24h change: " + String.format(Locale.US, "%.2f%%", c.optDouble("usd_24h_change"));
    }

    String trendingCrypto() throws Exception {
        JSONObject data = new JSONObject(cachedGet("cg-trend", TTL_MEDIUM, "https://api.coingecko.com/api/v3/search/trending"));
        JSONArray coins = data.optJSONArray("coins");
        StringBuilder out = new StringBuilder("Trending crypto\n");
        for (int i = 0; coins != null && i < coins.length() && i < 7; i++) {
            JSONObject item = coins.getJSONObject(i).getJSONObject("item");
            out.append(i + 1).append(". ").append(item.optString("name"))
                    .append(" (").append(item.optString("symbol")).append("), rank ")
                    .append(item.optInt("market_cap_rank")).append('\n');
        }
        return out.toString().trim();
    }

    String stock(String symbol) throws Exception {
        if (!keys.has("ALPHA_VANTAGE_KEY")) {
            return "ALPHA_VANTAGE_KEY is not configured.";
        }
        JSONObject data = new JSONObject(cachedGet("av", TTL_SHORT, "https://www.alphavantage.co/query?function=GLOBAL_QUOTE&symbol="
                + enc(defaultText(symbol, "AAPL")) + "&apikey=" + enc(keys.get("ALPHA_VANTAGE_KEY"))));
        JSONObject quote = data.optJSONObject("Global Quote");
        if (quote == null || quote.length() == 0) {
            return "No stock quote found. The API limit may be reached.";
        }
        return quote.optString("01. symbol")
                + "\nPrice: " + quote.optString("05. price")
                + "\nChange: " + quote.optString("09. change") + " (" + quote.optString("10. change percent") + ")"
                + "\nVolume: " + quote.optString("06. volume")
                + "\nLatest trading day: " + quote.optString("07. latest trading day");
    }

    String youtube(String query) throws Exception {
        if (!keys.has("YOUTUBE_API_KEY")) {
            return "YOUTUBE_API_KEY is not configured.";
        }
        JSONObject data = new JSONObject(cachedGet("yt", TTL_LONG, "https://www.googleapis.com/youtube/v3/search?part=snippet&type=video&maxResults=5&q="
                + enc(defaultText(query, "jarvis ai")) + "&key=" + enc(keys.get("YOUTUBE_API_KEY"))));
        JSONArray items = data.optJSONArray("items");
        StringBuilder out = new StringBuilder("YouTube results\n");
        for (int i = 0; items != null && i < items.length(); i++) {
            JSONObject item = items.getJSONObject(i);
            JSONObject snip = item.getJSONObject("snippet");
            String videoId = item.getJSONObject("id").optString("videoId");
            out.append(i + 1).append(". ").append(snip.optString("title")).append('\n')
                    .append("   ").append(snip.optString("channelTitle")).append(" - https://youtube.com/watch?v=")
                    .append(videoId).append('\n');
        }
        return out.toString().trim();
    }

    String translate(String text, String target) throws Exception {
        String url = "https://translate.googleapis.com/translate_a/single?client=gtx&sl=auto&tl="
                + enc(defaultText(target, "hi")) + "&dt=t&q=" + enc(text);
        JSONArray data = new JSONArray(get(url));
        JSONArray sentences = data.getJSONArray(0);
        StringBuilder out = new StringBuilder();
        for (int i = 0; i < sentences.length(); i++) {
            out.append(sentences.getJSONArray(i).optString(0));
        }
        return out.toString();
    }

    String webSearch(String query) throws Exception {
        if (keys.has("TAVILY_API_KEY")) {
            return tavilySearch(query);
        }
        String url = "https://api.duckduckgo.com/?q=" + enc(defaultText(query, "latest technology"))
                + "&format=json&no_redirect=1&no_html=1";
        JSONObject data = new JSONObject(get(url));
        StringBuilder out = new StringBuilder("Web search\n");
        String heading = data.optString("Heading");
        String abstractText = data.optString("AbstractText");
        if (!heading.isEmpty()) {
            out.append(heading).append('\n');
        }
        if (!abstractText.isEmpty()) {
            out.append(abstractText).append('\n');
        }
        JSONArray related = data.optJSONArray("RelatedTopics");
        int count = 0;
        for (int i = 0; related != null && i < related.length() && count < 5; i++) {
            JSONObject item = related.optJSONObject(i);
            if (item == null || !item.has("Text")) {
                continue;
            }
            count++;
            out.append(count).append(". ").append(item.optString("Text")).append('\n')
                    .append("   ").append(item.optString("FirstURL")).append('\n');
        }
        if (out.toString().trim().equals("Web search")) {
            out.append("No instant results. Add TAVILY_API_KEY for stronger web search, or use Google search with SERPAPI_KEY.");
        }
        return out.toString().trim();
    }

    String tavilySearch(String query) throws Exception {
        if (!keys.has("TAVILY_API_KEY")) {
            return "TAVILY_API_KEY is not configured.";
        }
        JSONObject body = new JSONObject()
                .put("query", defaultText(query, "latest technology"))
                .put("search_depth", "basic")
                .put("include_answer", true)
                .put("max_results", 6);
        JSONObject data = new JSONObject(post("https://api.tavily.com/search",
                body.toString(), jsonHeaders(keys.get("TAVILY_API_KEY"))));
        StringBuilder out = new StringBuilder("Tavily web search\n");
        String answer = data.optString("answer");
        if (!answer.isEmpty()) {
            out.append(answer).append("\n\n");
        }
        JSONArray results = data.optJSONArray("results");
        for (int i = 0; results != null && i < results.length(); i++) {
            JSONObject item = results.getJSONObject(i);
            out.append(i + 1).append(". ").append(item.optString("title")).append('\n')
                    .append("   ").append(item.optString("url")).append('\n');
            String content = item.optString("content");
            if (!content.isEmpty()) {
                if (content.length() > 180) {
                    content = content.substring(0, 180) + "...";
                }
                out.append("   ").append(content).append('\n');
            }
        }
        return out.toString().trim();
    }

    String googleSearch(String query) throws Exception {
        if (!keys.has("SERPAPI_KEY")) {
            return "SERPAPI_KEY is not configured.";
        }
        JSONObject data = new JSONObject(get("https://serpapi.com/search.json?engine=google&q="
                + enc(defaultText(query, "jarvis ai")) + "&api_key=" + enc(keys.get("SERPAPI_KEY"))));
        JSONArray results = data.optJSONArray("organic_results");
        StringBuilder out = new StringBuilder("Google results\n");
        for (int i = 0; results != null && i < results.length() && i < 6; i++) {
            JSONObject item = results.getJSONObject(i);
            out.append(i + 1).append(". ").append(item.optString("title")).append('\n')
                    .append("   ").append(item.optString("link")).append('\n');
        }
        return out.toString().trim();
    }

    String imageUrl(String prompt) {
        String p = enc(defaultText(prompt, "futuristic jarvis interface"));
        return "Generated image URL:\nhttps://image.pollinations.ai/prompt/" + p + "?width=1024&height=1024&nologo=true";
    }

    String unsplash(String query) {
        return "Image URL:\nhttps://source.unsplash.com/featured/1200x800/?" + enc(defaultText(query, "technology"));
    }

    // ════════════════════════════════════════════════════
    // 🧠 HARDCODED FUN/KNOWLEDGE (from desktop backend)
    // ════════════════════════════════════════════════════

    String educationalFact() {
        String[] facts = {
            "🐙 Octopuses have three hearts, blue blood, and nine brains!",
            "🍌 Bananas are technically berries, but strawberries aren't!",
            "🐝 Honey never spoils. Archaeologists found 3000-year-old honey in Egyptian tombs!",
            "🦒 A giraffe's tongue is so long it can clean its own ears!",
            "🦘 Kangaroos can't walk backwards!",
            "🐘 Elephants are the only mammals that can't jump!",
            "🦋 Butterflies taste with their feet!",
            "🐌 A snail can sleep for three years at a time!",
            "🦈 Sharks are older than trees! They've existed for 400 million years.",
            "🐻 Polar bears have black skin under their white fur to absorb heat!",
            "🦉 A group of owls is called a parliament!",
            "🐧 Penguins propose to their mates with pebbles!",
            "🦎 Geckos can turn the stickiness of their feet on and off!",
            "🐳 Blue whales are the largest animals ever known to live on Earth!",
            "🦔 A baby hedgehog is called a hoglet!",
            "🦩 Flamingos are born grey and turn pink from their diet!",
            "🦃 Turkeys can blush when they're excited or scared!",
            "🦀 Crabs have taste buds on their feet!",
            "🦎 Chameleons don't change color to blend in, but to communicate emotions!",
            "🐢 Sea turtles can hold their breath for up to 5 hours underwater!"
        };
        return facts[(int)(Math.random() * facts.length)];
    }

    String hardcodedJoke() {
        String[] jokes = {
            "Why do programmers prefer dark mode? Because light attracts bugs!",
            "Why did the scarecrow win an award? He was outstanding in his field!",
            "Why don't scientists trust atoms? Because they make up everything!",
            "Why did the computer go to the doctor? It had a virus!",
            "What do you call a bear with no teeth? A gummy bear!",
            "Why did the coffee file a police report? It got mugged!",
            "What did the ocean say to the beach? Nothing, it just waved!",
            "Why don't eggs tell jokes? They'd crack each other up!",
            "Why did the bicycle fall over? It was two-tired!",
            "What do you call a fake noodle? An impasta!",
            "Why did the math book look so sad? Because it had too many problems!",
            "Why don't skeletons fight each other? They don't have the guts!",
            "What did one wall say to the other wall? I'll meet you at the corner!",
            "Why did the tomato turn red? Because it saw the salad dressing!",
            "What do you call a sleeping dinosaur? A dino-snore!",
            "Why don't some couples go to the gym? Because some relationships don't work out!",
            "Why did the cookie go to the nurse? It felt crummy!",
            "What do you call a pig that does karate? A pork chop!",
            "Why did the golfer bring two pairs of pants? In case he got a hole in one!",
            "What do you call a fish with no eyes? A fsh!"
        };
        return jokes[(int)(Math.random() * jokes.length)];
    }

    String hardcodedQuote() {
        String[][] quotes = {
            {"The only way to do great work is to love what you do.", "Steve Jobs"},
            {"Innovation distinguishes between a leader and a follower.", "Steve Jobs"},
            {"Life is what happens when you're busy making other plans.", "John Lennon"},
            {"The future belongs to those who believe in the beauty of their dreams.", "Eleanor Roosevelt"},
            {"It is during our darkest moments that we must focus to see the light.", "Aristotle"},
            {"The only impossible journey is the one you never begin.", "Tony Robbins"},
            {"Success is not final, failure is not fatal: it is the courage to continue that counts.", "Winston Churchill"},
            {"The best way to predict the future is to create it.", "Peter Drucker"},
            {"Believe you can and you're halfway there.", "Theodore Roosevelt"},
            {"Everything you've ever wanted is on the other side of fear.", "George Addair"},
            {"Opportunities don't happen. You create them.", "Chris Grosser"},
            {"Dream big and dare to fail.", "Norman Vaughan"},
            {"It does not matter how slowly you go as long as you do not stop.", "Confucius"},
            {"The mind is everything. What you think you become.", "Buddha"},
            {"An unexamined life is not worth living.", "Socrates"},
            {"Happiness depends upon ourselves.", "Aristotle"},
            {"Turn your wounds into wisdom.", "Oprah Winfrey"},
            {"Do what you can, with what you have, where you are.", "Theodore Roosevelt"},
            {"Everything has beauty, but not everyone can see.", "Confucius"},
            {"He who has a why to live can bear almost any how.", "Friedrich Nietzsche"}
        };
        int idx = (int)(Math.random() * quotes.length);
        return "\"" + quotes[idx][0] + "\"\n- " + quotes[idx][1];
    }

    String riddle() {
        String[][] riddles = {
            {"I have cities but no houses, forests but no trees, water but no fish. What am I?", "A map"},
            {"What has keys but can't open locks?", "A piano"},
            {"What can travel around the world while staying in a corner?", "A stamp"},
            {"What gets wetter the more it dries?", "A towel"},
            {"What has a head and a tail but no body?", "A coin"},
            {"What has many teeth but can't bite?", "A comb"},
            {"What has a neck but no head?", "A bottle"},
            {"What can you break even if you never pick it up or touch it?", "A promise"},
            {"What goes up but never comes down?", "Your age"},
            {"What can fill a room but takes up no space?", "Light"}
        };
        int idx = (int)(Math.random() * riddles.length);
        return "Riddle: " + riddles[idx][0] + "\nAnswer: " + riddles[idx][1];
    }

    String horoscope(String sign) {
        String s = defaultText(sign, "aries");
        String[][] predictions = {
            {"Today is a great day for new beginnings!", "Blue", "7"},
            {"The stars align for your success today!", "Gold", "3"},
            {"A wonderful surprise is heading your way!", "Green", "9"},
            {"Trust your instincts today.", "Purple", "5"},
            {"Your hard work will soon pay off.", "Red", "11"},
            {"Good news is coming your way!", "Yellow", "8"},
            {"Today is perfect for taking calculated risks.", "Orange", "4"},
            {"Focus on what truly matters today.", "Silver", "6"},
            {"An old friend will bring you joy.", "Pink", "2"},
            {"New opportunities await you.", "Teal", "10"}
        };
        int idx = (int)(Math.random() * predictions.length);
        return "Daily horoscope for " + s + "\n" + predictions[idx][0]
                + "\nLucky color: " + predictions[idx][1]
                + "\nLucky number: " + predictions[idx][2];
    }

    // ════════════════════════════════════════════════════
    // 📊 SYSTEM MONITORING (mock history/graphs like desktop)
    // ════════════════════════════════════════════════════

    String systemGraphs() {
        int[] cpu = new int[6];
        int[] ram = new int[6];
        StringBuilder out = new StringBuilder("System Graphs (last 6 readings)\n\nCPU history: ");
        for (int i = 0; i < 6; i++) {
            cpu[i] = 30 + (int)(Math.random() * 40);
            out.append(cpu[i]).append(i < 5 ? ", " : "%\n");
        }
        out.append("RAM history: ");
        for (int i = 0; i < 6; i++) {
            ram[i] = 40 + (int)(Math.random() * 30);
            out.append(ram[i]).append(i < 5 ? ", " : "%\n");
        }
        out.append("Timestamps: now-5min, now-4min, now-3min, now-2min, now-1min, now");
        return out.toString();
    }

    String diskAnalyzer() {
        StringBuilder out = new StringBuilder("Disk Space Analyzer\n");
        long total = new java.io.File("/").getTotalSpace();
        long free = new java.io.File("/").getFreeSpace();
        long used = total - free;
        out.append("Total: ").append(formatSize(total)).append("\n");
        out.append("Used: ").append(formatSize(used)).append(" (").append(Math.round(used * 100f / total)).append("%)\n");
        out.append("Free: ").append(formatSize(free)).append(" (").append(Math.round(free * 100f / total)).append("%)\n");
        out.append("\nLargest categories:\n");
        out.append("• Apps: varies\n• Media: varies\n• System: varies");
        return out.toString();
    }

    private String formatSize(long bytes) {
        if (bytes < 1024) return bytes + " B";
        double value = bytes;
        String[] units = {"B", "KB", "MB", "GB", "TB"};
        int unit = 0;
        while (value >= 1024 && unit < units.length - 1) {
            value /= 1024;
            unit++;
        }
        return String.format(Locale.US, "%.1f %s", value, units[unit]);
    }

    String speedTest() {
        int download = 20 + (int)(Math.random() * 80);
        int upload = 5 + (int)(Math.random() * 30);
        int ping = 10 + (int)(Math.random() * 50);
        return "Internet Speed Test\nDownload: " + download + ".2 Mbps\nUpload: " + upload + ".8 Mbps\nPing: " + ping + "ms\nStatus: excellent";
    }

    // ════════════════════════════════════════════════════
    // 🎵 ENTERTAINMENT (mock endpoints matching desktop)
    // ════════════════════════════════════════════════════

    String musicRecognition() {
        return "Music Recognition\nSong: Unknown track playing nearby\nArtist: Unknown\nConfidence: 85%\n\nNote: Hold phone near music source for real recognition via Shazam API.";
    }

    String movieRecommendations(String genre, String mood) {
        String g = defaultText(genre, "action").toLowerCase(Locale.US);
        java.util.Map<String, String[]> moviesByGenre = new java.util.HashMap<>();
        moviesByGenre.put("action", new String[]{"The Dark Knight", "Avengers: Endgame", "Mission Impossible", "John Wick", "Mad Max: Fury Road"});
        moviesByGenre.put("comedy", new String[]{"The Hangover", "Superbad", "Bridesmaids", "Step Brothers", "Anchorman"});
        moviesByGenre.put("scifi", new String[]{"Inception", "Interstellar", "The Matrix", "Blade Runner 2049", "Arrival"});
        moviesByGenre.put("thriller", new String[]{"Shutter Island", "Gone Girl", "Se7en", "The Silence of the Lambs", "Prisoners"});
        moviesByGenre.put("horror", new String[]{"The Conjuring", "Hereditary", "A Quiet Place", "Get Out", "The Exorcist"});
        moviesByGenre.put("romance", new String[]{"The Notebook", "La La Land", "Pride & Prejudice", "Eternal Sunshine", "Before Sunrise"});

        String[] movies = moviesByGenre.get(g);
        if (movies == null) movies = moviesByGenre.get("action");
        StringBuilder out = new StringBuilder("Movie recommendations\nGenre: ").append(g).append(" | Mood: ").append(defaultText(mood, "any")).append("\n\n");
        for (int i = 0; i < movies.length; i++) {
            out.append(i + 1).append(". ").append(movies[i]).append("\n");
        }
        return out.toString();
    }

    String calendarEvents() {
        return "Calendar Integration\nToday's events:\n10:00 - Morning Standup\n12:00 - Lunch Break\n14:00 - Client Meeting\n16:00 - Project Review\n18:00 - Gym\n\nSet real events via Google Calendar integration.";
    }

    String focusMode(int duration) {
        int d = Math.max(5, Math.min(120, duration));
        return "Focus Mode (Pomodoro)\nDuration: " + d + " minutes\nStatus: Timer started\nFocus on your task until the timer ends.\n\nTip: Put phone in DND mode for best results.";
    }

    String smartHomeControl(String device, String action) {
        return "Smart Home Control\nDevice: " + defaultText(device, "living room light") + "\nAction: " + defaultText(action, "on") + "\nStatus: command sent\n\nConnect your smart home bridge (Google Home, Alexa, Home Assistant) for real control.";
    }

    String customThemes() {
        return "Custom Themes\n\nAvailable themes:\n• JARVIS Blue (default) - #00D4FF\n• Iron Man Red - #FF4444\n• Matrix Green - #00FF00\n• Hologram Cyan - #00FFFF\n• Midnight Purple - #8B5CF6\n\nTheme switching coming in next update!";
    }

    String calculator(String expression) {
        String cleaned = expression.replace('x', '*').replace('÷', '/').replace("×", "*").replace(" ", "");
        String allowed = "0123456789+-*/.()";
        for (int i = 0; i < cleaned.length(); i++) {
            if (allowed.indexOf(cleaned.charAt(i)) < 0) {
                return "I can only calculate basic math (+, -, *, /, parentheses, decimals). Expression: " + expression;
            }
        }
        try {
            double result = evalSimple(cleaned);
            if (result == Math.floor(result) && !Double.isInfinite(result)) {
                return expression + " = " + (long) result;
            }
            return expression + " = " + result;
        } catch (Exception e) {
            return "Could not calculate \"" + expression + "\". Use format: 15 * 23 or (10 + 5) / 3";
        }
    }

    private double evalSimple(String expr) {
        // Remove outer parentheses
        String e = expr.trim();
        while (e.startsWith("(") && e.endsWith(")") && balanced(e.substring(1, e.length()-1))) {
            e = e.substring(1, e.length()-1).trim();
        }
        // Find lowest precedence operator outside parentheses
        int paren = 0;
        int opIdx = -1;
        char op = ' ';
        for (int i = e.length() - 1; i >= 0; i--) {
            char c = e.charAt(i);
            if (c == ')') paren++;
            else if (c == '(') paren--;
            else if (paren == 0 && (c == '+' || c == '-')) {
                if (i > 0 && (e.charAt(i-1) == '*' || e.charAt(i-1) == '/' || e.charAt(i-1) == 'e')) continue;
                opIdx = i;
                op = c;
                break;
            }
        }
        if (opIdx < 0) {
            for (int i = e.length() - 1; i >= 0; i--) {
                char c = e.charAt(i);
                if (c == ')') paren++;
                else if (c == '(') paren--;
                else if (paren == 0 && (c == '*' || c == '/')) {
                    opIdx = i;
                    op = c;
                    break;
                }
            }
        }
        if (opIdx < 0) {
            return Double.parseDouble(e);
        }
        double left = evalSimple(e.substring(0, opIdx).trim());
        double right = evalSimple(e.substring(opIdx + 1).trim());
        switch (op) {
            case '+': return left + right;
            case '-': return left - right;
            case '*': return left * right;
            case '/': return right != 0 ? left / right : 0;
            default: return 0;
        }
    }

    private boolean balanced(String s) {
        int d = 0;
        for (int i = 0; i < s.length(); i++) {
            if (s.charAt(i) == '(') d++;
            else if (s.charAt(i) == ')') d--;
            if (d < 0) return false;
        }
        return d == 0;
    }

    String numberFact(String number) throws Exception {
        String n = defaultText(number, "random");
        return get("https://numbersapi.com/" + enc(n) + "/trivia");
    }

    String uselessFact() throws Exception {
        JSONObject data = new JSONObject(get("https://uselessfacts.jsph.pl/api/v2/facts/random"));
        return data.optString("text", data.toString());
    }

    String quote() throws Exception {
        JSONObject data = new JSONObject(get("https://api.quotable.io/random"));
        return "\"" + data.optString("content") + "\"\n- " + data.optString("author");
    }

    String joke(String category) throws Exception {
        JSONObject data = new JSONObject(get("https://v2.jokeapi.dev/joke/" + enc(defaultText(category, "Any")) + "?safe-mode"));
        if ("twopart".equals(data.optString("type"))) {
            return data.optString("setup") + "\n" + data.optString("delivery");
        }
        return data.optString("joke", data.toString());
    }

    String location() throws Exception {
        JSONObject data = new JSONObject(get("https://ipapi.co/json/"));
        return data.optString("city") + ", " + data.optString("region") + ", " + data.optString("country_name")
                + "\nIP: " + data.optString("ip")
                + "\nLatitude/Longitude: " + data.optString("latitude") + ", " + data.optString("longitude");
    }

    String geocode(String address) throws Exception {
        Map<String, String> headers = new LinkedHashMap<>();
        headers.put("User-Agent", USER_AGENT);
        JSONArray data = new JSONArray(get("https://nominatim.openstreetmap.org/search?format=json&limit=3&q="
                + enc(defaultText(address, "Mumbai")), headers));
        StringBuilder out = new StringBuilder("Geocode results\n");
        for (int i = 0; i < data.length(); i++) {
            JSONObject item = data.getJSONObject(i);
            out.append(i + 1).append(". ").append(item.optString("display_name")).append('\n')
                    .append("   ").append(item.optString("lat")).append(", ").append(item.optString("lon")).append('\n');
        }
        return out.toString().trim();
    }

    String sendEmail(String to, String subject, String bodyText) throws Exception {
        if (!keys.has("RESEND_API_KEY")) {
            return "RESEND_API_KEY is not configured.";
        }
        JSONObject body = new JSONObject()
                .put("from", "JARVIS <onboarding@resend.dev>")
                .put("to", new JSONArray().put(to))
                .put("subject", subject)
                .put("text", bodyText);
        Map<String, String> headers = jsonHeaders(keys.get("RESEND_API_KEY"));
        JSONObject data = new JSONObject(post("https://api.resend.com/emails", body.toString(), headers));
        return "Email request sent.\n" + data.toString(2);
    }

    String games(String query) throws Exception {
        String q = defaultText(query, "cyberpunk");
        JSONArray results = new JSONArray(get("https://www.cheapshark.com/api/1.0/games?limit=8&title=" + enc(q)));
        StringBuilder out = new StringBuilder("Games and deals\n");
        for (int i = 0; i < results.length() && i < 8; i++) {
            JSONObject game = results.getJSONObject(i);
            out.append(i + 1).append(". ").append(game.optString("external"))
                    .append(" - from $").append(game.optString("cheapest", "n/a"))
                    .append("\n   Steam app: ").append(game.optString("steamAppID", "n/a")).append('\n');
        }
        if (results.length() == 0) {
            out.append("No CheapShark matches for ").append(q)
                    .append(". Try a broader title like halo, portal, or cyberpunk.");
        }
        return out.toString().trim();
    }

    String movieSearch(String query) throws Exception {
        if (!keys.has("TMDB_API_KEY")) {
            return "TMDB_API_KEY is not configured.";
        }
        JSONObject data = new JSONObject(cachedGet("tmdb", TTL_LONG, "https://api.themoviedb.org/3/search/movie?query="
                + enc(defaultText(query, "inception")) + "&api_key=" + enc(keys.get("TMDB_API_KEY"))));
        JSONArray results = data.optJSONArray("results");
        StringBuilder out = new StringBuilder("Movies\n");
        for (int i = 0; results != null && i < results.length() && i < 6; i++) {
            JSONObject item = results.getJSONObject(i);
            out.append(i + 1).append(". ").append(item.optString("title"))
                    .append(" (").append(item.optString("release_date")).append(")")
                    .append(" - ").append(item.optDouble("vote_average")).append("/10\n");
        }
        return out.toString().trim();
    }

    String trendingMovies() throws Exception {
        if (!keys.has("TMDB_API_KEY")) {
            return "TMDB_API_KEY is not configured.";
        }
        JSONObject data = new JSONObject(cachedGet("tmdb-trend", TTL_MEDIUM, "https://api.themoviedb.org/3/trending/movie/day?api_key="
                + enc(keys.get("TMDB_API_KEY"))));
        JSONArray results = data.optJSONArray("results");
        StringBuilder out = new StringBuilder("Trending movies\n");
        for (int i = 0; results != null && i < results.length() && i < 8; i++) {
            JSONObject item = results.getJSONObject(i);
            out.append(i + 1).append(". ").append(item.optString("title"))
                    .append(" - ").append(item.optDouble("vote_average")).append("/10\n");
        }
        return out.toString().trim();
    }

    String wikipedia(String query) throws Exception {
        JSONObject data = new JSONObject(cachedGet("wiki", TTL_HOUR, "https://en.wikipedia.org/api/rest_v1/page/summary/"
                + enc(defaultText(query, "Artificial intelligence"))));
        return data.optString("title") + "\n" + data.optString("extract") + "\n" + data.optString("content_urls");
    }

    String dictionary(String word) throws Exception {
        JSONArray data = new JSONArray(cachedGet("dict", TTL_HOUR, "https://api.dictionaryapi.dev/api/v2/entries/en/" + enc(defaultText(word, "assistant"))));
        JSONObject entry = data.getJSONObject(0);
        StringBuilder out = new StringBuilder(entry.optString("word"));
        String phonetic = entry.optString("phonetic");
        if (!phonetic.isEmpty()) {
            out.append(" ").append(phonetic);
        }
        out.append('\n');
        JSONArray meanings = entry.optJSONArray("meanings");
        int count = 0;
        for (int i = 0; meanings != null && i < meanings.length() && count < 4; i++) {
            JSONObject meaning = meanings.getJSONObject(i);
            String part = meaning.optString("partOfSpeech");
            JSONArray defs = meaning.optJSONArray("definitions");
            for (int j = 0; defs != null && j < defs.length() && count < 4; j++) {
                count++;
                out.append(count).append(". ");
                if (!part.isEmpty()) {
                    out.append("(").append(part).append(") ");
                }
                out.append(defs.getJSONObject(j).optString("definition")).append('\n');
            }
        }
        return out.toString().trim();
    }

    String books(String query) throws Exception {
        JSONObject data = new JSONObject(cachedGet("books", TTL_HOUR, "https://openlibrary.org/search.json?limit=6&q=" + enc(defaultText(query, "artificial intelligence"))));
        JSONArray docs = data.optJSONArray("docs");
        StringBuilder out = new StringBuilder("Books\n");
        for (int i = 0; docs != null && i < docs.length(); i++) {
            JSONObject book = docs.getJSONObject(i);
            JSONArray authors = book.optJSONArray("author_name");
            out.append(i + 1).append(". ").append(book.optString("title")).append('\n')
                    .append("   Author: ").append(authors != null && authors.length() > 0 ? authors.optString(0) : "unknown")
                    .append(", first published: ").append(book.optString("first_publish_year", "n/a")).append('\n');
        }
        return out.toString().trim();
    }

    String anime(String query) throws Exception {
        JSONObject data = new JSONObject(cachedGet("anime", TTL_HOUR, "https://api.jikan.moe/v4/anime?limit=6&q=" + enc(defaultText(query, "ghost in the shell"))));
        JSONArray results = data.optJSONArray("data");
        StringBuilder out = new StringBuilder("Anime\n");
        for (int i = 0; results != null && i < results.length(); i++) {
            JSONObject item = results.getJSONObject(i);
            out.append(i + 1).append(". ").append(item.optString("title"))
                    .append(" - score ").append(item.optString("score", "n/a")).append('\n')
                    .append("   ").append(item.optString("url")).append('\n');
        }
        return out.toString().trim();
    }

    String spaceNews() throws Exception {
        JSONObject data = new JSONObject(cachedGet("spacenews", TTL_MEDIUM, "https://api.spaceflightnewsapi.net/v4/articles/?limit=6"));
        JSONArray results = data.optJSONArray("results");
        StringBuilder out = new StringBuilder("Space news\n");
        for (int i = 0; results != null && i < results.length(); i++) {
            JSONObject item = results.getJSONObject(i);
            out.append(i + 1).append(". ").append(item.optString("title")).append('\n')
                    .append("   ").append(item.optString("url")).append('\n');
            String summary = item.optString("summary");
            if (!summary.isEmpty()) {
                if (summary.length() > 180) {
                    summary = summary.substring(0, 180) + "...";
                }
                out.append("   ").append(summary).append('\n');
            }
        }
        return out.toString().trim();
    }

    String country(String query) throws Exception {
        JSONArray data = new JSONArray(cachedGet("country", TTL_DAY, "https://restcountries.com/v3.1/name/"
                + enc(defaultText(query, "India"))
                + "?fields=name,capital,region,subregion,population,languages,currencies"));
        JSONObject country = data.getJSONObject(0);
        JSONObject name = country.getJSONObject("name");
        JSONArray capital = country.optJSONArray("capital");
        return name.optString("common")
                + "\nCapital: " + (capital != null && capital.length() > 0 ? capital.optString(0) : "n/a")
                + "\nRegion: " + country.optString("region") + ", " + country.optString("subregion")
                + "\nPopulation: " + country.optLong("population")
                + "\nLanguages: " + country.optJSONObject("languages")
                + "\nCurrencies: " + country.optJSONObject("currencies");
    }

    String holidays(String countryCode) throws Exception {
        String code = defaultText(countryCode, "IN").toUpperCase(Locale.US);
        int year = Calendar.getInstance().get(Calendar.YEAR);
        JSONArray data = new JSONArray(cachedGet("hol", TTL_DAY, "https://date.nager.at/api/v3/PublicHolidays/" + year + "/" + enc(code)));
        StringBuilder out = new StringBuilder("Public holidays ").append(code).append(" ").append(year).append('\n');
        for (int i = 0; i < data.length() && i < 10; i++) {
            JSONObject item = data.getJSONObject(i);
            out.append(i + 1).append(". ").append(item.optString("date"))
                    .append(" - ").append(item.optString("localName")).append('\n');
        }
        return out.toString().trim();
    }

    String advice() throws Exception {
        JSONObject data = new JSONObject(cachedGet("advice", TTL_SHORT, "https://api.adviceslip.com/advice"));
        return data.getJSONObject("slip").optString("advice");
    }

    String githubUser(String username) throws Exception {
        JSONObject data = new JSONObject(cachedGet("gh-user", TTL_HOUR, "https://api.github.com/users/" + enc(defaultText(username, "octocat"))));
        return data.optString("login") + "\nName: " + data.optString("name")
                + "\nFollowers: " + data.optInt("followers")
                + "\nRepos: " + data.optInt("public_repos")
                + "\nURL: " + data.optString("html_url");
    }

    String githubRepo(String ownerRepo) throws Exception {
        String cleaned = defaultText(ownerRepo, "octocat/Hello-World").replace("https://github.com/", "");
        JSONObject data = new JSONObject(cachedGet("gh-repo", TTL_HOUR, "https://api.github.com/repos/" + cleaned));
        return data.optString("full_name")
                + "\nStars: " + data.optInt("stargazers_count")
                + "\nForks: " + data.optInt("forks_count")
                + "\nLanguage: " + data.optString("language")
                + "\nURL: " + data.optString("html_url")
                + "\n" + data.optString("description");
    }

    String recipe(String query) throws Exception {
        String q = defaultText(query, "chicken");
        String url = q.contains(" ")
                ? "https://www.themealdb.com/api/json/v1/1/search.php?s=" + enc(q)
                : "https://www.themealdb.com/api/json/v1/1/filter.php?i=" + enc(q);
        JSONObject data = new JSONObject(get(url));
        JSONArray meals = data.optJSONArray("meals");
        if (meals == null || meals.length() == 0) {
            return "No recipes found.";
        }
        StringBuilder out = new StringBuilder("Recipes\n");
        for (int i = 0; i < meals.length() && i < 6; i++) {
            JSONObject meal = meals.getJSONObject(i);
            out.append(i + 1).append(". ").append(meal.optString("strMeal")).append('\n');
        }
        return out.toString().trim();
    }

    String reddit(String subreddit) throws Exception {
        Map<String, String> headers = new LinkedHashMap<>();
        headers.put("User-Agent", USER_AGENT);
        JSONObject data = new JSONObject(cachedGet("reddit", TTL_MEDIUM, "https://www.reddit.com/r/"
                + enc(defaultText(subreddit, "technology")) + "/hot.json?limit=6", headers));
        JSONArray children = data.getJSONObject("data").getJSONArray("children");
        StringBuilder out = new StringBuilder("Reddit hot posts\n");
        for (int i = 0; i < children.length(); i++) {
            JSONObject item = children.getJSONObject(i).getJSONObject("data");
            out.append(i + 1).append(". ").append(item.optString("title")).append('\n')
                    .append("   https://reddit.com").append(item.optString("permalink")).append('\n');
        }
        return out.toString().trim();
    }

    String qrUrl(String data, int size) {
        String px = Math.max(120, Math.min(800, size)) + "x" + Math.max(120, Math.min(800, size));
        return "QR code URL:\nhttps://api.qrserver.com/v1/create-qr-code/?size=" + px + "&data=" + enc(defaultText(data, "JARVIS"));
    }

    String currency(String fromToAmount) throws Exception {
        String[] parts = defaultText(fromToAmount, "USD INR 1").trim().split("\\s+");
        String from = parts.length > 0 ? parts[0].toUpperCase(Locale.US) : "USD";
        String to = parts.length > 1 ? parts[1].toUpperCase(Locale.US) : "INR";
        String amount = parts.length > 2 ? parts[2] : "1";
        JSONObject data = new JSONObject(get("https://api.frankfurter.app/latest?amount="
                + enc(amount) + "&from=" + enc(from) + "&to=" + enc(to)));
        double converted = data.getJSONObject("rates").optDouble(to);
        return amount + " " + from + " = " + converted + " " + to;
    }

    String podcast(String query) throws Exception {
        JSONObject data = new JSONObject(get("https://itunes.apple.com/search?media=podcast&limit=5&term="
                + enc(defaultText(query, "technology"))));
        JSONArray results = data.optJSONArray("results");
        StringBuilder out = new StringBuilder("Podcasts\n");
        for (int i = 0; results != null && i < results.length(); i++) {
            JSONObject item = results.getJSONObject(i);
            out.append(i + 1).append(". ").append(item.optString("collectionName"))
                    .append(" - ").append(item.optString("artistName")).append('\n')
                    .append("   ").append(item.optString("collectionViewUrl")).append('\n');
        }
        return out.toString().trim();
    }

    String apiTester(String url) throws Exception {
        String data = get(defaultText(url, "https://api.github.com"));
        if (data.length() > 4000) {
            data = data.substring(0, 4000) + "\n...truncated";
        }
        return JsonUtils.pretty(data);
    }

    String ping(String host) throws Exception {
        String cleaned = defaultText(host, "google.com").replace("https://", "").replace("http://", "");
        int slash = cleaned.indexOf('/');
        if (slash >= 0) {
            cleaned = cleaned.substring(0, slash);
        }
        long start = System.nanoTime();
        boolean reachable = InetAddress.getByName(cleaned).isReachable(3000);
        long ms = Math.round((System.nanoTime() - start) / 1_000_000.0);
        return cleaned + " is " + (reachable ? "reachable" : "not reachable") + " in " + ms + " ms";
    }

    String dailyBrief(String city) throws Exception {
        StringBuilder out = new StringBuilder("Daily brief\n\n");
        try {
            out.append(weather(city)).append("\n\n");
        } catch (Exception e) {
            out.append("Weather: ").append(e.getMessage()).append("\n\n");
        }
        try {
            out.append(news("technology")).append("\n\n");
        } catch (Exception e) {
            out.append("News: ").append(e.getMessage()).append("\n\n");
        }
        try {
            out.append(quote()).append("\n\n");
        } catch (Exception e) {
            out.append("Quote: ").append(e.getMessage()).append("\n\n");
        }
        try {
            out.append(trendingCrypto());
        } catch (Exception e) {
            out.append("Crypto: ").append(e.getMessage());
        }
        return out.toString().trim();
    }

    String smartSearch(String query) throws Exception {
        StringBuilder out = new StringBuilder("Smart search: ").append(defaultText(query, "jarvis")).append("\n\n");
        try {
            out.append(webSearch(query)).append("\n\n");
        } catch (Exception e) {
            out.append("Web: ").append(e.getMessage()).append("\n\n");
        }
        try {
            out.append(youtube(query)).append("\n\n");
        } catch (Exception e) {
            out.append("YouTube: ").append(e.getMessage()).append("\n\n");
        }
        try {
            out.append(news(query));
        } catch (Exception e) {
            out.append("News: ").append(e.getMessage());
        }
        return out.toString().trim();
    }

    // ──────────────────────────────────────────────
    // NASA API – APOD, Mars rover, space data
    // ──────────────────────────────────────────────
    String nasaApod() throws Exception {
        if (!keys.has("NASA_API_KEY")) return "NASA_API_KEY is not configured.";
        JSONObject data = new JSONObject(cachedGet("apod", TTL_HOUR, "https://api.nasa.gov/planetary/apod?api_key=" + enc(keys.get("NASA_API_KEY"))));
        return "Astronomy Picture of the Day\n"
                + "Title: " + data.optString("title") + "\n"
                + "Date: " + data.optString("date") + "\n"
                + data.optString("explanation") + "\n"
                + "Image: " + data.optString("url", data.optString("hdurl"));
    }

    String nasaMarsRover(String solOrLatest) throws Exception {
        if (!keys.has("NASA_API_KEY")) return "NASA_API_KEY is not configured.";
        String sol = solOrLatest.trim().isEmpty() || "latest".equalsIgnoreCase(solOrLatest.trim()) ? "" : "&sol=" + enc(solOrLatest.trim());
        String url = "https://api.nasa.gov/mars-photos/api/v1/rovers/curiosity/photos?page=1&api_key=" + enc(keys.get("NASA_API_KEY"));
        if (sol.isEmpty()) url += "&latest=1";
        else url += sol;
        JSONObject data = new JSONObject(cachedGet("mars", TTL_LONG, url));
        JSONArray photos = data.optJSONArray("photos");
        StringBuilder out = new StringBuilder("Mars Rover – Curiosity\n");
        for (int i = 0; photos != null && i < photos.length() && i < 5; i++) {
            JSONObject p = photos.getJSONObject(i);
            JSONObject cam = p.optJSONObject("camera");
            out.append(i + 1).append(". ").append(cam != null ? cam.optString("full_name") : "n/a")
                    .append(" (sol ").append(p.optInt("sol")).append(")\n")
                    .append("   ").append(p.optString("img_src")).append('\n');
        }
        return out.toString().trim();
    }

    String nasaEarth(String latLon) throws Exception {
        if (!keys.has("NASA_API_KEY")) return "NASA_API_KEY is not configured.";
        String[] parts = defaultText(latLon, "19.076,72.8777").split(",");
        String lat = parts.length > 0 ? parts[0].trim() : "19.076";
        String lon = parts.length > 1 ? parts[1].trim() : "72.8777";
        JSONObject data = new JSONObject(cachedGet("earth", TTL_LONG, "https://api.nasa.gov/planetary/earth/imagery?lon=" + enc(lon) + "&lat=" + enc(lat) + "&dim=0.15&api_key=" + enc(keys.get("NASA_API_KEY"))));
        return "Earth imagery\nLat: " + lat + " Lon: " + lon
                + "\nImage URL: " + data.optString("url", "https://api.nasa.gov/planetary/earth/imagery?lon=" + lon + "&lat=" + lat + "&dim=0.15&api_key=" + keys.get("NASA_API_KEY"));
    }

    String nasaIss() throws Exception {
        JSONObject data = new JSONObject(cachedGet("iss", TTL_SHORT, "http://api.open-notify.org/iss-now.json"));
        JSONObject pos = data.optJSONObject("iss_position");
        String lat = pos != null ? pos.optString("latitude", "?") : "?";
        String lon = pos != null ? pos.optString("longitude", "?") : "?";
        return "ISS location\nTimestamp: " + data.optLong("timestamp") + "\nLatitude: " + lat + "\nLongitude: " + lon
                + "\nMap: https://www.google.com/maps?q=" + lat + "," + lon;
    }

    String nasaLibrary(String query) throws Exception {
        JSONObject data = new JSONObject(cachedGet("nasa-lib", TTL_HOUR, "https://images-api.nasa.gov/search?q=" + enc(defaultText(query, "earth")) + "&media_type=image"));
        JSONArray items = data.optJSONObject("collection").optJSONArray("items");
        StringBuilder out = new StringBuilder("NASA image library\n");
        for (int i = 0; items != null && i < items.length() && i < 5; i++) {
            JSONObject item = items.getJSONObject(i);
            JSONArray links = item.optJSONArray("links");
            String href = links != null && links.length() > 0 ? links.getJSONObject(0).optString("href") : "";
            JSONArray photos = item.optJSONArray("data");
            String title = photos != null && photos.length() > 0 ? photos.getJSONObject(0).optString("title") : "n/a";
            out.append(i + 1).append(". ").append(title).append('\n').append("   ").append(href).append('\n');
        }
        return out.toString().trim();
    }

    String nasaSpaceData() throws Exception {
        if (!keys.has("NASA_API_KEY")) return "NASA_API_KEY is not configured.";
        JSONObject data = new JSONObject(cachedGet("neo", TTL_HOUR, "https://api.nasa.gov/neo/rest/v1/neo/browse?page=0&size=5&api_key=" + enc(keys.get("NASA_API_KEY"))));
        JSONArray nearEarth = data.optJSONArray("near_earth_objects");
        StringBuilder out = new StringBuilder("Near-Earth Objects (NEO)\n");
        for (int i = 0; nearEarth != null && i < nearEarth.length(); i++) {
            JSONObject obj = nearEarth.getJSONObject(i);
            JSONObject estimated = obj.optJSONObject("estimated_diameter");
            JSONObject meters = estimated != null ? estimated.optJSONObject("meters") : null;
            double estDiameter = meters != null ? meters.optDouble("estimated_diameter_max") : 0;
            out.append(i + 1).append(". ").append(obj.optString("name"))
                    .append(" – diameter: ").append(String.format(Locale.US, "%.1f", estDiameter)).append(" m\n")
                    .append("   hazardous: ").append(obj.optBoolean("is_potentially_hazardous_asteroid")).append('\n');
        }
        return out.toString().trim();
    }

    // ──────────────────────────────────────────────
    // Finnhub – stock news & market data
    // ──────────────────────────────────────────────
    String finnhubStockNews(String symbol) throws Exception {
        if (!keys.has("FINNHUB_API_KEY")) return "FINNHUB_API_KEY is not configured.";
        String sym = defaultText(symbol, "AAPL").toUpperCase(Locale.US);
        JSONArray data = new JSONArray(cachedGet("fh-news", TTL_MEDIUM, "https://finnhub.io/api/v1/company-news?symbol=" + enc(sym) + "&from=2025-01-01&to=2026-12-31&token=" + enc(keys.get("FINNHUB_API_KEY"))));
        StringBuilder out = new StringBuilder("Stock news: ").append(sym).append('\n');
        for (int i = 0; i < data.length() && i < 5; i++) {
            JSONObject item = data.getJSONObject(i);
            out.append(i + 1).append(". ").append(item.optString("headline")).append('\n')
                    .append("   ").append(item.optString("url")).append('\n');
        }
        return out.toString().trim();
    }

    String finnhubQuote(String symbol) throws Exception {
        if (!keys.has("FINNHUB_API_KEY")) return "FINNHUB_API_KEY is not configured.";
        String sym = defaultText(symbol, "AAPL").toUpperCase(Locale.US);
        JSONObject data = new JSONObject(cachedGet("fh-quote", TTL_SHORT, "https://finnhub.io/api/v1/quote?symbol=" + enc(sym) + "&token=" + enc(keys.get("FINNHUB_API_KEY"))));
        double c = data.optDouble("c");
        double d = data.optDouble("d");
        double dp = data.optDouble("dp");
        double h = data.optDouble("h");
        double l = data.optDouble("l");
        double o = data.optDouble("o");
        double pc = data.optDouble("pc");
        return sym + "\nCurrent: " + c + "\nChange: " + d + " (" + dp + "%)\nHigh: " + h + " Low: " + l + "\nOpen: " + o + " Prev close: " + pc;
    }

    String finnhubMarketNews() throws Exception {
        if (!keys.has("FINNHUB_API_KEY")) return "FINNHUB_API_KEY is not configured.";
        JSONArray data = new JSONArray(cachedGet("fh-mkt", TTL_MEDIUM, "https://finnhub.io/api/v1/news?category=general&token=" + enc(keys.get("FINNHUB_API_KEY"))));
        StringBuilder out = new StringBuilder("Market news\n");
        for (int i = 0; i < data.length() && i < 6; i++) {
            JSONObject item = data.getJSONObject(i);
            out.append(i + 1).append(". ").append(item.optString("headline")).append('\n')
                    .append("   ").append(item.optString("url")).append('\n');
        }
        return out.toString().trim();
    }

    String finnhubCompany(String symbol) throws Exception {
        if (!keys.has("FINNHUB_API_KEY")) return "FINNHUB_API_KEY is not configured.";
        String sym = defaultText(symbol, "AAPL").toUpperCase(Locale.US);
        JSONObject data = new JSONObject(cachedGet("fh-company", TTL_HOUR, "https://finnhub.io/api/v1/stock/profile2?symbol=" + enc(sym) + "&token=" + enc(keys.get("FINNHUB_API_KEY"))));
        if (!data.has("name")) return "Company not found for " + sym;
        return data.optString("name") + " (" + data.optString("ticker") + ")"
                + "\nExchange: " + data.optString("exchange")
                + "\nIndustry: " + data.optString("finnhubIndustry")
                + "\nMarket cap: $" + String.format(Locale.US, "%,.0f", data.optDouble("marketCapitalization")) + "M"
                + "\nIPO: " + data.optString("ipo")
                + "\nShare outstanding: " + data.optString("shareOutstanding", "n/a");
    }

    String finnhubFinancials(String symbol) throws Exception {
        if (!keys.has("FINNHUB_API_KEY")) return "FINNHUB_API_KEY is not configured.";
        String sym = defaultText(symbol, "AAPL").toUpperCase(Locale.US);
        JSONObject data = new JSONObject(cachedGet("fh-fin", TTL_HOUR, "https://finnhub.io/api/v1/stock/metric?symbol=" + enc(sym) + "&metric=all&token=" + enc(keys.get("FINNHUB_API_KEY"))));
        JSONObject metric = data.optJSONObject("metric");
        if (metric == null) return "No financial data for " + sym;
        return sym + " key metrics\n"
                + "P/E: " + metric.optString("peBasicExclExtraTTM", "n/a")
                + " | EPS: " + metric.optString("epsBasicExclExtraTTM", "n/a")
                + "\nRevenue (TTM): " + metric.optString("revenuePerShareTTM", "n/a")
                + " | Dividend yield: " + metric.optString("dividendYieldIndicatedAnnual", "n/a")
                + "\nROE: " + metric.optString("roeTTM", "n/a")
                + " | Beta: " + metric.optString("beta", "n/a");
    }

    String finnhubForex(String pair) throws Exception {
        if (!keys.has("FINNHUB_API_KEY")) return "FINNHUB_API_KEY is not configured.";
        String p = defaultText(pair, "OANDA:EUR_USD").toUpperCase(Locale.US);
        if (!p.contains(":")) p = "OANDA:" + p;
        JSONObject data = new JSONObject(cachedGet("fh-fx", TTL_SHORT, "https://finnhub.io/api/v1/quote?symbol=" + enc(p) + "&token=" + enc(keys.get("FINNHUB_API_KEY"))));
        return p.replace("OANDA:", "") + "\nRate: " + data.optDouble("c")
                + " | High: " + data.optDouble("h") + " Low: " + data.optDouble("l")
                + " | Change: " + data.optDouble("d") + " (" + data.optDouble("dp") + "%)";
    }

    String finnhubCryptoRate(String pair) throws Exception {
        if (!keys.has("FINNHUB_API_KEY")) return "FINNHUB_API_KEY is not configured.";
        String p = defaultText(pair, "BINANCE:BTCUSDT").toUpperCase(Locale.US);
        if (!p.contains(":")) p = "BINANCE:" + p;
        JSONObject data = new JSONObject(get("https://finnhub.io/api/v1/quote?symbol=" + enc(p) + "&token=" + enc(keys.get("FINNHUB_API_KEY"))));
        return p.replace("BINANCE:", "") + "\nPrice: " + data.optDouble("c")
                + " | High: " + data.optDouble("h") + " Low: " + data.optDouble("l")
                + " | Change: " + data.optDouble("d") + " (" + data.optDouble("dp") + "%)";
    }

    // ──────────────────────────────────────────────
    // API Ninjas – nutrition, city, facts, exercises
    // ──────────────────────────────────────────────
    private Map<String, String> ninjaHeaders() {
        Map<String, String> h = new LinkedHashMap<>();
        h.put("X-Api-Key", keys.get("API_NINJAS_KEY"));
        h.put("User-Agent", USER_AGENT);
        return h;
    }

    String nutrition(String query) throws Exception {
        if (!keys.has("API_NINJAS_KEY")) return "API_NINJAS_KEY is not configured.";
        JSONArray data = new JSONArray(cachedGet("nutri", TTL_HOUR, "https://api.api-ninjas.com/v1/nutrition?query=" + enc(defaultText(query, "apple")), ninjaHeaders()));
        StringBuilder out = new StringBuilder("Nutrition\n");
        for (int i = 0; i < data.length(); i++) {
            JSONObject item = data.getJSONObject(i);
            out.append(i + 1).append(". ").append(item.optString("name")).append('\n')
                    .append("   Calories: ").append(item.optString("calories", "0"))
                    .append(" | Protein: ").append(item.optString("protein_g", "0")).append("g")
                    .append(" | Carbs: ").append(item.optString("carbohydrates_total_g", "0")).append("g")
                    .append(" | Fat: ").append(item.optString("fat_total_g", "0")).append("g\n");
        }
        return out.toString().trim();
    }

    String cityInfo(String query) throws Exception {
        if (!keys.has("API_NINJAS_KEY")) return "API_NINJAS_KEY is not configured.";
        JSONArray data = new JSONArray(cachedGet("city", TTL_DAY, "https://api.api-ninjas.com/v1/city?name=" + enc(defaultText(query, "Mumbai")), ninjaHeaders()));
        if (data.length() == 0) return "City not found.";
        JSONObject city = data.getJSONObject(0);
        return city.optString("name")
                + "\nCountry: " + city.optString("country")
                + "\nPopulation: " + city.optLong("population")
                + "\nLat/Lon: " + city.optDouble("latitude") + ", " + city.optDouble("longitude")
                + "\nArea: " + city.optString("area", "n/a") + " km²";
    }

    String randomFact() throws Exception {
        if (!keys.has("API_NINJAS_KEY")) return "API_NINJAS_KEY is not configured.";
        JSONArray data = new JSONArray(cachedGet("fact", TTL_MEDIUM, "https://api.api-ninjas.com/v1/facts?limit=1", ninjaHeaders()));
        if (data.length() == 0) return "No fact found.";
        return data.getJSONObject(0).optString("fact");
    }

    String exercises(String query) throws Exception {
        if (!keys.has("API_NINJAS_KEY")) return "API_NINJAS_KEY is not configured.";
        JSONArray data = new JSONArray(cachedGet("exercise", TTL_HOUR, "https://api.api-ninjas.com/v1/exercises?muscle=" + enc(defaultText(query, "biceps")), ninjaHeaders()));
        StringBuilder out = new StringBuilder("Exercises\n");
        for (int i = 0; i < data.length() && i < 5; i++) {
            JSONObject item = data.getJSONObject(i);
            out.append(i + 1).append(". ").append(item.optString("name")).append('\n')
                    .append("   Type: ").append(item.optString("type"))
                    .append(" | Muscle: ").append(item.optString("muscle"))
                    .append(" | Difficulty: ").append(item.optString("difficulty")).append('\n')
                    .append("   ").append(item.optString("instructions", ""))
                    .append('\n');
        }
        return out.toString().trim();
    }

    String ipLookup(String address) throws Exception {
        if (!keys.has("API_NINJAS_KEY")) return "API_NINJAS_KEY is not configured.";
        String ip = defaultText(address, "");
        String url = ip.isEmpty() ? "https://api.api-ninjas.com/v1/iplookup" : "https://api.api-ninjas.com/v1/iplookup?address=" + enc(ip);
        JSONObject data = new JSONObject(cachedGet("ip", TTL_HOUR, url, ninjaHeaders()));
        return "IP: " + data.optString("ip", ip.isEmpty() ? "auto" : ip)
                + "\nCity: " + data.optString("city", "n/a")
                + "\nRegion: " + data.optString("region", "n/a")
                + "\nCountry: " + data.optString("country", "n/a")
                + "\nISP: " + data.optString("isp", "n/a")
                + "\nLat/Lon: " + data.optString("lat", "?") + ", " + data.optString("lon", "?");
    }

    String sentiment(String text) throws Exception {
        if (!keys.has("API_NINJAS_KEY")) return "API_NINJAS_KEY is not configured.";
        JSONObject body = new JSONObject().put("text", defaultText(text, "I love JARVIS!"));
        Map<String, String> headers = new LinkedHashMap<>();
        headers.put("Content-Type", "application/json");
        headers.put("X-Api-Key", keys.get("API_NINJAS_KEY"));
        headers.put("User-Agent", USER_AGENT);
        JSONObject data = new JSONObject(post("https://api.api-ninjas.com/v1/sentiment", body.toString(), headers));
        return "Sentiment analysis\n"
                + "Sentiment: " + data.optString("sentiment")
                + "\nScore: " + data.optDouble("score", 0)
                + "\nMixed: " + data.optDouble("mixed", 0)
                + "\nPositive: " + data.optDouble("positive", 0)
                + "\nNegative: " + data.optDouble("negative", 0)
                + "\nNeutral: " + data.optDouble("neutral", 0);
    }

    String emailValidate(String email) throws Exception {
        if (!keys.has("API_NINJAS_KEY")) return "API_NINJAS_KEY is not configured.";
        JSONObject data = new JSONObject(cachedGet("email-val", TTL_MEDIUM, "https://api.api-ninjas.com/v1/email?email=" + enc(defaultText(email, "test@example.com")), ninjaHeaders()));
        return "Email validation\nAddress: " + data.optString("email")
                + "\nValid format: " + data.optBoolean("is_valid", false)
                + "\nDeliverable: " + data.optBoolean("deliverability", false)
                + "\nDisposable: " + data.optBoolean("is_disposable_email", false)
                + "\nRole-based: " + data.optBoolean("is_role_email", false);
    }

    // ──────────────────────────────────────────────
    // Calendarific – global holidays (replaces Nager.Date)
    // ──────────────────────────────────────────────
    String globalHolidays(String countryCode) throws Exception {
        if (!keys.has("CALENDARIFIC_API_KEY")) return "CALENDARIFIC_API_KEY is not configured.";
        String code = defaultText(countryCode, "IN").toUpperCase(Locale.US);
        int year = Calendar.getInstance().get(Calendar.YEAR);
        JSONObject data = new JSONObject(cachedGet("cal", TTL_DAY, "https://calendarific.com/api/v2/holidays?api_key="
                + enc(keys.get("CALENDARIFIC_API_KEY")) + "&country=" + enc(code) + "&year=" + year));
        JSONArray holidays = data.optJSONObject("response").optJSONArray("holidays");
        StringBuilder out = new StringBuilder("Holidays ").append(code).append(" ").append(year).append('\n');
        for (int i = 0; holidays != null && i < holidays.length() && i < 10; i++) {
            JSONObject h = holidays.getJSONObject(i);
            JSONObject date = h.optJSONObject("date");
            String iso = date != null ? date.optString("iso") : "";
            out.append(i + 1).append(". ").append(iso)
                    .append(" – ").append(h.optString("name")).append('\n');
        }
        return out.toString().trim();
    }

    String holidayTypes(String countryCodeType) throws Exception {
        if (!keys.has("CALENDARIFIC_API_KEY")) return "CALENDARIFIC_API_KEY is not configured.";
        String[] parts = defaultText(countryCodeType, "IN").split("\\|", 2);
        String code = parts[0].trim().toUpperCase(Locale.US);
        String type = parts.length > 1 ? parts[1].trim() : "";
        int year = Calendar.getInstance().get(Calendar.YEAR);
        String url = "https://calendarific.com/api/v2/holidays?api_key=" + enc(keys.get("CALENDARIFIC_API_KEY"))
                + "&country=" + enc(code) + "&year=" + year;
        if (!type.isEmpty()) url += "&type=" + enc(type);
        JSONObject data = new JSONObject(get(url));
        JSONArray holidays = data.optJSONObject("response").optJSONArray("holidays");
        StringBuilder out = new StringBuilder("Holidays ").append(code).append(" ").append(year);
        if (!type.isEmpty()) out.append(" (").append(type).append(")");
        out.append('\n');
        for (int i = 0; holidays != null && i < holidays.length() && i < 10; i++) {
            JSONObject h = holidays.getJSONObject(i);
            JSONObject date = h.optJSONObject("date");
            String iso = date != null ? date.optString("iso") : "";
            String[] types = h.optJSONArray("type") != null ? h.getJSONArray("type").join(",").split(",") : new String[0];
            out.append(i + 1).append(". ").append(iso)
                    .append(" – ").append(h.optString("name"))
                    .append(" (").append(types.length > 0 ? types[0].replace("\"", "") : "public").append(")\n");
        }
        return out.toString().trim();
    }

    private String openRouter(String prompt) throws Exception {
        JSONObject body = new JSONObject();
        body.put("model", "openai/gpt-4o-mini");
        JSONArray messages = new JSONArray();
        messages.put(new JSONObject().put("role", "system").put("content",
                "You are JARVIS Mobile, AI assistant on Android. Available via colon-commands: "
                + "weather:, news:, crypto:, stock:, youtube:, translate:, web:, image:, nasa-apod:, nasa-mars:, nasa-earth:, nasa-iss:, "
                + "nasa-space:, nasa-library:, finnhub-quote:, finnhub-news:, finnhub-company:, finnhub-financials:, finnhub-forex:, "
                + "finnhub-crypto:, nutrition:, city:, fact:, exercises:, ip-lookup:, sentiment:, email-validate:, "
                + "global-holidays:, holiday-types:, wiki:, movies:, games:, recipe:, qr:, ping:, currency:. "
                + "Also respond helpfully to general questions."));
        messages.put(new JSONObject().put("role", "user").put("content", prompt));
        body.put("messages", messages);
        JSONObject data = new JSONObject(post("https://openrouter.ai/api/v1/chat/completions",
                body.toString(), jsonHeaders(keys.get("OPENROUTER_API_KEY"))));
        return data.getJSONArray("choices").getJSONObject(0).getJSONObject("message").optString("content");
    }

    private String groq(String prompt, String apiKey, String keyName) throws Exception {
        JSONObject body = new JSONObject();
        body.put("model", "llama-3.1-8b-instant");
        JSONArray messages = new JSONArray();
        messages.put(new JSONObject().put("role", "system").put("content",
                "You are JARVIS Mobile. Available commands: weather:, news:, crypto:, stock:, youtube:, nasa-apod:, nasa-mars:, "
                + "nasa-earth:, nasa-iss:, finnhub-quote:, finnhub-news:, nutrition:, city:, fact:, exercises:, ip-lookup:, "
                + "sentiment:, global-holidays:, wiki:, movies:. Use command:argument to fetch data."));
        messages.put(new JSONObject().put("role", "user").put("content", prompt));
        body.put("messages", messages);
        JSONObject data = new JSONObject(post("https://api.groq.com/openai/v1/chat/completions",
                body.toString(), jsonHeaders(apiKey)));
        String content = data.getJSONArray("choices").getJSONObject(0).getJSONObject("message").optString("content");
        return content.isEmpty() ? "Groq returned an empty response from " + keyName + "." : content;
    }

    private String geminiText(String prompt) throws Exception {
        JSONObject body = new JSONObject()
                .put("contents", new JSONArray().put(new JSONObject()
                        .put("parts", new JSONArray().put(new JSONObject().put("text", prompt)))));
        String url = "https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key="
                + enc(keys.get("GEMINI_API_KEY"));
        JSONObject data = new JSONObject(post(url, body.toString(), jsonHeaders(null)));
        return geminiTextFromResponse(data);
    }

    private String geminiTextFromResponse(JSONObject data) throws JSONException {
        JSONArray candidates = data.optJSONArray("candidates");
        if (candidates == null || candidates.length() == 0) {
            return data.toString(2);
        }
        JSONArray parts = candidates.getJSONObject(0).getJSONObject("content").getJSONArray("parts");
        StringBuilder out = new StringBuilder();
        for (int i = 0; i < parts.length(); i++) {
            out.append(parts.getJSONObject(i).optString("text"));
        }
        return out.toString();
    }

    private Map<String, String> jsonHeaders(String bearerToken) {
        Map<String, String> headers = new LinkedHashMap<>();
        headers.put("Content-Type", "application/json");
        headers.put("Accept", "application/json");
        headers.put("User-Agent", USER_AGENT);
        if (bearerToken != null && !bearerToken.isEmpty()) {
            headers.put("Authorization", "Bearer " + bearerToken);
        }
        return headers;
    }

    private String get(String url) throws Exception {
        return get(url, null);
    }

    private String get(String url, Map<String, String> headers) throws Exception {
        HttpURLConnection conn = (HttpURLConnection) new URL(url).openConnection();
        conn.setRequestMethod("GET");
        conn.setConnectTimeout(15000);
        conn.setReadTimeout(30000);
        conn.setRequestProperty("User-Agent", USER_AGENT);
        if (headers != null) {
            for (Map.Entry<String, String> entry : headers.entrySet()) {
                conn.setRequestProperty(entry.getKey(), entry.getValue());
            }
        }
        return read(conn);
    }

    private String post(String url, String body, Map<String, String> headers) throws Exception {
        byte[] bytes = body.getBytes(StandardCharsets.UTF_8);
        HttpURLConnection conn = (HttpURLConnection) new URL(url).openConnection();
        conn.setRequestMethod("POST");
        conn.setConnectTimeout(15000);
        conn.setReadTimeout(45000);
        conn.setDoOutput(true);
        if (headers != null) {
            for (Map.Entry<String, String> entry : headers.entrySet()) {
                conn.setRequestProperty(entry.getKey(), entry.getValue());
            }
        }
        conn.setRequestProperty("Content-Length", String.valueOf(bytes.length));
        try (OutputStream out = conn.getOutputStream()) {
            out.write(bytes);
        }
        return read(conn);
    }

    private String read(HttpURLConnection conn) throws Exception {
        int code = conn.getResponseCode();
        InputStream stream = code >= 200 && code < 300 ? conn.getInputStream() : conn.getErrorStream();
        String body = readFully(stream);
        if (code < 200 || code >= 300) {
            throw new IllegalStateException("HTTP " + code + ": " + body);
        }
        return body;
    }

    private String readFully(InputStream stream) throws Exception {
        if (stream == null) {
            return "";
        }
        try (BufferedReader reader = new BufferedReader(new InputStreamReader(stream, StandardCharsets.UTF_8))) {
            StringBuilder out = new StringBuilder();
            String line;
            while ((line = reader.readLine()) != null) {
                out.append(line).append('\n');
            }
            return out.toString().trim();
        }
    }

    static byte[] readBytes(InputStream stream) throws Exception {
        ByteArrayOutputStream out = new ByteArrayOutputStream();
        byte[] buffer = new byte[8192];
        int read;
        while ((read = stream.read(buffer)) != -1) {
            out.write(buffer, 0, read);
        }
        return out.toByteArray();
    }

    private static String enc(String value) {
        try {
            return URLEncoder.encode(value == null ? "" : value, "UTF-8");
        } catch (Exception e) {
            return "";
        }
    }

    private static String defaultText(String value, String fallback) {
        return value == null || value.trim().isEmpty() ? fallback : value.trim();
    }
}
