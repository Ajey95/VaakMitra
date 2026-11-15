package com.team96.speakeasy.ui.components

import androidx.compose.foundation.Canvas
import androidx.compose.foundation.background
import androidx.compose.foundation.border
import androidx.compose.foundation.gestures.detectDragGestures
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material3.Text
import androidx.compose.material3.TextButton
import androidx.compose.runtime.*
import androidx.compose.ui.draw.clipToBounds
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.geometry.Offset
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.input.pointer.pointerInput
import androidx.compose.ui.platform.LocalDensity
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp

/** DEC-054: optional bounded transient touch strokes; no handwriting analysis/storage. */
@Composable
fun LetterTraceSlate(symbol:String,resetKey:Int,compact:Boolean=false) {
    var tracing by remember(symbol,resetKey){mutableStateOf(false)}
    val points=remember(symbol,resetKey){mutableStateListOf<Offset?>()}
    DisposableEffect(points){onDispose{points.clear()}}
    Column(horizontalAlignment=Alignment.CenterHorizontally) {
        val gesture=if(tracing)Modifier.pointerInput(symbol,resetKey){
            detectDragGestures(
                onDragStart={position->if(points.size<2046){points.add(null);points.add(position)}},
                onDragEnd={if(points.size<2048)points.add(null)},
                onDragCancel={if(points.size<2048)points.add(null)},
                onDrag={change,_->change.consume();if(points.size<2048)points.add(change.position)},
            )
        }else Modifier
        BoxWithConstraints(
            Modifier.fillMaxWidth().heightIn(min=if(compact)120.dp else 190.dp).aspectRatio(if(compact)2.7f else 1.65f).border(9.dp,HeritageWood,RoundedCornerShape(18.dp))
                .background(HeritageSlate,RoundedCornerShape(18.dp)).then(gesture),contentAlignment=Alignment.Center,
        ) {
            // The teaching glyph is a graphic: use Android's nonlinear font converter in reverse.
            val glyphSp=with(LocalDensity.current){minOf(if(compact)80f else 104f,maxWidth.value/2.5f).dp.toSp()}
            Text(symbol,color=HeritagePaper.copy(alpha=if(tracing).30f else .96f),fontWeight=FontWeight.Bold,fontSize=glyphSp)
            Canvas(Modifier.matchParentSize().padding(10.dp).clipToBounds()) {
                // Coordinates belong to the outer slate, so account for this inset.
                for(i in 1 until points.size){val a=points[i-1];val b=points[i];if(a!=null&&b!=null)drawLine(Color(0xFFF0C977),a-Offset(10.dp.toPx(),10.dp.toPx()),b-Offset(10.dp.toPx(),10.dp.toPx()),5.dp.toPx())}
            }
        }
        Row(Modifier.fillMaxWidth(),verticalAlignment=Alignment.CenterVertically,horizontalArrangement=Arrangement.Center) {
            TextButton(onClick={tracing=!tracing;if(!tracing)points.clear()},modifier=Modifier.weight(1f)){Text(if(tracing)"Finish tracing" else "Trace with your finger (optional)",color=HeritageMaroon)}
            if(tracing)TextButton(onClick={points.clear()}){Text("Clear",color=HeritageMuted)}
        }
        if(tracing)Text("Free tracing · not scored or saved",color=HeritageMuted,fontSize=12.sp)
    }
}
