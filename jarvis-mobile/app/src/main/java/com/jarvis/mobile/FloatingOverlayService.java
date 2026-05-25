package com.jarvis.mobile;

import android.app.Notification;
import android.app.NotificationChannel;
import android.app.NotificationManager;
import android.app.Service;
import android.content.Context;
import android.content.Intent;
import android.graphics.Color;
import android.graphics.PixelFormat;
import android.graphics.drawable.GradientDrawable;
import android.os.Build;
import android.os.Handler;
import android.os.IBinder;
import android.os.Looper;
import android.view.Gravity;
import android.view.MotionEvent;
import android.view.View;
import android.view.ViewGroup;
import android.view.WindowManager;
import android.view.animation.AccelerateDecelerateInterpolator;
import android.view.animation.AlphaAnimation;
import android.view.animation.DecelerateInterpolator;
import android.view.animation.OvershootInterpolator;
import android.view.animation.ScaleAnimation;
import android.widget.Button;
import android.widget.EditText;
import android.widget.FrameLayout;
import android.widget.LinearLayout;
import android.widget.ScrollView;
import android.widget.TextView;

import java.util.concurrent.ExecutorService;
import java.util.concurrent.Executors;

public final class FloatingOverlayService extends Service {
    private static final String CHANNEL_ID = "jarvis_overlay";
    private static final int NOTIF_ID = 42;

    private WindowManager wm;
    private FrameLayout overlayView;
    private View bubbleView;
    private View miniPanel;
    private Handler main = new Handler(Looper.getMainLooper());
    private ExecutorService executor = Executors.newFixedThreadPool(2);
    private boolean expanded = false;

    private int initialX, initialY;
    private float initialTouchX, initialTouchY;

    private JarvisApiClient api;
    private LocalMemory memory;
    private DeviceStats deviceStats;
    private JarvisBrain brain;

    @Override
    public void onCreate() {
        super.onCreate();
        wm = (WindowManager) getSystemService(WINDOW_SERVICE);
        api = new JarvisApiClient(new ApiKeys(this));
        memory = new LocalMemory(this);
        deviceStats = new DeviceStats(this);
        brain = new JarvisBrain(api, memory, deviceStats);
        createChannel();
        buildOverlay();
    }

    private void createChannel() {
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.O) {
            NotificationChannel ch = new NotificationChannel(CHANNEL_ID, "JARVIS Float",
                    NotificationManager.IMPORTANCE_LOW);
            ch.setDescription("Floating AI assistant");
            NotificationManager nm = (NotificationManager) getSystemService(NOTIFICATION_SERVICE);
            if (nm != null) nm.createNotificationChannel(ch);
        }
    }

    @Override
    public int onStartCommand(Intent intent, int flags, int startId) {
        Notification.Builder b = new Notification.Builder(this, CHANNEL_ID)
                .setSmallIcon(android.R.drawable.ic_dialog_info)
                .setContentTitle("JARVIS AI")
                .setContentText("Floating assistant is active")
                .setOngoing(true);
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.Q) {
            b.setForegroundServiceBehavior(Notification.FOREGROUND_SERVICE_IMMEDIATE);
        }
        startForeground(NOTIF_ID, Build.VERSION.SDK_INT >= 26 ? b.build() : b.getNotification());
        return START_STICKY;
    }

    @Override
    public IBinder onBind(Intent intent) { return null; }

    private void buildOverlay() {
        final int LAYOUT_FLAG;
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.O) {
            LAYOUT_FLAG = WindowManager.LayoutParams.TYPE_APPLICATION_OVERLAY;
        } else {
            LAYOUT_FLAG = WindowManager.LayoutParams.TYPE_PHONE;
        }

        final int FLAGS = WindowManager.LayoutParams.FLAG_NOT_FOCUSABLE
                | WindowManager.LayoutParams.FLAG_LAYOUT_NO_LIMITS
                | WindowManager.LayoutParams.FLAG_NOT_TOUCH_MODAL;

        WindowManager.LayoutParams params = new WindowManager.LayoutParams(
                WindowManager.LayoutParams.WRAP_CONTENT,
                WindowManager.LayoutParams.WRAP_CONTENT,
                LAYOUT_FLAG,
                FLAGS,
                PixelFormat.TRANSLUCENT);
        params.gravity = Gravity.TOP | Gravity.START;
        params.x = 100;
        params.y = 200;

        overlayView = new FrameLayout(this);

        // ── Bubble view (circular glowing AI icon) ──
        bubbleView = buildBubble();
        overlayView.addView(bubbleView);

        // ── Mini panel (hidden by default) ──
        miniPanel = buildMiniPanel();
        miniPanel.setVisibility(View.GONE);
        overlayView.addView(miniPanel);

        makeDraggable(bubbleView, params);

        bubbleView.setOnClickListener(v -> togglePanel(params));

        wm.addView(overlayView, params);

        // Start bubble glow animation
        startBubbleAnim();
    }

    private View buildBubble() {
        FrameLayout bubble = new FrameLayout(this);
        bubble.setPadding(dp(4), dp(4), dp(4), dp(4));

        // Glow ring
        View glow = new View(this);
        GradientDrawable gd = new GradientDrawable();
        gd.setShape(GradientDrawable.OVAL);
        gd.setColor(0xFFFF6EC7);
        gd.setGradientType(GradientDrawable.RADIAL_GRADIENT);
        gd.setGradientRadius(40f);
        glow.setBackground(gd);
        glow.setAlpha(0.15f);
        bubble.addView(glow, dp(56), dp(56));
        FrameLayout.LayoutParams glp = (FrameLayout.LayoutParams) glow.getLayoutParams();
        glp.gravity = Gravity.CENTER;

        // Inner circle
        View inner = new View(this);
        GradientDrawable ig = new GradientDrawable();
        ig.setShape(GradientDrawable.OVAL);
        ig.setColors(new int[]{0xFFFF6EC7, 0xFF3B82F6, 0xFF8A2BE2});
        ig.setGradientType(GradientDrawable.SWEEP_GRADIENT);
        inner.setBackground(ig);
        bubble.addView(inner, dp(44), dp(44));
        FrameLayout.LayoutParams ilp = (FrameLayout.LayoutParams) inner.getLayoutParams();
        ilp.gravity = Gravity.CENTER;

        // AI icon text
        TextView aiIcon = new TextView(this);
        aiIcon.setText("J");
        aiIcon.setTextSize(18);
        aiIcon.setTextColor(Color.WHITE);
        aiIcon.setTypeface(null, android.graphics.Typeface.BOLD);
        aiIcon.setGravity(Gravity.CENTER);
        bubble.addView(aiIcon, dp(44), dp(44));
        FrameLayout.LayoutParams alp = (FrameLayout.LayoutParams) aiIcon.getLayoutParams();
        alp.gravity = Gravity.CENTER;

        return bubble;
    }

    private View buildMiniPanel() {
        LinearLayout panel = new LinearLayout(this);
        panel.setOrientation(LinearLayout.VERTICAL);
        panel.setPadding(dp(8), dp(8), dp(8), dp(8));

        GradientDrawable pbg = new GradientDrawable();
        pbg.setColor(0xFF0B0B0F);
        pbg.setStroke(1, 0xFF2A2A3E);
        pbg.setCornerRadius(dp(16));
        panel.setBackground(pbg);

        // Header
        LinearLayout header = new LinearLayout(this);
        header.setGravity(Gravity.CENTER_VERTICAL);
        header.setPadding(dp(4), dp(4), dp(4), dp(4));

        View dot = new View(this);
        GradientDrawable dg = new GradientDrawable();
        dg.setShape(GradientDrawable.OVAL);
        dg.setColor(0xFF10B981);
        dot.setBackground(dg);
        header.addView(dot, dp(8), dp(8));

        View hsp = new View(this);
        hsp.setLayoutParams(new LinearLayout.LayoutParams(dp(6), 0));
        header.addView(hsp);

        TextView title = new TextView(this);
        title.setText("JARVIS AI");
        title.setTextSize(12);
        title.setTextColor(0xFFFF6EC7);
        title.setTypeface(null, android.graphics.Typeface.BOLD);
        header.addView(title);

        View spacer = new View(this);
        spacer.setLayoutParams(new LinearLayout.LayoutParams(0, 0, 1));
        header.addView(spacer);

        Button closeBtn = new Button(this);
        closeBtn.setText("✕");
        closeBtn.setTextSize(10);
        closeBtn.setTextColor(0xFF7A7A9A);
        closeBtn.setBackgroundColor(Color.TRANSPARENT);
        closeBtn.setPadding(dp(4), dp(2), dp(4), dp(2));
        closeBtn.setMinHeight(0);
        closeBtn.setMinWidth(0);
        closeBtn.setOnClickListener(v -> stopSelf());
        header.addView(closeBtn);

        panel.addView(header);

        View sep = new View(this);
        sep.setBackgroundColor(0x1AFFFFFF);
        panel.addView(sep, new LinearLayout.LayoutParams(-1, 1));

        // Response area
        final TextView responseText = new TextView(this);
        responseText.setText("Hey! How can I help you?");
        responseText.setTextSize(11);
        responseText.setTextColor(0xFFCBD5E1);
        responseText.setPadding(dp(4), dp(8), dp(4), dp(8));
        responseText.setMinHeight(dp(40));
        responseText.setLineSpacing(dp(2), 1.0f);
        panel.addView(responseText, new LinearLayout.LayoutParams(-1, dp(80)));

        // Input row
        LinearLayout inputRow = new LinearLayout(this);
        inputRow.setGravity(Gravity.CENTER_VERTICAL);
        inputRow.setPadding(0, dp(4), 0, 0);

        final EditText input = new EditText(this);
        input.setHint("Ask anything...");
        input.setTextSize(11);
        input.setTextColor(0xFFEAEAEA);
        input.setHintTextColor(0xFF7A7A9A);
        GradientDrawable ibg = new GradientDrawable();
        ibg.setColor(0x14161E);
        ibg.setStroke(1, 0x222A2A3E);
        ibg.setCornerRadius(dp(10));
        input.setBackground(ibg);
        input.setPadding(dp(10), dp(6), dp(10), dp(6));
        input.setSingleLine(true);
        inputRow.addView(input, new LinearLayout.LayoutParams(0, dp(36), 1));

        View isp = new View(this);
        isp.setLayoutParams(new LinearLayout.LayoutParams(dp(4), 0));
        inputRow.addView(isp);

        Button sendBtn = new Button(this);
        sendBtn.setText("➤");
        sendBtn.setTextSize(14);
        sendBtn.setTextColor(Color.WHITE);
        GradientDrawable sbg = new GradientDrawable();
        sbg.setColor(0xFFFF6EC7);
        sbg.setCornerRadius(dp(10));
        sendBtn.setBackground(sbg);
        sendBtn.setMinHeight(0);
        sendBtn.setMinWidth(0);
        sendBtn.setPadding(dp(8), dp(4), dp(8), dp(4));
        sendBtn.setOnClickListener(v -> {
            String text = input.getText().toString().trim();
            if (text.isEmpty()) return;
            input.setText("");
            responseText.setText("💭 Thinking...");
            executor.execute(() -> {
                String result;
                try { result = brain.run(text); }
                catch (Exception e) { result = "Sorry: " + e.getMessage(); }
                String fr = result;
                main.post(() -> responseText.setText(fr.length() > 200 ? fr.substring(0, 200) + "..." : fr));
            });
        });
        inputRow.addView(sendBtn, dp(36), dp(36));

        panel.addView(inputRow);

        return panel;
    }

    private void togglePanel(WindowManager.LayoutParams params) {
        expanded = !expanded;
        if (expanded) {
            miniPanel.setVisibility(View.VISIBLE);
            bubbleView.setVisibility(View.GONE);
            params.width = dp(260);
            params.height = dp(200);
            params.flags = WindowManager.LayoutParams.FLAG_LAYOUT_NO_LIMITS
                    | WindowManager.LayoutParams.FLAG_NOT_TOUCH_MODAL;
            wm.updateViewLayout(overlayView, params);
        } else {
            miniPanel.setVisibility(View.GONE);
            bubbleView.setVisibility(View.VISIBLE);
            params.width = WindowManager.LayoutParams.WRAP_CONTENT;
            params.height = WindowManager.LayoutParams.WRAP_CONTENT;
            params.flags = WindowManager.LayoutParams.FLAG_NOT_FOCUSABLE
                    | WindowManager.LayoutParams.FLAG_LAYOUT_NO_LIMITS
                    | WindowManager.LayoutParams.FLAG_NOT_TOUCH_MODAL;
            wm.updateViewLayout(overlayView, params);
        }
    }

    private void makeDraggable(View view, final WindowManager.LayoutParams params) {
        view.setOnTouchListener((v, event) -> {
            switch (event.getAction()) {
                case MotionEvent.ACTION_DOWN:
                    initialX = params.x;
                    initialY = params.y;
                    initialTouchX = event.getRawX();
                    initialTouchY = event.getRawY();
                    return false;
                case MotionEvent.ACTION_MOVE:
                    params.x = initialX + (int) (event.getRawX() - initialTouchX);
                    params.y = initialY + (int) (event.getRawY() - initialTouchY);
                    wm.updateViewLayout(overlayView, params);
                    return true;
            }
            return false;
        });
    }

    private void startBubbleAnim() {
        main.post(new Runnable() {
            boolean expand = true;
            public void run() {
                if (bubbleView == null) return;
                float s = expand ? 1.1f : 0.9f;
                View inner = ((FrameLayout) bubbleView).getChildAt(1);
                if (inner != null) {
                    inner.animate().scaleX(s).scaleY(s).alpha(expand ? 1f : 0.7f)
                            .setDuration(1200).setInterpolator(new AccelerateDecelerateInterpolator()).start();
                }
                expand = !expand;
                main.postDelayed(this, 1200);
            }
        });

        main.post(new Runnable() {
            float deg = 0;
            public void run() {
                if (bubbleView == null) return;
                View inner = ((FrameLayout) bubbleView).getChildAt(1);
                if (inner != null) {
                    deg += 1f;
                    inner.setRotation(deg);
                }
                main.postDelayed(this, 50);
            }
        });
    }

    @Override
    public void onDestroy() {
        super.onDestroy();
        executor.shutdownNow();
        main.removeCallbacksAndMessages(null);
        if (wm != null && overlayView != null) {
            try { wm.removeView(overlayView); } catch (Exception e) { }
        }
    }

    private int dp(int v) { return Math.round(v * getResources().getDisplayMetrics().density); }
}
