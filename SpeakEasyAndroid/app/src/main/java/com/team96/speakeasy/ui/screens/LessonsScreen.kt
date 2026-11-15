package com.team96.speakeasy.ui.screens
import androidx.activity.compose.BackHandler
import androidx.compose.foundation.background
import androidx.compose.foundation.border
import androidx.compose.foundation.clickable
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.itemsIndexed
import androidx.compose.foundation.shape.CircleShape
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.automirrored.rounded.ArrowBack
import androidx.compose.material3.Icon
import androidx.compose.material3.Text
import androidx.compose.runtime.*
import androidx.compose.runtime.saveable.rememberSaveable
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.text.font.FontFamily
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import androidx.lifecycle.compose.collectAsStateWithLifecycle
import androidx.navigation.NavController
import com.team96.speakeasy.journey.LetterGroup
import com.team96.speakeasy.journey.TamilAlphabet
import com.team96.speakeasy.journey.StarterWords
import com.team96.speakeasy.ui.components.*
import com.team96.speakeasy.ui.navigation.Routes
import com.team96.speakeasy.viewmodel.AppViewModel

/** DEC-053: optional entry section preserves the direct existing Words shortcut. */
@Composable
fun LessonsScreen(nav:NavController,vm:AppViewModel,initialSection:String="") {
    val context=LocalContext.current
    val storedJourney by vm.letterJourney.collectAsStateWithLifecycle()
    val ready by vm.letterReady.collectAsStateWithLifecycle()
    val letterReady=ready && vm.letterIdentityIsCurrent()
    val journey=if(letterReady)storedJourney else com.team96.speakeasy.journey.LetterJourneySnapshot()
    var category by rememberSaveable(initialSection){mutableStateOf(initialSection.takeIf{it=="WORDS"||LetterGroup.entries.any{g->g.name==it}})}
    LaunchedEffect(Unit){vm.loadLetterJourney(context)}
    val group=LetterGroup.entries.firstOrNull{it.name==category}
    val goBack={if(initialSection==category||category==null)nav.popBackStack() else {category=null;true}}
    BackHandler(enabled=category!=null){goBack()}
    if(group!=null && !letterReady){HeritagePage{Column(Modifier.fillMaxSize().safeDrawingPadding().padding(20.dp)){HeritageHeading("Letter progress unavailable","Your letter journey isn't ready yet. Try reopening your profile.",onBack={goBack()})}};return}
    if(group!=null){TamilLetterBrowser(group,onBack={goBack()},onLetter={nav.navigate("${Routes.LETTER}/$it")},progress=journey.progress);return}
    var focused by rememberSaveable { mutableStateOf(true) }
    val words=if(focused) StarterWords.focusedLessonIds.mapNotNull { id -> vm.localWordLessons.firstOrNull { it.id==id } } else vm.localWordLessons
    HeritagePage {
        Column(Modifier.fillMaxSize().safeDrawingPadding().padding(20.dp)) {
            HeritageHeading(if(category=="WORDS")"Tamil Words" else "Letters & Words",if(category=="WORDS")"${words.size} words · your familiar session flow" else "247 letter levels · ${StarterWords.all.size} words",onBack={goBack()})
            Spacer(Modifier.height(18.dp))
            LazyColumn(verticalArrangement=Arrangement.spacedBy(12.dp)) {
                if(category=="WORDS"){
                    item {
                        Column(verticalArrangement=Arrangement.spacedBy(8.dp)) {
                            HeritageButton("Focused practice · 18",onClick={focused=true},secondary=!focused,modifier=Modifier.fillMaxWidth())
                            HeritageButton("All words · ${StarterWords.all.size}",onClick={focused=false},secondary=focused,modifier=Modifier.fillMaxWidth())
                            Text("Choose a familiar word. Listen, look and practise at your pace.",color=HeritageMuted,fontSize=13.sp)
                        }
                    }
                    itemsIndexed(words,key={_,word->word.id}){_,word->
                        Row(Modifier.fillMaxWidth().clip(RoundedCornerShape(13.dp)).border(1.dp,HeritageGold,RoundedCornerShape(13.dp)).clickable{nav.navigate("${Routes.PRACTICE}/${word.id}?focused=$focused")}.padding(18.dp),verticalAlignment=Alignment.CenterVertically){
                            Text(word.symbol,color=HeritageMaroon,fontSize=27.sp,fontWeight=FontWeight.Bold,modifier=Modifier.weight(1f))
                            Column(Modifier.weight(1f)){
                                Text(word.english,color=HeritageInk,fontFamily=FontFamily.Serif,fontSize=20.sp,fontWeight=FontWeight.Bold)
                                Text(word.phoneme,color=HeritageMuted,fontSize=13.sp)
                            }
                        }
                    }
                }else{
                    item{HeritageProgress(journey.progress.completedCount)}
                    itemsIndexed(LetterGroup.entries){_,entry->
                        val letters=TamilAlphabet.inGroup(entry)
                        ChapterRow(entry.title,entry.tamil,"${letters.count{journey.progress.isPractised(it.id)}} / ${letters.size} practised"){category=entry.name}
                    }
                    item{ChapterRow("Words","சொற்கள்","${StarterWords.all.size} words · 18 focused"){category="WORDS"}}
                }
                item{Spacer(Modifier.height(18.dp))}
            }
        }
    }
}

@Composable
fun BackCircle(onClick: () -> Unit) {
    Box(
        Modifier.size(48.dp).clip(CircleShape).background(HeritageCard).border(1.dp,HeritageGold,CircleShape).clickable { onClick() },
        contentAlignment = Alignment.Center
    ) {
        Icon(Icons.AutoMirrored.Rounded.ArrowBack, "Back", tint = HeritageMaroon)
    }
}
