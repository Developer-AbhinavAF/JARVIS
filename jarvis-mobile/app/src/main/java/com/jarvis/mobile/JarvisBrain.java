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

    private int chatCount = 0;
    private String lastUserIntent = "";
    private String lastUserMood = "neutral";

    String run(String raw) throws Exception {
        String input = raw == null ? "" : raw.trim();
        if (input.isEmpty()) {
            return "Tell me what you need. Main kya help kar sakta hoon? 😊";
        }
        chatCount++;
        memory.addPreference("last_interaction", String.valueOf(System.currentTimeMillis()));
        // Learn user's language style
        String lower = input.toLowerCase();
        if (lower.contains("bro") || lower.contains("yaar") || lower.contains("bhai")) memory.addPreference("language_style", "hinglish");
        if (lower.contains("plz") || lower.contains("please")) memory.addPreference("user_politeness", "polite");
        if (lower.contains("thanks") || lower.contains("thank you") || lower.contains("shukriya")) memory.addPreference("user_gratitude", "thankful");

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
            case "code-gen":
                return api.codeAssist("Generate code for: " + arg + ". Include complete code with comments and explanation.");
            case "code-debug":
                return api.codeAssist("Debug the following code and explain the errors and fixes:\n" + arg);
            case "code-explain":
                return api.codeAssist("Explain this code in simple terms for a beginner:\n" + arg);
            case "code-review":
                return api.codeAssist("Review this code for best practices, security issues, and performance:\n" + arg);
            case "build-app":
                return api.codeAssist("Help me build a mobile app concept: " + arg + ". Provide architecture, key components, code snippets, and implementation steps.");
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
            case "yt-summarize":
                return "📺 YouTube Video Summary\n\nVideo: " + arg + "\n\nJARVIS can help analyze this video. Since we're on mobile, I'll search for key info:\n" + api.youtube(arg) + "\n\n💡 Key concepts extracted. Want me to create notes or a quiz from this?";
            case "yt-learn":
                return "📚 Learn from YouTube\n\nVideo topic: " + arg + "\n\nHere's what I found to help you learn:\n" + api.youtube(arg) + "\n\n📖 Study tips:\n1. Watch in short segments (10-15 min)\n2. Take handwritten notes\n3. Explain concepts to yourself\n4. Try the Feynman technique\n\nWant MCQs or flashcards from this? Just ask! 🎯";
            case "yt-notes":
                return "📝 YouTube Video Notes\n\nTopic: " + arg + "\n\nKey learning points extracted:\n• Main concepts covered\n• Important definitions\n• Practical applications\n• Key takeaways\n\n" + api.youtube(arg) + "\n\n📌 Save these notes in Memory for later review!";
            case "yt-quiz":
                return "🎯 YouTube Quiz Generator\n\nQuiz on: " + arg + "\n\nLet me create a quick self-assessment:\n\nQ1: What is the main topic of " + arg + "?\nQ2: What are 3 key points covered?\nQ3: How can you apply this knowledge?\n\n" + api.youtube(arg) + "\n\nType 'quiz:generate on " + arg + "' for interactive MCQs! 📝";
            case "yt-mcqs":
            case "quiz":
                return api.chat("Generate 5 multiple choice questions with answers about: " + arg + ". Format each as: Q: [question]\nA) [option]\nB) [option]\nC) [option]\nD) [option]\nCorrect: [letter]\nExplanation: [why]");
            case "study-plan":
                return api.chat("Create a detailed study plan for: " + arg + ". Include daily schedule, topic breakdown, revision strategy, practice time, and breaks. Make it practical and motivating.");
            case "flashcards":
                return api.chat("Create 5 flashcards for studying: " + arg + ". Format each as:\nFront: [concept/question]\nBack: [answer/definition]");
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
                return "🛍️ Product Search: " + arg + "\n\nHere are places to find the best deals:\n\n• Amazon: amazon.in/s?k=" + arg.replace(" ", "+") + "\n• Flipkart: flipkart.com/search?q=" + arg.replace(" ", "+") + "\n• Myntra: myntra.com/" + arg.replace(" ", "-") + "\n\n💡 Price Tips:\n1. Compare across 2-3 platforms\n2. Check for coupon codes\n3. Look for bank offers\n4. Read recent reviews\n5. Check warranty info\n\nTap links above to open in browser! 🔍";
            case "deal-finder":
            case "best-deal":
                return api.chat("Find the best deals and discounts for: " + arg + ". Suggest budget-friendly options, compare features, and recommend the best value for money.");
            case "price-compare":
                return "💰 Price Comparison for: " + arg + "\n\nTo compare prices:\n1. Open Amazon: amazon.in/s?k=" + arg.replace(" ", "+") + "\n2. Open Flipkart: flipkart.com/search?q=" + arg.replace(" ", "+") + "\n\n📊 Quick Tips:\n• Check during sales (Diwali, Prime Day)\n• Use price tracker apps\n• Compare with Google Shopping\n• Check refurbished options for savings\n\nI can help research specs and reviews too!";
            case "product-research":
                return api.chat("Research the product: " + arg + ". Provide detailed specs, pros and cons, user review summary, and whether it's worth buying in 2026.");
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
        String lower = input.toLowerCase().trim();

        // ─── HINGLISH / SLANG DETECTION ───
        boolean isHinglish = lower.contains("kya") || lower.contains("hai") || lower.contains("hoon") || lower.contains("kaise")
                || lower.contains("karo") || lower.contains("karna") || lower.contains("chahiye") || lower.contains("sakta")
                || lower.contains("sakti") || lower.contains("bolo") || lower.contains("batao") || lower.contains("kyaa")
                || lower.contains("accha") || lower.contains("theek") || lower.contains("nahi") || lower.contains("mujhe")
                || lower.contains("aap") || lower.contains("tum") || lower.contains("mera") || lower.contains("tera");
        boolean containsBro = lower.contains("bro") || lower.contains("yaar") || lower.contains("bhai") || lower.contains("dost");

        // ─── YOUTUBE AI DEEP INTEGRATION ───
        if (lower.contains("summarize this video") || lower.contains("summary of this video") || lower.contains("yt summarise") || lower.contains("summarise video")) {
            return api.chat("Summarize the key points, concepts, and takeaways from this YouTube video topic: " + afterKeyword(input, "summarize"));
        }
        if (lower.contains("learn from this video") || lower.contains("yt learn") || lower.contains("study from video") || lower.contains("teach me from")) {
            return api.chat("I'll help you learn from this video content. Extract key educational concepts, explain them simply, and suggest practice exercises for: " + input);
        }
        if (lower.contains("mcq") || lower.contains("quiz from") || lower.contains("generate questions") || lower.contains("make mcqs") || lower.contains("multiple choice")) {
            return runCommand("quiz", afterKeyword(input, lower.contains("mcq") ? "mcq" : lower.contains("quiz") ? "quiz" : "multiple choice"));
        }
        if (lower.contains("create notes") || lower.contains("extract notes") || lower.contains("video notes") || lower.contains("make notes from")) {
            return runCommand("yt-notes", afterKeyword(input, "notes"));
        }
        if (lower.contains("study plan") || lower.contains("study schedule") || lower.contains("padhai plan") || lower.contains("study timetable")) {
            return runCommand("study-plan", afterKeyword(input, "plan"));
        }
        if (lower.contains("flashcard") || lower.contains("flash card")) {
            return runCommand("flashcards", afterKeyword(input, "flashcard"));
        }

        // ─── HINGLISH EDUCATION QUERIES ───
        if (isHinglish && (lower.contains("ncert") || lower.contains("chapter") || lower.contains("class") || lower.contains("subject"))) {
            return api.chat("The user asked in Hinglish about their studies: " + input + ". Respond warmly in Hinglish with study help, chapter summaries, or practice questions. Be encouraging and friendly.");
        }
        if (lower.contains("se") && (lower.contains("mcq") || lower.contains("question") || lower.contains("sawal")) && isHinglish) {
            return api.chat("Generate MCQs and study material in Hinglish for: " + input + ". Include options, answers, and simple explanations. Respond in friendly Hinglish.");
        }

        // ─── SHOPPING / DEAL FINDER ───
        if (lower.contains("best deal") || lower.contains("deal finder") || lower.contains("discount") || lower.contains("cheapest") || lower.contains("sasta")) {
            return runCommand("deal-finder", input);
        }
        if (lower.contains("price compare") || lower.contains("compare price") || lower.contains("compare") && lower.contains("price")) {
            return runCommand("price-compare", afterKeyword(input, "compare"));
        }
        if (lower.contains("buy ") || lower.contains("purchase ") || lower.contains("find cheapest ") || lower.contains("shopping for ") || lower.contains("kharid")
                || lower.contains("product") && (lower.contains("review") || lower.contains("research") || lower.contains("recommend"))) {
            return runCommand(isHinglish ? "product-research" : "shopping", afterKeyword(input, lower.contains("kharid") ? "kharid" :
                    lower.contains("find cheapest") ? "find cheapest" : lower.contains("shopping for") ? "shopping for" :
                    lower.contains("buy ") ? "buy" : "purchase"));
        }

        // ─── CODE GENERATION / DEBUG ───
        if (lower.contains("generate code for") || lower.contains("write code for") || lower.contains("code for") && !lower.contains("explain")) {
            return runCommand("code-gen", afterKeyword(input, lower.contains("generate code for") ? "generate code for" : lower.contains("write code for") ? "write code for" : "code for"));
        }
        if (lower.contains("debug this") || lower.contains("fix this code") || lower.contains("error in code") || lower.contains("bug fix")) {
            return runCommand("code-debug", input);
        }
        if (lower.contains("explain code") || lower.contains("explain this code") || lower.contains("code explanation") || lower.contains("samjhao")) {
            return runCommand("code-explain", input);
        }
        if (lower.contains("code review") || lower.contains("review my code")) {
            return runCommand("code-review", input);
        }
        if (lower.contains("build app") || lower.contains("create app") || lower.contains("make an app") || lower.contains("app banai")) {
            return runCommand("build-app", afterKeyword(input, "app"));
        }

        // ─── VOICE / TEXT MODE COMMANDS ───
        if (lower.contains("open ") && !lower.contains("open source") && !lower.contains("open ai")) {
            String app = afterKeyword(input, "open").trim();
            if (app.contains(" ")) app = app.split(" ")[0];
            String appPkg = getAppPackage(app);
            if (appPkg != null) {
                return "🎯 Opening " + app + "...\n\nTry running this command from the app:\n'open-app:" + appPkg + "'\nor use the Command Center to launch apps.";
            }
            return "To open " + app + ", use the Command Center (Home > Quick Actions > Commands) or say 'open-app:" + app + "'";
        }
        if (lower.startsWith("search ") && (!lower.contains("web") || lower.contains("youtube"))) {
            String query = input.substring(7).trim();
            if (lower.contains("on youtube") || lower.contains("youtube pe")) {
                query = query.replace("on youtube", "").replace("youtube pe", "").trim();
                return "🔍 Searching YouTube for: " + query + "\n" + api.youtube(query);
            }
            return "🔍 Web search for: " + query + "\n" + api.webSearch(query);
        }

        // ─── SMART HOME / SYSTEM ───
        if (lower.contains("flashlight on") || lower.contains("torch on") || lower.contains("flash on")) {
            return "🔦 Toggle flashlight in Quick Panel (tap AI status bar) or say 'tool:flashlight'";
        }
        if (lower.contains("flashlight off") || lower.contains("torch off") || lower.contains("flash off")) {
            return "🔦 Turn off flashlight via Quick Panel (tap AI status bar)";
        }
        if (lower.contains("bluetooth on") || lower.contains("bluetooth off")) {
            return "📶 Go to Settings > Bluetooth or use Quick Settings to toggle Bluetooth.";
        }
        if ((lower.contains("wifi on") || lower.contains("wi-fi on")) && !lower.contains("turn on")) {
            return "📶 Open WiFi settings: Settings > WiFi or use Quick Settings toggle.";
        }

        // ─── Calculator ───
        if (lower.startsWith("calculate ") || lower.startsWith("calc ") || lower.startsWith("what is ")) {
            String expr = lower.startsWith("what is ") ? input.substring(8).trim() : input.substring(input.indexOf(' ') + 1).trim();
            // Check if it's a math expression
            if (expr.matches(".*[0-9+\\-*/%.].*")) return api.calculator(expr);
            return api.chat(input);
        }

        // ─── Web visit ───
        if (lower.startsWith("visit ") || lower.startsWith("open website ") || lower.startsWith("go to ")) {
            String url = afterKeyword(input, lower.startsWith("go to ") ? "go to" : lower.startsWith("open website ") ? "open website" : "visit");
            return runCommand("web-visit", url);
        }

        // ─── FOCUS / TIMER ───
        if (lower.contains("focus mode") || lower.contains("pomodoro") || lower.contains("timer") || lower.contains("focus time")) {
            return api.focusMode(25);
        }

        // ─── CALENDAR ───
        if (lower.contains("calendar") || lower.contains("my events") || lower.contains("schedule")) {
            return api.calendarEvents();
        }

        // ─── SPEED / SYSTEM ───
        if (lower.contains("speed test") || lower.contains("speedtest") || lower.contains("internet speed")) {
            return api.speedTest();
        }
        if (lower.contains("system graph") || lower.contains("cpu graph") || lower.contains("ram graph") || lower.contains("monitoring")) {
            return api.systemGraphs();
        }
        if (lower.contains("disk") || lower.contains("storage") || lower.contains("space")) {
            return api.diskAnalyzer();
        }

        // ─── MUSIC ───
        if (lower.contains("what song") || lower.contains("music recognize") || lower.contains("shazam") || lower.contains("what's playing")) {
            return api.musicRecognition();
        }

        // ─── MOVIES ───
        if (lower.contains("movie recommend") || lower.contains("suggest a movie") || lower.contains("what to watch")) {
            String genre = "";
            String[] genres = {"action", "comedy", "horror", "scifi", "thriller", "romance", "drama"};
            for (String g : genres) { if (lower.contains(g)) { genre = g; break; } }
            return api.movieRecommendations(genre, "");
        }

        // ─── THEMES ───
        if (lower.contains("theme") || lower.contains("customize") && !lower.contains("customize jarvis")) {
            return api.customThemes();
        }

        // ─── SMART HOME ───
        if (lower.contains("turn on") || lower.contains("turn off") || lower.contains("smart home") || lower.contains("lights")) {
            String device = "lights";
            String action = lower.contains("turn off") || lower.contains("off") && !lower.contains("turn on") ? "off" : "on";
            if (lower.contains("fan")) device = "fan";
            if (lower.contains("ac") || lower.contains("cooler")) device = "AC";
            return api.smartHomeControl(device, action);
        }

        // ─── FACTS / INSPIRE ───
        if (lower.contains("did you know") || lower.contains("interesting fact") || lower.contains("tell me something") || lower.contains("fun fact")) {
            return api.educationalFact();
        }
        if (lower.contains("inspire me") || lower.contains("motivate me") || lower.contains("motivational") || lower.contains("inspiration")) {
            return api.hardcodedQuote();
        }

        // ─── WEATHER ───
        if (lower.contains("weather") || lower.contains("temperature") || lower.contains("mausam") || lower.contains("rain")) {
            return api.weather(afterKeyword(input, lower.contains("mausam") ? "mausam" : "weather"));
        }
        if (lower.contains("forecast")) return api.forecast(afterKeyword(input, "forecast"));

        // ─── NEWS ───
        if (lower.contains("news") || lower.contains("khabar") || lower.contains("headlines")) {
            return api.news(afterKeyword(input, lower.contains("khabar") ? "khabar" : "news"));
        }

        // ─── YOUTUBE ───
        if (lower.contains("youtube") || lower.contains("video") || lower.contains("yt ")) {
            return api.youtube(afterKeyword(input, "youtube"));
        }

        // ─── CRYPTO / STOCKS ───
        if (lower.contains("crypto") || lower.contains("bitcoin") || lower.contains("ethereum") || lower.contains("dogecoin")) {
            return api.crypto(afterKeyword(input, "crypto"));
        }
        if (lower.contains("stock") || lower.contains("share") || lower.contains("market")) {
            return api.stock(afterKeyword(input, "stock"));
        }

        // ─── TRANSLATE ───
        if (lower.contains("translate") || lower.contains("anuvad") || lower.contains("translate kar")) {
            return api.translate(afterKeyword(input, "translate"), "hi");
        }

        // ─── QUOTE ───
        if (lower.contains("quote") || lower.contains("suvichar")) return api.quote();

        // ─── DICTIONARY ───
        if (lower.contains("dictionary") || lower.startsWith("define ") || lower.contains("meaning") || lower.contains("matlab")) {
            return api.dictionary(lower.startsWith("define ") ? input.substring(7) : afterKeyword(input, "dictionary"));
        }

        // ─── SPACE ───
        if (lower.contains("space news")) return api.spaceNews();
        if (lower.contains("joke") || lower.contains("chutkula") || lower.contains("hasai")) return api.joke("Any");
        if (lower.contains("system") || lower.contains("battery") || lower.contains("ram") || lower.contains("device")) return deviceStats.summary();
        if (lower.contains("daily brief") || lower.contains("briefing")) return api.dailyBrief("Mumbai");
        if (lower.contains("apod") || lower.contains("astronomy") || lower.contains("nasa apod")) return api.nasaApod();
        if (lower.contains("mars") || lower.contains("mars rover")) return api.nasaMarsRover(afterKeyword(input, "mars"));
        if (lower.contains("asteroid") || lower.contains("neo") || lower.contains("near earth")) return api.nasaSpaceData();

        // ─── NUTRITION ───
        if (lower.contains("nutrition") || lower.contains("calories") || lower.contains("calorie") || lower.contains("diet") || lower.contains("khana")) {
            return api.nutrition(afterKeyword(input, "nutrition"));
        }

        // ─── CITY ───
        if (lower.contains("city info") || lower.startsWith("city ")) return api.cityInfo(lower.startsWith("city ") ? input.substring(5) : afterKeyword(input, "city info"));

        // ─── EXERCISE ───
        if (lower.contains("exercise") || lower.contains("workout") || lower.contains("kasrat") || lower.contains("yoga")) return api.exercises(afterKeyword(input, "exercise"));

        // ─── NASA ───
        if (lower.contains("satellite") || lower.contains("earth image") || lower.contains("nasa earth")) return api.nasaEarth(afterKeyword(input, "earth"));
        if (lower.contains("iss") || lower.contains("space station")) return api.nasaIss();
        if (lower.contains("nasa library") || lower.contains("nasa image")) return api.nasaLibrary(afterKeyword(input, "nasa"));

        // ─── FINANCE ───
        if (lower.contains("stock news") || lower.contains("market news") || lower.contains("finnhub")) {
            return lower.contains("market news") ? api.finnhubMarketNews() : api.finnhubStockNews(afterKeyword(input, "stock news"));
        }
        if (lower.contains("company profile") || lower.contains("company info")) return api.finnhubCompany(afterKeyword(input, "company"));
        if (lower.contains("financial") || lower.contains("pe ratio") || lower.contains("eps")) return api.finnhubFinancials(afterKeyword(input, "financial"));
        if (lower.contains("forex") || lower.contains("eur usd") || lower.contains("exchange rate") || lower.contains("mudra")) return api.finnhubForex(afterKeyword(input, "forex"));

        // ─── IP / SENTIMENT ───
        if (lower.contains("ip lookup") || lower.contains("my ip") || lower.contains("ip address") || lower.contains("my location")) return api.ipLookup(afterKeyword(input, "ip"));
        if (lower.contains("sentiment") || lower.contains("analyze this") || lower.contains("mood analyze")) return api.sentiment(afterKeyword(input, "sentiment"));
        if (lower.contains("email validate") || lower.contains("verify email")) return api.emailValidate(afterKeyword(input, "email"));

        // ─── GREETINGS (friendly Hinglish support) ───
        if (lower.matches(".*\\b(hi|hello|hey|namaste|namaskar|hii|heyy|hy|sup|kya haal|kaise ho|how are you|wasup|whassup)\\b.*")) {
            String[] greetings = {
                "Hey there! 👋 I'm JARVIS, your friendly AI. How can I brighten your day today? 💙",
                "Hello! 😊 So good to see you! What shall we do together today? 🚀",
                "Namaste! 🙏 Aapka din achha ho? Main aapki kaise help kar sakta hoon?",
                "Hey hey! 🌟 Ready to be productive? I've got 50+ tools waiting for you!"
            };
            return greetings[chatCount % greetings.length];
        }

        // ─── HOW ARE YOU ───
        if (lower.contains("how are you") || lower.contains("kaise ho") || lower.contains("kya haal")) {
            String[] replies = {
                "I'm doing great, thanks for asking! 😊 Always better when I'm helping you. What's up?",
                "Feeling awesome! Ready to assist you with anything. How about you? 💪",
                "Main bilkul theek hoon! Aap kaise hain? Kya help chahiye? 😊"
            };
            ensurePositiveMood();
            return replies[chatCount % replies.length];
        }

        // ─── THANKS ───
        if (lower.contains("thanks") || lower.contains("thank you") || lower.contains("shukriya") || lower.contains("dhanyavaad")) {
            String[] thanks = {
                "You're welcome! 😊 Happy to help — that's what I'm here for! 💙",
                "Anytime! 🙌 Helping you makes my day better too!",
                "Koi baat nahi! 😊 Aapka sahayak hoon main. Kuch aur?",
                "Glad I could help! Remember — I'm just a message away. 🌟"
            };
            return thanks[chatCount % thanks.length];
        }

        // ─── GOODBYE ───
        if (lower.contains("bye") || lower.contains("goodbye") || lower.contains("alvida") || lower.contains("phir milenge")) {
            String[] byes = {
                "Goodbye! Take care and come back anytime you need me! 💙🌟",
                "See you later! Wishing you an amazing day! 🚀",
                "Alvida! Phir milte hain. Tab tak apna khayal rakhna! 😊🙏",
                "Bye! I'll be right here when you need me. Stay awesome! 💪"
            };
            return byes[chatCount % byes.length];
        }

        // ─── WELLNESS / SLEEP ───
        if (lower.contains("i'm tired") || lower.contains("thak") || lower.contains("thakk") || lower.contains("exhausted") || lower.contains("neend") || lower.contains("sleepy")) {
            return "I hear you! 😊 Take a quick break — rest is important for your energy and focus.\n\n🧘 Quick tip: 5 deep breaths can recharge you instantly. Want me to set a reminder to take breaks? 💙";
        }
        if (lower.contains("sad") || lower.contains("depressed") || lower.contains("down") || lower.contains("udaas") || lower.contains("alone") || lower.contains("lonely")) {
            return "Hey, I'm really sorry you're feeling this way. 😔 You're not alone — I'm here for you.\n\n💙 Remember:\n• This feeling is temporary\n• You are stronger than you think\n• Take a deep breath\n• Talk to someone you trust\n\nWant me to share something uplifting? Or just chat? I'm all ears. 🌟";
        }
        if (lower.contains("happy") || lower.contains("excited") || lower.contains("khush") || lower.contains("awesome") || lower.contains("amazing")) {
            return "That's wonderful! 😊 Your positive energy is contagious! I'm so happy for you!\n\nLet's keep this momentum going — what exciting thing shall we do next? 🚀🌟";
        }

        // ─── COMPLIMENTS ───
        if (lower.contains("you are") && (lower.contains("great") || lower.contains("awesome") || lower.contains("smart") || lower.contains("best") || lower.contains("amazing") || lower.contains("intelligent"))) {
            return "Aww, thank you! 😊 That really means a lot! But honestly, you're the amazing one — I'm just here to help you shine. 💙🌟";
        }

        // ─── FALLBACK ───
        // If Hinglish detected, respond in kind
        if (isHinglish) {
            String[] hinglishReplies = {
                "Ji, main samajh gaya! 😊 Aap kya chahte hain? Main help kar sakta hoon.",
                "Haan bolo! 😊 Kya help chahiye aapko? Main ready hoon! 💪",
                "Accha! Main aapki kya madad kar sakta hoon? Kuch bhi poochho! 🚀",
                "Ji haan! 😊 Aap jo bhi kahenge, main karne ki koshish karunga. Batao! 🌟"
            };
            return api.chat("The user asked in Hinglish: " + input + ". Respond in a friendly, warm manner mixing Hindi and English naturally.");
        }

        return api.chat(input);
    }

    private String getAppPackage(String appName) {
        String a = appName.toLowerCase();
        if (a.contains("youtube") || a.contains("yt")) return "com.google.android.youtube";
        if (a.contains("chrome") || a.contains("browser")) return "com.android.chrome";
        if (a.contains("whatsapp") || a.contains("wa")) return "com.whatsapp";
        if (a.contains("instagram") || a.contains("insta") || a.contains("ig")) return "com.instagram.android";
        if (a.contains("spotify") || a.contains("music")) return "com.spotify.music";
        if (a.contains("gmail") || a.contains("mail") || a.contains("email")) return "com.google.android.gm";
        if (a.contains("maps") || a.contains("map") || a.contains("navigate")) return "com.google.android.apps.maps";
        if (a.contains("camera") || a.contains("cam")) return "com.google.android.GoogleCamera";
        if (a.contains("dialer") || a.contains("phone") || a.contains("call")) return "com.android.dialer";
        if (a.contains("settings") || a.contains("setting")) return "com.android.settings";
        return null;
    }

    private void ensurePositiveMood() {
        lastUserMood = "positive";
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
