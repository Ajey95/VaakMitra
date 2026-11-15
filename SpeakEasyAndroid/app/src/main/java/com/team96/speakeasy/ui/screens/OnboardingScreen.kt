package com.team96.speakeasy.ui.screens
import androidx.compose.foundation.ExperimentalFoundationApi
import androidx.compose.foundation.background
import androidx.compose.foundation.border
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.pager.HorizontalPager
import androidx.compose.foundation.pager.rememberPagerState
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.foundation.verticalScroll
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.rounded.Mic
import androidx.compose.material.icons.rounded.Person
import androidx.compose.material.icons.rounded.Security
import androidx.compose.material3.Icon
import androidx.compose.material3.Text
import androidx.compose.material3.TextButton
import androidx.compose.runtime.*
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.vector.ImageVector
import androidx.compose.ui.text.font.FontFamily
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.style.TextAlign
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import androidx.navigation.NavController
import com.team96.speakeasy.ui.components.*
import com.team96.speakeasy.ui.navigation.Routes
import kotlinx.coroutines.launch
private data class Page(val icon:ImageVector,val title:String,val tamil:String,val body:String)
/** DEC057: the same three-step entry, presented as a quiet illustrated schoolbook. */
@OptIn(ExperimentalFoundationApi::class)
@Composable fun OnboardingScreen(nav:NavController){
 val pages=listOf(
  Page(Icons.Rounded.Mic,"Practise Tamil Words","தமிழின் முதல் படிகள்","Explore Tamil letters and familiar words. Look, listen, trace or speak—one small step at your pace."),
  Page(Icons.Rounded.Person,"Meet Your Guide","உங்களுக்கான துணை","Choose your familiar companion and the amount of movement that feels comfortable."),
  Page(Icons.Rounded.Security,"Private by Default","உங்கள் குரல், உங்கள் சாதனம்","Microphone audio stays in memory on this device and is discarded after each attempt."),
 )
 val pager=rememberPagerState(pageCount={pages.size});val scope=rememberCoroutineScope()
 HeritagePage{Column(Modifier.fillMaxSize().safeDrawingPadding().padding(22.dp),horizontalAlignment=Alignment.CenterHorizontally){
  Row(Modifier.fillMaxWidth(),verticalAlignment=Alignment.CenterVertically){BrandMark(Modifier.size(50.dp));Text("VaakMitra",color=HeritageMaroon,fontFamily=FontFamily.Serif,fontSize=24.sp,fontWeight=FontWeight.Bold,modifier=Modifier.weight(1f));if(pager.currentPage<2)TextButton(onClick={nav.navigate(Routes.LOGIN)}){Text("Skip",color=HeritageMaroon)}}
  HorizontalPager(state=pager,modifier=Modifier.weight(1f)){index->val page=pages[index]
   Column(Modifier.fillMaxSize().verticalScroll(rememberScrollState()).padding(vertical=24.dp),horizontalAlignment=Alignment.CenterHorizontally,verticalArrangement=Arrangement.Center){
    Box(Modifier.size(112.dp).background(HeritageCard,RoundedCornerShape(20.dp)).border(1.6.dp,HeritageGold,RoundedCornerShape(20.dp)),contentAlignment=Alignment.Center){Icon(page.icon,null,tint=HeritageMaroon,modifier=Modifier.size(55.dp))}
    Spacer(Modifier.height(24.dp));Text(page.tamil,color=HeritageMaroon,fontSize=16.sp,textAlign=TextAlign.Center)
    Text(page.title,color=HeritageInk,fontFamily=FontFamily.Serif,fontWeight=FontWeight.Bold,fontSize=30.sp,textAlign=TextAlign.Center,modifier=Modifier.padding(vertical=12.dp))
    Text(page.body,color=HeritageMuted,fontSize=17.sp,lineHeight=25.sp,textAlign=TextAlign.Center)
   }
  }
  Text("${pager.currentPage+1} of 3",color=HeritageMuted,fontSize=13.sp,modifier=Modifier.padding(vertical=12.dp))
  if(pager.currentPage==2){HeritageButton("Continue",onClick={nav.navigate(Routes.LOGIN)},modifier=Modifier.fillMaxWidth());Spacer(Modifier.height(10.dp));GhostButton("Create a caregiver account"){nav.navigate(Routes.REGISTER)}}
  else HeritageButton("Next",onClick={scope.launch{pager.animateScrollToPage(pager.currentPage+1)}},modifier=Modifier.fillMaxWidth())
 }}
}
