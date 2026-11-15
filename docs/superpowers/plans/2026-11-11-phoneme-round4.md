# Further local phoneme refinement Implementation Plan

> Use superpowers:executing-plans inline. One fresh final review, one TDD fix pass, no second review.

Goal: improve V5(16.11% descriptive adult app-word PER) with existing data and local RTX4060, deliver experimentally in app if final gates pass.
Architecture: same290701parameter61symbol/40ms75frame CTC, existing expanded14839train/1630cal/1665test cache, fixed beam5/top8 plus greedy control. No new data or labels.
Spec: docs/superpowers/specs/2026-11-11-phoneme-round4-design.md; normative VAAKMITRA_FINAL_SSOT.md PHN001..006/DEC037.

Global constraints: V5PTcd4e738aa3605d0a99047c955cc09af3295b277af5d09de8bc2f396834446574 and data5c4b3b1e...1969982 remain unchanged. Protected D:/VaakMitra and D:/projects/omen/VaakMitra read-only. Same provisional canonical labels/custom speaker splits including341 upstream official-test training clips, not an official benchmark. Audit192covers15words/71Vendum and was previously exposed. Child3speaker vowels not supplied. OfficialUNSCORABLE; no clinical/phone claim. Big/temp writesDonly, no duplicate cache.

1. [ ] Run3 predefined sequential continuations fromV5, seed211,45epochs/patience12,max20minutes each: focus80(channel,fraction.8,encoder3e-6/head3e-5); head65(channel,.65,encoder0/head5e-5,trueencoderfreezeincludingBN); polish65(basic,.65,encoder1e-6/head1e-5). Stop verified task emulator for RAM and restore later. TDD true freeze before head65.
2. [ ] TDD baseline declared-decoder comparison and robust provenance fallback before selection. Compare greedy+fixedbeam oncal only; correctbaselinebeamcal6.58135%,overall54.70072%. Freeze besteligible toexclusiveV6root and independentdigest before testing. If no improvement, diagnosecalonly and ledger next controlled trial rather than use tests to select.
3. [ ] Export, measure oldtest/audit and535stress WAV aggregateconditions. Deployonlyifnewtargettest<16.1111, broad<=+1pp andFP32/nativeparity. ActualVADtrim9phonefixedreference unchanged. BuildbothABI, install/pull/hash, native3, offlineUI. Packagecheckpoint/ONNX/sourceprovenance/results/rulings. KeepV5rollback. Freshfinalreviewonce, oneverifiedfixpass, no secondreview.

Review Focus: baselinebeam/greedy metric alignment; true frozen encoder including stateful statistics; immutable-by-procedure shared-cache provenance; no test-driven selection; exact manifest/decoder/native agreement; no exaggerated child/individual-synthetic/generalization claims. Source/runtime guards fromR3 stay intact. Existing uncommitted scope requires explicit-file review.
