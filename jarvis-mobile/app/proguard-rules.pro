# JARVIS Mobile ProGuard Rules
# Aggressive obfuscation to prevent reverse-engineering

# Keep application components that are referenced by the framework
-keep public class * extends android.app.Activity
-keep public class * extends android.app.Service
-keep public class * extends android.content.BroadcastReceiver
-keep public class * extends android.content.ContentProvider

# Keep AndroidManifest components
-keep public class com.jarvis.mobile.MainActivity
-keep public class com.jarvis.mobile.ReminderReceiver

# Keep all application classes (minimize to what's needed)
-keep public class com.jarvis.mobile.** { 
    public *; 
    protected *;
}

# Keep native methods
-keepclasseswithmembernames class * {
    native <methods>;
}

# Keep custom application classes
-keep class com.jarvis.mobile.** { *; }

# Keep serializable classes
-keep class * implements java.io.Serializable {
    static final long serialVersionUID;
    private static final java.io.ObjectStreamField[] serialPersistentFields;
    private void writeObject(java.io.ObjectOutputStream);
    private void readObject(java.io.ObjectInputStream);
    java.lang.Object writeReplace();
    java.lang.Object readResolve();
}

# Remove logging in release builds
-assumenosideeffects class android.util.Log {
    public static *** d(...);
    public static *** v(...);
    public static *** i(...);
}

# Aggressive renaming
-repackageclasses
-allowaccessmodification
-useuniqueclassmembernames

# Optimize aggressively
-optimizationpasses 5
-dontusemixedcaseclassnames
-verbose

# Preserve line numbers for crash reports
-keepattributes SourceFile,LineNumberTable
-renamesourcefileattribute SourceFile

# For API response classes
-keep class org.json.** { *; }

# Keep enum classes
-keepclassmembers enum * {
    public static **[] values();
    public static ** valueOf(java.lang.String);
}

# Keep annotation classes
-keepclassmembers class * {
    @java.lang.Override <methods>;
}

# Generic safety rules
-dontwarn android.**
-dontwarn javax.**
-dontwarn org.json.**
