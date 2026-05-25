package com.jarvis.mobile;

import org.json.JSONArray;
import org.json.JSONObject;

final class JarvisBrain {
    private final JarvisApiClient api;
    private final LocalMemory memory;
    private final DeviceStats deviceStats;

    JarvisBrain(JarvisApiClient api, LocalMemory memory, DeviceStats deviceStats) {
        this.api = api;
        this.memory = memory;
        this.deviceStats = deviceStats;
    }

    String run(String raw) throws Exception {
        String input = raw == null ? "" : raw.trim();
        if (input.isEmpty()) {
            return "Tell me what you need.";
        }
        int colon = input.indexOf(':');
        if (colon > 0) {
            String command = input.substring(0, colon).trim().toLowerCase();
            String arg = input.substring(colon + 1).trim();
            return runCommand(command, arg);
        }
        return routeNatural(input);
    }

    private String runCommand(String command, String arg) throws Exception {
        switch (command) {
            // ───────────── CORE AI ─────────────
            case "chat":
                return api.chat(arg);
            case "ai":
                return api.chat(arg);
            case "code":
                return api.codeAssist(arg);
            case "summarize":
                return api.summarize(arg);
            case "email-draft":
                return api.writeEmail(arg);
            case "email-send": {
                String[] parts = arg.split("\\|", 3);
                if (parts.length < 3) {
                    return "Use: recipient@example.com|Subject|Body";
                }
                return api.sendEmail(parts[0].trim(), parts[1].trim(), parts[2].trim());
            }
            case "meeting-notes":
                return api.meetingNotes(arg);
            case "story":
                return api.writeStory(arg);
            case "calculator":
            case "calc":
                return api.calculator(arg);
            case "calculate":
                return api.calculator(arg);
            case "weather":
                return api.weather(arg);
            case "forecast":
                return api.forecast(arg);
            case "news":
                return api.news(arg);
            case "headlines":
                return api.news(arg);
            case "crypto":
                return api.crypto(arg);
            case "crypto-trending":
                return api.trendingCrypto();
            case "stock":
                return api.stock(arg);
            case "youtube":
                return api.youtube(arg);
            case "translate": {
                String[] parts = arg.split("\\|", 2);
                String target = parts.length > 1 ? parts[0].trim() : "hi";
                String text = parts.length > 1 ? parts[1].trim() : arg;
                return api.translate(text, target);
            }
            case "web":
                return api.webSearch(arg);
            case "tavily":
                return api.tavilySearch(arg);
            case "google":
                return api.googleSearch(arg);
            case "image":
                return api.imageUrl(arg);
            case "unsplash":
                return api.unsplash(arg);
            case "fact-random":
            case "did-you-know":
                return api.educationalFact();
            case "number-fact":
                return api.numberFact(arg);
            case "useless-fact":
                return api.uselessFact();
            case "quote":
                return api.quote();
            case "quote-inspire":
            case "inspire":
                return api.hardcodedQuote();
            case "joke":
                return api.joke(arg.isEmpty() ? "Any" : arg);
            case "location":
                return api.location();
            case "geocode":
                return api.geocode(arg);
            case "games":
                return api.games(arg);
            case "movies":
                return api.movieSearch(arg);
            case "movies-trending":
                return api.trendingMovies();
            case "wiki":
                return api.wikipedia(arg);
            case "dictionary":
                return api.dictionary(arg);
            case "books":
                return api.books(arg);
            case "anime":
                return api.anime(arg);
            case "space-news":
                return api.spaceNews();
            case "country":
                return api.country(arg);
            case "holidays":
                return api.holidays(arg);
            case "global-holidays":
                return api.globalHolidays(arg);
            case "holiday-types":
                return api.holidayTypes(arg);
            case "nasa-apod":
                return api.nasaApod();
            case "nasa-mars":
                return api.nasaMarsRover(arg);
            case "nasa-space":
                return api.nasaSpaceData();
            case "nasa-earth":
                return api.nasaEarth(arg);
            case "nasa-iss":
                return api.nasaIss();
            case "nasa-library":
                return api.nasaLibrary(arg);
            case "finnhub-news":
                return api.finnhubStockNews(arg);
            case "finnhub-quote":
                return api.finnhubQuote(arg);
            case "finnhub-market":
                return api.finnhubMarketNews();
            case "finnhub-company":
                return api.finnhubCompany(arg);
            case "finnhub-financials":
                return api.finnhubFinancials(arg);
            case "finnhub-forex":
                return api.finnhubForex(arg);
            case "finnhub-crypto":
                return api.finnhubCryptoRate(arg);
            case "nutrition":
                return api.nutrition(arg);
            case "city":
                return api.cityInfo(arg);
            case "fact":
                return api.randomFact();
            case "exercises":
                return api.exercises(arg);
            case "ip-lookup":
                return api.ipLookup(arg);
            case "sentiment":
                return api.sentiment(arg);
            case "email-validate":
                return api.emailValidate(arg);
            case "advice":
                return api.advice();
            case "github-user":
                return api.githubUser(arg);
            case "github-repo":
                return api.githubRepo(arg);
            case "recipe":
                return api.recipe(arg);
            case "reddit":
                return api.reddit(arg);
            case "web-visit":
                return "Web page visit: " + arg + "\n\nFetching page content... JARVIS Mobile can open URLs in browser. Use the 'browser:' command to open, or copy the URL to your browser.\nSuggested: https://r.jina.ai/http://" + arg.replace("https://", "").replace("http://", "") + " for a text-readable version.";
            case "shopping":
                return "Shopping search for: " + arg + "\n\nProduct comparison:\n• Amazon: search.amazon.com/?q=" + arg.replace(" ", "+") + "\n• Flipkart: flipkart.com/search?q=" + arg.replace(" ", "+") + "\n\nOpen links in browser to compare prices.";
            case "youtube-learn":
                return "📚 YouTube Learning\n\nVideo: " + arg + "\n\nYouTube learning requires server-side processing (download + transcribe + summarize).\nOn mobile: Open the video in YouTube, then ask me to summarize what you learned!\n\nTo open: use 'browser:https://youtube.com/watch?v=" + arg + "'";
            case "qr":
                return api.qrUrl(arg, 360);
            case "wifi-qr":
                return api.qrUrl("WIFI:T:WPA;S:" + arg + ";P:password;;", 360);
            case "currency":
                return api.currency(arg);
            case "podcast":
                return api.podcast(arg);
            case "music-recognize":
                return api.musicRecognition();
            case "movies-recommend": {
                String[] parts = arg.split("\\|", 2);
                String genre = parts.length > 0 ? parts[0].trim() : "action";
                String mood = parts.length > 1 ? parts[1].trim() : "any";
                return api.movieRecommendations(genre, mood);
            }
            case "calendar":
                return api.calendarEvents();
            case "focus":
                return api.focusMode(parseInt(arg, 25));
            case "pomodoro":
                return api.focusMode(parseInt(arg, 25));
            case "smart-home":
                return api.smartHomeControl(arg, "on");
            case "smart-home-off":
                return api.smartHomeControl(arg, "off");
            case "themes":
            case "theme":
                return api.customThemes();
            case "api-test":
                return api.apiTester(arg);
            case "system-graphs":
                return api.systemGraphs();
            case "disk-analyzer":
                return api.diskAnalyzer();
            case "speed-test":
                return api.speedTest();
            case "network-status":
                return "Network Status\n" + deviceStats.summary() + "\n\nFor detailed diagnostics, run a speed test or ping a host.";
            case "wallpapers":
                return "Animated Wallpapers\n\nAvailable:\n• Neon City - animated\n• Matrix Rain - animated\n• Abstract Waves - animated\n• Starfield - animated\n• Aurora Borealis - animated\n\nSet wallpapers from your phone's Settings > Wallpaper.";
            case "network":
                return deviceStats.summary();
            case "json":
                return JsonUtils.pretty(arg);
            case "ping":
                return api.ping(arg);
            case "daily":
                return api.dailyBrief(arg);
            case "smart-search":
                return api.smartSearch(arg);
            case "system":
                return deviceStats.summary();
            case "note":
                memory.addNote(firstLine(arg, "Note"), arg);
                return "Saved note.";
            case "todo":
                memory.addTodo(arg);
                return "Added todo.";
            case "plugins":
                return pluginStatus();
            case "terminal":
                return "Terminal execution is intentionally not available on Android. Use API Tester, JSON Formatter, GitHub lookup, and browser actions instead.";
            case "screenshot":
                return "Android apps cannot silently capture the full screen. Use the phone screenshot buttons, or add a MediaProjection consent flow later.";
            case "record":
                return "Screen recording requires Android's MediaProjection consent UI. This lightweight build avoids that background permission flow.";
            // smart-home handled above with enhanced api.smartHomeControl()
            case "whatsapp":
                return "WhatsApp share URL:\nhttps://wa.me/?text=" + arg.replace(" ", "%20");
            case "horoscope":
                return api.horoscope(arg);
            case "riddle":
                return api.riddle();
            case "coin":
                return Math.random() > 0.5 ? "Heads" : "Tails";
            case "dice":
                int sides = parseInt(arg, 6);
                return "Rolled " + (1 + (int) Math.floor(Math.random() * Math.max(2, sides))) + " on a d" + Math.max(2, sides) + ".";
            case "8ball":
                String[] answers = {"It is certain.", "Most likely.", "Ask again later.", "My reply is no.", "Signs point to yes."};
                return answers[(int) Math.floor(Math.random() * answers.length)];
            case "joke-hardcoded":
                return api.hardcodedJoke();
            case "riddle-random":
                return api.riddle();
            case "horoscope-enhanced":
                return api.horoscope(arg);
            default:
                return api.chat(arg.isEmpty() ? command : command + ": " + arg);
        }
    }

    private String routeNatural(String input) throws Exception {
        String lower = input.toLowerCase();

        // Calculator
        if (lower.startsWith("calculate ") || lower.startsWith("calc ") || lower.startsWith("what is ")) {
            String expr = lower.startsWith("what is ") ? input.substring(8).trim() : input.substring(input.indexOf(' ') + 1).trim();
            return api.calculator(expr);
        }

        // Shopping
        if (lower.startsWith("buy ") || lower.startsWith("purchase ") || lower.startsWith("find cheapest ") || lower.startsWith("shopping for ")) {
            return runCommand("shopping", afterKeyword(input, lower.startsWith("find cheapest ") ? "find cheapest" : lower.startsWith("shopping for ") ? "shopping for" : lower.startsWith("buy ") ? "buy" : "purchase"));
        }

        // Web visit
        if (lower.startsWith("visit ") || lower.startsWith("open website ") || lower.startsWith("go to ")) {
            String url = afterKeyword(input, lower.startsWith("go to ") ? "go to" : lower.startsWith("open website ") ? "open website" : "visit");
            return runCommand("web-visit", url);
        }

        // Focus mode
        if (lower.contains("focus mode") || lower.contains("pomodoro")) {
            return api.focusMode(25);
        }

        // Calendar
        if (lower.contains("calendar") || lower.contains("my events") || lower.contains("schedule")) {
            return api.calendarEvents();
        }

        // Speed test
        if (lower.contains("speed test") || lower.contains("speedtest") || lower.contains("internet speed")) {
            return api.speedTest();
        }

        // System graphs/monitoring
        if (lower.contains("system graph") || lower.contains("cpu graph") || lower.contains("ram graph") || lower.contains("monitoring")) {
            return api.systemGraphs();
        }

        // Disk
        if (lower.contains("disk") || lower.contains("storage") || lower.contains("space")) {
            return api.diskAnalyzer();
        }

        // Music recognition
        if (lower.contains("what song") || lower.contains("music recognize") || lower.contains("shazam") || lower.contains("what's playing")) {
            return api.musicRecognition();
        }

        // Movie recommendations
        if (lower.contains("movie recommend") || lower.contains("suggest a movie") || lower.contains("what to watch")) {
            String genre = "";
            String[] genres = {"action", "comedy", "horror", "scifi", "thriller", "romance", "drama"};
            for (String g : genres) {
                if (lower.contains(g)) { genre = g; break; }
            }
            return api.movieRecommendations(genre, "");
        }

        // Themes
        if (lower.contains("theme") || lower.contains("customize")) {
            return api.customThemes();
        }

        // Smart home
        if (lower.contains("turn on") || lower.contains("turn off") || (lower.contains("smart home") || lower.contains("lights"))) {
            String device = "lights";
            String action = "on";
            if (lower.contains("turn off") || lower.contains("off")) action = "off";
            if (lower.contains("fan")) device = "fan";
            if (lower.contains("ac") || lower.contains("cooler")) device = "AC";
            return api.smartHomeControl(device, action);
        }

        // Did you know / random fact
        if (lower.contains("did you know") || lower.contains("interesting fact") || lower.contains("tell me something")) {
            return api.educationalFact();
        }

        // Inspire me
        if (lower.contains("inspire me") || lower.contains("motivate me") || lower.contains("motivational")) {
            return api.hardcodedQuote();
        }

        if (lower.contains("weather")) {
            return api.weather(afterKeyword(input, "weather"));
        }
        if (lower.contains("forecast")) {
            return api.forecast(afterKeyword(input, "forecast"));
        }
        if (lower.contains("news")) {
            return api.news(afterKeyword(input, "news"));
        }
        if (lower.contains("youtube")) {
            return api.youtube(afterKeyword(input, "youtube"));
        }
        if (lower.contains("crypto") || lower.contains("bitcoin")) {
            return api.crypto(afterKeyword(input, "crypto"));
        }
        if (lower.contains("stock")) {
            return api.stock(afterKeyword(input, "stock"));
        }
        if (lower.contains("translate")) {
            return api.translate(afterKeyword(input, "translate"), "hi");
        }
        if (lower.contains("quote")) {
            return api.quote();
        }
        if (lower.contains("dictionary") || lower.startsWith("define ")) {
            return api.dictionary(lower.startsWith("define ") ? input.substring(7) : afterKeyword(input, "dictionary"));
        }
        if (lower.contains("space news")) {
            return api.spaceNews();
        }
        if (lower.contains("joke")) {
            return api.joke("Any");
        }
        if (lower.contains("system") || lower.contains("battery") || lower.contains("ram")) {
            return deviceStats.summary();
        }
        if (lower.contains("daily brief")) {
            return api.dailyBrief("Mumbai");
        }
        if (lower.contains("apod") || lower.contains("astronomy") || lower.contains("nasa apod")) {
            return api.nasaApod();
        }
        if (lower.contains("mars") || lower.contains("mars rover")) {
            return api.nasaMarsRover(afterKeyword(input, "mars"));
        }
        if (lower.contains("asteroid") || lower.contains("neo") || lower.contains("near earth")) {
            return api.nasaSpaceData();
        }
        if (lower.contains("stock news") || lower.contains("market news") || lower.contains("finnhub")) {
            return lower.contains("market news") ? api.finnhubMarketNews() : api.finnhubStockNews(afterKeyword(input, "stock news"));
        }
        if (lower.contains("nutrition") || lower.contains("calories") || lower.contains("calorie")) {
            return api.nutrition(afterKeyword(input, "nutrition"));
        }
        if (lower.contains("city info") || lower.startsWith("city ")) {
            return api.cityInfo(lower.startsWith("city ") ? input.substring(5) : afterKeyword(input, "city info"));
        }
        if (lower.contains("fact") || lower.contains("tell me something")) {
            return api.randomFact();
        }
        if (lower.contains("exercise") || lower.contains("workout")) {
            return api.exercises(afterKeyword(input, "exercise"));
        }
        if (lower.contains("global holiday") || lower.contains("calendarific")) {
            return api.globalHolidays(afterKeyword(input, "global holiday"));
        }
        if (lower.contains("satellite") || lower.contains("earth image") || lower.contains("nasa earth")) {
            return api.nasaEarth(afterKeyword(input, "earth"));
        }
        if (lower.contains("iss") || lower.contains("space station")) {
            return api.nasaIss();
        }
        if (lower.contains("nasa library") || lower.contains("nasa image")) {
            return api.nasaLibrary(afterKeyword(input, "nasa"));
        }
        if (lower.contains("company profile") || lower.contains("company info")) {
            return api.finnhubCompany(afterKeyword(input, "company"));
        }
        if (lower.contains("financial") || lower.contains("pe ratio") || lower.contains("eps")) {
            return api.finnhubFinancials(afterKeyword(input, "financial"));
        }
        if (lower.contains("forex") || lower.contains("eur usd") || lower.contains("exchange rate")) {
            return api.finnhubForex(afterKeyword(input, "forex"));
        }
        if (lower.contains("ip lookup") || lower.contains("my ip") || lower.contains("ip address")) {
            return api.ipLookup(afterKeyword(input, "ip"));
        }
        if (lower.contains("sentiment") || lower.contains("analyze this")) {
            return api.sentiment(afterKeyword(input, "sentiment"));
        }
        if (lower.contains("email validate") || lower.contains("verify email")) {
            return api.emailValidate(afterKeyword(input, "email"));
        }
        if (lower.contains("holiday type")) {
            return api.holidayTypes(afterKeyword(input, "holiday"));
        }
        if (lower.contains("calculate") || lower.contains("what is ") && (lower.contains("+") || lower.contains("-") || lower.contains("*") || lower.contains("/"))) {
            for (String prefix : new String[]{"calculate ", "what is "}) {
                if (lower.startsWith(prefix)) {
                    return api.calculator(input.substring(prefix.length()).trim());
                }
            }
        }
        if (lower.contains("speed test") || lower.contains("speedtest")) {
            return api.speedTest();
        }
        if (lower.contains("disk") || lower.contains("storage space")) {
            return api.diskAnalyzer();
        }
        if (lower.contains("movie") && (lower.contains("recommend") || lower.contains("suggest"))) {
            return api.movieRecommendations("", "");
        }
        if (lower.contains("pomodoro") || lower.contains("focus mode")) {
            return api.focusMode(25);
        }
        if (lower.contains("calendar") || lower.contains("events today") || lower.contains("my schedule")) {
            return api.calendarEvents();
        }
        if (lower.contains("theme") || lower.contains("customize jarvis")) {
            return api.customThemes();
        }
        if (lower.contains("turn on") || lower.contains("turn off")) {
            String device = "lights";
            String action = lower.contains("turn off") ? "off" : "on";
            if (lower.contains("fan")) device = "fan";
            if (lower.contains("ac") || lower.contains("cooler")) device = "AC";
            return api.smartHomeControl(device, action);
        }
        if (lower.contains("did you know") || lower.contains("tell me something") || lower.contains("interesting fact") || lower.contains("fun fact")) {
            return api.educationalFact();
        }
        return api.chat(input);
    }

    private String pluginStatus() throws Exception {
        JSONArray plugins = new JSONArray();
        plugins.put(plugin("Vision", "Camera image analysis through Gemini Vision", "ready"));
        plugins.put(plugin("OCR", "Extract text from selected images through Gemini Vision", "ready"));
        plugins.put(plugin("File AI", "Read selected text files and summarize with AI", "ready"));
        plugins.put(plugin("Browser Agent", "Open URLs and run web/search/API tools", "ready"));
        plugins.put(plugin("Local LLM", "Kept cloud-first to stay lightweight", "not_loaded"));
        return plugins.toString(2);
    }

    private JSONObject plugin(String name, String description, String status) throws Exception {
        return new JSONObject()
                .put("name", name)
                .put("description", description)
                .put("status", status);
    }

    private String firstLine(String text, String fallback) {
        if (text == null || text.trim().isEmpty()) {
            return fallback;
        }
        String first = text.trim().split("\\r?\\n", 2)[0];
        return first.length() > 80 ? first.substring(0, 80) : first;
    }

    private String afterKeyword(String input, String keyword) {
        int idx = input.toLowerCase().indexOf(keyword);
        if (idx < 0) {
            return "";
        }
        return input.substring(idx + keyword.length()).replace("in ", "").replace("for ", "").trim();
    }

    private int parseInt(String text, int fallback) {
        try {
            return Integer.parseInt(text.trim());
        } catch (Exception e) {
            return fallback;
        }
    }
}
