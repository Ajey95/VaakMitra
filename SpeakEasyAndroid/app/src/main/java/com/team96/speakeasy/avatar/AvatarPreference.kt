package com.team96.speakeasy.avatar

import android.content.Context
import java.security.MessageDigest

enum class AvatarId(val wire: String, val displayName: String, val description: String) {
    MEERA("meera", "Meera", "Warm and reassuring"),
    KAVIN("kavin", "Kavin", "Friendly and encouraging"),
    NILA("nila", "Nila", "Calm and gentle"),
    PIPPIN("pippin", "Pippin", "Playful storybook friend");

    companion object { fun from(value: String?) = entries.firstOrNull { it.wire == value } ?: MEERA }
}

enum class AvatarPalette(val wire: String, val displayName: String) {
    CORAL_TEAL("coral-teal", "Coral & teal"), SUNRISE("sunrise", "Sunrise"), LOTUS("lotus", "Lotus");
    companion object { fun from(value: String?) = entries.firstOrNull { it.wire == value } ?: CORAL_TEAL }
}

enum class AvatarMotion(val wire: String, val displayName: String, val description: String) {
    GENTLE("gentle", "Gentle", "Natural breathing and short gestures"),
    REDUCED("reduced", "Reduced", "Slower, smaller reactions"),
    STILL("still", "Still", "Expressions without body movement");
    companion object { fun from(value: String?) = entries.firstOrNull { it.wire == value } ?: GENTLE }
}

data class AvatarPreference(
    val schemaVersion: Int = 1,
    val avatarId: AvatarId = AvatarId.MEERA,
    val palette: AvatarPalette = AvatarPalette.CORAL_TEAL,
    val motion: AvatarMotion = AvatarMotion.GENTLE,
) {
    companion object {
        /** DEC-026/AVT-001..003: only closed-catalogue values can enter the renderer. */
        fun normalize(avatarId: String?, palette: String?, motion: String?) = AvatarPreference(
            avatarId = AvatarId.from(avatarId), palette = AvatarPalette.from(palette), motion = AvatarMotion.from(motion)
        )
    }
}

object AvatarPreferenceStore {
    private const val STORE = "vaakmitra_avatar_v1"

    private fun scope(childId: String?): String {
        val raw = childId?.trim().orEmpty().ifEmpty { "device-preview" }
        return MessageDigest.getInstance("SHA-256").digest(raw.toByteArray())
            .take(8).joinToString("") { "%02x".format(it) }
    }

    fun load(context: Context, childId: String?): AvatarPreference {
        val prefs = context.getSharedPreferences(STORE, Context.MODE_PRIVATE)
        val prefix = scope(childId)
        return AvatarPreference.normalize(
            prefs.getString("${prefix}_avatar", null),
            prefs.getString("${prefix}_palette", null),
            prefs.getString("${prefix}_motion", null),
        )
    }

    fun save(context: Context, childId: String?, value: AvatarPreference): AvatarPreference {
        val normalized = AvatarPreference.normalize(value.avatarId.wire, value.palette.wire, value.motion.wire)
        val prefix = scope(childId)
        context.getSharedPreferences(STORE, Context.MODE_PRIVATE).edit()
            .putString("${prefix}_avatar", normalized.avatarId.wire)
            .putString("${prefix}_palette", normalized.palette.wire)
            .putString("${prefix}_motion", normalized.motion.wire)
            .apply()
        return normalized
    }
}
