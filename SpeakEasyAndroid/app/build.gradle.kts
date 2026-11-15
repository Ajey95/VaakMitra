import java.io.File
import java.security.MessageDigest
import groovy.json.JsonSlurper

plugins {
    id("com.android.application")
    id("org.jetbrains.kotlin.android")
}

// DEC068: explicit temporary build storage keeps review APKs off the full data drive.
providers.gradleProperty("vaakmitraBuildRoot").orNull?.let { requested ->
    val root = File(requested)
    require(root.isAbsolute) { "vaakmitraBuildRoot must be absolute" }
    layout.buildDirectory.set(root.resolve("app"))
}
val reviewAbi = providers.gradleProperty("vaakmitraReviewAbi").orNull
require(reviewAbi == null || reviewAbi in setOf("arm64-v8a", "x86_64")) { "Unsupported review ABI" }
val extraAssets = providers.gradleProperty("vaakmitraExtraAssets").orNull?.let(::File)
val verifyOfflineReviewAssets = tasks.register("verifyOfflineReviewAssets") {
    // DEC079: delivery may change, but the accepted model and its evidence gates may not.
    doLast {
        extraAssets?.let { root ->
            require(root.isAbsolute && root.isDirectory) { "Extra assets must be an existing absolute directory" }
            val relative = "vaakmitra/phoneme-ta-backbone-v1"
            val source = JsonSlurper().parse(file("src/main/assets/$relative/bundle.json")) as Map<*, *>
            val staged = JsonSlurper().parse(root.resolve("$relative/bundle.json")) as Map<*, *>
            val deliveryFields = setOf("model_delivery", "review_install_requires_model_provisioning")
            require(source.filterKeys { it !in deliveryFields } == staged.filterKeys { it !in deliveryFields }) { "Review bundle changed model evidence" }
            require(staged["model_delivery"] == "bundled_asset_and_authenticated_app_private_cache" && staged["review_install_requires_model_provisioning"] == false)
            fun sha256(file: File): String {
                val digest = MessageDigest.getInstance("SHA-256")
                file.inputStream().buffered().use { input ->
                    val buffer = ByteArray(1024 * 1024)
                    while (true) { val count = input.read(buffer); if (count < 0) break; digest.update(buffer, 0, count) }
                }
                return digest.digest().joinToString("") { "%02x".format(it) }
            }
            val model = root.resolve("$relative/phoneme.fp32.onnx")
            require(model.length() == 1262607977L && sha256(model) == "ff41636b23a41baa0ebb08e59f00fe684c9a054e40a9c41eb685542b5f5020cf") { "Review model identity mismatch" }
            require(sha256(root.resolve("$relative/vocabulary.json")) == source["vocabulary_sha256"]) { "Review vocabulary mismatch" }
        }
    }
}
tasks.matching { it.name == "preDebugBuild" }.configureEach { dependsOn(verifyOfflineReviewAssets) }

android {
    namespace = "com.team96.speakeasy"
    // Compile against the locally installed SDK; targetSdk remains frozen at 34.
    compileSdk = 36
    buildToolsVersion = "35.0.0"

    defaultConfig {
        applicationId = "com.team96.speakeasy"
        minSdk = 26
        targetSdk = 34
        versionCode = 1
        versionName = "1.0"

        testInstrumentationRunner = "androidx.test.runner.AndroidJUnitRunner"
        vectorDrawables {
            useSupportLibrary = true
        }

    }

    buildTypes {
        debug {
            val backendUrl = (project.findProperty("backendUrl") as String?)
                ?: "http://10.0.2.2:8000/"
            buildConfigField("String", "BASE_URL", "\"$backendUrl\"")
        }
        release {
            val configuredBackendUrl = project.findProperty("backendUrl") as String?
            val releaseRequested = gradle.startParameter.taskNames.any {
                it.contains("release", ignoreCase = true)
            }
            require(!releaseRequested || configuredBackendUrl != null) {
                "Release builds require -PbackendUrl=https://<private-edge-host>/"
            }
            val backendUrl = configuredBackendUrl ?: "https://private-edge.invalid/"
            require(backendUrl.startsWith("https://")) { "Release backendUrl must use HTTPS" }
            require("onrender.com" !in backendUrl && "vercel.app" !in backendUrl) {
                "Public-cloud inference URLs are prohibited by VAAKMITRA_FINAL_SSOT.md"
            }
            buildConfigField("String", "BASE_URL", "\"$backendUrl\"")
            isMinifyEnabled = true
            isShrinkResources = true
            proguardFiles(
                getDefaultProguardFile("proguard-android-optimize.txt"),
                "proguard-rules.pro"
            )
        }
    }
    compileOptions {
        sourceCompatibility = JavaVersion.VERSION_17
        targetCompatibility = JavaVersion.VERSION_17
    }
    kotlinOptions {
        jvmTarget = "17"
    }
    buildFeatures {
        compose = true
        buildConfig = true
    }
    composeOptions {
        kotlinCompilerExtensionVersion = "1.5.14"
    }
    extraAssets?.let { sourceSets.getByName("debug").assets.srcDir(it) }
    androidResources { noCompress += "onnx" }
    packaging {
        resources {
            excludes += "/META-INF/{AL2.0,LGPL2.1}"
        }
    }
    // MST-010: deliver an ARM64 review APK without bundling unrelated native ABIs.
    splits {
        abi {
            isEnable = true
            reset()
            include(*(reviewAbi?.let { arrayOf(it) } ?: arrayOf("arm64-v8a", "x86_64")))
            isUniversalApk = false
        }
    }
}

dependencies {
    val composeBom = platform("androidx.compose:compose-bom:2024.06.00")
    implementation(composeBom)

    implementation("androidx.core:core-ktx:1.13.1")
    implementation("androidx.lifecycle:lifecycle-runtime-ktx:2.8.2")
    implementation("androidx.lifecycle:lifecycle-viewmodel-compose:2.8.2")
    implementation("androidx.lifecycle:lifecycle-runtime-compose:2.8.2")
    implementation("androidx.activity:activity-compose:1.9.0")

    // Compose
    implementation("androidx.compose.ui:ui")
    implementation("androidx.compose.ui:ui-graphics")
    implementation("androidx.compose.ui:ui-tooling-preview")
    implementation("androidx.compose.foundation:foundation")
    implementation("androidx.compose.material3:material3")
    implementation("androidx.compose.material:material-icons-extended")
    implementation("androidx.compose.animation:animation")

    // Navigation
    implementation("androidx.navigation:navigation-compose:2.7.7")

    // Networking
    implementation("com.squareup.retrofit2:retrofit:2.11.0")
    implementation("com.squareup.retrofit2:converter-moshi:2.11.0")
    implementation("com.squareup.moshi:moshi:1.15.1")
    implementation("com.squareup.moshi:moshi-kotlin:1.15.1")
    implementation("com.squareup.okhttp3:okhttp:4.12.0")
    implementation("com.squareup.okhttp3:logging-interceptor:4.12.0")

    // DataStore (token persistence)
    implementation("androidx.datastore:datastore-preferences:1.1.1")

    // Coroutines
    implementation("org.jetbrains.kotlinx:kotlinx-coroutines-android:1.8.1")

    // DEC-028/MST-008: fully offline CPU inference; NNAPI remains disabled.
    implementation("com.microsoft.onnxruntime:onnxruntime-android:1.30.0")

    testImplementation("junit:junit:4.13.2")
    androidTestImplementation("androidx.test.ext:junit:1.2.1")
    androidTestImplementation("androidx.test:runner:1.6.1")

    debugImplementation("androidx.compose.ui:ui-tooling")
}
