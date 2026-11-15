package com.team96.speakeasy.ui.screens

import androidx.activity.compose.BackHandler
import androidx.compose.foundation.background
import androidx.compose.foundation.border
import androidx.compose.foundation.clickable
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.lazy.grid.GridCells
import androidx.compose.foundation.lazy.grid.LazyVerticalGrid
import androidx.compose.foundation.lazy.grid.items
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.rounded.CheckCircle
import androidx.compose.material.icons.rounded.Lock
import androidx.compose.material3.Icon
import androidx.compose.material3.Text
import androidx.compose.runtime.*
import androidx.compose.runtime.saveable.rememberSaveable
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.platform.LocalDensity
import androidx.compose.ui.semantics.Role
import androidx.compose.ui.semantics.contentDescription
import androidx.compose.ui.semantics.semantics
import androidx.compose.ui.text.font.FontFamily
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.style.TextAlign
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import com.team96.speakeasy.journey.*
import com.team96.speakeasy.ui.components.*

/** DEC-053: a pallanguzhi-inspired level board; all locks also hold at the detail route. */
@Composable
fun TamilLetterBrowser(group:LetterGroup,onBack:()->Unit,onLetter:(String)->Unit,progress:LetterProgress=LetterProgress.restore(0)) {
    var familyId by rememberSaveable(group.name){mutableStateOf<String?>(null)}
    val family=familyId?.let{TamilAlphabet.find(it)}
    val choosingFamily=group==LetterGroup.UYIRMEI && family==null
    val compounds=TamilAlphabet.inGroup(LetterGroup.UYIRMEI)
    val letters=when{choosingFamily->TamilAlphabet.inGroup(LetterGroup.MEI);family!=null->compounds.filter{it.meiId==family.id};else->TamilAlphabet.inGroup(group)}
    val goBack={if(familyId!=null)familyId=null else onBack()}
    BackHandler(enabled=familyId!=null){familyId=null}
    HeritagePage {
        Column(Modifier.fillMaxSize().safeDrawingPadding().padding(20.dp)) {
            HeritageHeading(if(family==null)group.title else "${family.symbol} family",group.tamil,goBack)
            Spacer(Modifier.height(16.dp))
            Text(if(choosingFamily)"18 families · 12 letter levels each" else "${letters.size} letters · one little step at a time",color=HeritageInk,fontFamily=FontFamily.Serif,fontSize=17.sp)
            Text("Practise in order. Revisit earlier letters any time.",color=HeritageMuted,fontSize=13.sp,modifier=Modifier.padding(top=5.dp,bottom=18.dp))
            LazyVerticalGrid(
                columns=GridCells.Adaptive(92.dp),modifier=Modifier.weight(1f).clip(RoundedCornerShape(26.dp)).background(HeritageWood).border(2.dp,Color(0xFF70492E),RoundedCornerShape(26.dp)),
                contentPadding=PaddingValues(13.dp),horizontalArrangement=Arrangement.spacedBy(10.dp),verticalArrangement=Arrangement.spacedBy(12.dp),
            ) {
                items(letters,key={it.id}) { letter ->
                    val target=if(choosingFamily)compounds.first{it.meiId==letter.id}else letter
                    val open=progress.canOpen(target.id)
                    val done=if(choosingFamily)compounds.filter{it.meiId==letter.id}.all{progress.isPractised(it.id)}else progress.isPractised(letter.id)
                    val description="${if(open)"Open" else "Locked"} ${if(choosingFamily)"family" else "letter"} ${letter.symbol}"
                    Column(
                        Modifier.fillMaxWidth().clip(RoundedCornerShape(15.dp)).background(if(open)HeritagePaper else Color(0xFFE2D3B8)).border(if(open&&!done)2.dp else 1.dp,if(open&&!done)HeritageMaroon else Color(0xFFC3AE8E),RoundedCornerShape(15.dp))
                            .semantics{contentDescription=description}.clickable(enabled=open,role=Role.Button){if(choosingFamily)familyId=letter.id else onLetter(letter.id)}.padding(horizontal=6.dp,vertical=13.dp),horizontalAlignment=Alignment.CenterHorizontally,
                    ) {
                        Text(if(choosingFamily)"12 forms" else "Level ${TamilAlphabet.all.indexOf(letter)+1}",color=HeritageMuted,fontSize=11.sp,textAlign=TextAlign.Center)
                        BoxWithConstraints(Modifier.fillMaxWidth(),contentAlignment=Alignment.Center) {
                            val scale=LocalDensity.current.fontScale.coerceAtLeast(1f)
                            Text(letter.symbol,fontSize=(minOf(38f,maxWidth.value/2f)/scale).sp,fontWeight=FontWeight.Bold,color=if(open)HeritageMaroon else Color(0xFF817663),textAlign=TextAlign.Center,modifier=Modifier.padding(vertical=8.dp))
                        }
                        when { !open->Icon(Icons.Rounded.Lock,"Locked",tint=HeritageMuted,modifier=Modifier.size(19.dp));done->Icon(Icons.Rounded.CheckCircle,"Practised",tint=HeritageMaroon,modifier=Modifier.size(19.dp));else->Text("Start here",color=HeritageMaroon,fontSize=12.sp,fontWeight=FontWeight.Bold) }
                    }
                }
            }
            Text("Practice stamps record participation, not pronunciation accuracy.",color=HeritageMuted,fontSize=11.sp,lineHeight=16.sp,modifier=Modifier.padding(top=12.dp))
        }
    }
}
