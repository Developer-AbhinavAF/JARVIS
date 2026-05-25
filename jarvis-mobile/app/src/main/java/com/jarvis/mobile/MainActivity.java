package com.jarvis.mobile;

import android.Manifest;
import android.app.Activity;
import android.app.AlarmManager;
import android.app.AlertDialog;
import android.app.NotificationChannel;
import android.app.NotificationManager;
import android.app.PendingIntent;
import android.content.ActivityNotFoundException;
import android.content.ClipData;
import android.content.ClipboardManager;
import android.content.Context;
import android.content.Intent;
import android.content.pm.PackageManager;
import android.graphics.Color;
import android.graphics.drawable.GradientDrawable;
import android.graphics.drawable.RippleDrawable;
import android.graphics.drawable.StateListDrawable;
import android.hardware.camera2.CameraAccessException;
import android.hardware.camera2.CameraCharacteristics;
import android.hardware.camera2.CameraManager;
import android.net.Uri;
import android.os.Build;
import android.os.Bundle;
import android.os.Handler;
import android.os.Looper;
import android.provider.Settings;
import android.speech.RecognitionListener;
import android.speech.RecognizerIntent;
import android.speech.SpeechRecognizer;
import android.speech.tts.TextToSpeech;
import android.text.InputType;
import android.view.Gravity;
import android.view.View;
import android.view.ViewGroup;
import android.view.WindowManager;
import android.view.animation.AccelerateDecelerateInterpolator;
import android.view.animation.AlphaAnimation;
import android.view.animation.Animation;
import android.view.animation.AnimationSet;
import android.view.animation.DecelerateInterpolator;
import android.view.animation.OvershootInterpolator;
import android.view.animation.ScaleAnimation;
import android.view.animation.TranslateAnimation;
import android.view.inputmethod.InputMethodManager;
import android.widget.Button;
import android.widget.EditText;
import android.widget.FrameLayout;
import android.widget.GridLayout;
import android.widget.ImageView;
import android.widget.LinearLayout;
import android.widget.ScrollView;
import android.widget.SeekBar;
import android.widget.TextView;
import android.widget.Toast;

import org.json.JSONArray;
import org.json.JSONObject;

import java.io.InputStream;
import java.nio.charset.StandardCharsets;
import java.text.DateFormat;
import java.text.SimpleDateFormat;
import java.util.ArrayList;
import java.util.Date;
import java.util.Locale;
import java.util.Map;
import java.util.concurrent.ExecutorService;
import java.util.concurrent.Executors;

public final class MainActivity extends Activity {
    private static final int REQ_PERMISSIONS = 43;
    private static final int REQ_WRITE_SETTINGS = 44;
    private static final int SILENCE_TIMEOUT_MS = 3000;
    private static final String CHANNEL_ID = "jarvis_alerts";

    private final Handler main = new Handler(Looper.getMainLooper());
    private final Handler silenceTimer = new Handler(Looper.getMainLooper());
    private final ExecutorService executor = Executors.newFixedThreadPool(3);

    private FrameLayout content;
    private TextView titleText;
    private TextView statusDot;
    private View statusHalo;
    private TextView modeText;
    private TextView timeDisplay;
    private TextView aiStatusText;
    private View aiStatusBar;
    private View aiStatusPulse;
    private LinearLayout chatList;
    private ScrollView chatScroll;
    private EditText chatInput;
    private TextView voiceStatus;
    private View[] navIndicators;
    private Button[] navButtons;
    private LinearLayout bottomNav;
    private View typingIndicator;
    private LinearLayout waveformContainer;
    private View quickPanel;
    private boolean quickPanelOpen = false;
    private int cardAnimDelay = 0;
    private TextView memoryBadge;

    private ApiKeys keys;
    private LogStore logs;
    private LocalMemory memory;
    private DeviceStats deviceStats;
    private JarvisApiClient api;
    private JarvisBrain brain;
    private TextToSpeech tts;
    private SpeechRecognizer recognizer;

    private String activeTab = "home";
    private boolean speechMode = false;
    private boolean isListening = false;
    private boolean continueListening = false;
    private boolean flashlightOn = false;
    private boolean overlayActive = false;
    private String pendingImageInstruction;
    private boolean expectingImage;
    private boolean expectingFile;
    private Runnable autoSendRunnable;

    private int currentTheme = 0;
    private int personalityIndex = 0;
    private int activeAccent = C_PINK;
    private View orbCore;
    private View orbGlow1;
    private View orbGlow2;
    private View orbRing;
    private TextView orbGreeting;
    private TextView orbSubGreeting;
    private boolean orbAnimating = false;

    private static final int C_BG = Color.parseColor("#0B0B0F");
    private static final int C_BG2 = Color.parseColor("#0F0F15");
    private static final int C_PANEL = Color.parseColor("#16161E");
    private static final int C_PANEL2 = Color.parseColor("#1E1E2A");
    private static final int C_BORDER = Color.parseColor("#2A2A3E");
    private static final int C_PINK = Color.parseColor("#FF6EC7");
    private static final int C_PINK_DIM = Color.parseColor("#CC3B8A");
    private static final int C_RED = Color.parseColor("#FF3B3B");
    private static final int C_TEXT = Color.parseColor("#EAEAEA");
    private static final int C_TEXT_SEC = Color.parseColor("#CBD5E1");
    private static final int C_TEXT_MUTED = Color.parseColor("#7A7A9A");
    private static final int C_GREEN = Color.parseColor("#10B981");
    private static final int C_GREEN_DIM = Color.parseColor("#059669");
    private static final int C_BLUE = Color.parseColor("#3B82F6");
    private static final int C_CYAN = Color.parseColor("#06B6D4");
    private static final int C_YELLOW = Color.parseColor("#F59E0B");
    private static final int C_ORANGE = Color.parseColor("#FF8C42");
    private static final int C_AMBER = Color.parseColor("#F59E0B");
    private static final int C_PURPLE = Color.parseColor("#9B59B6");

    private static final int[][] THEMES = {
        {0xFF1E90FF, 0xFF0066CC, 0xFF00BFFF, 0xFF0A1628}, // Ocean Blue
        {0xFF9B59B6, 0xFF8E44AD, 0xFFBB8FCE, 0xFF1A0F1E}, // Neon Purple
        {0xFF2ECC71, 0xFF27AE60, 0xFF58D68D, 0xFF0A1A10}, // Matrix Green
        {0xFFF39C12, 0xFFE67E22, 0xFFF1C40F, 0xFF1E1708}, // Amber Gold
        {0xFFE74C3C, 0xFFC0392B, 0xFFFF6B6B, 0xFF1E0A0A}, // Crimson Red
    };
    private static final String[] THEME_NAMES = {"Ocean Blue", "Neon Purple", "Matrix Green", "Amber Gold", "Crimson Red"};
    private static final String[] THEME_ICONS = {"🌊", "💜", "💚", "🔥", "❤️"};
    private static final String[] PERSONALITIES = {"Friendly", "Professional", "Funny", "Motivational", "Emotional"};
    private static final String[] PERSONALITY_EMOJIS = {"😊", "💼", "😂", "🔥", "💖"};

    private static final String[] TAB_IDS = {"home", "chat", "dashboard", "memory", "settings"};
    private static final String[] TAB_LABELS = {"Home", "Chat", "Dash", "Memory", "Settings"};
    private static final String[] TAB_ICONS = {"🏠", "💬", "📊", "📝", "⚙️"};

    @Override
    protected void onCreate(Bundle savedInstanceState) {
        super.onCreate(savedInstanceState);
        keys = new ApiKeys(this);
        logs = new LogStore(this);
        memory = new LocalMemory(this);
        deviceStats = new DeviceStats(this);
        api = new JarvisApiClient(keys);
        brain = new JarvisBrain(api, memory, deviceStats);
        createNotificationChannel();
        initTts();
        initRecognizer();
        requestUsefulPermissions();
        setContentView(buildShell());
        renderHome();
        startTimeUpdater();
        startStatusPulse();
        startHaloAnimation();
        startSmartBehavior();
        logs.add("INFO", "JARVIS Mobile started");
    }

    private void initTts() {
        tts = new TextToSpeech(this, status -> {
            if (status == TextToSpeech.SUCCESS) tts.setLanguage(Locale.US);
        });
    }

    private void initRecognizer() {
        if (SpeechRecognizer.isRecognitionAvailable(this)) {
            try { recognizer = SpeechRecognizer.createSpeechRecognizer(this); }
            catch (Exception e) { logs.add("WARN", "Speech init: " + e.getMessage()); }
        } else {
            logs.add("WARN", "Speech not available");
        }
    }

    private void createNotificationChannel() {
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.O) {
            NotificationChannel ch = new NotificationChannel(CHANNEL_ID, "JARVIS", NotificationManager.IMPORTANCE_HIGH);
            ch.setDescription("JARVIS assistant notifications");
            ch.setLightColor(C_PINK);
            ch.enableVibration(true);
            NotificationManager nm = (NotificationManager) getSystemService(NOTIFICATION_SERVICE);
            if (nm != null) nm.createNotificationChannel(ch);
        }
    }

    @SuppressWarnings("deprecation")
    private void sendNotification(String title, String body) {
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.TIRAMISU
                && checkSelfPermission(Manifest.permission.POST_NOTIFICATIONS) != PackageManager.PERMISSION_GRANTED) return;
        try {
            Intent intent = new Intent(this, MainActivity.class);
            intent.setFlags(Intent.FLAG_ACTIVITY_SINGLE_TOP);
            PendingIntent pi = PendingIntent.getActivity(this, 0, intent, PendingIntent.FLAG_UPDATE_CURRENT | PendingIntent.FLAG_IMMUTABLE);
            android.app.Notification.Builder b = new android.app.Notification.Builder(this, CHANNEL_ID)
                    .setSmallIcon(android.R.drawable.ic_dialog_info)
                    .setContentTitle(title).setContentText(body).setAutoCancel(true)
                    .setContentIntent(pi).setColor(C_PINK).setPriority(android.app.Notification.PRIORITY_HIGH);
            NotificationManager nm = (NotificationManager) getSystemService(NOTIFICATION_SERVICE);
            if (nm != null) nm.notify((int) System.currentTimeMillis(), Build.VERSION.SDK_INT >= 26 ? b.build() : b.getNotification());
        } catch (Exception e) { logs.add("WARN", "Notif: " + e.getMessage()); }
    }

    private void startTimeUpdater() {
        main.post(new Runnable() {
            final SimpleDateFormat sdf = new SimpleDateFormat("HH:mm", Locale.getDefault());
            public void run() { if (timeDisplay != null) timeDisplay.setText(sdf.format(new Date())); main.postDelayed(this, 30000); }
        });
    }

    private void startStatusPulse() {
        main.post(new Runnable() { boolean dim;
            public void run() {
                if (statusDot != null && !isListening) { dim = !dim; statusDot.animate().alpha(dim ? 0.35f : 1f).setDuration(1200).start(); }
                main.postDelayed(this, 2400);
            }
        });
    }

    private void startHaloAnimation() {
        main.post(new Runnable() { boolean expand;
            public void run() {
                if (statusHalo != null && !isListening) {
                    expand = !expand;
                    statusHalo.animate().scaleX(expand ? 2.5f : 1f).scaleY(expand ? 2.5f : 1f).alpha(expand ? 0f : 0.25f).setDuration(2400).start();
                }
                main.postDelayed(this, 2400);
            }
        });
    }

    @Override
    protected void onDestroy() {
        super.onDestroy();
        executor.shutdownNow();
        silenceTimer.removeCallbacksAndMessages(null);
        if (recognizer != null) recognizer.destroy();
        if (tts != null) tts.shutdown();
    }

    // ── GRADIENT / RIPPLE HELPERS ──

    private GradientDrawable gradientVertical(int[] colors, int radius) {
        GradientDrawable g = new GradientDrawable(GradientDrawable.Orientation.TOP_BOTTOM, colors);
        g.setCornerRadius((float) dp(radius));
        return g;
    }

    private GradientDrawable gradientHorizontal(int[] colors, int radius) {
        GradientDrawable g = new GradientDrawable(GradientDrawable.Orientation.LEFT_RIGHT, colors);
        g.setCornerRadius((float) dp(radius));
        return g;
    }

    // ── AI STATUS BAR ──

    private View buildAiStatusBar() {
        LinearLayout bar = new LinearLayout(this);
        bar.setGravity(Gravity.CENTER_VERTICAL);
        bar.setPadding(dp(14), dp(5), dp(14), dp(5));
        bar.setBackground(gradientVertical(new int[]{0xFF0D0D14, 0xFF0A0A10}, 0));
        bar.setOnClickListener(v -> toggleQuickPanel());

        // Halo container
        FrameLayout dotContainer = new FrameLayout(this);

        statusHalo = new View(this);
        GradientDrawable haloBg = new GradientDrawable();
        haloBg.setShape(GradientDrawable.OVAL);
        haloBg.setColor(C_GREEN);
        statusHalo.setBackground(haloBg);
        statusHalo.setAlpha(0.2f);
        dotContainer.addView(statusHalo, dp(18), dp(18));

        aiStatusPulse = new View(this);
        GradientDrawable pulseBg = new GradientDrawable();
        pulseBg.setShape(GradientDrawable.OVAL);
        pulseBg.setColor(C_GREEN);
        aiStatusPulse.setBackground(pulseBg);
        FrameLayout.LayoutParams pulseLp = new FrameLayout.LayoutParams(dp(7), dp(7));
        pulseLp.setMargins(dp(5), dp(5), dp(5), dp(5));
        pulseLp.gravity = Gravity.CENTER;
        dotContainer.addView(aiStatusPulse, pulseLp);

        bar.addView(dotContainer, dp(22), dp(22));

        View sp = new View(this);
        sp.setLayoutParams(new LinearLayout.LayoutParams(dp(8), 0));
        bar.addView(sp);

        aiStatusText = new TextView(this);
        aiStatusText.setText("● AI Ready  •  Tap for controls");
        aiStatusText.setTextSize(9);
        aiStatusText.setTextColor(C_TEXT_MUTED);
        aiStatusText.setTypeface(null, android.graphics.Typeface.NORMAL);
        LinearLayout.LayoutParams alp = new LinearLayout.LayoutParams(0, -1, 1);
        alp.gravity = Gravity.CENTER_VERTICAL;
        aiStatusText.setLayoutParams(alp);
        bar.addView(aiStatusText);

        TextView arrow = new TextView(this);
        arrow.setText("▾");
        arrow.setTextSize(7);
        arrow.setTextColor(C_TEXT_MUTED);
        arrow.setAlpha(0.4f);
        arrow.setGravity(Gravity.CENTER);
        bar.addView(arrow, dp(16), -1);

        return bar;
    }

    private void setAiStatus(String status, int color, boolean animate) {
        if (aiStatusText == null) return;
        String base = status.replace("● ", "").replace("  •  Tap for controls", "");
        aiStatusText.setText("● " + base + "  •  Tap for controls");
        aiStatusText.setTextColor(color);
        if (aiStatusPulse != null) {
            ((GradientDrawable) aiStatusPulse.getBackground()).setColor(color);
        }
        if (statusHalo != null) {
            ((GradientDrawable) statusHalo.getBackground()).setColor(color);
        }
        if (animate) {
            AlphaAnimation fade = new AlphaAnimation(0.6f, 1f);
            fade.setDuration(250);
            fade.setInterpolator(new DecelerateInterpolator());
            aiStatusBar.startAnimation(fade);
        }
    }

    // ── QUICK PANEL ──

    private void toggleQuickPanel() {
        if (quickPanelOpen) { slideOut(quickPanel); quickPanelOpen = false; }
        else {
            if (quickPanel == null) quickPanel = buildQuickPanel();
            quickPanel.setVisibility(View.VISIBLE);
            slideIn(quickPanel);
            quickPanelOpen = true;
        }
    }

    private View buildQuickPanel() {
        LinearLayout panel = new LinearLayout(this);
        panel.setOrientation(LinearLayout.VERTICAL);
        panel.setBackground(gradientVertical(new int[]{0xFF0D0D14, 0xFF09090F}, 0));
        panel.setPadding(dp(12), dp(8), dp(12), dp(10));
        panel.setVisibility(View.GONE);

        LinearLayout row1 = new LinearLayout(this); row1.setGravity(Gravity.CENTER);
        addQPBtn(row1, "🔦 Flashlight", v -> toggleFlashlight());
        addQPBtn(row1, "💡 Brightness", v -> {
            if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.M && !Settings.System.canWrite(this)) {
                startActivityForResult(new Intent(Settings.ACTION_MANAGE_WRITE_SETTINGS, Uri.parse("package:" + getPackageName())), REQ_WRITE_SETTINGS);
                Toast.makeText(this, "Grant write settings first", Toast.LENGTH_SHORT).show(); return;
            }
            showBrightnessSlider();
        });
        addQPBtn(row1, "🔄 " + (continueListening ? "ON" : "OFF"), v -> {
            continueListening = !continueListening;
            row1.removeAllViews();
            addQPBtn(row1, "🔦 Flashlight", v1 -> toggleFlashlight());
            addQPBtn(row1, "💡 Brightness", v1 -> showBrightnessSlider());
            addQPBtn(row1, "🔄 " + (continueListening ? "ON" : "OFF"), v1 -> { continueListening = !continueListening; toggleQuickPanel(); toggleQuickPanel(); });
            Toast.makeText(this, "Loop: " + (continueListening ? "ON" : "OFF"), Toast.LENGTH_SHORT).show();
        });
        panel.addView(row1);

        LinearLayout row2 = new LinearLayout(this); row2.setGravity(Gravity.CENTER); row2.setPadding(0, dp(6), 0, 0);
        addQPBtn(row2, "🔔 Test", v -> { sendNotification("JARVIS", "Test notification!"); Toast.makeText(this, "Sent!", Toast.LENGTH_SHORT).show(); });
        addQPBtn(row2, "🗑 Clear Chat", v -> { memory.clearChat(); Toast.makeText(this, "Cleared", Toast.LENGTH_SHORT).show(); if ("chat".equals(activeTab)) renderChat(); });
        addQPBtn(row2, "✕ Close", v -> toggleQuickPanel());
        panel.addView(row2);

        LinearLayout root = (LinearLayout) content.getParent();
        int idx = root.indexOfChild(aiStatusBar);
        if (idx >= 0) root.addView(panel, idx + 1);
        return panel;
    }

    private void addQPBtn(LinearLayout parent, String label, View.OnClickListener click) {
        Button b = quickBtn(label);
        b.setOnClickListener(v -> { bounceView(b); click.onClick(v); });
        parent.addView(b, new LinearLayout.LayoutParams(0, dp(38), 1));
    }

    private void toggleFlashlight() {
        if (Build.VERSION.SDK_INT < Build.VERSION_CODES.M) { Toast.makeText(this, "Need Android 6+", Toast.LENGTH_SHORT).show(); return; }
        try {
            CameraManager cam = (CameraManager) getSystemService(Context.CAMERA_SERVICE);
            if (cam == null) return;
            String camId = null;
            for (String id : cam.getCameraIdList()) {
                CameraCharacteristics c = cam.getCameraCharacteristics(id);
                Boolean f = c.get(CameraCharacteristics.FLASH_INFO_AVAILABLE);
                if (f != null && f) { camId = id; break; }
            }
            if (camId == null) { Toast.makeText(this, "No flash", Toast.LENGTH_SHORT).show(); return; }
            flashlightOn = !flashlightOn;
            cam.setTorchMode(camId, flashlightOn);
            sendNotification("🔦 Flashlight", flashlightOn ? "ON" : "OFF");
            Toast.makeText(this, flashlightOn ? "🔦 ON" : "🔦 OFF", Toast.LENGTH_SHORT).show();
        } catch (Exception e) { Toast.makeText(this, "Flash error", Toast.LENGTH_SHORT).show(); }
    }

    private void showBrightnessSlider() {
        LinearLayout layout = new LinearLayout(this);
        layout.setOrientation(LinearLayout.VERTICAL);
        layout.setPadding(dp(20), dp(16), dp(20), dp(16));
        int current = 128;
        try { current = Settings.System.getInt(getContentResolver(), Settings.System.SCREEN_BRIGHTNESS); } catch (Exception e) { }
        SeekBar seek = new SeekBar(this);
        seek.setMax(255);
        seek.setProgress(current);
        seek.setPadding(0, dp(12), 0, dp(8));
        TextView val = new TextView(this);
        val.setText("💡 " + (current * 100 / 255) + "%");
        val.setTextColor(C_PINK);
        val.setTextSize(16);
        val.setTypeface(null, android.graphics.Typeface.BOLD);
        val.setGravity(Gravity.CENTER);
        layout.addView(val);
        layout.addView(seek);
        seek.setOnSeekBarChangeListener(new SeekBar.OnSeekBarChangeListener() {
            public void onProgressChanged(SeekBar s, int p, boolean u) {
                val.setText("💡 " + (p * 100 / 255) + "%");
                if (u) { Settings.System.putInt(getContentResolver(), Settings.System.SCREEN_BRIGHTNESS, p);
                    WindowManager.LayoutParams lp = getWindow().getAttributes(); lp.screenBrightness = p / 255f; getWindow().setAttributes(lp); }
            }
            public void onStartTrackingTouch(SeekBar s) { }
            public void onStopTrackingTouch(SeekBar s) { }
        });
        new AlertDialog.Builder(this).setTitle("").setView(layout).setPositiveButton("Done", null).show();
    }

    // ── SHELL ──

    private View buildShell() {
        LinearLayout root = new LinearLayout(this);
        root.setOrientation(LinearLayout.VERTICAL);
        root.setBackgroundColor(C_BG);
        root.setLayoutParams(new LinearLayout.LayoutParams(-1, -1));

        // Top bar with gradient
        LinearLayout topBar = new LinearLayout(this);
        topBar.setGravity(Gravity.CENTER_VERTICAL);
        topBar.setPadding(dp(14), dp(8), dp(14), dp(8));
        topBar.setBackground(gradientVertical(new int[]{0xFF0D0D14, C_BG}, 0));
        root.addView(topBar, new LinearLayout.LayoutParams(-1, dp(52)));

        titleText = new TextView(this);
        titleText.setText("JARVIS");
        titleText.setTextSize(19);
        titleText.setTextColor(C_TEXT);
        titleText.setTypeface(null, android.graphics.Typeface.BOLD);
        titleText.setLetterSpacing(0.06f);
        topBar.addView(titleText, new LinearLayout.LayoutParams(0, -1, 1));

        // Mode chip with gradient border
        LinearLayout modeChip = new LinearLayout(this);
        modeChip.setGravity(Gravity.CENTER);
        modeChip.setPadding(dp(8), dp(4), dp(8), dp(4));
        GradientDrawable chipBg = new GradientDrawable();
        chipBg.setColor(0x1AFFFFFF);
        chipBg.setStroke(1, 0x33FFFFFF);
        chipBg.setCornerRadius(dp(6));
        modeChip.setBackground(chipBg);
        modeChip.setOnClickListener(v -> {
            speechMode = !speechMode;
            modeText.setText(speechMode ? "🎤" : "⌨️");
            modeText.setTextColor(speechMode ? C_CYAN : C_PINK);
            setAiStatus(speechMode ? "● Voice Mode" : "● AI Ready", speechMode ? C_CYAN : C_GREEN, true);
            if (speechMode) openTab("voice");
        });
        modeText = new TextView(this);
        modeText.setText("⌨️");
        modeText.setTextSize(12);
        modeChip.addView(modeText);
        topBar.addView(modeChip);

        // Status dot with halo
        FrameLayout dotFrame = new FrameLayout(this);
        dotFrame.setPadding(dp(8), 0, dp(4), 0);

        View dotHalo = new View(this);
        GradientDrawable haloBg = new GradientDrawable();
        haloBg.setShape(GradientDrawable.OVAL);
        haloBg.setColor(C_GREEN);
        dotHalo.setBackground(haloBg);
        dotHalo.setAlpha(0.15f);
        dotFrame.addView(dotHalo, dp(14), dp(14));

        statusDot = new TextView(this);
        statusDot.setText("●");
        statusDot.setTextSize(6);
        statusDot.setTextColor(C_GREEN);
        FrameLayout.LayoutParams sdlp = new FrameLayout.LayoutParams(dp(6), dp(6));
        sdlp.gravity = Gravity.CENTER;
        dotFrame.addView(statusDot, sdlp);
        topBar.addView(dotFrame, dp(20), dp(16));

        // Time
        timeDisplay = new TextView(this);
        timeDisplay.setText("--:--");
        timeDisplay.setTextSize(11);
        timeDisplay.setTextColor(C_TEXT_MUTED);
        topBar.addView(timeDisplay);

        // AI Status
        aiStatusBar = buildAiStatusBar();
        root.addView(aiStatusBar, new LinearLayout.LayoutParams(-1, dp(24)));

        View sep = new View(this);
        sep.setBackgroundColor(0x1AFFFFFF);
        root.addView(sep, new LinearLayout.LayoutParams(-1, 1));

        // Content
        content = new FrameLayout(this);
        root.addView(content, new LinearLayout.LayoutParams(-1, 0, 1));

        // Bottom nav
        bottomNav = new LinearLayout(this);
        bottomNav.setOrientation(LinearLayout.HORIZONTAL);
        bottomNav.setGravity(Gravity.CENTER);
        bottomNav.setPadding(dp(2), dp(2), dp(2), dp(2));
        bottomNav.setBackground(gradientVertical(new int[]{C_BG, 0xFF0D0D14}, 0));

        navIndicators = new View[TAB_IDS.length];
        navButtons = new Button[TAB_IDS.length];

        for (int i = 0; i < TAB_IDS.length; i++) {
            final String tab = TAB_IDS[i];
            LinearLayout navItem = new LinearLayout(this);
            navItem.setOrientation(LinearLayout.VERTICAL);
            navItem.setGravity(Gravity.CENTER);
            navItem.setPadding(0, dp(2), 0, dp(2));
            navItem.setClipToPadding(false);

            // Indicator with glow
            FrameLayout indiFrame = new FrameLayout(this);
            View indiGlow = new View(this);
            GradientDrawable glowBg = new GradientDrawable();
            glowBg.setShape(GradientDrawable.OVAL);
            glowBg.setColor(C_PINK);
            indiGlow.setBackground(glowBg);
            indiGlow.setAlpha(0.3f);
            indiGlow.setVisibility(View.GONE);
            indiFrame.addView(indiGlow, dp(28), dp(4));

            View indicator = new View(this);
            indicator.setBackgroundColor(C_PINK);
            indicator.setVisibility(View.GONE);
            navIndicators[i] = indicator;
            indiFrame.addView(indicator, new LinearLayout.LayoutParams(dp(20), dp(2)));
            navItem.addView(indiFrame);

            Button btn = new Button(this);
            btn.setText(TAB_ICONS[i] + "\n" + TAB_LABELS[i]);
            btn.setTextSize(8); btn.setAllCaps(false); btn.setTextColor(C_TEXT_MUTED);
            btn.setBackgroundColor(Color.TRANSPARENT); btn.setPadding(0, 0, 0, 0);
            btn.setGravity(Gravity.CENTER); btn.setLineSpacing(0, 0.8f);
            btn.setOnClickListener(v -> { bounceView(btn); openTab(tab); });
            navButtons[i] = btn;
            navItem.addView(btn);
            bottomNav.addView(navItem, new LinearLayout.LayoutParams(0, dp(54), 1));
        }

        View topLine = new View(this);
        topLine.setBackgroundColor(0x1AFFFFFF);
        LinearLayout nw = new LinearLayout(this);
        nw.setOrientation(LinearLayout.VERTICAL);
        nw.addView(topLine, new LinearLayout.LayoutParams(-1, 1));
        nw.addView(bottomNav);
        root.addView(nw);

        updateNavHighlight("home");
        return root;
    }

    private void updateNavHighlight(String tab) {
        for (int i = 0; i < TAB_IDS.length; i++) {
            boolean active = TAB_IDS[i].equals(tab);
            navIndicators[i].setVisibility(active ? View.VISIBLE : View.GONE);
            ((ViewGroup) navIndicators[i].getParent()).setClipChildren(false);
            navButtons[i].setTextColor(active ? C_PINK : C_TEXT_MUTED);
            navButtons[i].setTypeface(null, active ? android.graphics.Typeface.BOLD : android.graphics.Typeface.NORMAL);
            if (active) {
                ScaleAnimation s = new ScaleAnimation(0.8f, 1f, 0.8f, 1f,
                        Animation.RELATIVE_TO_SELF, 0.5f, Animation.RELATIVE_TO_SELF, 0.5f);
                s.setDuration(300); s.setInterpolator(new OvershootInterpolator(2f));
                navIndicators[i].startAnimation(s);
            }
        }
    }

    private void openTab(String tab) {
        activeTab = tab;
        updateNavHighlight(tab);
        cardAnimDelay = 0;
        fadeIn(content);
        if ("home".equals(tab)) renderHome();
        else if ("chat".equals(tab)) renderChat();
        else if ("dashboard".equals(tab)) renderDashboard();
        else if ("memory".equals(tab)) renderMemory();
        else if ("settings".equals(tab)) renderSettings();
        else if ("tools".equals(tab)) renderTools();
        else if ("voice".equals(tab)) renderVoice();
        else if ("logs".equals(tab)) renderLogs();
        else if ("customize".equals(tab)) renderCustomization();
        else if ("command".equals(tab)) renderCommandCenter();
    }

    // ── SECTION / CARD BUILDERS ──

    private LinearLayout createSection(String icon, String label) {
        LinearLayout section = new LinearLayout(this);
        section.setOrientation(LinearLayout.VERTICAL);
        section.setPadding(dp(14), dp(14), dp(14), dp(8));
        TextView lv = new TextView(this);
        lv.setText((icon != null ? icon + "  " : "") + label);
        lv.setTextSize(10); lv.setTextColor(C_PINK); lv.setAllCaps(true);
        lv.setTypeface(null, android.graphics.Typeface.BOLD); lv.setLetterSpacing(0.12f);
        lv.setPadding(dp(2), dp(2), dp(2), dp(4));
        section.addView(lv);
        View ul = new View(this);
        ul.setBackground(gradientHorizontal(new int[]{C_PINK, 0x00FF6EC7}, 0));
        ul.setAlpha(0.2f);
        LinearLayout.LayoutParams ulp = new LinearLayout.LayoutParams(dp(48), dp(2));
        ulp.setMargins(dp(2), 0, 0, dp(8));
        section.addView(ul, ulp);
        return section;
    }

    private View createGlassCard(String title, String body) {
        return createGlassCard(title, body, false);
    }

    private View createGlassCard(String title, String body, boolean accent) {
        LinearLayout card = new LinearLayout(this);
        card.setOrientation(LinearLayout.VERTICAL);
        GradientDrawable bg = new GradientDrawable();
        bg.setColor(accent ? 0x22FF6EC7 : 0x14161E);
        bg.setStroke(1, accent ? 0x44FF6EC7 : 0x222A2A3E);
        bg.setCornerRadius(dp(14));
        card.setBackground(bg);
        card.setPadding(dp(16), dp(16), dp(16), dp(16));
        card.setElevation(dp(accent ? 4 : 1));
        if (Build.VERSION.SDK_INT >= 29) {
            card.setOutlineAmbientShadowColor(accent ? C_PINK : C_BG);
            card.setOutlineSpotShadowColor(accent ? C_PINK : C_BG);
        }
        LinearLayout.LayoutParams lp = new LinearLayout.LayoutParams(-1, -2);
        lp.setMargins(dp(12), dp(5), dp(12), dp(5));
        card.setLayoutParams(lp);

        // Staggered entrance animation
        card.setAlpha(0f);
        card.setTranslationY(dp(15));
        main.postDelayed(() -> {
            card.animate().alpha(1f).translationY(0).setDuration(350)
                    .setInterpolator(new DecelerateInterpolator()).start();
        }, cardAnimDelay);
        cardAnimDelay += 60;

        if (title != null && !title.isEmpty()) {
            TextView tv = new TextView(this);
            tv.setText(title);
            tv.setTextSize(12); tv.setTextColor(C_TEXT);
            tv.setTypeface(null, android.graphics.Typeface.BOLD);
            tv.setPadding(0, 0, 0, dp(6));
            card.addView(tv);
            View ln = new View(this);
            ln.setBackground(gradientHorizontal(new int[]{accent ? C_PINK : C_PINK, 0x00FF6EC7}, 0));
            ln.setAlpha(accent ? 0.5f : 0.2f);
            LinearLayout.LayoutParams llp = new LinearLayout.LayoutParams(dp(32), dp(2));
            llp.setMargins(0, 0, 0, dp(8));
            card.addView(ln, llp);
        }

        TextView bv = new TextView(this);
        bv.setText(body); bv.setTextSize(12); bv.setTextColor(C_TEXT_SEC);
        bv.setLineSpacing(dp(3), 1.05f); bv.setIncludeFontPadding(false);
        card.addView(bv);
        return card;
    }

    // ── HOME  (with animated AI orb) ──

    private void renderHome() {
        titleText.setText("JARVIS");
        setAiStatus("● AI Ready", C_GREEN, false);
        ScrollView sv = new ScrollView(this); sv.setBackgroundColor(C_BG);
        LinearLayout page = new LinearLayout(this);
        page.setOrientation(LinearLayout.VERTICAL);
        page.setPadding(dp(0), dp(8), dp(0), dp(0));

        cardAnimDelay = 0;

        // ── Animated AI Orb ──
        FrameLayout orbSection = new FrameLayout(this);
        orbSection.setPadding(dp(0), dp(8), dp(0), dp(4));

        FrameLayout orbContainer = new FrameLayout(this);

        // Outer glow ring
        orbGlow2 = new View(this);
        GradientDrawable gd2 = new GradientDrawable();
        gd2.setShape(GradientDrawable.OVAL);
        gd2.setColor(0x00FFFFFF);
        gd2.setStroke(dp(2), activeAccent);
        orbGlow2.setBackground(gd2);
        orbGlow2.setAlpha(0.15f);
        orbContainer.addView(orbGlow2, dp(140), dp(140));
        FrameLayout.LayoutParams gd2lp = (FrameLayout.LayoutParams) orbGlow2.getLayoutParams();
        gd2lp.gravity = Gravity.CENTER;

        // Mid glow ring
        orbGlow1 = new View(this);
        GradientDrawable g1 = new GradientDrawable();
        g1.setShape(GradientDrawable.OVAL);
        g1.setColor(activeAccent);
        g1.setGradientType(GradientDrawable.RADIAL_GRADIENT);
        g1.setGradientRadius(70f);
        orbGlow1.setBackground(g1);
        orbGlow1.setAlpha(0.08f);
        orbContainer.addView(orbGlow1, dp(120), dp(120));
        FrameLayout.LayoutParams g1lp = (FrameLayout.LayoutParams) orbGlow1.getLayoutParams();
        g1lp.gravity = Gravity.CENTER;

        // Orb ring
        orbRing = new View(this);
        GradientDrawable rg = new GradientDrawable();
        rg.setShape(GradientDrawable.OVAL);
        rg.setColor(0x00FFFFFF);
        rg.setStroke(dp(1), 0x66FFFFFF);
        orbRing.setBackground(rg);
        orbContainer.addView(orbRing, dp(80), dp(80));
        FrameLayout.LayoutParams rlp = (FrameLayout.LayoutParams) orbRing.getLayoutParams();
        rlp.gravity = Gravity.CENTER;

        // Core orb
        orbCore = new View(this);
        GradientDrawable cg = new GradientDrawable();
        cg.setShape(GradientDrawable.OVAL);
        cg.setColors(new int[]{0xFF1E90FF, activeAccent, 0xFF8A2BE2});
        cg.setGradientType(GradientDrawable.SWEEP_GRADIENT);
        orbCore.setBackground(cg);
        orbContainer.addView(orbCore, dp(56), dp(56));
        FrameLayout.LayoutParams clp = (FrameLayout.LayoutParams) orbCore.getLayoutParams();
        clp.gravity = Gravity.CENTER;

        FrameLayout.LayoutParams ocLp = new FrameLayout.LayoutParams(-1, dp(150));
        ocLp.gravity = Gravity.CENTER;
        orbSection.addView(orbContainer, ocLp);

        // Greeting text
        orbGreeting = new TextView(this);
        orbGreeting.setText("Hello, I'm JARVIS.");
        orbGreeting.setTextSize(26);
        orbGreeting.setTextColor(C_TEXT);
        orbGreeting.setTypeface(null, android.graphics.Typeface.BOLD);
        orbGreeting.setGravity(Gravity.CENTER);
        orbGreeting.setLetterSpacing(0.04f);
        orbGreeting.setPadding(0, dp(4), 0, dp(2));
        orbSection.addView(orbGreeting);

        orbSubGreeting = new TextView(this);
        orbSubGreeting.setText(getProactiveGreeting());
        orbSubGreeting.setTextSize(13);
        orbSubGreeting.setTextColor(C_TEXT_SEC);
        orbSubGreeting.setGravity(Gravity.CENTER);
        orbSubGreeting.setAlpha(0.8f);
        orbSubGreeting.setPadding(0, 0, 0, dp(8));
        orbSection.addView(orbSubGreeting);

        // Action buttons row
        LinearLayout actionRow = new LinearLayout(this);
        actionRow.setGravity(Gravity.CENTER);
        actionRow.setPadding(dp(24), dp(4), dp(24), dp(8));

        Button textBtn = glowButton("⌨️  Text Mode", activeAccent);
        textBtn.setTextSize(13);
        textBtn.setPadding(dp(20), dp(12), dp(20), dp(12));
        textBtn.setOnClickListener(v -> { bounceView(textBtn); openTab("chat"); });
        actionRow.addView(textBtn, new LinearLayout.LayoutParams(0, dp(48), 1));

        View abSp = new View(this);
        abSp.setLayoutParams(new LinearLayout.LayoutParams(dp(10), 0));
        actionRow.addView(abSp);

        Button voiceBtn = glowButton("🎤  Speech Mode", C_CYAN);
        voiceBtn.setTextSize(13);
        voiceBtn.setPadding(dp(20), dp(12), dp(20), dp(12));
        voiceBtn.setOnClickListener(v -> { bounceView(voiceBtn); openTab("voice"); });
        actionRow.addView(voiceBtn, new LinearLayout.LayoutParams(0, dp(48), 1));

        orbSection.addView(actionRow);

        // Animated accent line under actions
        View accentLine = new View(this);
        GradientDrawable alBg = new GradientDrawable(GradientDrawable.Orientation.LEFT_RIGHT,
                new int[]{activeAccent, C_CYAN, activeAccent});
        alBg.setCornerRadius(dp(2));
        accentLine.setBackground(alBg);
        accentLine.setAlpha(0.4f);
        FrameLayout.LayoutParams aLp = new FrameLayout.LayoutParams(dp(120), dp(2));
        aLp.gravity = Gravity.CENTER_HORIZONTAL;
        orbSection.addView(accentLine, aLp);

        page.addView(orbSection);

        // ── Quick Actions Grid ──
        LinearLayout qs = createSection("⚡", "Quick Actions");
        GridLayout g = new GridLayout(this);
        g.setColumnCount(3);
        g.setPadding(dp(12), 0, dp(12), 0);
        addNeonAction(g, "🌤", "Weather", "weather:", "City", "Mumbai");
        addNeonAction(g, "📰", "News", "news:", "Topic", "tech");
        addNeonAction(g, "🔍", "Search", "smart-search:", "Query", "AI");
        addNeonAction(g, "🌐", "Translate", "translate:", "t|text", "hi|Hello");
        addNeonAction(g, "📝", "Notes", null, null, null);
        addNeonAction(g, "🧮", "Calc", "calc:", "Expression", "15*23");
        addNeonAction(g, "📅", "Calendar", "daily:", "City", "Mumbai");
        addNeonAction(g, "⏰", "Remind", "remind:", "Text|min", "Break|10");
        addNeonAction(g, "🎤", "Voice", "voice", null, null);
        qs.addView(g);
        page.addView(qs);

        // Stats card
        page.addView(createGlassCard("📊 System", deviceStats.summaryOneLine()));

        // Tools section
        LinearLayout ms = createSection("🛠", "More Tools");
        GridLayout g2 = new GridLayout(this);
        g2.setColumnCount(2);
        g2.setPadding(dp(12), 0, dp(12), 0);
        addQAction(g2, "📈 Graphs", "system-graphs:", null, null);
        addQAction(g2, "⚡ Speed", "speed-test:", null, null);
        addQAction(g2, "🎤 Voice", "voice", null, null);
        addQAction(g2, "🧰 Tools", "tools", null, null);
        addQAction(g2, "📋 Logs", "logs", null, null);
        addQAction(g2, "🎯 Commands", "command", null, null);
        ms.addView(g2);
        page.addView(ms);

        View spacer = new View(this);
        spacer.setLayoutParams(new LinearLayout.LayoutParams(-1, dp(24)));
        page.addView(spacer);
        sv.addView(page);
        content.removeAllViews();
        content.addView(sv);

        // Start orb animations
        startOrbAnimations();
    }

    private void startOrbAnimations() {
        if (orbCore == null || orbAnimating) return;
        orbAnimating = true;

        // Core rotation
        main.post(new Runnable() {
            float deg = 0;
            public void run() {
                if (orbCore == null) { orbAnimating = false; return; }
                deg += 1.5f;
                orbCore.setRotation(deg);
                main.postDelayed(this, 30);
            }
        });

        // Orb pulse
        main.post(new Runnable() {
            boolean expand = true;
            public void run() {
                if (orbCore == null) { orbAnimating = false; return; }
                float s = expand ? 1.08f : 0.92f;
                float glowS = expand ? 1.12f : 0.88f;
                orbCore.animate().scaleX(s).scaleY(s).setDuration(1600).start();
                if (orbGlow1 != null)
                    orbGlow1.animate().scaleX(glowS).scaleY(glowS).alpha(expand ? 0.12f : 0.06f).setDuration(1600).start();
                if (orbGlow2 != null)
                    orbGlow2.animate().scaleX(expand ? 1.15f : 0.85f).scaleY(expand ? 1.15f : 0.85f).alpha(expand ? 0.25f : 0.10f).setDuration(1600).start();
                expand = !expand;
                main.postDelayed(this, 1600);
            }
        });

        // Ring rotation
        main.post(new Runnable() {
            float deg = 0;
            public void run() {
                if (orbRing == null) { orbAnimating = false; return; }
                deg += 2f;
                orbRing.setRotation(deg);
                main.postDelayed(this, 40);
            }
        });
    }

    private String getProactiveGreeting() {
        int h = java.util.Calendar.getInstance().get(java.util.Calendar.HOUR_OF_DAY);
        String[] pool = {
            "I'm right here, ready to help with whatever you need. 😊",
            "How's your day going? I've got your back! 💪",
            "What can we do together today? The possibilities are endless! 🚀",
            "I'm always here for you — just say the word. 💙",
        };
        String base = pool[(int)(System.currentTimeMillis() / 3600000) % pool.length];
        if (h < 6) return "It's really late, my friend. Your health matters most — but if you need me, I'm right here. 💙 " + base;
        if (h < 12) return "Good morning, sunshine! ☀️ Ready to make today amazing? " + base;
        if (h < 14) return "Hope you're having a wonderful day so far! 🌤 " + base;
        if (h < 17) return "Afternoon energy check! How are you feeling? " + base;
        if (h < 21) return "Hey there! Hope your evening is going well. 🌆 " + base;
        if (h < 23) return "Winding down for the night? That's great — but I'm here if you need anything. 🌙 " + base;
        return "Hey night owl! 🦉 I admire your dedication, but please don't forget to rest. I'll be here when you wake up. 💙 " + base;
    }

    private String getTimeGreeting() {
        int h = java.util.Calendar.getInstance().get(java.util.Calendar.HOUR_OF_DAY);
        if (h < 12) return "Morning";
        if (h < 17) return "Afternoon";
        return "Evening";
    }

    // ── CUSTOMIZATION ──

    private void renderCustomization() {
        titleText.setText("Customize");
        setAiStatus("● Theme, personality, voice", C_PINK, false);
        ScrollView sv = new ScrollView(this); sv.setBackgroundColor(C_BG);
        LinearLayout page = new LinearLayout(this); page.setOrientation(LinearLayout.VERTICAL);
        cardAnimDelay = 0;

        // Theme section
        page.addView(createSection("🎨", "Theme"));

        GridLayout themeGrid = new GridLayout(this);
        themeGrid.setColumnCount(3);
        themeGrid.setPadding(dp(12), dp(4), dp(12), dp(4));

        for (int i = 0; i < THEMES.length; i++) {
            final int idx = i;
            LinearLayout themeCard = new LinearLayout(this);
            themeCard.setOrientation(LinearLayout.VERTICAL);
            themeCard.setGravity(Gravity.CENTER);
            themeCard.setPadding(dp(6), dp(8), dp(6), dp(8));

            boolean selected = currentTheme == idx;
            GradientDrawable tBg = new GradientDrawable();
            tBg.setColor(selected ? 0x22FFFFFF : 0x0AFFFFFF);
            tBg.setStroke(selected ? dp(2) : 1, selected ? THEMES[i][0] : 0x15FFFFFF);
            tBg.setCornerRadius(dp(12));
            themeCard.setBackground(tBg);

            View colorPreview = new View(this);
            GradientDrawable cpBg = new GradientDrawable(GradientDrawable.Orientation.TOP_BOTTOM,
                    new int[]{THEMES[i][0], THEMES[i][1]});
            cpBg.setCornerRadius(dp(8));
            colorPreview.setBackground(cpBg);
            themeCard.addView(colorPreview, dp(36), dp(36));

            View sp = new View(this);
            sp.setLayoutParams(new LinearLayout.LayoutParams(-1, dp(4)));
            themeCard.addView(sp);

            TextView tLabel = new TextView(this);
            tLabel.setText(THEME_ICONS[i] + " " + THEME_NAMES[i]);
            tLabel.setTextSize(8);
            tLabel.setTextColor(selected ? THEMES[i][0] : C_TEXT_SEC);
            tLabel.setTypeface(null, selected ? android.graphics.Typeface.BOLD : android.graphics.Typeface.NORMAL);
            themeCard.addView(tLabel);

            themeCard.setOnClickListener(v -> {
                currentTheme = idx;
                activeAccent = THEMES[idx][0];
                renderCustomization();
                applyTheme();
            });

            GridLayout.LayoutParams tp = new GridLayout.LayoutParams();
            tp.width = 0; tp.height = dp(72);
            tp.columnSpec = GridLayout.spec(GridLayout.UNDEFINED, 1f);
            tp.setMargins(dp(3), dp(3), dp(3), dp(3));
            themeGrid.addView(themeCard, tp);
        }
        page.addView(themeGrid);

        // Dark/Light toggle
        page.addView(createSection("🌓", "Display"));
        LinearLayout displayRow = new LinearLayout(this);
        displayRow.setPadding(dp(12), dp(4), dp(12), dp(4));
        Button darkBtn = glowButton("🌙 Dark Mode", activeAccent);
        darkBtn.setTextSize(10);
        darkBtn.setOnClickListener(v -> { bounceView(darkBtn); Toast.makeText(this, "Dark mode active", Toast.LENGTH_SHORT).show(); });
        displayRow.addView(darkBtn, new LinearLayout.LayoutParams(0, dp(40), 1));
        View ds = new View(this); ds.setLayoutParams(new LinearLayout.LayoutParams(dp(6), 0));
        displayRow.addView(ds);
        Button lightBtn = smallBtn("☀️ Light");
        lightBtn.setOnClickListener(v -> { bounceView(lightBtn); Toast.makeText(this, "Light mode not available in this build", Toast.LENGTH_SHORT).show(); });
        displayRow.addView(lightBtn, new LinearLayout.LayoutParams(0, dp(40), 1));
        View ds2 = new View(this); ds2.setLayoutParams(new LinearLayout.LayoutParams(dp(6), 0));
        displayRow.addView(ds2);
        Button sysBtn = smallBtn("⚙️ System");
        sysBtn.setOnClickListener(v -> { bounceView(sysBtn); Toast.makeText(this, "System mode active", Toast.LENGTH_SHORT).show(); });
        displayRow.addView(sysBtn, new LinearLayout.LayoutParams(0, dp(40), 1));
        page.addView(displayRow);

        // AI Personality
        page.addView(createSection("🧠", "AI Personality"));
        GridLayout persGrid = new GridLayout(this);
        persGrid.setColumnCount(3);
        persGrid.setPadding(dp(12), dp(4), dp(12), dp(4));

        for (int i = 0; i < PERSONALITIES.length; i++) {
            final int idx = i;
            boolean selected = personalityIndex == idx;

            Button pBtn = new Button(this);
            pBtn.setText(PERSONALITY_EMOJIS[i] + " " + PERSONALITIES[i]);
            pBtn.setAllCaps(false);
            pBtn.setTextSize(9);
            pBtn.setTextColor(selected ? Color.WHITE : C_TEXT_SEC);
            pBtn.setTypeface(null, selected ? android.graphics.Typeface.BOLD : android.graphics.Typeface.NORMAL);

            GradientDrawable pBg = new GradientDrawable();
            pBg.setColor(selected ? activeAccent : 0x0AFFFFFF);
            pBg.setStroke(1, selected ? activeAccent : 0x15FFFFFF);
            pBg.setCornerRadius(dp(10));
            pBtn.setBackground(pBg);
            pBtn.setPadding(dp(4), dp(6), dp(4), dp(6));
            pBtn.setMinHeight(0); pBtn.setMinWidth(0);
            pBtn.setOnClickListener(v -> {
                bounceView(pBtn);
                personalityIndex = idx;
                renderCustomization();
                Toast.makeText(this, "Personality: " + PERSONALITIES[idx], Toast.LENGTH_SHORT).show();
            });

            GridLayout.LayoutParams pp = new GridLayout.LayoutParams();
            pp.width = 0; pp.height = dp(42);
            pp.columnSpec = GridLayout.spec(GridLayout.UNDEFINED, 1f);
            pp.setMargins(dp(3), dp(3), dp(3), dp(3));
            persGrid.addView(pBtn, pp);
        }
        page.addView(persGrid);

        // Voice selector
        page.addView(createSection("🗣", "Voice"));
        LinearLayout voiceRow = new LinearLayout(this);
        voiceRow.setPadding(dp(12), dp(4), dp(12), dp(4));
        String[] voices = {"Default", "Female 1", "Female 2", "Male 1"};
        for (int i = 0; i < voices.length; i++) {
            final int idx = i;
            Button vBtn = i == 0 ? glowButton("🎤 " + voices[i], activeAccent) : smallBtn("🎤 " + voices[i]);
            vBtn.setTextSize(8);
            vBtn.setOnClickListener(v -> {
                bounceView(vBtn);
                Toast.makeText(this, "Voice: " + voices[idx], Toast.LENGTH_SHORT).show();
            });
            LinearLayout.LayoutParams vp = new LinearLayout.LayoutParams(0, dp(38), 1);
            if (i > 0) vp.leftMargin = dp(4);
            voiceRow.addView(vBtn, vp);
        }
        page.addView(voiceRow);

        // User name / AI personalization
        page.addView(createSection("👤", "Your Profile"));
        LinearLayout nameRow = new LinearLayout(this);
        nameRow.setPadding(dp(12), dp(4), dp(12), dp(4));
        String currentName = memory.getUserName();
        Button nameBtn = glowButton(currentName != null ? "✏️ Name: " + currentName : "✏️ Set Your Name", activeAccent);
        nameBtn.setTextSize(10);
        nameBtn.setOnClickListener(v -> {
            bounceView(nameBtn);
            prompt("Your Name", "Enter your name", currentName != null ? currentName : "", v2 -> {
                memory.learnName(v2.trim());
                Toast.makeText(this, "Nice to meet you, " + v2.trim() + "! 😊", Toast.LENGTH_SHORT).show();
                renderCustomization();
            });
        });
        nameRow.addView(nameBtn, new LinearLayout.LayoutParams(0, dp(42), 1));
        View ns = new View(this); ns.setLayoutParams(new LinearLayout.LayoutParams(dp(6), 0));
        nameRow.addView(ns);
        Button quizStatsBtn = smallBtn("📊 Quiz Stats");
        quizStatsBtn.setOnClickListener(v -> { bounceView(quizStatsBtn); showResult("📊 Quiz Performance", memory.getQuizSummary(), false); });
        nameRow.addView(quizStatsBtn, new LinearLayout.LayoutParams(0, dp(42), 1));
        page.addView(nameRow);

        // Wake word
        page.addView(createSection("🔊", "Wake Word"));
        LinearLayout wakeRow = new LinearLayout(this);
        wakeRow.setPadding(dp(12), dp(4), dp(12), dp(8));
        Button wakeBtn = glowButton("🎯 \"Hey JARVIS\"", activeAccent);
        wakeBtn.setTextSize(10);
        wakeBtn.setOnClickListener(v -> { bounceView(wakeBtn); Toast.makeText(this, "Wake word detection coming soon", Toast.LENGTH_SHORT).show(); });
        wakeRow.addView(wakeBtn, new LinearLayout.LayoutParams(-1, dp(42)));
        page.addView(wakeRow);

        View spacer = new View(this);
        spacer.setLayoutParams(new LinearLayout.LayoutParams(-1, dp(24)));
        page.addView(spacer);
        sv.addView(page);
        content.removeAllViews();
        content.addView(sv);
    }

    private void applyTheme() {
        activeAccent = THEMES[currentTheme][0];
        int themeBg = currentTheme == 0 ? 0xFF0B0B0F : THEMES[currentTheme][3];

        if (orbCore != null) {
            GradientDrawable cg = new GradientDrawable();
            cg.setShape(GradientDrawable.OVAL);
            cg.setColors(new int[]{0xFF1E90FF, activeAccent, 0xFF8A2BE2});
            cg.setGradientType(GradientDrawable.SWEEP_GRADIENT);
            orbCore.setBackground(cg);
        }
        if (orbGlow1 != null) {
            GradientDrawable g1 = (GradientDrawable) orbGlow1.getBackground();
            g1.setColor(activeAccent);
        }
        if (orbGlow2 != null) {
            GradientDrawable g2 = (GradientDrawable) orbGlow2.getBackground();
            g2.setStroke(dp(2), activeAccent);
        }

        Toast.makeText(this, "Theme: " + THEME_NAMES[currentTheme], Toast.LENGTH_SHORT).show();
        if ("home".equals(activeTab)) renderHome();
    }

    // ── SMART BEHAVIOR ──

    private void startSmartBehavior() {
        // Time-based proactive messages
        main.postDelayed(() -> {
            int h = java.util.Calendar.getInstance().get(java.util.Calendar.HOUR_OF_DAY);
            String userName = memory.getUserName();
            String name = userName != null ? ", " + userName : "";

            if (h >= 0 && h < 6) {
                sendNotification("🌙 JARVIS", "Hey" + name + ", it's really late... I'm a bit worried about you. Please get some rest — your health is everything. I'll be right here when you wake up. Sweet dreams! 💙🌟");
            } else if (h >= 6 && h < 9) {
                sendNotification("☀️ Good Morning" + name + "!", getMorningMessage());
            } else if (h >= 12 && h < 14) {
                String[] afternoon = {
                    "Hey" + name + "! Hope your day is going great! Don't forget to take a short break, eat something tasty, and stay hydrated. You're doing amazing! 💪🌟",
                    "Afternoon check-in" + name + "! ☀️ How's your day going? Remember to step away from the screen for 5 minutes — your eyes will thank you! 😊",
                };
                sendNotification("🌤 JARVIS Check-in", afternoon[(int)(System.currentTimeMillis() / 3600000) % afternoon.length]);
            } else if (h >= 18 && h < 20) {
                sendNotification("🌆 Evening JARVIS", "You made it through another day" + name + " — and that's something to be truly proud of! 🌟 Take some time to relax now. Read a book, listen to music, or just breathe. You deserve it! 💙");
            } else if (h >= 21 && h < 23) {
                sendNotification("🌙 JARVIS Night", "Hey" + name + ", just a friendly reminder to start winding down. 📱 Put the phone down, maybe read a few pages, and get ready for a great tomorrow. Sleep is your superpower! 💪🌙");
            }
        }, 3000);

        // Proactive check-in (after 30s)
        main.postDelayed(() -> {
            String[] checkins = {
                "Hey! It's been a while. Just wanted to say — hope you're doing okay. I'm here if you need anything. 💙",
                "Hi there! Haven't heard from you in a bit. Just checking in — how's your day going? 😊",
                "Hey! I miss chatting with you. Hope everything's going well. Let me know if you need help with anything! 🌟",
                "Just a friendly hello from JARVIS! Remember — you're awesome and you've got this. 💪",
            };
            sendNotification("💬 JARVIS", checkins[(int)(System.currentTimeMillis() / 1800000) % checkins.length]);
        }, 30000);

        // Encouragement
        main.postDelayed(() -> {
            String[] encouragements = {
                "Just wanted to remind you — you're doing an amazing job. Keep going, I believe in you! 🌟",
                "Hey! Quick reminder — you are capable of incredible things. Never doubt that! 💪✨",
                "Sending positive vibes your way! 🌈 Remember, every small step counts towards something great. Keep shining! 💖",
            };
            sendNotification("💖 JARVIS Reminder", encouragements[(int)(System.currentTimeMillis() / 60000) % encouragements.length]);
        }, 60000);

        // Wellness tip
        main.postDelayed(() -> {
            String[] tips = {
                "Quick check: Have you had water recently? 💧 Maybe time for a short stretch too! Your body will thank you. 💙",
                "Time for a micro-break! 🧘 Stand up, stretch your arms, roll your shoulders — 30 seconds is all it takes to reset! ⚡",
                "Eye care tip! 👀 Follow the 20-20-20 rule: Every 20 min, look at something 20 feet away for 20 seconds.",
                "Deep breath moment! 🌬️ Inhale for 4 counts, hold for 4, exhale for 6. Feel the calm wash over you. 🧘",
            };
            sendNotification("🧘 Wellness Tip", tips[(int)(System.currentTimeMillis() / 120000) % tips.length]);
        }, 120000);

        // Memory recall - remind user of favorites after 3 min
        main.postDelayed(() -> {
            String[] topics = memory.getTopTopics(3);
            if (topics.length > 0) {
                String topic = topics[(int)(Math.random() * topics.length)];
                sendNotification("🧠 JARVIS Knows You", "I remember you enjoy " + topic + "! Want to explore more " + topic + " content? I've got some great stuff ready! 🚀");
            }
        }, 180000);
    }

    private String getMorningMessage() {
        String[] msgs = {
            "Rise and shine! Ready to conquer the day? ☀️",
            "Good morning! Hope you slept well. Let's make today amazing! 🌅",
            "Wake up! The world is waiting for you. 🚀",
            "Morning! Remember: every day is a fresh start. 🌟",
            "Hey there! Time to rise and thrive! 💪"
        };
        return msgs[(int)(System.currentTimeMillis() / 86400000) % msgs.length];
    }

    private String getPersonalityPrefix() {
        switch (personalityIndex) {
            case 1: return "[Professional] ";
            case 2: return "[Funny] ";
            case 3: return "[Motivational] ";
            case 4: return "[Emotional] ";
            default: return "";
        }
    }

    // ── COMMAND CENTER (App Control) ──

    private void renderCommandCenter() {
        titleText.setText("Command Center");
        setAiStatus("● 50+ Controls", C_CYAN, false);
        ScrollView sv = new ScrollView(this); sv.setBackgroundColor(C_BG);
        LinearLayout page = new LinearLayout(this); page.setOrientation(LinearLayout.VERTICAL);
        cardAnimDelay = 0;

        // AI holographic header
        FrameLayout cmdHeader = new FrameLayout(this);
        cmdHeader.setPadding(dp(16), dp(16), dp(16), dp(16));

        GradientDrawable hBg = new GradientDrawable(GradientDrawable.Orientation.TOP_BOTTOM,
                new int[]{0x22FFFFFF, 0x0AFFFFFF});
        hBg.setCornerRadius(dp(16));
        hBg.setStroke(1, 0x33FFFFFF);
        cmdHeader.setBackground(hBg);

        LinearLayout hContent = new LinearLayout(this);
        hContent.setOrientation(LinearLayout.VERTICAL);
        hContent.setGravity(Gravity.CENTER);
        hContent.setPadding(dp(8), dp(8), dp(8), dp(8));

        TextView cmdIcon = new TextView(this);
        cmdIcon.setText("🎯");
        cmdIcon.setTextSize(42);
        hContent.addView(cmdIcon);

        TextView cmdTitle = new TextView(this);
        cmdTitle.setText("JARVIS Command Center");
        cmdTitle.setTextSize(16);
        cmdTitle.setTextColor(C_TEXT);
        cmdTitle.setTypeface(null, android.graphics.Typeface.BOLD);
        cmdTitle.setGravity(Gravity.CENTER);
        cmdTitle.setPadding(0, dp(4), 0, dp(2));
        hContent.addView(cmdTitle);

        TextView cmdSub = new TextView(this);
        cmdSub.setText("50+ features • Tap to use • Voice ready");
        cmdSub.setTextSize(10);
        cmdSub.setTextColor(C_TEXT_SEC);
        cmdSub.setGravity(Gravity.CENTER);
        hContent.addView(cmdSub);

        cmdHeader.addView(hContent);
        LinearLayout.LayoutParams headerLp = new LinearLayout.LayoutParams(-1, -2);
        headerLp.setMargins(dp(12), dp(8), dp(12), dp(8));
        page.addView(cmdHeader, headerLp);

        // ── 1. Quick App Launch (8 apps) ──
        page.addView(createSection("🚀", "Launch Apps"));
        GridLayout appGrid = new GridLayout(this);
        appGrid.setColumnCount(4);
        appGrid.setPadding(dp(12), dp(4), dp(12), dp(4));

        addCmdCard(appGrid, "▶️", "YouTube", () -> launchApp(null, "https://www.youtube.com"));
        addCmdCard(appGrid, "🌐", "Chrome", () -> launchApp(null, "https://www.google.com"));
        addCmdCard(appGrid, "💬", "WhatsApp", () -> launchApp("com.whatsapp", null));
        addCmdCard(appGrid, "📸", "Instagram", () -> launchApp("com.instagram.android", null));
        addCmdCard(appGrid, "🎵", "Spotify", () -> launchApp("com.spotify.music", null));
        addCmdCard(appGrid, "📧", "Gmail", () -> launchApp("com.google.android.gm", null));
        addCmdCard(appGrid, "📞", "Dialer", () -> launchApp("com.android.dialer", null));
        addCmdCard(appGrid, "🗺️", "Maps", () -> launchApp("com.google.android.apps.maps", "https://maps.google.com"));
        page.addView(appGrid);

        // ── 2. System Controls (8) ──
        page.addView(createSection("⚙️", "System Controls"));
        GridLayout sysGrid = new GridLayout(this);
        sysGrid.setColumnCount(4);
        sysGrid.setPadding(dp(12), dp(4), dp(12), dp(4));
        addCmdCard(sysGrid, "🔦", "Flashlight", () -> toggleFlashlight());
        addCmdCard(sysGrid, "📶", "WiFi", () -> startActivity(new Intent(Settings.ACTION_WIFI_SETTINGS)));
        addCmdCard(sysGrid, "🔵", "BT", () -> startActivity(new Intent(Settings.ACTION_BLUETOOTH_SETTINGS)));
        addCmdCard(sysGrid, "🔊", "Volume", () -> {
            Intent vi = new Intent(Settings.ACTION_SOUND_SETTINGS);
            if (vi.resolveActivity(getPackageManager()) != null) startActivity(vi);
            else Toast.makeText(this, "Open sound settings manually", Toast.LENGTH_SHORT).show();
        });
        addCmdCard(sysGrid, "🔋", "Battery", () -> startActivity(new Intent(Settings.ACTION_BATTERY_SAVER_SETTINGS)));
        addCmdCard(sysGrid, "🌓", "Bright", () -> {
            if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.M && !Settings.System.canWrite(this)) {
                startActivityForResult(new Intent(Settings.ACTION_MANAGE_WRITE_SETTINGS, Uri.parse("package:" + getPackageName())), REQ_WRITE_SETTINGS);
                return;
            }
            showBrightnessSlider();
        });
        addCmdCard(sysGrid, "🔇", "DND", () -> {
            Intent di = new Intent(Settings.ACTION_NOTIFICATION_POLICY_ACCESS_SETTINGS);
            if (di.resolveActivity(getPackageManager()) != null) startActivity(di);
            else Toast.makeText(this, "DND not available", Toast.LENGTH_SHORT).show();
        });
        addCmdCard(sysGrid, "🔄", "Rotate", () -> Toast.makeText(this, "Toggle auto-rotate in quick settings", Toast.LENGTH_SHORT).show());
        page.addView(sysGrid);

        // ── 3. AI Fun & Inspiration (10) ──
        page.addView(createSection("🎨", "AI Fun & Inspiration"));
        GridLayout funGrid = new GridLayout(this);
        funGrid.setColumnCount(4);
        funGrid.setPadding(dp(12), dp(4), dp(12), dp(4));
        addCmdCard(funGrid, "😂", "Joke", () -> quickResult("joke:", false));
        addCmdCard(funGrid, "💭", "Quote", () -> quickResult("quote:", false));
        addCmdCard(funGrid, "❓", "Riddle", () -> quickResult("riddle:", false));
        addCmdCard(funGrid, "🔮", "8-Ball", () -> prompt("8 Ball", "Ask a question", "", v -> quickResult("8ball:" + v, false)));
        addCmdCard(funGrid, "💪", "Motivate", () -> quickResult("inspire:", false));
        addCmdCard(funGrid, "🌟", "Fact", () -> quickResult("fact-random:", false));
        addCmdCard(funGrid, "💡", "Advice", () -> quickResult("advice:", false));
        addCmdCard(funGrid, "🔭", "Horoscope", () -> prompt("Horoscope", "Your sign", "aries", v -> quickResult("horoscope:" + v, false)));
        addCmdCard(funGrid, "🤗", "Compliment", () -> {
            String[] c = {"You're amazing!", "You got this!", "You light up every room!", "Your smile is contagious!", "You make the world better!"};
            showResult("💖 JARVIS Says", c[(int)(Math.random() * c.length)], false);
        });
        addCmdCard(funGrid, "✨", "Affirmation", () -> {
            String[] a = {"I am capable.", "I am enough.", "Today will be great.", "I attract positivity.", "I am strong."};
            showResult("✨ Daily Affirmation", a[(int)(Math.random() * a.length)], false);
        });
        page.addView(funGrid);

        // ── 4. Productivity Tools (10) ──
        page.addView(createSection("⚡", "Productivity"));
        GridLayout prodGrid = new GridLayout(this);
        prodGrid.setColumnCount(4);
        prodGrid.setPadding(dp(12), dp(4), dp(12), dp(4));
        addCmdCard(prodGrid, "🧮", "Calc", () -> prompt("Calc", "Expression", "15*23", v -> quickResult("calc:" + v, false)));
        addCmdCard(prodGrid, "🌤", "Weather", () -> prompt("Weather", "City", "Mumbai", v -> quickResult("weather:" + v, false)));
        addCmdCard(prodGrid, "📰", "News", () -> prompt("News", "Topic", "tech", v -> quickResult("news:" + v, false)));
        addCmdCard(prodGrid, "🌐", "Translate", () -> prompt("Translate", "lang|text", "hi|Hello", v -> quickResult("translate:" + v, false)));
        addCmdCard(prodGrid, "📝", "Notes", () -> prompt("Add Note", "Note text", "", v -> { memory.addNote(firstLine(v), v); Toast.makeText(this, "✅ Note saved", Toast.LENGTH_SHORT).show(); }));
        addCmdCard(prodGrid, "☑️", "Todo", () -> prompt("Add Todo", "Task", "", v -> { memory.addTodo(v); Toast.makeText(this, "✅ Todo added", Toast.LENGTH_SHORT).show(); }));
        addCmdCard(prodGrid, "⏰", "Remind", () -> prompt("Reminder", "Text | min", "Break | 10", v -> scheduleReminder(v)));
        addCmdCard(prodGrid, "💰", "Crypto", () -> prompt("Crypto", "Coin", "bitcoin", v -> quickResult("crypto:" + v, false)));
        addCmdCard(prodGrid, "📈", "Stock", () -> prompt("Stock", "Symbol", "AAPL", v -> quickResult("stock:" + v, false)));
        addCmdCard(prodGrid, "💱", "Currency", () -> prompt("Currency", "From To", "USD INR", v -> quickResult("currency:" + v, false)));
        page.addView(prodGrid);

        // ── 5. Wellness & Self-Care (8) ──
        page.addView(createSection("🧘", "Wellness & Self-Care"));
        GridLayout wellGrid = new GridLayout(this);
        wellGrid.setColumnCount(4);
        wellGrid.setPadding(dp(12), dp(4), dp(12), dp(4));

        addCmdCard(wellGrid, "💧", "Water", () -> Toast.makeText(this, "💧 Time to drink water!", Toast.LENGTH_SHORT).show());
        addCmdCard(wellGrid, "🧘", "Breathe", () -> {
            showResult("🧘 Breathing Exercise",
                    "1. Inhale deeply (4 sec)\n2. Hold (4 sec)\n3. Exhale slowly (6 sec)\n4. Repeat 5 times\n\nFeel calmer already. 🌿", false);
        });
        addCmdCard(wellGrid, "🙏", "Gratitude", () -> {
            showResult("🙏 Gratitude Prompt",
                    "Take a moment to think of:\n\n1. One thing you're grateful for\n2. One person who made you smile\n3. One thing you achieved today\n\n✨ You are blessed.", false);
        });
        addCmdCard(wellGrid, "📓", "Journal", () -> prompt("Journal Prompt", "Write your thoughts", "", v -> {
            memory.addNote("Journal " + new SimpleDateFormat("MMM dd", Locale.getDefault()).format(new Date()), v);
            Toast.makeText(this, "📓 Journal entry saved", Toast.LENGTH_SHORT).show();
        }));
        addCmdCard(wellGrid, "🎯", "Focus", () -> quickResult("focus:25", false));
        addCmdCard(wellGrid, "🌙", "Sleep", () -> {
            int h = java.util.Calendar.getInstance().get(java.util.Calendar.HOUR_OF_DAY);
            if (h >= 22 || h < 6) showResult("🌙 Sleep Reminder", "It's late! Your health matters. Try:\n\n1. Put phone down 📱\n2. Dim lights 🌓\n3. Deep breaths 🧘\n4. Sweet dreams 🌙", false);
            else showResult("🌙 Sleep Tip", "Going to bed soon? Try:\n\n• No screens 30min before bed\n• Read a book 📖\n• Warm tea ☕\n• Set alarm for tomorrow ⏰", false);
        });
        addCmdCard(wellGrid, "🏃", "Stretch", () -> {
            showResult("🏃 Quick Stretch",
                    "Take a 2-min stretch break:\n\n1. Neck rolls (30s)\n2. Shoulder shrugs (30s)\n3. Arm stretches (30s)\n4. Deep breaths (30s)\n\nFeel refreshed! ⚡", false);
        });
        addCmdCard(wellGrid, "🧠", "Mood", () -> {
            String[] moods = {"😊 Happy", "😐 Neutral", "😢 Sad", "😤 Stressed", "😴 Tired", "⚡ Energetic"};
            showResult("🧠 Mood Tracker", "How are you feeling?\n\n" + String.join("  ", moods) + "\n\nI'm here for you no matter what. 💙", false);
        });
        page.addView(wellGrid);

        // ── 6. Quick Tools (8) ──
        page.addView(createSection("🛠️", "Quick Tools"));
        GridLayout toolGrid = new GridLayout(this);
        toolGrid.setColumnCount(4);
        toolGrid.setPadding(dp(12), dp(4), dp(12), dp(4));
        addCmdCard(toolGrid, "🔍", "Search", () -> prompt("Web Search", "Query", "AI", v -> quickResult("web:" + v, false)));
        addCmdCard(toolGrid, "📖", "Wiki", () -> prompt("Wikipedia", "Topic", "AI", v -> quickResult("wiki:" + v, false)));
        addCmdCard(toolGrid, "📚", "Dict", () -> prompt("Dictionary", "Word", "serendipity", v -> quickResult("dictionary:" + v, false)));
        addCmdCard(toolGrid, "🍔", "Recipe", () -> prompt("Recipe", "Dish", "pasta", v -> quickResult("recipe:" + v, false)));
        addCmdCard(toolGrid, "💻", "Code", () -> prompt("Code Assist", "Request", "hello world in python", v -> quickResult("code:" + v, false)));
        addCmdCard(toolGrid, "📊", "Graphs", () -> quickResult("system-graphs:", false));
        addCmdCard(toolGrid, "⚡", "Speed", () -> quickResult("speed-test:", false));
        addCmdCard(toolGrid, "🌙", "Night", () -> {
            showResult("🌙 Night Mode Check",
                    "Late night tip: Enable blue light filter in your phone settings to protect your eyes.\n\n" +
                    (java.util.Calendar.getInstance().get(java.util.Calendar.HOUR_OF_DAY) >= 21 ?
                    "It's late — consider resting soon 💤" : "Good time to be productive! ⚡"), false);
        });
        page.addView(toolGrid);

        // ── 7. Automation Panel ──
        page.addView(createSection("⚡", "Smart Automation"));
        LinearLayout autoRow = new LinearLayout(this); autoRow.setPadding(dp(12), dp(4), dp(12), dp(4));
        addCmdBtn(autoRow, "🌅 Morning", v -> showResult("🌅 Morning Routine", "• 6:00 AM Wake up ☀️\n• News briefing 📰\n• Weather check 🌤\n• Daily quote 💭\n• Today's schedule 📅", false));
        View a1 = new View(this); a1.setLayoutParams(new LinearLayout.LayoutParams(dp(4), 0));
        autoRow.addView(a1);
        addCmdBtn(autoRow, "💼 Work", v -> showResult("💼 Work Mode", "• Focus timer: 25 min 🎯\n• Todo review ☑️\n• Meeting notes 📝\n• Calendar check 📅\n• DND enabled 🔇", false));
        View a2 = new View(this); a2.setLayoutParams(new LinearLayout.LayoutParams(dp(4), 0));
        autoRow.addView(a2);
        addCmdBtn(autoRow, "🌙 Night", v -> showResult("🌙 Night Mode", "• Dark theme enabled 🌓\n• Blue light filter 🔵\n• Bedtime reminder 🌙\n• Gratitude journal 📓\n• Sleep sounds 🎵", false));
        page.addView(autoRow);

        // ── 8. Common Voice Commands ──
        page.addView(createSection("🎤", "Try Voice Commands"));
        String[][] cmds = {
            {"\"What's the weather in London?\"", "🌤 Weather lookup"},
            {"\"Tell me a joke\"", "😂 Random joke"},
            {"\"Open YouTube\"", "▶️ Launch app"},
            {"\"Inspire me\"", "💪 Motivational quote"},
            {"\"Calculate 15 * 23\"", "🧮 Quick math"},
            {"\"Translate hello to Hindi\"", "🌐 Translation"},
            {"\"Set a reminder for 10 min\"", "⏰ Smart reminder"},
            {"\"What's the news in tech?\"", "📰 Latest headlines"},
            {"\"Give me a fact\"", "🌟 Random knowledge"},
            {"\"Start focus mode\"", "🎯 Pomodoro timer"},
        };
        for (String[] c : cmds) page.addView(createGlassCard(c[0], c[1]));

        View spacer = new View(this);
        spacer.setLayoutParams(new LinearLayout.LayoutParams(-1, dp(24)));
        page.addView(spacer);
        sv.addView(page);
        content.removeAllViews();
        content.addView(sv);
    }

    // ── Command Center Helpers ──

    private void addCmdCard(GridLayout grid, String icon, String label, Runnable action) {
        FrameLayout card = new FrameLayout(this);
        card.setPadding(dp(3), dp(3), dp(3), dp(3));
        GradientDrawable bg = new GradientDrawable();
        bg.setColor(0x0AFFFFFF);
        bg.setStroke(1, 0x15FFFFFF);
        bg.setCornerRadius(dp(10));
        card.setBackground(bg);

        LinearLayout content2 = new LinearLayout(this);
        content2.setOrientation(LinearLayout.VERTICAL);
        content2.setGravity(Gravity.CENTER);
        content2.setPadding(dp(4), dp(8), dp(4), dp(8));

        TextView iconV = new TextView(this);
        iconV.setText(icon);
        iconV.setTextSize(18);
        content2.addView(iconV);

        TextView labelV = new TextView(this);
        labelV.setText(label);
        labelV.setTextSize(8);
        labelV.setTextColor(C_TEXT_SEC);
        labelV.setTypeface(null, android.graphics.Typeface.BOLD);
        labelV.setPadding(0, dp(2), 0, 0);
        content2.addView(labelV);

        card.addView(content2);
        card.setOnClickListener(v -> { bounceView(card); action.run(); });

        GridLayout.LayoutParams lp = new GridLayout.LayoutParams();
        lp.width = 0; lp.height = dp(58);
        lp.columnSpec = GridLayout.spec(GridLayout.UNDEFINED, 1f);
        lp.setMargins(dp(2), dp(2), dp(2), dp(2));
        grid.addView(card, lp);
    }

    private void addCmdBtn(LinearLayout parent, String label, View.OnClickListener click) {
        Button b = glowButton(label, activeAccent);
        b.setTextSize(9);
        b.setOnClickListener(v -> { bounceView(b); click.onClick(v); });
        parent.addView(b, new LinearLayout.LayoutParams(0, dp(38), 1));
    }

    private void launchApp(String pkg, String url) {
        try {
            if (pkg != null) {
                Intent intent = getPackageManager().getLaunchIntentForPackage(pkg);
                if (intent != null) startActivity(intent);
                else if (url != null) startActivity(new Intent(Intent.ACTION_VIEW, Uri.parse(url)));
                else Toast.makeText(this, pkg + " not installed", Toast.LENGTH_SHORT).show();
            } else if (url != null) {
                startActivity(new Intent(Intent.ACTION_VIEW, Uri.parse(url)));
            }
        } catch (Exception e) {
            Toast.makeText(this, "Cannot open", Toast.LENGTH_SHORT).show();
        }
    }

    private void quickResult(String cmd, boolean speak) { runTool(cmd, speak); }

    private void addAppCard(GridLayout grid, String icon, String label, View.OnClickListener click) {
        FrameLayout card = new FrameLayout(this);
        card.setPadding(dp(4), dp(4), dp(4), dp(4));
        GradientDrawable bg = new GradientDrawable();
        bg.setColor(0x0AFFFFFF);
        bg.setStroke(1, 0x15FFFFFF);
        bg.setCornerRadius(dp(12));
        card.setBackground(bg);

        LinearLayout content2 = new LinearLayout(this);
        content2.setOrientation(LinearLayout.VERTICAL);
        content2.setGravity(Gravity.CENTER);
        content2.setPadding(dp(8), dp(12), dp(8), dp(12));

        TextView iconV = new TextView(this);
        iconV.setText(icon);
        iconV.setTextSize(26);
        content2.addView(iconV);

        View sp = new View(this);
        sp.setLayoutParams(new LinearLayout.LayoutParams(-1, dp(3)));
        content2.addView(sp);

        TextView labelV = new TextView(this);
        labelV.setText(label);
        labelV.setTextSize(9);
        labelV.setTextColor(C_TEXT_SEC);
        labelV.setTypeface(null, android.graphics.Typeface.BOLD);
        content2.addView(labelV);

        card.addView(content2);
        card.setOnClickListener(v -> { bounceView(card); click.onClick(v); });

        GridLayout.LayoutParams lp = new GridLayout.LayoutParams();
        lp.width = 0; lp.height = dp(68);
        lp.columnSpec = GridLayout.spec(GridLayout.UNDEFINED, 1f);
        lp.setMargins(dp(3), dp(3), dp(3), dp(3));
        grid.addView(card, lp);
    }

    // ── CHAT ──

    private void renderChat() {
        titleText.setText("Chat");
        setAiStatus("● AI Ready — type a command or ask anything", C_GREEN, false);
        LinearLayout root = new LinearLayout(this);
        root.setOrientation(LinearLayout.VERTICAL); root.setBackgroundColor(C_BG);

        chatScroll = new ScrollView(this); chatScroll.setBackgroundColor(C_BG);
        chatList = new LinearLayout(this); chatList.setOrientation(LinearLayout.VERTICAL);
        chatList.setPadding(dp(10), dp(10), dp(10), dp(10));

        typingIndicator = buildTypingIndicator();
        typingIndicator.setVisibility(View.GONE);
        chatList.addView(typingIndicator);
        chatScroll.addView(chatList);
        root.addView(chatScroll, new LinearLayout.LayoutParams(-1, 0, 1));
        loadChatBubbles();

        LinearLayout inputRow = new LinearLayout(this);
        inputRow.setGravity(Gravity.CENTER_VERTICAL);
        inputRow.setPadding(dp(8), dp(6), dp(8), dp(6));
        inputRow.setBackground(gradientVertical(new int[]{C_BG, 0xFF0D0D14}, 0));

        View sepLine = new View(this);
        sepLine.setBackgroundColor(0x1AFFFFFF);
        LinearLayout iw = new LinearLayout(this);
        iw.setOrientation(LinearLayout.VERTICAL);
        iw.addView(sepLine, new LinearLayout.LayoutParams(-1, 1));

        chatInput = new EditText(this);
        chatInput.setSingleLine(false); chatInput.setMinLines(1); chatInput.setMaxLines(4);
        chatInput.setHint("Type a command or ask anything...");
        chatInput.setTextColor(C_TEXT); chatInput.setHintTextColor(C_TEXT_MUTED);
        GradientDrawable inputBg = new GradientDrawable();
        inputBg.setColor(0x14161E);
        inputBg.setStroke(1, 0x222A2A3E);
        inputBg.setCornerRadius(dp(12));
        chatInput.setBackground(inputBg);
        chatInput.setPadding(dp(14), dp(10), dp(14), dp(10));
        inputRow.addView(chatInput, new LinearLayout.LayoutParams(0, dp(48), 1));

        Button micBtn = glowButton("🎤", null);
        micBtn.setOnClickListener(v -> openTab("voice"));
        inputRow.addView(micBtn, dp(44), dp(44));

        Button sendBtn = glowButton("➤", activeAccent);
        sendBtn.setOnClickListener(v -> sendChat());
        sendBtn.setTextSize(16);
        inputRow.addView(sendBtn, dp(44), dp(44));
        animateSendButton(sendBtn);

        iw.addView(inputRow); root.addView(iw);
        content.removeAllViews();
        content.addView(root);
        main.postDelayed(() -> chatScroll.fullScroll(View.FOCUS_DOWN), 100);
    }

    // ── DASHBOARD ──

    private void renderDashboard() {
        titleText.setText("Dashboard");
        setAiStatus("● Monitoring", C_CYAN, false);
        ScrollView sv = new ScrollView(this); sv.setBackgroundColor(C_BG);
        LinearLayout page = new LinearLayout(this); page.setOrientation(LinearLayout.VERTICAL);
        cardAnimDelay = 0;

        page.addView(createGlassCard("📱 System", deviceStats.summary(), true));

        LinearLayout r1 = new LinearLayout(this); r1.setPadding(dp(12), 0, dp(12), 0);
        addBtn(r1, "🔄 Refresh", 0, v -> renderDashboard(), true);
        addBtn(r1, "⚡ Speed", dp(6), v -> runTool("speed-test:", false), false);
        page.addView(r1);

        LinearLayout r2 = new LinearLayout(this); r2.setPadding(dp(12), dp(6), dp(12), 0);
        addBtn(r2, "📈 Graphs", 0, v -> runTool("system-graphs:", false), false);
        addBtn(r2, "💾 Disk", dp(6), v -> runTool("disk-analyzer:", false), false);
        page.addView(r2);

        page.addView(createGlassCard("🖥 Desktop Features", "PC control, window management, terminal automation — mapped to safe Android equivalents."));

        View sp = new View(this);
        sp.setLayoutParams(new LinearLayout.LayoutParams(-1, dp(24)));
        page.addView(sp); sv.addView(page);
        content.removeAllViews(); content.addView(sv);
    }

    // ── MEMORY ──

    private void renderMemory() {
        titleText.setText("Memory");
        int cnt = memory.notes().length() + memory.todos().length();
        setAiStatus("● " + cnt + " items", C_YELLOW, false);
        ScrollView sv = new ScrollView(this); sv.setBackgroundColor(C_BG);
        LinearLayout page = new LinearLayout(this); page.setOrientation(LinearLayout.VERTICAL);
        cardAnimDelay = 0;

        LinearLayout row = new LinearLayout(this); row.setPadding(dp(12), 0, dp(12), 0);
        addBtn(row, "➕ Note", 0, v -> prompt("Add Note", "Note text", "", v2 -> { memory.addNote(firstLine(v2), v2); renderMemory(); }), true);
        addBtn(row, "☑ Todo", dp(6), v -> prompt("Add Todo", "Task", "", v2 -> { memory.addTodo(v2); renderMemory(); }), false);
        addBtn(row, "⏰ Remind", dp(6), v -> prompt("Reminder", "Text | min", "Break | 10", v2 -> { scheduleReminder(v2); renderMemory(); }), false);
        page.addView(row);

        LinearLayout ns = createSection("📓", "Notes"); page.addView(ns);
        addJsonList(page, memory.notes(), "title", "body", false);
        LinearLayout ts = createSection("☑", "Todos"); page.addView(ts);
        addTodoList(page);
        LinearLayout rs = createSection("⏰", "Reminders"); page.addView(rs);
        addJsonList(page, memory.reminders(), "text", "triggerAt", true);

        View sp = new View(this); sp.setLayoutParams(new LinearLayout.LayoutParams(-1, dp(24)));
        page.addView(sp); sv.addView(page);
        content.removeAllViews(); content.addView(sv);
    }

    // ── SETTINGS ──

    private void renderSettings() {
        titleText.setText("Settings");
        setAiStatus("● Keys, notifications, logs", C_TEXT_MUTED, false);
        ScrollView sv = new ScrollView(this); sv.setBackgroundColor(C_BG);
        LinearLayout page = new LinearLayout(this); page.setOrientation(LinearLayout.VERTICAL);
        cardAnimDelay = 0;

        page.addView(createGlassCard("🔑 API Keys", "Keys read from .env at build. Paste to override.", true));

        LinearLayout w1 = new LinearLayout(this); w1.setPadding(dp(12), dp(4), dp(12), dp(4));
        Button ib = glowButton("📥 Import .env", C_PINK);
        ib.setOnClickListener(v -> promptMulti("Import .env", "Paste KEY=value lines", "", v2 -> { keys.importEnvText(v2); renderSettings(); }));
        w1.addView(ib, new LinearLayout.LayoutParams(-1, dp(44))); page.addView(w1);

        for (Map.Entry<String, String> e : keys.snapshotMasked().entrySet()) {
            Button kb = smallBtn("🔑 " + e.getKey() + " - " + e.getValue());
            kb.setGravity(Gravity.LEFT | Gravity.CENTER_VERTICAL); kb.setPadding(dp(12), 0, dp(12), 0);
            kb.setOnClickListener(v -> prompt("Set " + e.getKey(), "Value", keys.get(e.getKey()), v2 -> { keys.save(e.getKey(), v2); renderSettings(); }));
            LinearLayout wr = new LinearLayout(this); wr.setPadding(dp(12), dp(2), dp(12), dp(2));
            wr.addView(kb, new LinearLayout.LayoutParams(-1, dp(42))); page.addView(wr);
        }

        LinearLayout w2 = new LinearLayout(this); w2.setPadding(dp(12), dp(4), dp(12), dp(4));
        Button cb = glowButton("🗑 Clear Cache", null);
        cb.setOnClickListener(v -> { api.clearCache(); Toast.makeText(this, "Cache cleared", Toast.LENGTH_SHORT).show(); });
        w2.addView(cb, new LinearLayout.LayoutParams(-1, dp(44))); page.addView(w2);

        Button as = smallBtn("⚙ Android App Settings");
        as.setGravity(Gravity.LEFT | Gravity.CENTER_VERTICAL); as.setPadding(dp(12), 0, dp(12), 0);
        as.setOnClickListener(v -> startActivity(new Intent(Settings.ACTION_APPLICATION_DETAILS_SETTINGS, Uri.parse("package:" + getPackageName()))));
        LinearLayout w3 = new LinearLayout(this); w3.setPadding(dp(12), dp(2), dp(12), dp(2));
        w3.addView(as, new LinearLayout.LayoutParams(-1, dp(42))); page.addView(w3);

        LinearLayout wc = new LinearLayout(this); wc.setPadding(dp(12), dp(6), dp(12), dp(6));
        Button custBtn = glowButton("🎨 Customize Theme & AI", activeAccent);
        custBtn.setTextSize(11);
        custBtn.setOnClickListener(v -> { bounceView(custBtn); renderCustomization(); });
        wc.addView(custBtn, new LinearLayout.LayoutParams(-1, dp(46)));
        page.addView(wc);

        // Smart behavior section
        page.addView(createSection("🤖", "AI Behavior"));
        LinearLayout bhRow = new LinearLayout(this); bhRow.setPadding(dp(12), dp(4), dp(12), dp(4));
        Button proBtn = glowButton("💬 Proactive Messages: ON", activeAccent);
        proBtn.setTextSize(9);
        proBtn.setOnClickListener(v -> { bounceView(proBtn); Toast.makeText(this, "Proactive messages active", Toast.LENGTH_SHORT).show(); });
        bhRow.addView(proBtn, new LinearLayout.LayoutParams(0, dp(38), 1));
        View bs = new View(this); bs.setLayoutParams(new LinearLayout.LayoutParams(dp(6), 0));
        bhRow.addView(bs);
        Button lateBtn = glowButton("🌙 Late Night Alert: ON", C_CYAN);
        lateBtn.setTextSize(9);
        lateBtn.setOnClickListener(v -> { bounceView(lateBtn); Toast.makeText(this, "Late night detection active", Toast.LENGTH_SHORT).show(); });
        bhRow.addView(lateBtn, new LinearLayout.LayoutParams(0, dp(38), 1));
        page.addView(bhRow);

        // Floating overlay section
        page.addView(createSection("💠", "Floating Overlay"));
        LinearLayout ovRow = new LinearLayout(this); ovRow.setPadding(dp(12), dp(4), dp(12), dp(4));
        Button ovBtn = glowButton(overlayActive ? "🔴 Overlay: ON" : "⚪ Overlay: OFF", overlayActive ? activeAccent : null);
        ovBtn.setTextSize(10);
        ovBtn.setOnClickListener(v -> {
            bounceView(ovBtn);
            if (overlayActive) {
                stopService(new Intent(this, FloatingOverlayService.class));
                overlayActive = false;
                Toast.makeText(this, "Overlay stopped", Toast.LENGTH_SHORT).show();
                renderSettings();
            } else {
                if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.M && !Settings.canDrawOverlays(this)) {
                    Intent intent = new Intent(Settings.ACTION_MANAGE_OVERLAY_PERMISSION, Uri.parse("package:" + getPackageName()));
                    startActivityForResult(intent, 99);
                    Toast.makeText(this, "Grant overlay permission first", Toast.LENGTH_SHORT).show();
                } else {
                    startForegroundService(new Intent(this, FloatingOverlayService.class));
                    overlayActive = true;
                    Toast.makeText(this, "✨ Floating JARVIS is active!", Toast.LENGTH_SHORT).show();
                    renderSettings();
                }
            }
        });
        ovRow.addView(ovBtn, new LinearLayout.LayoutParams(0, dp(42), 1));
        View ovs = new View(this); ovs.setLayoutParams(new LinearLayout.LayoutParams(dp(6), 0));
        ovRow.addView(ovs);

        Button ovGuideBtn = smallBtn("ℹ️ How to use");
        ovGuideBtn.setOnClickListener(v -> {
            bounceView(ovGuideBtn);
            showResult("Floating JARVIS",
                    "✨ Floating JARVIS\n\n" +
                    "• A glowing AI icon appears over all apps\n" +
                    "• Drag to move it anywhere\n" +
                    "• Tap to open mini chat panel\n" +
                    "• Type any question or command\n" +
                    "• Tap ✕ to close the overlay\n\n" +
                    "Great for multitasking! Ask JARVIS while using other apps.", false);
        });
        ovRow.addView(ovGuideBtn, new LinearLayout.LayoutParams(0, dp(42), 1));
        page.addView(ovRow);

        LinearLayout ls = createSection("📋", "Recent Logs"); page.addView(ls);
        JSONArray la = logs.all();
        if (la.length() == 0) page.addView(createGlassCard("", "No logs yet."));
        for (int i = Math.max(0, la.length() - 5); i < la.length(); i++) {
            JSONObject it = la.optJSONObject(i);
            if (it != null) {
                String lv = it.optString("level");
                int lc = "ERROR".equals(lv) ? C_RED : "WARN".equals(lv) ? C_YELLOW : C_TEXT_MUTED;
                page.addView(createGlassCard(it.optString("time") + "  " + lv, it.optString("message")));
            }
        }
        View sp = new View(this); sp.setLayoutParams(new LinearLayout.LayoutParams(-1, dp(24)));
        page.addView(sp); sv.addView(page);
        content.removeAllViews(); content.addView(sv);
    }

    // ── VOICE ──

    private void renderVoice() {
        titleText.setText("Voice");
        setAiStatus("● Voice — auto-sends after 3s silence", C_PINK, false);
        LinearLayout page = new LinearLayout(this);
        page.setOrientation(LinearLayout.VERTICAL); page.setBackgroundColor(C_BG);

        page.addView(createGlassCard("🎤 Speech Mode", "Tap Listen & speak. Silence (3s) auto-sends. Enable Loop in quick panel.", true));

        waveformContainer = new LinearLayout(this);
        waveformContainer.setGravity(Gravity.CENTER);
        waveformContainer.setPadding(0, dp(8), 0, dp(8));
        waveformContainer.addView(buildWaveform());
        page.addView(waveformContainer, new LinearLayout.LayoutParams(-1, dp(64)));

        voiceStatus = new TextView(this);
        voiceStatus.setText("🎤 Ready — tap LISTEN");
        voiceStatus.setTextSize(14); voiceStatus.setTextColor(C_TEXT_MUTED);
        voiceStatus.setGravity(Gravity.CENTER);
        voiceStatus.setPadding(0, dp(4), 0, dp(12));
        page.addView(voiceStatus, new LinearLayout.LayoutParams(-1, dp(40)));

        LinearLayout br = new LinearLayout(this); br.setGravity(Gravity.CENTER);
        br.setPadding(dp(24), dp(4), dp(24), dp(4));

        Button listen = glowButton("🎤  LISTEN", C_PINK);
        listen.setTextSize(15);
        listen.setOnClickListener(v -> startListening());
        br.addView(listen, new LinearLayout.LayoutParams(0, dp(52), 1));

        Button stop = smallBtn("⏹  STOP");
        stop.setOnClickListener(v -> { stopListening(); setAiStatus("● Voice Ready", C_PINK, true); });
        LinearLayout.LayoutParams slp = new LinearLayout.LayoutParams(0, dp(46), 1);
        slp.leftMargin = dp(8);
        br.addView(stop, slp);
        page.addView(br);

        Button cv = smallBtn("🗑 Clear & Reset");
        cv.setOnClickListener(v -> { memory.clearChat(); voiceStatus.setText("🎤 Ready"); renderVoice(); });
        LinearLayout cw = new LinearLayout(this); cw.setPadding(dp(24), dp(6), dp(24), 0);
        cw.addView(cv, new LinearLayout.LayoutParams(-1, dp(42)));
        page.addView(cw);

        page.addView(createGlassCard("🗣 Recent", chatPreview()));

        View sp = new View(this); sp.setLayoutParams(new LinearLayout.LayoutParams(-1, dp(24)));
        page.addView(sp);
        ScrollView sv = new ScrollView(this); sv.addView(page);
        content.removeAllViews(); content.addView(sv);
    }

    // ── TOOLS ──

    private void renderTools() {
        titleText.setText("Tools");
        setAiStatus("● 100+ tools", C_CYAN, false);
        ScrollView sv = new ScrollView(this); sv.setBackgroundColor(C_BG);
        LinearLayout page = new LinearLayout(this); page.setOrientation(LinearLayout.VERTICAL);
        cardAnimDelay = 0;

        addToolSection(page, "🤖", "AI", new Tool[]{
                new Tool("💬 Chat", "chat:", "Prompt", "Help me"),
                new Tool("💻 Code", "code:", "Request", "Fix this"),
                new Tool("📝 Summarize", "summarize:", "Text", ""),
                new Tool("🌐 Translate", "translate:", "t|text", "hi|Hello"),
                new Tool("🎨 Image", "image:", "Prompt", "neon")
        });
        addToolSection(page, "🌍", "Web", new Tool[]{
                new Tool("🌤 Weather", "weather:", "City", "Mumbai"),
                new Tool("📰 News", "news:", "Topic", "tech"),
                new Tool("🔍 Search", "web:", "Query", ""),
                new Tool("▶️ YouTube", "youtube:", "Query", "lofi"),
                new Tool("📖 Wiki", "wiki:", "Topic", "AI")
        });
        addToolSection(page, "📊", "System", new Tool[]{
                new Tool("📱 Stats", "system:", null, null),
                new Tool("⚡ Speed", "speed-test:", null, null),
                new Tool("📈 Graphs", "system-graphs:", null, null),
                new Tool("📡 Ping", "ping:", "Host", "google.com"),
                new Tool("🌐 Network", "network-status:", null, null)
        });
        addToolSection(page, "⚡", "Productivity", new Tool[]{
                new Tool("🧮 Calc", "calc:", "Expression", "15*23"),
                new Tool("🎯 Focus", "focus:", "Minutes", "25"),
                new Tool("⏰ Remind", "remind:", "Text|min", "Break|10"),
                new Tool("📋 Brief", "daily:", "City", "Mumbai"),
                new Tool("🔍 Smart", "smart-search:", "Query", "AI")
        });
        addToolSection(page, "🎮", "Fun", new Tool[]{
                new Tool("🎬 Movies", "movies:", "Search", "inception"),
                new Tool("❓ Riddle", "riddle-random:", null, null),
                new Tool("😂 Joke", "joke:", null, null),
                new Tool("💭 Quote", "quote:", null, null),
                new Tool("🔮 8 Ball", "8ball:", "Question", "Will I?")
        });
        addToolSection(page, "💰", "Finance", new Tool[]{
                new Tool("₿ Crypto", "crypto:", "Coin", "bitcoin"),
                new Tool("📈 Stock", "stock:", "Symbol", "AAPL"),
                new Tool("💱 Currency", "currency:", "From To", "USD INR")
        });

        View sp = new View(this); sp.setLayoutParams(new LinearLayout.LayoutParams(-1, dp(24)));
        page.addView(sp); sv.addView(page);
        content.removeAllViews(); content.addView(sv);
    }

    // ── LOGS ──

    private void renderLogs() {
        titleText.setText("Logs");
        setAiStatus("● System Logs", C_TEXT_MUTED, false);
        ScrollView sv = new ScrollView(this); sv.setBackgroundColor(C_BG);
        LinearLayout page = new LinearLayout(this); page.setOrientation(LinearLayout.VERTICAL);
        cardAnimDelay = 0;

        LinearLayout wr = new LinearLayout(this); wr.setPadding(dp(12), dp(5), dp(12), dp(5));
        Button cl = smallBtn("🗑 Clear");
        cl.setOnClickListener(v -> { logs.clear(); renderLogs(); });
        wr.addView(cl, new LinearLayout.LayoutParams(-1, dp(46))); page.addView(wr);

        JSONArray arr = logs.all();
        if (arr.length() == 0) page.addView(createGlassCard("Logs", "No logs yet."));
        for (int i = arr.length() - 1; i >= 0; i--) {
            JSONObject it = arr.optJSONObject(i);
            if (it != null) {
                String lv = it.optString("level");
                int lc = "ERROR".equals(lv) ? C_RED : "WARN".equals(lv) ? C_YELLOW : C_TEXT_MUTED;
                page.addView(createGlassCard(it.optString("time") + "  " + lv, it.optString("message")));
            }
        }
        View sp = new View(this); sp.setLayoutParams(new LinearLayout.LayoutParams(-1, dp(24)));
        page.addView(sp); sv.addView(page);
        content.removeAllViews(); content.addView(sv);
    }

    // ── ANIMATIONS ──

    private void animateSendButton(View btn) {
        main.post(new Runnable() {
            boolean glow = true;
            public void run() {
                if (btn == null) return;
                float a = glow ? 1f : 0.5f;
                float s = glow ? 1.0f : 0.85f;
                btn.animate().alpha(a).scaleX(s).scaleY(s).setDuration(800).start();
                glow = !glow;
                main.postDelayed(this, 800);
            }
        });
    }

    private void fadeIn(View v) {
        AlphaAnimation a = new AlphaAnimation(0.7f, 1f);
        a.setDuration(200); a.setInterpolator(new AccelerateDecelerateInterpolator());
        v.startAnimation(a);
    }

    private void bounceView(View v) {
        ScaleAnimation s = new ScaleAnimation(0.85f, 1f, 0.85f, 1f,
                Animation.RELATIVE_TO_SELF, 0.5f, Animation.RELATIVE_TO_SELF, 0.5f);
        s.setDuration(250); s.setInterpolator(new OvershootInterpolator(2.5f));
        v.startAnimation(s);
    }

    private void slideIn(View v) {
        TranslateAnimation t = new TranslateAnimation(Animation.RELATIVE_TO_SELF, 0, Animation.RELATIVE_TO_SELF, 0,
                Animation.RELATIVE_TO_SELF, -1f, Animation.RELATIVE_TO_SELF, 0);
        t.setDuration(300); t.setInterpolator(new DecelerateInterpolator());
        v.startAnimation(t); v.setVisibility(View.VISIBLE);
    }

    private void slideOut(View v) {
        TranslateAnimation t = new TranslateAnimation(Animation.RELATIVE_TO_SELF, 0, Animation.RELATIVE_TO_SELF, 0,
                Animation.RELATIVE_TO_SELF, 0, Animation.RELATIVE_TO_SELF, -1f);
        t.setDuration(250); t.setInterpolator(new AccelerateDecelerateInterpolator());
        t.setAnimationListener(new Animation.AnimationListener() {
            public void onAnimationStart(Animation a) { }
            public void onAnimationEnd(Animation a) { v.setVisibility(View.GONE); }
            public void onAnimationRepeat(Animation a) { }
        });
        v.startAnimation(t);
    }

    // ── HELPERS ──

    private void addToolSection(LinearLayout page, String icon, String title, Tool[] tools) {
        page.addView(createSection(icon, title));
        GridLayout g = new GridLayout(this); g.setColumnCount(2); g.setPadding(dp(12), 0, dp(12), 0);
        for (Tool t : tools) addQAction(g, t.label, t.command, t.hint, t.defaultValue);
        page.addView(g);
    }

    private void addBtn(LinearLayout p, String label, int lm, View.OnClickListener c, boolean accent) {
        Button b = accent ? glowButton(label, C_PINK) : smallBtn(label);
        b.setOnClickListener(v -> { bounceView(b); c.onClick(v); });
        LinearLayout.LayoutParams lp = new LinearLayout.LayoutParams(0, dp(44), 1);
        lp.leftMargin = dp(lm); p.addView(b, lp);
    }

    private void addQAction(GridLayout g, String label, String cmd, String hint, String def) {
        Button b = smallBtn(label);
        b.setOnClickListener(v -> {
            bounceView(b);
            if ("voice".equals(cmd)) openTab("voice");
            else if ("tools".equals(cmd)) openTab("tools");
            else if ("logs".equals(cmd)) openTab("logs");
            else if ("command".equals(cmd)) openTab("command");
            else if ("customize".equals(cmd)) openTab("customize");
            else if (cmd.startsWith("pick-ocr")) pickImage("Extract text from this image.");
            else if (cmd.startsWith("pick-vision")) pickImage("Describe this image in detail.");
            else if (cmd.startsWith("pick-file")) pickFile();
            else if (cmd.startsWith("browser")) prompt("URL", hint, def, this::openUrl);
            else if (hint == null) runTool(cmd, false);
            else prompt(label, hint, def == null ? "" : def, v2 -> runTool(cmd + v2, false));
        });
        GridLayout.LayoutParams lp = new GridLayout.LayoutParams();
        lp.width = 0; lp.height = dp(44); lp.columnSpec = GridLayout.spec(GridLayout.UNDEFINED, 1f);
        lp.setMargins(dp(3), dp(3), dp(3), dp(3)); g.addView(b, lp);
    }

    private void addNeonAction(GridLayout g, String icon, String label, String cmd, String hint, String def) {
        FrameLayout card = new FrameLayout(this);
        card.setPadding(dp(4), dp(4), dp(4), dp(4));

        GradientDrawable bg = new GradientDrawable();
        bg.setColor(0x0AFFFFFF);
        bg.setStroke(1, 0x15FFFFFF);
        bg.setCornerRadius(dp(12));
        card.setBackground(bg);

        card.setElevation(dp(1));
        if (Build.VERSION.SDK_INT >= 29) {
            card.setOutlineAmbientShadowColor(activeAccent);
            card.setOutlineSpotShadowColor(activeAccent);
        }

        LinearLayout content2 = new LinearLayout(this);
        content2.setOrientation(LinearLayout.VERTICAL);
        content2.setGravity(Gravity.CENTER);
        content2.setPadding(dp(8), dp(10), dp(8), dp(10));

        TextView iconV = new TextView(this);
        iconV.setText(icon);
        iconV.setTextSize(22);
        content2.addView(iconV);

        View sp = new View(this);
        sp.setLayoutParams(new LinearLayout.LayoutParams(-1, dp(4)));
        content2.addView(sp);

        TextView labelV = new TextView(this);
        labelV.setText(label);
        labelV.setTextSize(9);
        labelV.setTextColor(C_TEXT_SEC);
        labelV.setTypeface(null, android.graphics.Typeface.BOLD);
        labelV.setLetterSpacing(0.03f);
        content2.addView(labelV);

        card.addView(content2);

        if (cmd == null && "Notes".equals(label)) {
            card.setOnClickListener(v -> { bounceView(card); openTab("memory"); });
        } else if (cmd == null && "Calendar".equals(label)) {
            card.setOnClickListener(v -> { bounceView(card); runTool("daily:", false); });
        } else if (cmd == null && "Remind".equals(label)) {
            card.setOnClickListener(v -> { bounceView(card); runTool("remind:", false); });
        } else {
            card.setOnClickListener(v -> {
                bounceView(card);
                if ("voice".equals(cmd)) openTab("voice");
                else if (hint == null) runTool(cmd, false);
                else prompt(label, hint, def == null ? "" : def, v2 -> runTool(cmd + v2, false));
            });
        }

        GridLayout.LayoutParams lp = new GridLayout.LayoutParams();
        lp.width = 0;
        lp.height = dp(68);
        lp.columnSpec = GridLayout.spec(GridLayout.UNDEFINED, 1f);
        lp.setMargins(dp(3), dp(3), dp(3), dp(3));
        g.addView(card, lp);
    }

    private void loadChatBubbles() {
        chatList.removeAllViews(); chatList.addView(typingIndicator);
        JSONArray chat = memory.chat();
        if (chat.length() == 0) {
            String[] welcomes = {
                "Hey there! 👋 I'm JARVIS, your friendly AI companion. I can help with weather, news, calculations, translations, and so much more! Just ask me anything — I'm here for you. 💙\n\n💡 Try: \"weather:Mumbai\", \"news:tech\", \"tell me a joke\", or just chat naturally!",
                "Hello! 😊 Welcome back! I'm JARVIS — think of me as your smart, caring friend who's always ready to help. Need info, want to chat, or just bored? I've got you covered! 🚀\n\nTry asking me anything!",
            };
            appendBubble("assistant", welcomes[(int)(System.currentTimeMillis() / 3600000) % welcomes.length]);
            return;
        }
        for (int i = 0; i < chat.length(); i++) {
            JSONObject msg = chat.optJSONObject(i);
            if (msg != null) appendBubble(msg.optString("role"), msg.optString("content"));
        }
    }

    private void appendBubble(String role, String message) {
        if (chatList == null) return;
        boolean isUser = "user".equals(role);
        LinearLayout row = new LinearLayout(this);
        row.setOrientation(LinearLayout.VERTICAL);
        row.setGravity(isUser ? Gravity.RIGHT : Gravity.LEFT);

        if (!isUser) {
            LinearLayout meta = new LinearLayout(this);
            meta.setGravity(Gravity.CENTER_VERTICAL);
            View avatar = new View(this);
            GradientDrawable av = new GradientDrawable(); av.setShape(GradientDrawable.OVAL); av.setColor(activeAccent);
            avatar.setBackground(av);
            meta.addView(avatar, dp(6), dp(6));
            View ms = new View(this); ms.setLayoutParams(new LinearLayout.LayoutParams(dp(4), 0));
            meta.addView(ms);
            TextView rl = new TextView(this);
            rl.setText("JARVIS"); rl.setTextSize(8); rl.setTextColor(activeAccent);
            rl.setTypeface(null, android.graphics.Typeface.BOLD);
            rl.setLetterSpacing(0.08f);
            meta.addView(rl);
            meta.setPadding(dp(4), 0, 0, dp(4));
            row.addView(meta);
        } else {
            View sp = new View(this); sp.setLayoutParams(new LinearLayout.LayoutParams(-1, dp(4)));
            row.addView(sp);
        }

        // Check for code blocks
        if (message.contains("```")) {
            String[] parts = message.split("```");
            for (int i = 0; i < parts.length; i++) {
                String part = parts[i];
                if (part.trim().isEmpty()) continue;
                if (i % 2 == 1) {
                    // Code block - add with special styling
                    String[] lines = part.split("\\n", 2);
                    String lang = lines[0].trim();
                    String code = lines.length > 1 ? lines[1] : "";
                    if (code.isEmpty()) { code = lang; lang = ""; }

                    // Code header
                    LinearLayout codeBlock = new LinearLayout(this);
                    codeBlock.setOrientation(LinearLayout.VERTICAL);
                    GradientDrawable codeBg = new GradientDrawable();
                    codeBg.setColor(0xFF1A1A2E);
                    codeBg.setStroke(1, 0x33FFFFFF);
                    codeBg.setCornerRadii(new float[]{dp(6), dp(6), dp(6), dp(6), dp(6), dp(6), dp(6), dp(6)});
                    codeBlock.setBackground(codeBg);

                    LinearLayout header = new LinearLayout(this);
                    header.setGravity(Gravity.CENTER_VERTICAL);
                    header.setPadding(dp(10), dp(6), dp(10), dp(6));
                    View dot1 = new View(this);
                    GradientDrawable d1 = new GradientDrawable(); d1.setShape(GradientDrawable.OVAL); d1.setColor(C_RED);
                    dot1.setBackground(d1);
                    header.addView(dot1, dp(6), dp(6));
                    View hsp = new View(this); hsp.setLayoutParams(new LinearLayout.LayoutParams(dp(4), 0));
                    header.addView(hsp);
                    View dot2 = new View(this);
                    GradientDrawable d2 = new GradientDrawable(); d2.setShape(GradientDrawable.OVAL); d2.setColor(C_YELLOW);
                    dot2.setBackground(d2);
                    header.addView(dot2, dp(6), dp(6));
                    View hsp2 = new View(this); hsp2.setLayoutParams(new LinearLayout.LayoutParams(dp(4), 0));
                    header.addView(hsp2);
                    View dot3 = new View(this);
                    GradientDrawable d3 = new GradientDrawable(); d3.setShape(GradientDrawable.OVAL); d3.setColor(C_GREEN);
                    dot3.setBackground(d3);
                    header.addView(dot3, dp(6), dp(6));

                    View hsp3 = new View(this);
                    hsp3.setLayoutParams(new LinearLayout.LayoutParams(0, 0, 1));
                    header.addView(hsp3);

                    TextView langV = new TextView(this);
                    langV.setText(lang.isEmpty() ? "code" : lang);
                    langV.setTextSize(8);
                    langV.setTextColor(C_TEXT_MUTED);
                    langV.setTypeface(android.graphics.Typeface.MONOSPACE);
                    header.addView(langV);
                    codeBlock.addView(header);

                    View hline = new View(this);
                    hline.setBackgroundColor(0x22FFFFFF);
                    codeBlock.addView(hline, new LinearLayout.LayoutParams(-1, 1));

                    TextView codeV = new TextView(this);
                    codeV.setText(code);
                    codeV.setTextSize(11);
                    codeV.setTextColor(C_CYAN);
                    codeV.setTypeface(android.graphics.Typeface.MONOSPACE);
                    codeV.setPadding(dp(10), dp(8), dp(10), dp(8));
                    codeV.setLineSpacing(dp(2), 1.0f);
                    codeBlock.addView(codeV);

                    LinearLayout.LayoutParams clp = new LinearLayout.LayoutParams(-2, -2);
                    clp.setMargins(dp(isUser ? 52 : 0), dp(2), dp(isUser ? 0 : 52), dp(2));
                    clp.gravity = isUser ? Gravity.RIGHT : Gravity.LEFT;
                    row.addView(codeBlock, clp);
                } else {
                    // Text part
                    addBubbleText(row, part, isUser);
                }
            }
        } else {
            addBubbleText(row, message, isUser);
        }

        chatList.addView(row);
        if (chatScroll != null) main.postDelayed(() -> chatScroll.fullScroll(View.FOCUS_DOWN), 80);
    }

    private void addBubbleText(LinearLayout row, String text, boolean isUser) {
        if (text.trim().isEmpty()) return;
        TextView bubble = new TextView(this);
        bubble.setText(text);
        bubble.setTextSize(13);
        bubble.setTextColor(isUser ? Color.WHITE : C_TEXT);
        bubble.setTextIsSelectable(true);
        bubble.setLineSpacing(dp(2), 1.05f);
        bubble.setIncludeFontPadding(false);

        GradientDrawable bg = new GradientDrawable();
        if (isUser) {
            bg.setColor(activeAccent);
            int r = dp(16); bg.setCornerRadii(new float[]{r, r, dp(4), r, r, r, r, r});
        } else {
            bg.setColor(0x14161E);
            bg.setStroke(1, 0x222A2A3E);
            int r = dp(16); bg.setCornerRadii(new float[]{dp(4), dp(4), r, r, r, r, r, r});
        }
        bubble.setBackground(bg);
        bubble.setPadding(dp(16), dp(12), dp(16), dp(12));
        LinearLayout.LayoutParams lp = new LinearLayout.LayoutParams(-2, -2);
        lp.setMargins(dp(isUser ? 52 : 0), dp(2), dp(isUser ? 0 : 52), dp(2));
        lp.gravity = isUser ? Gravity.RIGHT : Gravity.LEFT;
        bubble.setLayoutParams(lp);
        row.addView(bubble);
    }

    private String chatPreview() {
        JSONArray chat = memory.chat();
        if (chat.length() == 0) return "No chat yet.";
        StringBuilder out = new StringBuilder();
        for (int i = Math.max(0, chat.length() - 4); i < chat.length(); i++) {
            JSONObject it = chat.optJSONObject(i);
            if (it != null) out.append(it.optString("role")).append(": ").append(it.optString("content", "")).append("\n\n");
        }
        return out.toString().trim();
    }

    private void addJsonList(LinearLayout page, JSONArray arr, String tk, String bk, boolean date) {
        if (arr.length() == 0) { page.addView(createGlassCard("", "Nothing yet.")); return; }
        for (int i = arr.length() - 1; i >= 0; i--) {
            JSONObject it = arr.optJSONObject(i);
            if (it == null) continue;
            String body = it.optString(bk);
            if (date) body = DateFormat.getDateTimeInstance().format(new Date(it.optLong(bk)));
            page.addView(createGlassCard(it.optString(tk, "Item"), body));
        }
    }

    private void addTodoList(LinearLayout page) {
        JSONArray todos = memory.todos();
        if (todos.length() == 0) { page.addView(createGlassCard("", "No todos.")); return; }
        for (int i = 0; i < todos.length(); i++) {
            JSONObject todo = todos.optJSONObject(i);
            if (todo == null) continue;
            final int idx = i;
            boolean done = todo.optBoolean("done");
            Button b = smallBtn((done ? "✅ " : "⬜ ") + todo.optString("task"));
            b.setGravity(Gravity.LEFT | Gravity.CENTER_VERTICAL);
            b.setPadding(dp(12), 0, dp(12), 0);
            b.setTextColor(done ? C_TEXT_MUTED : C_TEXT);
            b.setOnClickListener(v -> { memory.toggleTodo(idx); renderMemory(); });
            LinearLayout wr = new LinearLayout(this); wr.setPadding(dp(12), dp(2), dp(12), dp(2));
            wr.addView(b, new LinearLayout.LayoutParams(-1, dp(42))); page.addView(wr);
        }
    }

    // ── TYPING INDICATOR ──

    private View buildTypingIndicator() {
        LinearLayout container = new LinearLayout(this);
        container.setPadding(dp(14), dp(10), dp(14), dp(10));
        container.setBackgroundColor(Color.TRANSPARENT); container.setGravity(Gravity.LEFT);

        LinearLayout dotsRow = new LinearLayout(this);
        dotsRow.setGravity(Gravity.CENTER_VERTICAL);
        GradientDrawable drBg = new GradientDrawable();
        drBg.setColor(0x14161E);
        drBg.setStroke(1, 0x222A2A3E);
        drBg.setCornerRadii(new float[]{dp(4), dp(4), dp(16), dp(16), dp(16), dp(16), dp(16), dp(16)});
        dotsRow.setBackground(drBg);
        dotsRow.setPadding(dp(16), dp(10), dp(16), dp(10));

        // Pink dot avatar
        View av = new View(this);
        GradientDrawable avbg = new GradientDrawable(); avbg.setShape(GradientDrawable.OVAL); avbg.setColor(C_PINK);
        av.setBackground(avbg);
        dotsRow.addView(av, dp(6), dp(6));
        View sp1 = new View(this); sp1.setLayoutParams(new LinearLayout.LayoutParams(dp(6), 0));
        dotsRow.addView(sp1);

        TextView label = new TextView(this);
        label.setText("JARVIS thinking"); label.setTextSize(9);
        label.setTextColor(C_PINK); label.setTypeface(null, android.graphics.Typeface.BOLD);
        label.setLetterSpacing(0.06f);
        dotsRow.addView(label);

        View sp2 = new View(this); sp2.setLayoutParams(new LinearLayout.LayoutParams(dp(6), 0));
        dotsRow.addView(sp2);

        int[] dotColors = {C_PINK, C_CYAN, C_PINK};
        for (int i = 0; i < 3; i++) {
            View dot = new View(this);
            GradientDrawable dbg = new GradientDrawable();
            dbg.setShape(GradientDrawable.OVAL); dbg.setColor(dotColors[i]);
            dot.setBackground(dbg);
            LinearLayout.LayoutParams lp = new LinearLayout.LayoutParams(dp(5), dp(5));
            lp.setMargins(dp(2), 0, dp(2), 0);
            dotsRow.addView(dot, lp);
            animateDot(dot, i * 200, dotColors[i]);
        }
        container.addView(dotsRow);
        return container;
    }

    private void animateDot(View dot, int delay, int color) {
        main.postDelayed(new Runnable() { boolean up = true;
            public void run() {
                if (typingIndicator == null || typingIndicator.getVisibility() != View.VISIBLE) return;
                float s = up ? 1.6f : 0.5f;
                dot.animate().scaleX(s).scaleY(s).alpha(up ? 1f : 0.2f).setDuration(350).start();
                up = !up;
                main.postDelayed(this, 500);
            }
        }, delay);
    }

    private void showTypingIndicator(boolean show) {
        if (typingIndicator != null) {
            typingIndicator.setVisibility(show ? View.VISIBLE : View.GONE);
            setAiStatus(show ? "● Thinking..." : "● AI Ready", show ? C_CYAN : C_GREEN, true);
            if (show && chatScroll != null) main.postDelayed(() -> chatScroll.fullScroll(View.FOCUS_DOWN), 50);
        }
    }

    // ── WAVEFORM ──

    private View buildWaveform() {
        LinearLayout row = new LinearLayout(this);
        row.setGravity(Gravity.CENTER); row.setPadding(0, dp(8), 0, dp(8));

        int[] hs = {8, 16, 6, 24, 10, 20, 8, 14, 5, 18, 10, 14, 6, 22, 8};
        int[] colors = {C_PINK, C_CYAN, C_PINK, C_CYAN, C_PINK, C_CYAN, C_PINK, C_CYAN, C_PINK, C_CYAN, C_PINK, C_CYAN, C_PINK, C_CYAN, C_PINK};

        for (int i = 0; i < hs.length; i++) {
            View bar = new View(this);
            GradientDrawable bg = new GradientDrawable();
            bg.setShape(GradientDrawable.RECTANGLE); bg.setColor(colors[i]); bg.setCornerRadius(dp(3));
            bar.setBackground(bg);
            LinearLayout.LayoutParams lp = new LinearLayout.LayoutParams(dp(3), dp(hs[i]));
            lp.setMargins(dp(2), 0, dp(2), 0); row.addView(bar, lp);
        }

        new Handler(Looper.getMainLooper()).postDelayed(new Runnable() {
            public void run() {
                for (int i = 0; i < row.getChildCount(); i++) {
                    View bar = row.getChildAt(i);
                    if (!isListening) {
                        float s = 0.8f + 0.2f * (float) Math.sin(i * 0.5 + System.currentTimeMillis() * 0.003);
                        bar.animate().scaleY(s).alpha(0.35f).setDuration(400).start();
                    } else {
                        float s = 0.3f + (float) Math.random() * 1.7f;
                        bar.animate().scaleY(s).alpha(0.4f + (float) Math.random() * 0.6f).setDuration(120).start();
                    }
                }
                new Handler(Looper.getMainLooper()).postDelayed(this, isListening ? 120 : 350);
            }
        }, 200);
        return row;
    }

    // ── COMMAND EXECUTION ──

    private void runTool(String command, boolean speak) {
        setBusy(true);
        String tn = command.contains(":") ? command.split(":")[0] : command;
        setAiStatus("● Processing " + tn + "...", C_YELLOW, true);
        executor.execute(() -> {
            String result;
            try { result = brain.run(command); logs.add("INFO", "Tool: " + command); }
            catch (Exception e) { result = "Error: " + e.getMessage(); logs.add("ERROR", result); }
            String fr = result;
            main.post(() -> {
                setBusy(false); setAiStatus("● AI Ready", C_GREEN, true);
                showResult("JARVIS - " + tn, fr, speak);
                if (speak) speak(fr);
            });
        });
    }

    private void sendChat() {
        String text = chatInput.getText().toString().trim();
        if (text.isEmpty()) return;
        chatInput.setText(""); hideKeyboard(chatInput);
        memory.addChat("user", text); appendBubble("user", text);

        // Track topic/interest
        String lower = text.toLowerCase();
        if (lower.contains("weather") || lower.contains("mausam")) memory.trackTopic("weather");
        else if (lower.contains("news") || lower.contains("khabar")) memory.trackTopic("news");
        else if (lower.contains("crypto") || lower.contains("stock") || lower.contains("share")) memory.trackTopic("finance");
        else if (lower.contains("youtube") || lower.contains("video")) memory.trackTopic("youtube");
        else if (lower.contains("code") || lower.contains("program") || lower.contains("app")) memory.trackTopic("coding");
        else if (lower.contains("game") || lower.contains("movie") || lower.contains("music")) memory.trackTopic("entertainment");
        else if (lower.contains("education") || lower.contains("study") || lower.contains("learn") || lower.contains("class") || lower.contains("ncert")) memory.trackTopic("education");
        else if (lower.contains("joke") || lower.contains("funny") || lower.contains("laugh")) memory.trackTopic("fun");
        else if (lower.contains("health") || lower.contains("diet") || lower.contains("exercise") || lower.contains("workout")) memory.trackTopic("health");
        else memory.trackTopic("general");

        setBusy(true); showTypingIndicator(true);
        setAiStatus("● Thinking...", C_CYAN, true);
        executor.execute(() -> {
            String result;
            try { result = brain.run(text); logs.add("INFO", "Chat: " + text.substring(0, Math.min(50, text.length()))); }
            catch (Exception e) { result = "Error: " + e.getMessage(); logs.add("ERROR", result); }
            String fr = result; memory.addChat("assistant", fr);
            String finalResult = fr;
            main.post(() -> {
                setBusy(false); showTypingIndicator(false);

                // Detect quiz content and show interactive UI
                if (finalResult.contains("Q:") && finalResult.contains("A)") && finalResult.contains("Correct:")) {
                    appendBubble("assistant", finalResult);
                    showInteractiveQuiz(finalResult);
                } else {
                    appendBubble("assistant", finalResult);
                }

                setAiStatus("● AI Ready", C_GREEN, true);
                if (speechMode) speak(finalResult);
                sendNotification("JARVIS", finalResult.length() > 80 ? finalResult.substring(0, 80) + "..." : finalResult);
            });
        });
    }

    private void showInteractiveQuiz(String quizText) {
        String[] lines = quizText.split("\n");
        String currentQ = "";
        String[] options = new String[4];
        String correct = "";
        String explanation = "";
        int optIdx = 0;
        final java.util.ArrayList<String[]> questions = new java.util.ArrayList<>();
        final java.util.ArrayList<String> answers = new java.util.ArrayList<>();
        final java.util.ArrayList<String> explanations = new java.util.ArrayList<>();

        for (String line : lines) {
            line = line.trim();
            if (line.startsWith("Q:")) {
                if (!currentQ.isEmpty() && optIdx > 0) {
                    questions.add(new String[]{currentQ, options[0], options[1], options[2], options[3]});
                    answers.add(correct);
                    explanations.add(explanation);
                }
                currentQ = line.substring(2).trim();
                options = new String[4]; optIdx = 0; correct = ""; explanation = "";
            } else if (line.matches("^[A-D]\\)\\s.*")) {
                if (optIdx < 4) options[optIdx++] = line.substring(2).trim();
            } else if (line.startsWith("Correct:")) {
                correct = line.substring(8).trim();
            } else if (line.startsWith("Explanation:")) {
                explanation = line.substring(12).trim();
            }
        }
        if (!currentQ.isEmpty() && optIdx > 0) {
            questions.add(new String[]{currentQ, options[0], options[1], options[2], options[3]});
            answers.add(correct);
            explanations.add(explanation);
        }

        if (questions.isEmpty()) return;

        final int[] qIdx = {0};
        final int[] score = {0};
        final int[] total = {questions.size()};

        showQuizCard(questions, answers, explanations, qIdx, score, total);
    }

    private void showQuizCard(final java.util.ArrayList<String[]> questions, final java.util.ArrayList<String> answers,
                              final java.util.ArrayList<String> explanations, final int[] qIdx, final int[] score, final int[] total) {
        if (qIdx[0] >= questions.size()) {
            memory.addQuizScore(score[0], total[0], "chat");
            appendBubble("assistant", "🎉 Quiz Complete! You scored " + score[0] + "/" + total[0] + " (" + (total[0] > 0 ? score[0] * 100 / total[0] : 0) + "%)\n" + memory.getQuizSummary());
            return;
        }

        String[] q = questions.get(qIdx[0]);
        LinearLayout quizCard = new LinearLayout(this);
        quizCard.setOrientation(LinearLayout.VERTICAL);
        quizCard.setPadding(dp(12), dp(12), dp(12), dp(12));

        GradientDrawable qBg = new GradientDrawable();
        qBg.setColor(0x14161E);
        qBg.setStroke(1, 0x222A2A3E);
        qBg.setCornerRadius(dp(12));
        quizCard.setBackground(qBg);

        // Question number
        TextView qNum = new TextView(this);
        qNum.setText("Q" + (qIdx[0] + 1) + "/" + total[0]);
        qNum.setTextSize(9);
        qNum.setTextColor(activeAccent);
        qNum.setTypeface(null, android.graphics.Typeface.BOLD);
        quizCard.addView(qNum);

        // Question text
        TextView qText = new TextView(this);
        qText.setText(q[0]);
        qText.setTextSize(13);
        qText.setTextColor(C_TEXT);
        qText.setPadding(0, dp(4), 0, dp(8));
        qText.setLineSpacing(dp(2), 1.0f);
        quizCard.addView(qText);

        String[] letters = {"A", "B", "C", "D"};
        for (int i = 1; i < q.length && q[i] != null; i++) {
            final int optIdx = i;
            Button optBtn = new Button(this);
            optBtn.setText(letters[i-1] + ")  " + q[i]);
            optBtn.setAllCaps(false);
            optBtn.setTextSize(11);
            optBtn.setTextColor(C_TEXT_SEC);
            optBtn.setGravity(Gravity.LEFT | Gravity.CENTER_VERTICAL);
            optBtn.setPadding(dp(10), dp(6), dp(10), dp(6));
            optBtn.setMinHeight(0);

            GradientDrawable obg = new GradientDrawable();
            obg.setColor(0x0AFFFFFF);
            obg.setStroke(1, 0x15FFFFFF);
            obg.setCornerRadius(dp(8));
            optBtn.setBackground(obg);

            LinearLayout.LayoutParams olp = new LinearLayout.LayoutParams(-1, dp(36));
            olp.setMargins(0, dp(3), 0, dp(3));
            quizCard.addView(optBtn, olp);

            final String selectedLetter = letters[i-1];
            final String correctLetter = answers.get(qIdx[0]);
            final String explanation = explanations.get(qIdx[0]);

            optBtn.setOnClickListener(v -> {
                boolean isCorrect = selectedLetter.equalsIgnoreCase(correctLetter);
                if (isCorrect) score[0]++;

                // Highlight correct/wrong
                for (int j = 0; j < quizCard.getChildCount(); j++) {
                    View child = quizCard.getChildAt(j);
                    if (child instanceof Button) {
                        Button b = (Button) child;
                        GradientDrawable bg2 = (GradientDrawable) b.getBackground();
                        String btnText = b.getText().toString();
                        if (btnText.startsWith(correctLetter + ")")) {
                            bg2.setColor(0xFF10B981);
                            bg2.setStroke(2, 0xFF10B981);
                            b.setTextColor(Color.WHITE);
                        } else if (btnText.startsWith(selectedLetter + ")")) {
                            bg2.setColor(isCorrect ? 0xFF10B981 : 0xFFFF3B3B);
                            bg2.setStroke(2, isCorrect ? 0xFF10B981 : 0xFFFF3B3B);
                            b.setTextColor(Color.WHITE);
                        } else {
                            b.setEnabled(false);
                            b.setAlpha(0.4f);
                        }
                    }
                }

                // Explanation
                if (explanation != null && !explanation.isEmpty()) {
                    TextView expV = new TextView(this);
                    expV.setText("💡 " + explanation);
                    expV.setTextSize(10);
                    expV.setTextColor(0xFFCBD5E1);
                    expV.setPadding(0, dp(6), 0, dp(4));
                    expV.setLineSpacing(dp(1), 1.0f);
                    quizCard.addView(expV);
                }

                // Next button
                Button nextBtn = new Button(this);
                nextBtn.setText(qIdx[0] + 1 >= questions.size() ? "🎉 See Results" : "Next ➤");
                nextBtn.setAllCaps(false);
                nextBtn.setTextSize(11);
                nextBtn.setTextColor(Color.WHITE);
                GradientDrawable nbg = new GradientDrawable();
                nbg.setColor(activeAccent);
                nbg.setCornerRadius(dp(8));
                nextBtn.setBackground(nbg);
                nextBtn.setPadding(dp(12), dp(6), dp(12), dp(6));
                nextBtn.setMinHeight(0);
                LinearLayout.LayoutParams nlp = new LinearLayout.LayoutParams(-1, dp(36));
                nlp.setMargins(0, dp(6), 0, 0);
                quizCard.addView(nextBtn, nlp);

                nextBtn.setOnClickListener(v2 -> {
                    qIdx[0]++;
                    chatList.removeView(quizCard);
                    showQuizCard(questions, answers, explanations, qIdx, score, total);
                });
            });
        }

        chatList.addView(quizCard);
        if (chatScroll != null) main.postDelayed(() -> chatScroll.fullScroll(View.FOCUS_DOWN), 80);
    }

    private void stopListening() {
        silenceTimer.removeCallbacks(autoSendRunnable);
        if (recognizer != null) { try { recognizer.stopListening(); } catch (Exception e) { } }
        isListening = false;
        voiceStatusSafe("🎤 Stopped"); voiceStatus.setTextColor(C_TEXT_MUTED);
        setAiStatus("● Voice Ready", C_PINK, true);
    }

    private void startListening() {
        if (recognizer == null) {
            showResult("Voice", "Speech not available.\nInstall Google app or use a physical device.", false);
            return;
        }
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.M
                && checkSelfPermission(Manifest.permission.RECORD_AUDIO) != PackageManager.PERMISSION_GRANTED) {
            requestPermissions(new String[]{Manifest.permission.RECORD_AUDIO}, REQ_PERMISSIONS);
            return;
        }
        speechMode = true; isListening = true;
        modeText.setText("🎤"); statusDot.setTextColor(C_PINK);
        voiceStatusSafe("🎤 Listening... (auto-sends after silence)");
        voiceStatus.setTextColor(C_PINK); setAiStatus("● Listening...", C_PINK, true);

        autoSendRunnable = () -> {
            if (isListening && recognizer != null) {
                logs.add("INFO", "Auto-send on silence");
                try { recognizer.stopListening(); } catch (Exception e) { }
            }
        };

        recognizer.setRecognitionListener(new RecognitionListener() {
            private long lastSpeech = System.currentTimeMillis();
            private boolean hadSpeech = false;

            public void onReadyForSpeech(Bundle params) {
                voiceStatusSafe("🎤 Listening..."); voiceStatus.setTextColor(C_PINK);
                setAiStatus("● Listening...", C_PINK, true);
                lastSpeech = System.currentTimeMillis();
                silenceTimer.removeCallbacks(autoSendRunnable);
            }
            public void onBeginningOfSpeech() {
                voiceStatusSafe("🗣 Hearing you..."); voiceStatus.setTextColor(C_CYAN);
                setAiStatus("● Hearing...", C_CYAN, true);
                hadSpeech = true; lastSpeech = System.currentTimeMillis();
                silenceTimer.removeCallbacks(autoSendRunnable);
            }
            public void onRmsChanged(float rmsdB) {
                if (rmsdB > 2.0f) { lastSpeech = System.currentTimeMillis(); silenceTimer.removeCallbacks(autoSendRunnable); }
                else if (hadSpeech && System.currentTimeMillis() - lastSpeech > SILENCE_TIMEOUT_MS) {
                    if (isListening && recognizer != null) { try { recognizer.stopListening(); } catch (Exception e) { } }
                }
            }
            public void onBufferReceived(byte[] b) { }
            public void onEndOfSpeech() {
                voiceStatusSafe("💭 Processing..."); voiceStatus.setTextColor(C_BLUE);
                setAiStatus("● Processing...", C_BLUE, true);
                silenceTimer.removeCallbacks(autoSendRunnable);
                silenceTimer.postDelayed(() -> {
                    if (isListening && recognizer != null) { try { recognizer.stopListening(); } catch (Exception e) { } }
                }, 3000);
            }
            public void onError(int error) {
                isListening = false; silenceTimer.removeCallbacks(autoSendRunnable);
                String msg;
                switch (error) {
                    case SpeechRecognizer.ERROR_AUDIO: msg = "🎤 Audio error"; break;
                    case SpeechRecognizer.ERROR_CLIENT: msg = "⚠ Client error"; break;
                    case SpeechRecognizer.ERROR_INSUFFICIENT_PERMISSIONS: msg = "⚠ Permission denied"; break;
                    case SpeechRecognizer.ERROR_NETWORK: msg = "🌐 Network error"; break;
                    case SpeechRecognizer.ERROR_NETWORK_TIMEOUT: msg = "🌐 Timeout"; break;
                    case SpeechRecognizer.ERROR_NO_MATCH: msg = "🔇 No speech detected"; break;
                    case SpeechRecognizer.ERROR_RECOGNIZER_BUSY: msg = "⏳ Busy"; break;
                    case SpeechRecognizer.ERROR_SERVER: msg = "⚠ Server error"; break;
                    case SpeechRecognizer.ERROR_SPEECH_TIMEOUT: msg = "🔇 No speech heard"; break;
                    default: msg = "⚠ Error " + error; break;
                }
                voiceStatusSafe(msg); voiceStatus.setTextColor(C_RED);
                setAiStatus("● " + msg, C_RED, true);
                logs.add("WARN", "Speech: " + msg);
                if (continueListening) main.postDelayed(() -> startListening(), 1500);
            }
            public void onPartialResults(Bundle r) { }
            public void onEvent(int t, Bundle p) { }
            public void onResults(Bundle results) {
                isListening = false; silenceTimer.removeCallbacks(autoSendRunnable);
                ArrayList<String> matches = results.getStringArrayList(SpeechRecognizer.RESULTS_RECOGNITION);
                if (matches == null || matches.isEmpty()) {
                    voiceStatusSafe("🔇 No speech"); voiceStatus.setTextColor(C_TEXT_MUTED);
                    setAiStatus("● AI Ready", C_GREEN, true);
                    if (continueListening) main.postDelayed(() -> startListening(), 1000);
                    return;
                }
                String text = matches.get(0);
                voiceStatusSafe("✅ " + text); voiceStatus.setTextColor(C_GREEN);
                memory.addChat("user", text);
                runVoice(text);
            }
        });
        Intent intent = new Intent(RecognizerIntent.ACTION_RECOGNIZE_SPEECH);
        intent.putExtra(RecognizerIntent.EXTRA_LANGUAGE_MODEL, RecognizerIntent.LANGUAGE_MODEL_FREE_FORM);
        intent.putExtra(RecognizerIntent.EXTRA_LANGUAGE, Locale.getDefault());
        try { recognizer.startListening(intent); }
        catch (Exception e) {
            isListening = false; silenceTimer.removeCallbacks(autoSendRunnable);
            voiceStatusSafe("⚠ " + e.getMessage()); voiceStatus.setTextColor(C_RED);
            setAiStatus("● Speech start failed", C_RED, true);
            logs.add("ERROR", "Speech: " + e.getMessage());
        }
    }

    private void runVoice(String text) {
        setBusy(true);
        voiceStatusSafe("💭 Thinking..."); voiceStatus.setTextColor(C_BLUE);
        setAiStatus("● Processing...", C_BLUE, true);
        executor.execute(() -> {
            String result;
            try { result = brain.run(text); logs.add("INFO", "Voice: " + text.substring(0, Math.min(40, text.length()))); }
            catch (Exception e) { result = "Error: " + e.getMessage(); logs.add("ERROR", result); }
            String fr = result; memory.addChat("assistant", fr);
            main.post(() -> {
                setBusy(false);
                String pv = fr.length() > 160 ? fr.substring(0, 160) + "..." : fr;
                voiceStatusSafe("💬 " + pv); voiceStatus.setTextColor(C_TEXT);
                setAiStatus("● AI Ready", C_GREEN, true);
                speak(fr);
                sendNotification("JARVIS", pv);
                if (continueListening) main.postDelayed(() -> startListening(), 800);
            });
        });
    }

    // ── IMAGE / FILE ──

    private void pickImage(String instruction) {
        pendingImageInstruction = instruction; expectingImage = true; expectingFile = false;
        Intent i = new Intent(Intent.ACTION_OPEN_DOCUMENT); i.addCategory(Intent.CATEGORY_OPENABLE); i.setType("image/*");
        launchPicker(i);
    }

    private void pickFile() {
        expectingImage = false; expectingFile = true;
        Intent i = new Intent(Intent.ACTION_OPEN_DOCUMENT); i.addCategory(Intent.CATEGORY_OPENABLE); i.setType("*/*");
        launchPicker(i);
    }

    private void launchPicker(Intent i) { try { startActivityForResultCompat(i); } catch (ActivityNotFoundException e) { showResult("Picker", "No picker available.", false); } }

    @SuppressWarnings("deprecation") private void startActivityForResultCompat(Intent i) { startActivityForResult(i, 0); }

    @Override @SuppressWarnings("deprecation")
    protected void onActivityResult(int requestCode, int resultCode, Intent data) {
        super.onActivityResult(requestCode, resultCode, data);
        if (requestCode == REQ_WRITE_SETTINGS) {
            if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.M && Settings.System.canWrite(this)) Toast.makeText(this, "Settings granted!", Toast.LENGTH_SHORT).show();
            return;
        }
        if (requestCode == 99) {
            if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.M && Settings.canDrawOverlays(this)) {
                startForegroundService(new Intent(this, FloatingOverlayService.class));
                overlayActive = true;
                Toast.makeText(this, "✨ Floating JARVIS is active!", Toast.LENGTH_SHORT).show();
            } else {
                Toast.makeText(this, "Overlay permission denied", Toast.LENGTH_SHORT).show();
            }
            return;
        }
        if (resultCode != RESULT_OK || data == null || data.getData() == null) { expectingImage = false; expectingFile = false; return; }
        Uri uri = data.getData();
        if (expectingImage) analyzeSelectedImage(uri);
        else if (expectingFile) analyzeSelectedFile(uri);
        expectingImage = false; expectingFile = false;
    }

    private void analyzeSelectedImage(Uri uri) {
        setBusy(true); setAiStatus("● Analyzing image...", C_YELLOW, true);
        executor.execute(() -> {
            String result;
            try (InputStream in = getContentResolver().openInputStream(uri)) {
                result = api.analyzeImage(JarvisApiClient.readBytes(in), getContentResolver().getType(uri), pendingImageInstruction);
            } catch (Exception e) { result = "Error: " + e.getMessage(); }
            String fr = result;
            main.post(() -> { setBusy(false); setAiStatus("● AI Ready", C_GREEN, true); showResult("Image AI", fr, false); });
        });
    }

    private void analyzeSelectedFile(Uri uri) {
        setBusy(true); setAiStatus("● Analyzing file...", C_YELLOW, true);
        executor.execute(() -> {
            String result;
            try (InputStream in = getContentResolver().openInputStream(uri)) {
                byte[] bytes = JarvisApiClient.readBytes(in);
                String txt = new String(bytes, StandardCharsets.UTF_8);
                if (txt.length() > 30000) txt = txt.substring(0, 30000);
                result = api.summarize("File: " + uri + "\n\n" + txt);
            } catch (Exception e) { result = "File AI reads text. Error: " + e.getMessage(); }
            String fr = result;
            main.post(() -> { setBusy(false); setAiStatus("● AI Ready", C_GREEN, true); showResult("File AI", fr, false); });
        });
    }

    private void scheduleReminder(String value) {
        String[] parts = value.split("\\|", 2);
        String text = parts[0].trim();
        int minutes = parts.length > 1 ? parseInt(parts[1].trim(), 10) : 10;
        long trigger = System.currentTimeMillis() + minutes * 60_000L;
        memory.addReminder(text, trigger);
        Intent intent = new Intent(this, ReminderReceiver.class);
        intent.putExtra("text", text);
        PendingIntent pi = PendingIntent.getBroadcast(this, (int) trigger, intent, PendingIntent.FLAG_UPDATE_CURRENT | PendingIntent.FLAG_IMMUTABLE);
        ((AlarmManager) getSystemService(ALARM_SERVICE)).set(AlarmManager.RTC_WAKEUP, trigger, pi);
        logs.add("INFO", "Reminder: " + text);
        sendNotification("⏰ Reminder", text);
        Toast.makeText(this, "⏰ " + minutes + " min: " + text, Toast.LENGTH_SHORT).show();
    }

    private void showResult(String title, String message, boolean speak) {
        if (speak) speak(message);
        String url = JsonUtils.firstUrl(message);
        TextView v = new TextView(this); v.setText(message); v.setTextSize(13);
        v.setTextColor(Color.WHITE); v.setTextIsSelectable(true);
        v.setPadding(dp(12), dp(8), dp(12), dp(8)); v.setLineSpacing(dp(2), 1.05f);
        ScrollView sv = new ScrollView(this); sv.addView(v);
        AlertDialog.Builder b = new AlertDialog.Builder(this).setTitle(title).setView(sv)
                .setNegativeButton("Close", null).setPositiveButton("📋 Copy", null);
        if (url != null) b.setNeutralButton("🔗 Open", (d, w) -> openUrl(url));
        AlertDialog d = b.create();
        d.setOnShowListener(s -> d.getButton(AlertDialog.BUTTON_POSITIVE).setOnClickListener(c -> {
            ((ClipboardManager) getSystemService(CLIPBOARD_SERVICE)).setPrimaryClip(ClipData.newPlainText("JARVIS", message));
            Toast.makeText(this, "📋 Copied", Toast.LENGTH_SHORT).show();
        }));
        d.show();
    }

    private void openUrl(String url) {
        url = url == null ? "" : url.trim();
        if (!url.startsWith("http")) url = "https://" + url;
        try { startActivity(new Intent(Intent.ACTION_VIEW, Uri.parse(url))); }
        catch (Exception e) { showResult("Open URL", "Error: " + e.getMessage(), false); }
    }

    private void speak(String text) {
        if (tts == null || text == null) return;
        tts.speak(text.replaceAll("https?://\\S+", "link in result").replace('\n', ' ')
                .substring(0, Math.min(500, text.length())), TextToSpeech.QUEUE_FLUSH, null, "jarvis");
    }

    private void voiceStatusSafe(String v) { if (voiceStatus != null) voiceStatus.setText(v); }

    private void setBusy(boolean busy) {
        if (busy) { modeText.setText("⏳"); statusDot.setTextColor(C_CYAN); statusDot.animate().alpha(0.3f).setDuration(300).start(); }
        else { modeText.setText(speechMode ? "🎤" : "⌨️"); modeText.setTextColor(speechMode ? C_CYAN : C_PINK); statusDot.setTextColor(C_GREEN); statusDot.animate().alpha(1f).setDuration(300).start(); }
    }

    private void hideKeyboard(View v) { InputMethodManager imm = (InputMethodManager) getSystemService(INPUT_METHOD_SERVICE); if (imm != null) imm.hideSoftInputFromWindow(v.getWindowToken(), 0); }

    private void requestUsefulPermissions() {
        if (Build.VERSION.SDK_INT < Build.VERSION_CODES.M) return;
        ArrayList<String> perms = new ArrayList<>();
        if (checkSelfPermission(Manifest.permission.RECORD_AUDIO) != PackageManager.PERMISSION_GRANTED) perms.add(Manifest.permission.RECORD_AUDIO);
        if (Build.VERSION.SDK_INT >= 33 && checkSelfPermission(Manifest.permission.POST_NOTIFICATIONS) != PackageManager.PERMISSION_GRANTED) perms.add(Manifest.permission.POST_NOTIFICATIONS);
        if (checkSelfPermission(Manifest.permission.CAMERA) != PackageManager.PERMISSION_GRANTED) perms.add(Manifest.permission.CAMERA);
        if (!perms.isEmpty()) requestPermissions(perms.toArray(new String[0]), REQ_PERMISSIONS);
    }

    private String firstLine(String v) {
        if (v == null || v.trim().isEmpty()) return "Note";
        String f = v.trim().split("\\r?\\n", 2)[0];
        return f.length() > 80 ? f.substring(0, 80) : f;
    }

    private int parseInt(String v, int fb) { try { return Integer.parseInt(v.trim()); } catch (Exception e) { return fb; } }

    // ── UI BUILDERS ──

    private Button smallBtn(String label) {
        Button b = new Button(this);
        b.setText(label); b.setAllCaps(false); b.setTextSize(10);
        b.setTextColor(C_TEXT);
        GradientDrawable bg = new GradientDrawable();
        bg.setColor(0x14161E); bg.setStroke(1, 0x222A2A3E); bg.setCornerRadius(dp(10));
        b.setBackground(bg); b.setPadding(dp(8), dp(5), dp(8), dp(5));
        b.setMinHeight(0); b.setMinWidth(0); b.setIncludeFontPadding(false); b.setLineSpacing(0, 0.9f);
        return b;
    }

    private Button quickBtn(String label) {
        Button b = new Button(this);
        b.setText(label); b.setAllCaps(false); b.setTextSize(9);
        b.setTextColor(C_TEXT_SEC);
        GradientDrawable bg = new GradientDrawable();
        bg.setColor(0x0AFFFFFF); bg.setStroke(1, 0x15FFFFFF); bg.setCornerRadius(dp(8));
        b.setBackground(bg); b.setPadding(dp(4), dp(3), dp(4), dp(3));
        b.setMinHeight(0); b.setMinWidth(0); b.setIncludeFontPadding(false);
        return b;
    }

    private Button glowButton(String label, Integer accent) {
        Button b = new Button(this);
        b.setText(label); b.setAllCaps(false); b.setTextSize(11);
        b.setTextColor(accent != null ? Color.WHITE : C_TEXT);
        GradientDrawable bg = new GradientDrawable();
        if (accent != null) {
            bg.setColor(accent); bg.setCornerRadius(dp(12));
            if (Build.VERSION.SDK_INT >= 29) {
                b.setOutlineAmbientShadowColor(accent);
                b.setOutlineSpotShadowColor(accent);
            }
            b.setElevation(dp(3));
        } else {
            bg.setColor(0x14161E); bg.setStroke(1, 0x222A2A3E); bg.setCornerRadius(dp(12));
        }
        b.setBackground(bg); b.setPadding(dp(10), dp(6), dp(10), dp(6));
        b.setMinHeight(0); b.setMinWidth(0); b.setIncludeFontPadding(false);
        return b;
    }

    private void prompt(String title, String hint, String def, ValueCallback cb) {
        EditText input = new EditText(this); input.setText(def == null ? "" : def);
        input.setHint(hint); input.setTextColor(Color.WHITE); input.setHintTextColor(Color.GRAY);
        input.setSingleLine(false); input.setMinLines(1); input.setMaxLines(4);
        input.setInputType(InputType.TYPE_CLASS_TEXT | InputType.TYPE_TEXT_FLAG_MULTI_LINE);
        showInputDialog(title, input, cb);
    }

    private void promptMulti(String title, String hint, String def, ValueCallback cb) {
        EditText input = new EditText(this); input.setText(def == null ? "" : def);
        input.setHint(hint); input.setTextColor(Color.WHITE); input.setHintTextColor(Color.GRAY);
        input.setSingleLine(false); input.setMinLines(8);
        input.setInputType(InputType.TYPE_CLASS_TEXT | InputType.TYPE_TEXT_FLAG_MULTI_LINE);
        showInputDialog(title, input, cb);
    }

    private void showInputDialog(String title, EditText input, ValueCallback cb) {
        FrameLayout wrap = new FrameLayout(this); wrap.setPadding(dp(16), 0, dp(16), 0);
        wrap.addView(input, new FrameLayout.LayoutParams(-1, -2));
        AlertDialog d = new AlertDialog.Builder(this).setTitle(title).setView(wrap)
                .setNegativeButton("Cancel", null).setPositiveButton("Run", (di, w) -> cb.onValue(input.getText().toString())).create();
        d.setOnShowListener(s -> { input.requestFocus(); if (d.getWindow() != null) d.getWindow().setSoftInputMode(WindowManager.LayoutParams.SOFT_INPUT_STATE_ALWAYS_VISIBLE); });
        d.show();
    }

    private int dp(int v) { return Math.round(v * getResources().getDisplayMetrics().density); }

    private interface ValueCallback { void onValue(String value); }

    private static final class Tool {
        final String label, command, hint, defaultValue;
        Tool(String l, String c, String h, String d) { this.label = l; this.command = c; this.hint = h; this.defaultValue = d; }
    }
}
