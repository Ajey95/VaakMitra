package com.team96.speakeasy.ui.components
import androidx.compose.foundation.Image
import androidx.compose.foundation.layout.*
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.res.painterResource
import androidx.compose.ui.text.font.FontFamily
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.style.TextAlign
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import com.team96.speakeasy.R
/** DEC057: one owned mark across launcher, welcome and page branding. */
@Composable fun BrandMark(modifier:Modifier=Modifier){Image(painterResource(R.drawable.vm_brand_mark),"VaakMitra logo",modifier)}
@Composable fun BrandLockup(compact:Boolean=false){
 Column(horizontalAlignment=Alignment.CenterHorizontally){
  BrandMark(Modifier.size(if(compact)96.dp else 176.dp))
  Text("VaakMitra",color=HeritageMaroon,fontFamily=FontFamily.Serif,fontWeight=FontWeight.Bold,fontSize=if(compact)30.sp else 40.sp,textAlign=TextAlign.Center)
  Text("தமிழோடு வளர்வோம்",color=HeritageMuted,fontSize=14.sp,textAlign=TextAlign.Center,modifier=Modifier.padding(top=6.dp))
 }
}
@Composable fun BrandWelcome(){
 HeritagePage{Column(Modifier.fillMaxSize().safeDrawingPadding().padding(28.dp),verticalArrangement=Arrangement.Center,horizontalAlignment=Alignment.CenterHorizontally){
  BrandLockup();Spacer(Modifier.height(28.dp));KolamMark(Modifier.size(48.dp));Spacer(Modifier.height(20.dp))
  Text("A little Tamil. At your pace.",color=HeritageInk,fontFamily=FontFamily.Serif,fontSize=21.sp,textAlign=TextAlign.Center)
  Text("Letters · Words · Your familiar guide",color=HeritageMuted,fontSize=13.sp,textAlign=TextAlign.Center,modifier=Modifier.padding(top=12.dp))
 }}
}
