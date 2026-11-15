package com.team96.speakeasy.ui.screens
import androidx.compose.foundation.background
import androidx.compose.foundation.border
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.lazy.grid.GridItemSpan
import androidx.compose.foundation.lazy.grid.GridCells
import androidx.compose.foundation.lazy.grid.LazyVerticalGrid
import androidx.compose.foundation.lazy.grid.items
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material3.Text
import androidx.compose.runtime.*
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.text.font.FontFamily
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.style.TextAlign
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import androidx.lifecycle.compose.collectAsStateWithLifecycle
import androidx.navigation.NavController
import com.team96.speakeasy.ui.components.*
import com.team96.speakeasy.viewmodel.AppViewModel
private data class Badge(val title:String,val needStars:Int)
/** DEC057: actual account counters/thresholds, quiet printed stamps without ability labels. */
@Composable fun RewardsScreen(nav:NavController,vm:AppViewModel){
 val stats by vm.stats.collectAsStateWithLifecycle();LaunchedEffect(Unit){vm.loadHome()}
 val loading by vm.loading.collectAsStateWithLifecycle()
 val badges=listOf(Badge("First Steps",1),Badge("Little Kolam",5),Badge("Tamil Garden",10),Badge("School Slate",20),Badge("Pallanguzhi",35),Badge("Story Time",50),Badge("Growing Path",75),Badge("Tamil Trail",100))
 HeritagePage{Column(Modifier.fillMaxSize().safeDrawingPadding().padding(20.dp)){
  HeritageHeading("Rewards","முயற்சிப் பயணம்",onBack={nav.popBackStack()})
  LazyVerticalGrid(columns=GridCells.Adaptive(140.dp),modifier=Modifier.weight(1f),horizontalArrangement=Arrangement.spacedBy(12.dp),verticalArrangement=Arrangement.spacedBy(12.dp)){
  item(span={GridItemSpan(maxLineSpan)}){Column{
  Spacer(Modifier.height(18.dp))
  Row(Modifier.fillMaxWidth().background(HeritageCard,RoundedCornerShape(16.dp)).border(1.dp,HeritageGold,RoundedCornerShape(16.dp)).padding(18.dp),verticalAlignment=Alignment.CenterVertically){
   KolamMark(Modifier.size(52.dp));Column(Modifier.weight(1f).padding(start=12.dp)){
    Text(if(stats.stars==null)if(loading)"Loading account stars…" else "Account stars unavailable" else "${stats.stars} account stars",color=HeritageMaroon,fontFamily=FontFamily.Serif,fontSize=24.sp,fontWeight=FontWeight.Bold)
    Text(when(stats.stars){null->"Earned stamps will appear when account data is available.";0->"No stars recorded yet. There is no hurry.";else->"A record of your journey together."},color=HeritageMuted,fontSize=13.sp)
   }
  }
  Text("Stamps are not pronunciation or attention scores.",color=HeritageMuted,fontSize=13.sp,modifier=Modifier.padding(vertical=16.dp))
  EncouragementPanel(vm,com.team96.speakeasy.journey.PraiseEvent.PRACTICE,heading="Your encouragement",settingsButton=true,compact=true)
  Spacer(Modifier.height(12.dp))
  }}
   items(badges){badge->val open=stats.stars?.let{it>=badge.needStars}
    Column(Modifier.fillMaxWidth().background(HeritageCard,RoundedCornerShape(14.dp)).border(1.3.dp,if(open==true)HeritageMaroon else HeritageGold,RoundedCornerShape(14.dp)).padding(18.dp),horizontalAlignment=Alignment.CenterHorizontally){
     KolamMark(Modifier.size(48.dp),color=if(open==true)HeritageMaroon else HeritageMuted)
     Text(badge.title,color=HeritageInk,fontFamily=FontFamily.Serif,fontSize=19.sp,fontWeight=FontWeight.Bold,textAlign=TextAlign.Center,modifier=Modifier.padding(top=12.dp))
     Text(when(open){true->"Unlocked";false->"${badge.needStars} account stars";null->"Goal: ${badge.needStars} account stars"},color=HeritageMuted,fontSize=12.sp,textAlign=TextAlign.Center,modifier=Modifier.padding(top=7.dp))
    }
   }
  }
 }}
}
