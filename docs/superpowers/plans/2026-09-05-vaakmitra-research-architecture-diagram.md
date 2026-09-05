# VaakMitra Research Architecture Diagram Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Produce a self-contained, editable, academically structured, three-page diagrams.net file with recognizable technology icons and animated directional flows for the complete VaakMitra research system.

**Architecture:** A deterministic Python builder will emit uncompressed diagrams.net XML from reusable page, container, node, edge, legend, and embedded-icon helpers. The same builder will create all three pages with a shared visual grammar, while a focused XML test suite verifies page coverage, unique identifiers, animation, privacy boundaries, icon embedding, and absence of remote dependencies.

**Tech Stack:** Python 3.12 standard library, `xml.etree.ElementTree`, base64-embedded SVG assets, diagrams.net `mxGraphModel` XML, pytest.

**Spec:** `docs/superpowers/specs/2026-09-05-vaakmitra-research-architecture-diagram-design.md`

## Global Constraints

- Create `docs/architecture/VaakMitra_Academic_Research_Architecture.drawio` as uncompressed, editable diagrams.net XML.
- Include exactly three coordinated pages: operational architecture, research/model lifecycle, and validation/governance.
- Use embedded SVG assets or diagrams.net-native shapes; the output must not depend on remote image URLs.
- Add `flowAnimation=1`, explicit dash patterns, arrowheads, and labels to primary data/model flows.
- Preserve comprehension in static exports by retaining arrowheads, sequence numbers, labels, and legends.
- Mark synthetic fixtures as engineering evidence rather than clinical evidence.
- Mark final GPU training, expert phoneme approval, Member 1 validated alignment, child-domain validation, clinician calibration, and physical Android timing as pending gates.
- Show that raw audio, transcripts, embeddings, MFCCs, spectrograms, voiceprints, and frame-level probabilities cannot cross the network boundary.
- Do not describe VaakMitra as an autonomous diagnostic or clinical decision system.

## File Structure

- Create `tools/architecture/generate_vaakmitra_drawio.py`: reusable XML builder, page geometry, styles, icon embedding, and final artifact generation.
- Create `tools/architecture/icons/android.svg`: vendored Android platform mark used only at the mobile edge boundary.
- Create `tools/architecture/icons/unity.svg`: vendored Unity mark used only at the presentation layer.
- Create `tools/architecture/icons/python.svg`: vendored Python mark used only in the research environment.
- Create `tools/architecture/icons/pytorch.svg`: vendored PyTorch mark used only in teacher/student training blocks.
- Create `tools/architecture/icons/onnx.svg`: vendored ONNX mark used only in export and runtime blocks.
- Create `tools/architecture/icons/ATTRIBUTION.md`: icon source URLs, retrieval date, trademark notice, and usage context.
- Create `tests/architecture/test_vaakmitra_drawio.py`: structural, semantic, animation, icon, and truth-boundary tests.
- Create `docs/architecture/VaakMitra_Academic_Research_Architecture.drawio`: generated user deliverable.

---

### Task 1: Establish the deterministic diagrams.net builder and contract tests

**Files:**
- Create: `tools/architecture/generate_vaakmitra_drawio.py`
- Create: `tests/architecture/test_vaakmitra_drawio.py`

**Interfaces:**
- Produces: `build_document() -> xml.etree.ElementTree.ElementTree`
- Produces: `write_document(output_path: pathlib.Path) -> pathlib.Path`
- Produces: `add_vertex(root, cell_id, label, x, y, width, height, style, parent='1') -> Element`
- Produces: `add_edge(root, cell_id, source, target, label, style, parent='1') -> Element`
- Consumes: no project runtime modules; only Python standard library.

- [ ] **Step 1: Write the failing document-contract test**

```python
from pathlib import Path
import importlib.util
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parents[2]
OUTPUT = ROOT / "docs" / "architecture" / "VaakMitra_Academic_Research_Architecture.drawio"


def load_generator():
    path = ROOT / "tools" / "architecture" / "generate_vaakmitra_drawio.py"
    spec = importlib.util.spec_from_file_location("vaakmitra_drawio", path)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def test_document_has_three_named_editable_pages(tmp_path):
    module = load_generator()
    output = module.write_document(tmp_path / OUTPUT.name)
    mxfile = ET.parse(output).getroot()
    assert mxfile.tag == "mxfile"
    assert [page.attrib["name"] for page in mxfile.findall("diagram")] == [
        "1. Edge Therapy System",
        "2. Research & Model Lifecycle",
        "3. Validation, Governance & Privacy",
    ]
    assert all(page.find("mxGraphModel/root") is not None for page in mxfile.findall("diagram"))
```

- [ ] **Step 2: Run the test and verify the generator is absent**

Run: `python -m pytest tests/architecture/test_vaakmitra_drawio.py::test_document_has_three_named_editable_pages -v`

Expected: FAIL because `tools/architecture/generate_vaakmitra_drawio.py` does not exist.

- [ ] **Step 3: Implement the XML builder skeleton**

Define constants for page size (`1600 x 1000`), fonts, colors, common node styles, and edge semantics. Create each `<diagram>` with an uncompressed `<mxGraphModel>` containing required root cells `0` and `1`. Implement `add_vertex`, `add_edge`, `build_document`, and `write_document` using `ElementTree`; create parent directories in `write_document` and emit an XML declaration.

- [ ] **Step 4: Run the document-contract test**

Run: `python -m pytest tests/architecture/test_vaakmitra_drawio.py::test_document_has_three_named_editable_pages -v`

Expected: PASS with three editable pages.

- [ ] **Step 5: Commit the builder foundation**

```powershell
git add tools/architecture/generate_vaakmitra_drawio.py tests/architecture/test_vaakmitra_drawio.py
git commit -m "test: define VaakMitra diagram document contract"
```

### Task 2: Add embedded real-world icons and the operational architecture page

**Files:**
- Create: `tools/architecture/icons/android.svg`
- Create: `tools/architecture/icons/unity.svg`
- Create: `tools/architecture/icons/onnx.svg`
- Create: `tools/architecture/icons/ATTRIBUTION.md`
- Modify: `tools/architecture/generate_vaakmitra_drawio.py`
- Modify: `tests/architecture/test_vaakmitra_drawio.py`
- Generate: `docs/architecture/VaakMitra_Academic_Research_Architecture.drawio`

**Interfaces:**
- Consumes: `add_vertex`, `add_edge` from Task 1.
- Produces: `embedded_svg_style(icon_path: Path, **style_options) -> str`.
- Produces: Page 1 component IDs prefixed `p1_` and edge IDs prefixed `p1_e_`.

- [ ] **Step 1: Vendor and document the platform icons**

Save SVG-only assets from these Simple Icons endpoints, then record the source URL, retrieval date `2026-09-05`, original brand owner, and the statement “Marks identify compatible technology; no endorsement is implied” in `ATTRIBUTION.md`:

- `https://cdn.simpleicons.org/android/3DDC84`
- `https://cdn.simpleicons.org/unity/000000`
- `https://cdn.simpleicons.org/onnx/005CED`

- [ ] **Step 2: Write failing Page 1 tests**

Add tests that assert Page 1 contains these IDs: `p1_child`, `p1_therapist`, `p1_unity`, `p1_orchestrator`, `p1_capture`, `p1_g2p`, `p1_ctc`, `p1_alignment`, `p1_gop`, `p1_onnx`, `p1_local_db`, `p1_sync_gate`, and `p1_therapist_api`. Assert at least eight Page 1 edges contain `flowAnimation=1`, every animated edge contains `dashed=1` and `endArrow=block`, and every icon cell contains an inline `data:image/svg+xml;base64,` URI.

- [ ] **Step 3: Run Page 1 tests and verify failure**

Run: `python -m pytest tests/architecture/test_vaakmitra_drawio.py -k "page1 or icon or animation" -v`

Expected: FAIL because Page 1 blocks and embedded icon helpers are absent.

- [ ] **Step 4: Implement Page 1 geometry and flows**

Build six horizontal layer containers, with a left-to-right numbered inference loop and a separated consent-controlled network zone. Use animated blue edges for audio and inference, solid purple edges for control/configuration, green animated edges for approved metric sync, and red stop-marker edges for prohibited payloads. Add responsibility tags `M1`, `M2`, and `M3` to each relevant node.

- [ ] **Step 5: Generate the artifact and run Page 1 tests**

Run:

```powershell
python tools/architecture/generate_vaakmitra_drawio.py
python -m pytest tests/architecture/test_vaakmitra_drawio.py -k "page1 or icon or animation" -v
```

Expected: the `.drawio` file exists and all selected tests pass.

- [ ] **Step 6: Commit Page 1 and embedded icons**

```powershell
git add tools/architecture/icons tools/architecture/generate_vaakmitra_drawio.py tests/architecture/test_vaakmitra_drawio.py docs/architecture/VaakMitra_Academic_Research_Architecture.drawio
git commit -m "docs: add animated VaakMitra edge architecture"
```

### Task 3: Add the research and model-lifecycle page

**Files:**
- Create: `tools/architecture/icons/python.svg`
- Create: `tools/architecture/icons/pytorch.svg`
- Modify: `tools/architecture/icons/ATTRIBUTION.md`
- Modify: `tools/architecture/generate_vaakmitra_drawio.py`
- Modify: `tests/architecture/test_vaakmitra_drawio.py`
- Regenerate: `docs/architecture/VaakMitra_Academic_Research_Architecture.drawio`

**Interfaces:**
- Consumes: shared XML, style, edge, and icon helpers.
- Produces: Page 2 component IDs prefixed `p2_` and edge IDs prefixed `p2_e_`.

- [ ] **Step 1: Vendor and document research-framework icons**

Save and document:

- `https://cdn.simpleicons.org/python/3776AB`
- `https://cdn.simpleicons.org/pytorch/EE4C2C`

- [ ] **Step 2: Write failing Page 2 semantic tests**

Assert Page 2 contains corpus/provenance, speaker-disjoint split, leakage audit, AI4Bharat Tamil IndicConformer teacher, provisional phoneme CTC head, compact Conformer student, compact Conv-BiGRU student, multi-loss distillation, evaluation gates, FP32/INT8 ONNX, model card, immutable manifest, and deployment-promotion blocks. Assert the page includes the phrases `89,387 eligible recordings`, `638 speakers`, `approximately 150 hours`, `text-token outputs are not phoneme posteriors`, and `98.2% PER — rejected baseline`.

- [ ] **Step 3: Run Page 2 tests and verify failure**

Run: `python -m pytest tests/architecture/test_vaakmitra_drawio.py -k page2 -v`

Expected: FAIL because Page 2 research content is absent.

- [ ] **Step 4: Implement Page 2 geometry and evidence loops**

Build six stage columns from governed corpus to deployment packaging. Use animated teal edges for artifacts and distilled knowledge, blue edges for samples/features, and amber return edges from failed evaluation gates to the appropriate training stage. Add status chips: `RECORDED EVIDENCE`, `DESIGN VALIDATED`, `GPU RUN PENDING`, and `EXPERT/CHILD VALIDATION PENDING`.

- [ ] **Step 5: Regenerate and pass Page 2 tests**

Run:

```powershell
python tools/architecture/generate_vaakmitra_drawio.py
python -m pytest tests/architecture/test_vaakmitra_drawio.py -k page2 -v
```

Expected: PASS, with Page 2 labels matching repository evidence and no final-model claim.

- [ ] **Step 6: Commit the research lifecycle page**

```powershell
git add tools/architecture/icons tools/architecture/generate_vaakmitra_drawio.py tests/architecture/test_vaakmitra_drawio.py docs/architecture/VaakMitra_Academic_Research_Architecture.drawio
git commit -m "docs: map VaakMitra research model lifecycle"
```

### Task 4: Add validation, governance, privacy, and truth boundaries

**Files:**
- Modify: `tools/architecture/generate_vaakmitra_drawio.py`
- Modify: `tests/architecture/test_vaakmitra_drawio.py`
- Regenerate: `docs/architecture/VaakMitra_Academic_Research_Architecture.drawio`

**Interfaces:**
- Consumes: shared page, node, edge, legend, and boundary helpers.
- Produces: Page 3 component IDs prefixed `p3_` and edge IDs prefixed `p3_e_`.

- [ ] **Step 1: Write failing Page 3 governance tests**

Assert the evidence ladder has eight ordered gates, the deterministic decision boundary contains `UNSCORABLE`, and prohibited flows name all of: raw audio, transcript, embedding, MFCC, spectrogram, voiceprint, and frame-level probabilities. Assert Page 3 includes `Research prototype — not diagnosis`, `Synthetic evidence proves mechanics, not clinical accuracy`, and separate `IMPLEMENTED`, `PENDING`, and `PROHIBITED` status styles.

- [ ] **Step 2: Run Page 3 tests and verify failure**

Run: `python -m pytest tests/architecture/test_vaakmitra_drawio.py -k page3 -v`

Expected: FAIL because Page 3 governance content is absent.

- [ ] **Step 3: Implement Page 3**

Arrange five vertical zones: hypotheses, evidence ladder, deterministic controls, privacy/security boundary, and current-status truth boundary. Use grey dotted dependencies for pending evidence, green solid approval paths, amber review loops, and red stop-marker prohibited paths. Ensure model scores terminate at deterministic confidence/action gates rather than at a clinical verdict node.

- [ ] **Step 4: Regenerate and pass Page 3 tests**

Run:

```powershell
python tools/architecture/generate_vaakmitra_drawio.py
python -m pytest tests/architecture/test_vaakmitra_drawio.py -k page3 -v
```

Expected: PASS with all privacy and scientific-integrity labels present.

- [ ] **Step 5: Commit the governance page**

```powershell
git add tools/architecture/generate_vaakmitra_drawio.py tests/architecture/test_vaakmitra_drawio.py docs/architecture/VaakMitra_Academic_Research_Architecture.drawio
git commit -m "docs: add VaakMitra research governance architecture"
```

### Task 5: Perform full artifact verification and delivery cleanup

**Files:**
- Modify if required: `tools/architecture/generate_vaakmitra_drawio.py`
- Modify if required: `tests/architecture/test_vaakmitra_drawio.py`
- Regenerate: `docs/architecture/VaakMitra_Academic_Research_Architecture.drawio`

**Interfaces:**
- Consumes: complete generator and test suite.
- Produces: final verified `.drawio` deliverable.

- [ ] **Step 1: Add final cross-page integrity tests**

Assert all `mxCell` IDs are unique per page, every edge references existing source/target cells, every page contains a title/subtitle/legend/status boundary, no `http://` or `https://` occurs in any image style, the output contains at least five embedded SVG icons, and XML parsing succeeds after a fresh regeneration.

- [ ] **Step 2: Run the complete test suite**

Run:

```powershell
python tools/architecture/generate_vaakmitra_drawio.py
python -m pytest tests/architecture/test_vaakmitra_drawio.py -v
```

Expected: all diagram tests pass.

- [ ] **Step 3: Check XML and repository hygiene**

Run:

```powershell
python -c "import xml.etree.ElementTree as ET; p='docs/architecture/VaakMitra_Academic_Research_Architecture.drawio'; r=ET.parse(p).getroot(); print(r.tag, len(r.findall('diagram')))"
git diff --check
git status --short
```

Expected: `mxfile 3`, no whitespace errors, and only intended architecture files staged or modified.

- [ ] **Step 4: Inspect the generated page bounds and text density**

Use the generator's geometry audit to print each page's cells outside the `1600 x 1000` canvas, overlapping sibling blocks, and labels longer than their configured wrap capacity. Expected output: zero out-of-bounds cells, zero unintended overlaps, and zero unwrapped labels.

- [ ] **Step 5: Open the final artifact for user inspection**

Open `docs/architecture/VaakMitra_Academic_Research_Architecture.drawio` in the Codex file panel. If a diagrams.net renderer becomes available, export each page to PNG and visually verify arrow direction, clipping, icon placement, and layer separation before delivery.

- [ ] **Step 6: Commit final verification adjustments**

```powershell
git add tools/architecture tests/architecture docs/architecture/VaakMitra_Academic_Research_Architecture.drawio
git commit -m "docs: finalize verified VaakMitra research architecture"
```
