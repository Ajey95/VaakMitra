# Keep Moshi generated adapters
-keep class com.team96.speakeasy.data.** { *; }
-keepclassmembers class kotlin.Metadata { *; }
-dontwarn okhttp3.**
-dontwarn retrofit2.**

# MST-008: preserve the JNI-facing ONNX Runtime surface in review builds.
-keep class ai.onnxruntime.** { *; }
