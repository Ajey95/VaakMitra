package com.team96.speakeasy.ui.components

import androidx.compose.foundation.Canvas
import androidx.compose.foundation.background
import androidx.compose.foundation.border
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.automirrored.rounded.ArrowBack
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.geometry.Offset
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.graphics.Path
import androidx.compose.ui.graphics.drawscope.Stroke
import androidx.compose.ui.graphics.drawscope.rotate
import androidx.compose.ui.text.font.FontFamily
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.style.TextAlign
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import com.team96.speakeasy.journey.LetterPracticeSettings

val HeritagePaper = Color(0xFFFFF6E3)
val HeritageCard = Color(0xFFFFFBF2)
val HeritageInk = Color(0xFF292438)
val HeritageMaroon = Color(0xFF762B32)
val HeritageWood = Color(0xFF9B643D)
val HeritageGold = Color(0xFFB68B42)
val HeritageMuted = Color(0xFF786A59)
val HeritageSlate = Color(0xFF293B3A)

/** DEC-053/054: static printed-paper motifs, never motion during focused learning. */
@Composable
fun HeritagePage(content: @Composable BoxScope.() -> Unit) {
    Box(Modifier.fillMaxSize().background(HeritagePaper)) {
        Canvas(Modifier.fillMaxSize()) {
            val step = 17.dp.toPx()
            var y = 0f
            while (y < size.height) {
                var x = (y.toInt() % 29).toFloat()
                while (x < size.width) {
                    drawCircle(HeritageWood.copy(alpha = .035f), .6.dp.toPx(), Offset(x,y))
                    x += step
                }
                y += step
            }
            drawRect(HeritagePaper, size = androidx.compose.ui.geometry.Size(size.width, 26.dp.toPx()))
            val baseline = size.height - 5.dp.toPx()
            drawLine(HeritageMaroon, Offset(0f,baseline),Offset(size.width,baseline), 5.dp.toPx())
            val unit = 18.dp.toPx()
            var start = 0f
            while(start < size.width) {
                val tile = Path().apply { moveTo(start,baseline-10.dp.toPx()); lineTo(start+unit/2,baseline-3.dp.toPx()); lineTo(start+unit,baseline-10.dp.toPx()) }
                drawPath(tile,HeritageMaroon.copy(alpha=.7f), style=Stroke(1.4.dp.toPx()))
                start += unit
            }
        }
        content()
    }
}

@Composable
fun KolamMark(modifier: Modifier = Modifier, color: Color = HeritageMaroon) {
    Canvas(modifier) {
        val cx=size.width/2;val cy=size.height/2;val r=minOf(size.width,size.height)/5
        repeat(4) { i ->
            rotate(i*90f,Offset(cx,cy)) {
                val petal=Path().apply {
                    moveTo(cx,cy-r*.25f)
                    cubicTo(cx-r*1.1f,cy-r*1.5f,cx+r*1.1f,cy-r*1.9f,cx,cy-r*.25f)
                    moveTo(cx-r,cy);lineTo(cx,cy-r);lineTo(cx+r,cy)
                }
                drawPath(petal,color,style=Stroke(1.5.dp.toPx()))
            }
        }
        for(x in -1..1)for(y in -1..1)drawCircle(color,1.6.dp.toPx(),Offset(cx+x*r*.7f,cy+y*r*.7f))
    }
}

@Composable
fun HeritageHeading(title: String, subtitle: String, onBack: (() -> Unit)? = null, compact:Boolean=false, trailing: (@Composable () -> Unit)? = null) {
    Row(Modifier.fillMaxWidth(),verticalAlignment=Alignment.CenterVertically) {
        if(onBack!=null) IconButton(onClick=onBack,modifier=Modifier.size(48.dp)) { Icon(Icons.AutoMirrored.Rounded.ArrowBack,"Back",tint=HeritageMaroon) }
        Column(Modifier.weight(1f)) {
            Text(title,color=HeritageInk,fontFamily=FontFamily.Serif,fontWeight=FontWeight.Bold,fontSize=if(compact)20.sp else 26.sp,lineHeight=if(compact)26.sp else 34.sp)
            if(subtitle.isNotBlank())Text(subtitle,color=HeritageMuted,fontSize=if(compact)12.sp else 14.sp,lineHeight=if(compact)17.sp else 20.sp)
        }
        trailing?.invoke()
    }
}

@Composable
fun HeritageButton(text: String,onClick:()->Unit,modifier:Modifier=Modifier,enabled:Boolean=true,secondary:Boolean=false,danger:Boolean=false) {
    val background=if(danger)Color(0xFFB62828) else if(secondary)HeritagePaper else HeritageMaroon
    Button(
        onClick=onClick,enabled=enabled,modifier=modifier.heightIn(min=56.dp),shape=RoundedCornerShape(12.dp),
        border=if(secondary)androidx.compose.foundation.BorderStroke(1.4.dp,HeritageMaroon)else null,
        colors=ButtonDefaults.buttonColors(containerColor=background,contentColor=if(secondary)HeritageMaroon else HeritagePaper,disabledContainerColor=Color(0xFFE2D5BC),disabledContentColor=Color(0xFF6A5D4D)),
        contentPadding=PaddingValues(horizontal=16.dp,vertical=13.dp),
    ) { Text(text,fontWeight=FontWeight.Bold,fontSize=17.sp,textAlign=TextAlign.Center) }
}

@Composable
fun HeritageProgress(count:Int,total:Int=247) {
    Column(Modifier.fillMaxWidth().border(1.dp,HeritageGold,RoundedCornerShape(12.dp)).padding(14.dp)) {
        Row(Modifier.fillMaxWidth(),horizontalArrangement=Arrangement.SpaceBetween) {
            Text("Practice journey",color=HeritageInk,fontFamily=FontFamily.Serif,fontWeight=FontWeight.Bold)
            Text("$count of $total",color=HeritageMaroon,fontWeight=FontWeight.Bold)
        }
        Spacer(Modifier.height(9.dp))
        LinearProgressIndicator(progress=count.toFloat()/total,modifier=Modifier.fillMaxWidth().height(7.dp),color=HeritageMaroon,trackColor=Color(0xFFE5D7BE))
        Spacer(Modifier.height(6.dp))
        Text("Letters marked practised · not pronunciation scores",color=HeritageMuted,fontSize=11.sp,lineHeight=16.sp)
    }
}

@Composable
fun LearningRhythmDialog(settings:LetterPracticeSettings,onSave:(LetterPracticeSettings)->Boolean,onDismiss:()->Unit) {
    var size by remember { mutableIntStateOf(settings.roundSize) }
    var rewards by remember { mutableStateOf(settings.rewardsEnabled) }
    var error by remember { mutableStateOf(false) }
    AlertDialog(
        onDismissRequest=onDismiss,containerColor=HeritagePaper,
        title={Text("A comfortable rhythm",color=HeritageInk,fontFamily=FontFamily.Serif)},
        text={Column(verticalArrangement=Arrangement.spacedBy(14.dp)) {
            Text("First a little practice. Then an invitation to rest.",color=HeritageMuted)
            Text("Letters in a round",color=HeritageInk,fontWeight=FontWeight.Bold)
            Row(horizontalArrangement=Arrangement.spacedBy(10.dp)) { listOf(1,3,5).forEach { n ->
                HeritageButton(n.toString(),onClick={size=n},secondary=size!=n,modifier=Modifier.weight(1f))
            } }
            Row(verticalAlignment=Alignment.CenterVertically) {
                Text("Quiet practice stamps",color=HeritageInk,modifier=Modifier.weight(1f))
                Switch(checked=rewards,onCheckedChange={rewards=it})
            }
            Text("Spoken cheers are optional in Rewards. No streak penalties or pressure to continue. Caregiver time limits still apply.",color=HeritageMuted,fontSize=13.sp)
            if(error)Text("These preferences could not be saved. Please try again.",color=HeritageMaroon)
        }},
        confirmButton={TextButton(onClick={if(onSave(LetterPracticeSettings.normalize(size,rewards)))onDismiss()else error=true}){Text("Save",color=HeritageMaroon)}},
        dismissButton={TextButton(onClick=onDismiss){Text("Cancel",color=HeritageMuted)}},
    )
}
