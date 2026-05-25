package com.jarvis.mobile;

import android.app.ActivityManager;
import android.content.Context;
import android.content.Intent;
import android.content.IntentFilter;
import android.net.ConnectivityManager;
import android.net.Network;
import android.net.NetworkCapabilities;
import android.os.BatteryManager;
import android.os.Environment;
import android.os.StatFs;

import java.io.BufferedReader;
import java.io.FileReader;
import java.util.Locale;

final class DeviceStats {
    private final Context context;

    DeviceStats(Context context) {
        this.context = context.getApplicationContext();
    }

    String summaryOneLine() {
        int batt = batteryLevel();
        String net = network();
        return "Battery: " + (batt >= 0 ? batt + "%" : "?") + " | RAM: " + ramPercent() + "% | Network: " + net + " | CPU: " + cpuPercent() + "%";
    }

    int batteryLevel() {
        Intent intent = context.registerReceiver(null, new IntentFilter(Intent.ACTION_BATTERY_CHANGED));
        if (intent == null) return -1;
        int level = intent.getIntExtra(BatteryManager.EXTRA_LEVEL, -1);
        int scale = intent.getIntExtra(BatteryManager.EXTRA_SCALE, -1);
        return scale > 0 ? Math.round(level * 100f / scale) : -1;
    }

    int ramPercent() {
        ActivityManager manager = (ActivityManager) context.getSystemService(Context.ACTIVITY_SERVICE);
        ActivityManager.MemoryInfo info = new ActivityManager.MemoryInfo();
        manager.getMemoryInfo(info);
        long used = info.totalMem - info.availMem;
        return (int) Math.round(used * 100f / info.totalMem);
    }

    int cpuPercent() {
        try (BufferedReader reader = new BufferedReader(new FileReader("/proc/loadavg"))) {
            String[] parts = reader.readLine().split("\\s+");
            float oneMinute = Float.parseFloat(parts[0]);
            int cores = Math.max(1, Runtime.getRuntime().availableProcessors());
            return Math.min(100, Math.round(oneMinute * 100f / cores));
        } catch (Exception e) {
            return -1;
        }
    }

    String summary() {
        return "Battery: " + battery()
                + "\nRAM: " + ram()
                + "\nStorage: " + storage()
                + "\nNetwork: " + network()
                + "\nCPU load: " + cpuLoad();
    }

    String battery() {
        Intent intent = context.registerReceiver(null, new IntentFilter(Intent.ACTION_BATTERY_CHANGED));
        if (intent == null) {
            return "unavailable";
        }
        int level = intent.getIntExtra(BatteryManager.EXTRA_LEVEL, -1);
        int scale = intent.getIntExtra(BatteryManager.EXTRA_SCALE, -1);
        int status = intent.getIntExtra(BatteryManager.EXTRA_STATUS, -1);
        int percent = scale > 0 ? Math.round(level * 100f / scale) : -1;
        String charging = status == BatteryManager.BATTERY_STATUS_CHARGING
                || status == BatteryManager.BATTERY_STATUS_FULL ? "charging" : "not charging";
        return percent >= 0 ? percent + "%, " + charging : "unavailable";
    }

    String ram() {
        ActivityManager manager = (ActivityManager) context.getSystemService(Context.ACTIVITY_SERVICE);
        ActivityManager.MemoryInfo info = new ActivityManager.MemoryInfo();
        manager.getMemoryInfo(info);
        long used = info.totalMem - info.availMem;
        return formatBytes(used) + " / " + formatBytes(info.totalMem)
                + " (" + Math.round(used * 100f / info.totalMem) + "%)";
    }

    String storage() {
        StatFs fs = new StatFs(Environment.getDataDirectory().getPath());
        long total = fs.getBlockCountLong() * fs.getBlockSizeLong();
        long free = fs.getAvailableBlocksLong() * fs.getBlockSizeLong();
        long used = total - free;
        return formatBytes(used) + " / " + formatBytes(total)
                + " (" + Math.round(used * 100f / total) + "%)";
    }

    String network() {
        ConnectivityManager manager = (ConnectivityManager) context.getSystemService(Context.CONNECTIVITY_SERVICE);
        Network network = manager.getActiveNetwork();
        if (network == null) {
            return "offline";
        }
        NetworkCapabilities caps = manager.getNetworkCapabilities(network);
        if (caps == null) {
            return "connected";
        }
        if (caps.hasTransport(NetworkCapabilities.TRANSPORT_WIFI)) {
            return "Wi-Fi";
        }
        if (caps.hasTransport(NetworkCapabilities.TRANSPORT_CELLULAR)) {
            return "cellular";
        }
        if (caps.hasTransport(NetworkCapabilities.TRANSPORT_ETHERNET)) {
            return "ethernet";
        }
        return "connected";
    }

    String cpuLoad() {
        try (BufferedReader reader = new BufferedReader(new FileReader("/proc/loadavg"))) {
            String[] parts = reader.readLine().split("\\s+");
            float oneMinute = Float.parseFloat(parts[0]);
            int cores = Math.max(1, Runtime.getRuntime().availableProcessors());
            int percent = Math.min(100, Math.round(oneMinute * 100f / cores));
            return percent + "% (" + cores + " cores)";
        } catch (Exception e) {
            return "unavailable";
        }
    }

    private String formatBytes(long bytes) {
        if (bytes < 1024) {
            return bytes + " B";
        }
        double value = bytes;
        String[] units = {"B", "KB", "MB", "GB", "TB"};
        int unit = 0;
        while (value >= 1024 && unit < units.length - 1) {
            value /= 1024;
            unit++;
        }
        return String.format(Locale.US, "%.1f %s", value, units[unit]);
    }
}
