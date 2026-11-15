package com.team96.speakeasy.ui.components

import androidx.compose.foundation.Canvas
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.runtime.Composable
import androidx.compose.ui.Modifier
import androidx.compose.ui.geometry.CornerRadius
import androidx.compose.ui.geometry.Offset
import androidx.compose.ui.geometry.Size
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.graphics.Path
import androidx.compose.ui.graphics.StrokeCap
import androidx.compose.ui.graphics.drawscope.DrawScope
import androidx.compose.ui.graphics.drawscope.Stroke
import androidx.compose.ui.graphics.drawscope.withTransform
import androidx.compose.ui.unit.Dp
import androidx.compose.ui.unit.dp
import com.team96.speakeasy.journey.*

private val Skin=Color(0xFFB56F48)
private val Hair=Color(0xFF302838)
private val Teal=Color(0xFF287E78)
private val Leaf=Color(0xFF53794A)
private val Rice=Color(0xFFFFF7DF)
private val Clay=Color(0xFFB86142)

/** DEC061: original vector examples, bundled code only; no actual-child or parent likeness. */
@Composable
fun WordSceneIllustration(art:WordArt,explored:Boolean=false,modifier:Modifier=Modifier,height:Dp=96.dp){
    Canvas(modifier.fillMaxWidth().height(height)){
        if(size.width<=0f || size.height<=0f)return@Canvas
        drawRoundRect(HeritagePaper,Offset.Zero,size,CornerRadius(7f))
        val frame=fitIllustration(size.width,size.height,120f,90f)
        withTransform({translate(frame.dx,frame.dy);scale(frame.scale,frame.scale,Offset.Zero)}){
            drawWordExample(art,explored)
        }
    }
}

/** Exposed for deterministic public-art rendering checks, with no UI or capture side effects. */
fun DrawScope.drawWordExample(art:WordArt,explored:Boolean){
    drawLine(HeritageGold.copy(alpha=.4f),Offset(5f,83f),Offset(115f,83f),1f)
    when(art){
        WordArt.MOTHER,WordArt.FATHER->{
            drawLine(Clay.copy(alpha=.35f),Offset(9f,23f),Offset(58f,6f),2f)
            drawLine(Clay.copy(alpha=.35f),Offset(58f,6f),Offset(111f,23f),2f)
            person(40f,81f,70f,adult=true,feminine=art==WordArt.MOTHER)
            person(78f,81f,43f)
            drawLine(Skin,Offset(51f,57f),Offset(69f,64f),4f,cap=StrokeCap.Round)
            drawCircle(Skin,2.4f,Offset(62f,61f))
            kolam(13f,79f)
        }
        WordArt.FOOD->meal()
        WordArt.HAND->hand()
        WordArt.HEAD->head()
        WordArt.HOME->home()
        else->contextScene(art,explored)
    }
}

private fun DrawScope.person(x:Float,floor:Float,h:Float,adult:Boolean=false,feminine:Boolean=false,raised:Boolean=false){
    val r=h*.12f;val faceY=floor-h*.82f
    if(feminine)drawOval(Hair,Offset(x-r*1.25f,faceY-r*1.35f),Size(r*2.5f,h*.49f))
    drawLine(Hair,Offset(x-h*.07f,floor-h*.24f),Offset(x-h*.09f,floor),h*.075f,cap=StrokeCap.Round)
    drawLine(Hair,Offset(x+h*.07f,floor-h*.24f),Offset(x+h*.09f,floor),h*.075f,cap=StrokeCap.Round)
    val clothes=if(feminine)HeritageMaroon else if(adult)Color(0xFFE7C58D)else Teal
    if(feminine){
        val p=Path().apply{moveTo(x-h*.12f,floor-h*.66f);lineTo(x+h*.12f,floor-h*.66f);lineTo(x+h*.21f,floor-h*.12f);lineTo(x-h*.21f,floor-h*.12f);close()}
        drawPath(p,clothes);drawLine(HeritageGold,Offset(x-h*.09f,floor-h*.63f),Offset(x+h*.14f,floor-h*.19f),h*.035f)
    }else{
        drawRoundRect(clothes,Offset(x-h*.145f,floor-h*.65f),Size(h*.29f,h*.43f),CornerRadius(h*.04f))
        if(adult)drawRect(Rice,Offset(x-h*.145f,floor-h*.30f),Size(h*.29f,h*.18f))
    }
    drawCircle(Skin,r,Offset(x,faceY))
    drawArc(Hair,180f,180f,true,Offset(x-r*1.05f,faceY-r*1.15f),Size(r*2.1f,r*1.45f))
    drawCircle(Hair,h*.010f,Offset(x-r*.35f,faceY))
    drawCircle(Hair,h*.010f,Offset(x+r*.35f,faceY))
    drawArc(Hair,10f,160f,false,Offset(x-r*.30f,faceY+r*.3f),Size(r*.6f,r*.25f),style=Stroke(h*.012f))
    drawLine(Skin,Offset(x-h*.12f,floor-h*.59f),Offset(x-h*.23f,floor-h*(if(raised).76f else .36f)),h*.055f,cap=StrokeCap.Round)
    drawLine(Skin,Offset(x+h*.12f,floor-h*.59f),Offset(x+h*.23f,floor-h*.36f),h*.055f,cap=StrokeCap.Round)
}

private fun DrawScope.ball(x:Float,y:Float){drawCircle(Clay,7f,Offset(x,y));drawArc(HeritageGold,30f,160f,false,Offset(x-5f,y-5f),Size(10f,10f),style=Stroke(1.5f))}
private fun DrawScope.kolam(x:Float,y:Float){
    val p=Path().apply{moveTo(x,y-4);lineTo(x+4,y);lineTo(x,y+4);lineTo(x-4,y);close()};drawPath(p,HeritageGold,style=Stroke(.8f))
    drawCircle(HeritageGold,.9f,Offset(x,y))
}
private fun DrawScope.meal(){
    drawOval(Leaf,Offset(8f,19f),Size(104f,57f));drawLine(Color(0xFF9CB879),Offset(14f,49f),Offset(106f,49f),1.5f)
    drawOval(Rice,Offset(35f,30f),Size(44f,33f))
    for((x,c)in listOf(25f to Clay,87f to Color(0xFFC69A37),102f to Teal)){
        drawCircle(Rice,8f,Offset(x,37f));drawCircle(c,5.5f,Offset(x,37f))
    }
    drawOval(HeritageGold,Offset(80f,55f),Size(21f,9f))
}
private fun DrawScope.hand(){
    drawRoundRect(Skin,Offset(43f,34f),Size(34f,34f),CornerRadius(12f))
    for((x,y)in listOf(46f to 25f,54f to 15f,62f to 11f,70f to 17f))drawLine(Skin,Offset(x,y),Offset(x,48f),7f,cap=StrokeCap.Round)
    drawLine(Skin,Offset(46f,57f),Offset(30f,40f),9f,cap=StrokeCap.Round)
    drawRect(Skin,Offset(50f,61f),Size(20f,21f));drawLine(Clay,Offset(49f,53f),Offset(66f,55f),1.2f)
}
private fun DrawScope.head(){
    drawRoundRect(Teal,Offset(33f,74f),Size(54f,10f),CornerRadius(6f));drawRect(Skin,Offset(52f,62f),Size(16f,15f))
    drawCircle(Skin,6f,Offset(34f,43f));drawCircle(Skin,6f,Offset(86f,43f));drawOval(Skin,Offset(34f,13f),Size(52f,57f))
    drawArc(Hair,180f,180f,true,Offset(32f,7f),Size(56f,34f))
    drawCircle(Hair,2f,Offset(50f,41f));drawCircle(Hair,2f,Offset(70f,41f))
    drawArc(Hair,10f,160f,false,Offset(51f,52f),Size(18f,8f),style=Stroke(1.5f))
}
private fun DrawScope.home(){
    drawRect(Color(0xFFE4C99B),Offset(22f,37f),Size(76f,44f))
    val roof=Path().apply{moveTo(11f,39f);lineTo(60f,8f);lineTo(109f,39f);close()};drawPath(roof,Clay)
    for(y in listOf(25f,31f,37f))drawLine(HeritageMaroon.copy(alpha=.5f),Offset(34f-(y-25f),y),Offset(86f+(y-25f),y),1f)
    drawRect(HeritageWood,Offset(49f,49f),Size(23f,32f));drawRect(Teal,Offset(28f,49f),Size(13f,15f));drawRect(Teal,Offset(80f,49f),Size(12f,15f))
    drawLine(HeritageGold,Offset(60f,51f),Offset(60f,79f),1f);drawCircle(HeritageGold,1f,Offset(65f,65f));kolam(60f,86f)
}
private fun DrawScope.book(x:Float,y:Float,open:Boolean){
    if(!open){drawRoundRect(HeritageMaroon,Offset(x-18,y),Size(36f,23f),CornerRadius(3f));drawLine(HeritageGold,Offset(x-13,y+3),Offset(x-13,y+20),1.3f);return}
    val p=Path().apply{moveTo(x,y+3);quadraticBezierTo(x-16,y-4,x-29,y+1);lineTo(x-29,y+25);quadraticBezierTo(x-14,y+20,x,y+27);quadraticBezierTo(x+14,y+20,x+29,y+25);lineTo(x+29,y+1);quadraticBezierTo(x+15,y-4,x,y+3);close()}
    drawPath(p,Rice);drawPath(p,HeritageMaroon,style=Stroke(1.6f));drawLine(HeritageGold,Offset(x,y+4),Offset(x,y+26),1.4f)
    for(dy in listOf(7f,12f,17f)){drawLine(HeritageGold.copy(alpha=.65f),Offset(x-23,y+dy),Offset(x-7,y+dy),1f);drawLine(HeritageGold.copy(alpha=.65f),Offset(x+7,y+dy),Offset(x+23,y+dy),1f)}
}
private fun DrawScope.box(open:Boolean){
    drawRoundRect(Clay,Offset(65f,54f),Size(31f,25f),CornerRadius(3f))
    if(open){drawLine(HeritageWood,Offset(65f,54f),Offset(88f,39f),5f,cap=StrokeCap.Round);ball(81f,61f)}
    else drawRect(HeritageWood,Offset(63f,50f),Size(35f,6f))
}
private fun DrawScope.point(x:Float,y:Float){drawLine(Skin,Offset(41f,54f),Offset(x,y),3f,cap=StrokeCap.Round);drawCircle(HeritageGold,4f,Offset(x,y),style=Stroke(1.2f))}

private fun DrawScope.contextScene(art:WordArt,active:Boolean){
    if(art==WordArt.SAFETY){
        drawRect(Color(0xFFD9D1C0),Offset(4f,70f),Size(112f,18f));for(x in 35..85 step 12)drawRect(Rice,Offset(x.toFloat(),73f),Size(7f,13f))
        person(if(active)48f else 28f,68f,36f);person(78f,68f,60f,adult=true)
        if(active)drawLine(Skin,Offset(57f,52f),Offset(67f,47f),3f,cap=StrokeCap.Round)
        return
    }
    if(art==WordArt.SELF){person(60f,83f,65f);if(active){drawLine(Skin,Offset(74f,56f),Offset(61f,47f),3f,cap=StrokeCap.Round);drawCircle(HeritageGold,5f,Offset(60f,47f),style=Stroke(1.5f))};return}
    if(art==WordArt.TOGETHER){person(if(active)43f else 25f,82f,49f);person(if(active)78f else 99f,82f,49f);ball(61f,75f);return}
    person(28f,82f,48f,raised=active && art==WordArt.ENOUGH)
    when(art){
        WordArt.REQUEST->{person(99f,82f,64f,adult=true);ball(if(active)64f else 78f,61f);if(active){drawLine(Skin,Offset(36f,56f),Offset(51f,57f),3f,cap=StrokeCap.Round);drawLine(Skin,Offset(48f,57f),Offset(54f,55f),2f,cap=StrokeCap.Round)}}
        WordArt.YES->{person(99f,82f,64f,adult=true);ball(if(active)47f else 78f,61f);if(active){drawLine(Skin,Offset(38f,64f),Offset(45f,65f),3f,cap=StrokeCap.Round);drawArc(Teal,10f,160f,false,Offset(23f,28f),Size(10f,6f),style=Stroke(1.5f));drawLine(Teal,Offset(32f,31f),Offset(31f,35f),1.5f)}}
        WordArt.FOR_ME->{person(99f,82f,64f,adult=true);ball(if(active)57f else 78f,61f);if(active){drawLine(Skin,Offset(17f,61f),Offset(29f,53f),3f,cap=StrokeCap.Round);drawCircle(HeritageGold,17f,Offset(28f,60f),style=Stroke(1.2f));drawLine(Skin,Offset(39f,64f),Offset(51f,63f),3f,cap=StrokeCap.Round)}}
        WordArt.DECLINE->{person(99f,82f,64f,adult=true);ball(if(active)87f else 60f,61f);if(active){drawLine(Skin,Offset(35f,54f),Offset(43f,47f),3f,cap=StrokeCap.Round);withTransform({translate(31f,31f);scale(.2f,.2f,Offset.Zero)}){hand()}}}
        WordArt.NO->{person(99f,82f,64f,adult=true);ball(if(active)87f else 60f,61f);if(active){drawArc(Teal,100f,150f,false,Offset(13f,35f),Size(8f,10f),style=Stroke(1.5f));drawArc(Teal,-70f,150f,false,Offset(36f,35f),Size(8f,10f),style=Stroke(1.5f))}}
        WordArt.MORE->{for(i in 0..(if(active)2 else 1))drawRoundRect(if(i%2==0)Teal else Clay,Offset(73f,70f-i*15f),Size(22f,13f),CornerRadius(2f))}
        WordArt.ENOUGH->{if(active)box(false)else{drawRect(Teal,Offset(65f,65f),Size(16f,15f));ball(95f,71f)}}
        WordArt.HELP->{if(active)person(104f,82f,62f,adult=true);box(active)}
        WordArt.SPEAK->{person(99f,82f,64f,adult=true);if(active){drawRoundRect(Rice,Offset(40f,14f),Size(31f,20f),CornerRadius(6f));drawRoundRect(HeritageMaroon,Offset(40f,14f),Size(31f,20f),CornerRadius(6f),style=Stroke(1.2f));drawLine(HeritageMaroon,Offset(45f,34f),Offset(37f,39f),1.3f);for(x in listOf(48f,55f,62f))drawCircle(Teal,1.8f,Offset(x,24f))}}
        WordArt.READ->{person(100f,82f,63f,adult=true);book(63f,49f,active)}
        WordArt.PICTURE->{drawRect(HeritageWood,Offset(65f,17f),Size(43f,49f));drawRect(Rice,Offset(69f,21f),Size(35f,41f));drawCircle(HeritageGold,5f,Offset(94f,31f));val p=Path().apply{moveTo(72f,56f);lineTo(82f,38f);lineTo(99f,56f);close()};drawPath(p,Leaf);if(active)point(68f,51f)}
        WordArt.AGAIN->{ball(if(active)94f else 64f,73f);if(active){drawArc(Teal,185f,170f,false,Offset(53f,43f),Size(47f,24f),style=Stroke(2f));drawLine(Teal,Offset(56f,55f),Offset(57f,47f),2f)}}
        WordArt.HERE,WordArt.THERE->{val x=if(art==WordArt.HERE)42f else 90f;drawRoundRect(Teal.copy(alpha=.5f),Offset(x-12,70f),Size(25f,11f),CornerRadius(4f));if(active)point(x,70f)}
        WordArt.WHAT->{box(active);if(active)point(72f,56f)}
        WordArt.THIS->{ball(81f,57f);if(active)point(75f,54f)}
        else->error("Expected an explicit contextual illustration")
    }
}

/** Static scene responds only to current round turns; no timer, sound or autonomous animation. */
@Composable
fun PlaySceneIllustration(theme:InterestTheme,completed:Int,modifier:Modifier=Modifier,height:Dp=60.dp){
    val step=playSceneStep(completed)
    Canvas(modifier.fillMaxWidth().height(height)){
        if(size.width<=0f || size.height<=0f)return@Canvas
        val width=maxOf(120f,size.width*44f/size.height)
        val frame=fitIllustration(size.width,size.height,width,44f)
        withTransform({translate(frame.dx,frame.dy);scale(frame.scale,frame.scale,Offset.Zero)}){
            drawLine(HeritageGold.copy(alpha=.45f),Offset(4f,33f),Offset(width-4f,33f),1f)
            val x=6f+step*(width-46f)/3f
            when(theme){
                InterestTheme.TRAINS->{
                    drawRect(Clay.copy(alpha=.45f),Offset(width-15f,13f),Size(9f,20f));val p=Path().apply{moveTo(width-18f,13f);lineTo(width-10f,6f);lineTo(width-2f,13f);close()};drawPath(p,HeritageMaroon)
                    drawRoundRect(HeritageMaroon,Offset(x,12f),Size(19f,16f),CornerRadius(3f));drawRect(Teal,Offset(x+19f,18f),Size(13f,10f));drawRect(Rice,Offset(x+3f,15f),Size(6f,6f))
                    for(dx in listOf(4f,14f,24f,29f))drawCircle(HeritageGold,3f,Offset(x+dx,31f))
                }
                InterestTheme.ANIMALS->{
                    drawOval(Color(0xFF73787C),Offset(x,13f),Size(24f,16f));drawCircle(Color(0xFF73787C),8f,Offset(x+24f,20f));drawCircle(Color(0xFF9EA6A7),6f,Offset(x+18f,20f))
                    for(dx in listOf(5f,16f))drawRect(Color(0xFF73787C),Offset(x+dx,26f),Size(5f,7f))
                    val trunk=Path().apply{moveTo(x+29f,21f);quadraticBezierTo(x+36f,34f,x+39f,27f)};drawPath(trunk,Color(0xFF73787C),style=Stroke(4f,cap=StrokeCap.Round));drawCircle(Hair,1f,Offset(x+26f,18f))
                    drawLine(HeritageWood,Offset(width-6f,32f),Offset(width-6f,8f),2f);drawOval(Leaf,Offset(width-17f,4f),Size(15f,8f))
                }
                InterestTheme.STORIES->{book(width/2f,7f,true);for(i in 0 until step)drawCircle(Teal,2f,Offset(width/2f+9f+i*6f,22f))}
                InterestTheme.NEUTRAL->{for(i in 0..2){val cx=width*(i+1)/4f;drawLine(Leaf,Offset(cx,31f),Offset(cx,17f),1.3f);drawCircle(if(i<step)Clay else HeritageGold.copy(alpha=.35f),5f,Offset(cx,15f))}}
            }
            for(i in 1..3)drawCircle(if(i<=step)HeritageMaroon else HeritageGold.copy(alpha=.3f),1.7f,Offset(width*i/4f,40f))
        }
    }
}
