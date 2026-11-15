package com.team96.speakeasy.ui.components

import androidx.compose.foundation.background
import androidx.compose.foundation.border
import androidx.compose.foundation.clickable
import androidx.compose.foundation.ExperimentalFoundationApi
import androidx.compose.foundation.relocation.BringIntoViewRequester
import androidx.compose.foundation.relocation.bringIntoViewRequester
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material3.Text
import androidx.compose.runtime.*
import androidx.compose.runtime.saveable.rememberSaveable
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.platform.LocalDensity
import androidx.compose.ui.semantics.Role
import androidx.compose.ui.semantics.clearAndSetSemantics
import androidx.compose.ui.semantics.contentDescription
import androidx.compose.ui.semantics.role
import androidx.compose.ui.semantics.selected
import androidx.compose.ui.semantics.stateDescription
import androidx.compose.ui.semantics.semantics
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.style.TextAlign
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import com.team96.speakeasy.journey.*
import kotlinx.coroutines.launch

/** DEC061: clear local examples; themes change the play scene, never the word or assessment. */
@Composable
@OptIn(ExperimentalFoundationApi::class)
fun InterestLearningCard(
    target:StarterWord,progress:PictureProgress,theme:InterestTheme,turn:Int,steps:Int,
    feedback:Boolean?,enabled:Boolean,partsOpen:Boolean,
    onScene:(InterestTheme)->Unit,onChoice:(String,List<String>)->Unit,
    onHelp:()->Unit,onParts:()->Unit,onAgain:()->Unit,onNext:()->Unit,onEnough:()->Unit,
    contextExplored:Boolean,onContextAction:()->Unit,
    encouragement:@Composable ()->Unit={},automaticCycles:Boolean=false,
) {
    val example=WordActivityCatalog.context(target.id)
    var choosingScene by rememberSaveable(target.id){mutableStateOf(false)}
    var contextHelpOpen by rememberSaveable(target.id){mutableStateOf(false)}
    val sceneAnchor=remember{BringIntoViewRequester()}
    val sceneScope=rememberCoroutineScope()
    fun focusScene(){sceneScope.launch{withFrameNanos{};withFrameNanos{};sceneAnchor.bringIntoView()}}
    Column(Modifier.fillMaxWidth().clip(RoundedCornerShape(14.dp)).background(HeritageCard).border(1.dp,HeritageGold,RoundedCornerShape(14.dp)).padding(12.dp),verticalArrangement=Arrangement.spacedBy(8.dp)){
      Column(Modifier.fillMaxWidth().bringIntoViewRequester(sceneAnchor),verticalArrangement=Arrangement.spacedBy(8.dp)){
        BoxWithConstraints(Modifier.fillMaxWidth().heightIn(min=56.dp).clip(RoundedCornerShape(10.dp)).background(HeritageSlate).padding(8.dp),contentAlignment=Alignment.Center){
            val scale=LocalDensity.current.fontScale.coerceAtLeast(1f)
            Text(target.tamil,color=HeritagePaper,fontSize=(minOf(38f,maxWidth.value/(target.tamil.length.coerceAtLeast(3)*.7f))/scale).sp,fontWeight=FontWeight.Bold)
        }
        Text("Play scene · விளையாட்டு",color=HeritageMuted,fontSize=12.sp)
        if(LocalDensity.current.fontScale>1.3f){
            Text(theme.title,color=HeritageMaroon,fontSize=18.sp,fontWeight=FontWeight.Bold)
            HeritageButton(if(choosingScene)"Close scene choices" else "Change play scene",{choosingScene=!choosingScene;if(!choosingScene)focusScene()},enabled=enabled,secondary=true,modifier=Modifier.fillMaxWidth())
        }else Row(verticalAlignment=Alignment.CenterVertically,horizontalArrangement=Arrangement.spacedBy(8.dp)){
            Text(theme.title,color=HeritageMaroon,fontSize=18.sp,fontWeight=FontWeight.Bold,modifier=Modifier.weight(1f))
            HeritageButton(if(choosingScene)"Close scene choices" else "Change play scene",{choosingScene=!choosingScene;if(!choosingScene)focusScene()},enabled=enabled,secondary=true,modifier=Modifier.weight(1f))
        }
        if(choosingScene){
            Text("Your word stays the same",color=HeritageInk,fontSize=14.sp)
            for(scene in listOf(InterestTheme.TRAINS,InterestTheme.ANIMALS,InterestTheme.STORIES)){
                Row(Modifier.fillMaxWidth().clip(RoundedCornerShape(10.dp)).background(HeritagePaper)
                    .border(if(theme==scene)3.dp else 1.dp,if(theme==scene)HeritageMaroon else HeritageGold,RoundedCornerShape(10.dp))
                    .clickable(enabled=enabled){onScene(scene);choosingScene=false;focusScene()}
                    .semantics{contentDescription="Scene: ${scene.preference}";selected=theme==scene;role=Role.Button}
                    .padding(8.dp),verticalAlignment=Alignment.CenterVertically,horizontalArrangement=Arrangement.spacedBy(12.dp)){
                    PlaySceneIllustration(scene,0,Modifier.width(76.dp),height=48.dp)
                    Column(Modifier.weight(1f)){
                        Text(scene.tamilLabel(),color=HeritageInk,fontSize=16.sp,fontWeight=FontWeight.Bold)
                        Text(scene.choiceLabel(),color=HeritageMuted,fontSize=14.sp)
                    }
                }
            }
        }
        val step=playSceneStep(steps)
        PlaySceneIllustration(theme,step,Modifier.semantics{contentDescription="${theme.title} · $step of 3 turns"})
        Text(if(automaticCycles)"Cycle practice · $step / 3 words" else "Practice · $step / 3 turns, then a break",color=HeritageMuted,fontSize=12.sp)
      }
        if(example==null){
            if(target.id in setOf("TA_WORD_0001","TA_WORD_0002"))Text("Family example",color=HeritageMuted,fontSize=12.sp)
            Text(progress.help.caption,color=HeritageInk,fontWeight=FontWeight.Bold,fontSize=16.sp)
            Text("Find ${target.tamil}",color=HeritageMuted,fontSize=14.sp)
            val options=learningOptions(target.id,progress.optionCount,turn)
            Row(Modifier.fillMaxWidth(),horizontalArrangement=Arrangement.spacedBy(8.dp)){
                for(id in options){
                    val word=StarterWords.all.first{it.id==id}
                    val highlighted=progress.help==PromptHelp.GUIDED && id==target.id
                    Column(Modifier.weight(1f).clip(RoundedCornerShape(12.dp)).background(HeritagePaper)
                        .border(if(highlighted)3.dp else 1.dp,if(highlighted)HeritageMaroon else HeritageGold,RoundedCornerShape(12.dp))
                        .clickable(enabled=enabled && feedback!=true){onChoice(id,options)}
                        .clearAndSetSemantics{contentDescription="Picture: ${word.transliteration} · ${word.tamil} · ${WordActivityCatalog.pictureCaption(id)}";stateDescription=WordActivityCatalog.pictureCaption(id);role=Role.Button}
                        .padding(6.dp),horizontalAlignment=Alignment.CenterHorizontally){
                        Box(Modifier.fillMaxWidth().height(96.dp)){
                            WordSceneIllustration(WordActivityCatalog.art(id))
                        }
                        Text(word.tamil,color=HeritageInk,fontSize=16.sp,textAlign=TextAlign.Center)
                        Text(WordActivityCatalog.pictureCaption(id),color=HeritageMuted,fontSize=12.sp,textAlign=TextAlign.Center)
                    }
                }
            }
            feedback?.let{Text(if(it)"Picture matched" else "Let's look together",color=HeritageMaroon,fontSize=14.sp,fontWeight=FontWeight.Bold)}
        }else{
            Text("Explore the word",color=HeritageMaroon,fontSize=12.sp,fontWeight=FontWeight.Bold)
            Text(example.prompt,color=HeritageInk,fontSize=16.sp,fontWeight=FontWeight.Bold)
            WordSceneIllustration(example.art,contextExplored,height=120.dp)
            Text(if(contextExplored)example.after else example.before,color=HeritageMuted,fontSize=14.sp)
            HeritageButton(if(contextExplored)"See it again" else "Show the action",onContextAction,enabled=enabled,modifier=Modifier.fillMaxWidth())
            if(contextExplored)Text("Example explored",color=HeritageMaroon,fontSize=14.sp)
            if(contextHelpOpen)Text("Look together. ${example.before}. Show the action, then tap Example to hear the whole word.",color=HeritageInk,fontSize=14.sp)
            Text("A shared example · speaking is optional",color=HeritageMuted,fontSize=12.sp)
        }
        encouragement()
        Row(horizontalArrangement=Arrangement.spacedBy(8.dp)){
            HeritageButton("Show help",{if(example!=null)contextHelpOpen=true;onHelp()},enabled=enabled,secondary=true,modifier=Modifier.weight(1f))
            HeritageButton("Writing parts",onParts,enabled=enabled,secondary=true,modifier=Modifier.weight(1f))
        }
        if(partsOpen){Text("Writing parts · whole-word audio only",color=HeritageMuted,fontSize=12.sp);WritingParts(target.tamil)}
        Row(horizontalArrangement=Arrangement.spacedBy(8.dp)){
            HeritageButton("இன்னும் · More",onAgain,enabled=enabled,secondary=true,modifier=Modifier.weight(1f))
            HeritageButton("Next activity",onNext,enabled=enabled,modifier=Modifier.weight(1f))
        }
        HeritageButton("போதும் · Enough",onEnough,secondary=true,modifier=Modifier.fillMaxWidth())
        Text(if(example==null)"Picture choices help set the activity. They do not score speech." else "Exploring an example does not produce a speech score.",color=HeritageMuted,fontSize=11.sp)
    }
}

@OptIn(ExperimentalLayoutApi::class)
@Composable
private fun WritingParts(word:String){
    FlowRow(horizontalArrangement=Arrangement.spacedBy(6.dp),verticalArrangement=Arrangement.spacedBy(6.dp)){
        for(part in tamilWritingParts(word))Text(part,color=HeritageInk,fontSize=24.sp,modifier=Modifier.clip(RoundedCornerShape(8.dp)).background(HeritagePaper).padding(8.dp))
    }
}
