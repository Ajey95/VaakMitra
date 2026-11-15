package com.team96.speakeasy.ui.components

import androidx.compose.foundation.border
import androidx.compose.foundation.background
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.OutlinedTextField
import androidx.compose.material3.OutlinedTextFieldDefaults
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.text.input.KeyboardType
import androidx.compose.ui.text.input.VisualTransformation
import androidx.compose.foundation.text.KeyboardOptions
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp

/** Frosted translucent panel that holds form content over a gradient. */
@Composable
fun GlassCard(content: @Composable () -> Unit) {
    Column(
        Modifier
            .fillMaxWidth()
            .clip(RoundedCornerShape(18.dp))
            .background(HeritageCard)
            .border(1.3.dp,HeritageGold,RoundedCornerShape(18.dp))
            .padding(22.dp)
    ) { content() }
}

/** Rounded, high-contrast text field that reads well on colorful backgrounds. */
@Composable
fun CuteTextField(
    value: String,
    onChange: (String) -> Unit,
    label: String,
    keyboard: KeyboardType = KeyboardType.Text,
    visual: VisualTransformation = VisualTransformation.None,
    modifier: Modifier = Modifier,
) {
    OutlinedTextField(
        value = value,
        onValueChange = onChange,
        label = { Text(label, fontWeight = FontWeight.Bold) },
        singleLine = true,
        visualTransformation = visual,
        keyboardOptions = KeyboardOptions(keyboardType = keyboard),
        shape = RoundedCornerShape(18.dp),
        modifier = modifier.fillMaxWidth(),
        colors = OutlinedTextFieldDefaults.colors(
            focusedTextColor = HeritageInk,
            unfocusedTextColor = HeritageInk,
            cursorColor = HeritageMaroon,
            focusedBorderColor = HeritageMaroon,
            unfocusedBorderColor = HeritageGold,
            focusedLabelColor = HeritageMaroon,
            unfocusedLabelColor = HeritageMuted,
            focusedContainerColor = HeritageCard,
            unfocusedContainerColor = HeritageCard,
        )
    )
}
