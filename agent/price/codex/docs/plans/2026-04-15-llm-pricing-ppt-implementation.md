# LLM Pricing PPT Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Build an editable `.pptx` executive report from the existing Markdown research using a reproducible local generation script.

**Architecture:** Use the Markdown report as the single source of truth, encode the approved 12-slide narrative into a small Python generator based on `python-pptx`, then run a smoke verification script to confirm slide count and key content. Keep the implementation minimal: one generator, one output file, one verification script.

**Tech Stack:** Python 3, `python-pptx`, standard library zip/xml parsing or `python-pptx` inspection, local filesystem

---

### Task 1: Scaffold PPT Generation Files

**Files:**
- Create: `ppt/generate_llm_pricing_report.py`
- Create: `ppt/__init__.py`
- Create: `tests/test_generate_llm_pricing_report.py`
- Test: `tests/test_generate_llm_pricing_report.py`

**Step 1: Write the failing test**

```python
from pathlib import Path

from ppt.generate_llm_pricing_report import build_presentation


def test_build_presentation_creates_expected_slide_count(tmp_path: Path):
    output = tmp_path / "report.pptx"
    build_presentation(output)
    assert output.exists()
```

**Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_generate_llm_pricing_report.py -v`
Expected: FAIL with import error or missing function

**Step 3: Write minimal implementation**

```python
from pathlib import Path

from pptx import Presentation


def build_presentation(output_path: Path) -> None:
    prs = Presentation()
    prs.slides.add_slide(prs.slide_layouts[0])
    output_path.parent.mkdir(parents=True, exist_ok=True)
    prs.save(str(output_path))
```

**Step 4: Run test to verify it passes**

Run: `python -m pytest tests/test_generate_llm_pricing_report.py -v`
Expected: PASS

**Step 5: Commit**

```bash
git add ppt/__init__.py ppt/generate_llm_pricing_report.py tests/test_generate_llm_pricing_report.py
git commit -m "feat: scaffold ppt generation script"
```

### Task 2: Encode Approved Slide Narrative

**Files:**
- Modify: `ppt/generate_llm_pricing_report.py`
- Test: `tests/test_generate_llm_pricing_report.py`

**Step 1: Write the failing test**

```python
from pathlib import Path

from pptx import Presentation

from ppt.generate_llm_pricing_report import build_presentation


def test_build_presentation_contains_expected_titles(tmp_path: Path):
    output = tmp_path / "report.pptx"
    build_presentation(output)
    prs = Presentation(str(output))
    titles = [
        slide.shapes.title.text
        for slide in prs.slides
        if slide.shapes.title is not None
    ]
    assert "执行摘要" in titles
    assert "三家模型价格总览" in titles
    assert "20 人团队月度 Token 基线模型" in titles
    assert "基线月费测算" in titles
```

**Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_generate_llm_pricing_report.py -v`
Expected: FAIL because only one slide exists

**Step 3: Write minimal implementation**

```python
SLIDES = [
    {"title": "标题页", "bullets": [...]},
    {"title": "执行摘要", "bullets": [...]},
    ...
]
```

Add helper functions to:
- create title/content slides
- render 3-5 bullets per slide
- preserve the approved 12-slide order

**Step 4: Run test to verify it passes**

Run: `python -m pytest tests/test_generate_llm_pricing_report.py -v`
Expected: PASS

**Step 5: Commit**

```bash
git add ppt/generate_llm_pricing_report.py tests/test_generate_llm_pricing_report.py
git commit -m "feat: add approved slide narrative"
```

### Task 3: Add Key Tables and Visual Summaries

**Files:**
- Modify: `ppt/generate_llm_pricing_report.py`
- Test: `tests/test_generate_llm_pricing_report.py`

**Step 1: Write the failing test**

```python
from pathlib import Path

from pptx import Presentation

from ppt.generate_llm_pricing_report import build_presentation


def test_build_presentation_contains_key_metrics(tmp_path: Path):
    output = tmp_path / "report.pptx"
    build_presentation(output)
    prs = Presentation(str(output))
    all_text = []
    for slide in prs.slides:
        for shape in slide.shapes:
            if hasattr(shape, "text"):
                all_text.append(shape.text)
    merged = "\n".join(all_text)
    assert "618.2M" in merged
    assert "5,102 元 ~ 6,252 元/月" in merged
    assert "$2,828 /月" in merged
```

**Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_generate_llm_pricing_report.py -v`
Expected: FAIL because key metrics are not yet rendered

**Step 3: Write minimal implementation**

Add structured slide renderers for:
- price comparison table
- limits comparison table
- token usage summary slide
- monthly cost summary slide

Prefer simple native PPT tables/shapes over image export.

**Step 4: Run test to verify it passes**

Run: `python -m pytest tests/test_generate_llm_pricing_report.py -v`
Expected: PASS

**Step 5: Commit**

```bash
git add ppt/generate_llm_pricing_report.py tests/test_generate_llm_pricing_report.py
git commit -m "feat: render pricing and cost summary slides"
```

### Task 4: Polish Theme and Export Final PPT

**Files:**
- Modify: `ppt/generate_llm_pricing_report.py`
- Create: `2026-04-15-llm-pricing-and-usage-report.pptx`
- Test: `tests/test_generate_llm_pricing_report.py`

**Step 1: Write the failing test**

```python
from pathlib import Path

from pptx import Presentation

from ppt.generate_llm_pricing_report import build_presentation


def test_final_presentation_has_expected_slide_count(tmp_path: Path):
    output = tmp_path / "report.pptx"
    build_presentation(output)
    prs = Presentation(str(output))
    assert len(prs.slides) == 12
```

**Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_generate_llm_pricing_report.py -v`
Expected: FAIL until slide count and final structure are aligned

**Step 3: Write minimal implementation**

Polish:
- unified theme colors
- consistent title/body font sizes
- slide footer with date/source note where needed
- final output path in repo root

Add a `main()` entrypoint:

```python
if __name__ == "__main__":
    build_presentation(Path("2026-04-15-llm-pricing-and-usage-report.pptx"))
```

**Step 4: Run test to verify it passes**

Run: `python -m pytest tests/test_generate_llm_pricing_report.py -v`
Expected: PASS

**Step 5: Commit**

```bash
git add ppt/generate_llm_pricing_report.py tests/test_generate_llm_pricing_report.py 2026-04-15-llm-pricing-and-usage-report.pptx
git commit -m "feat: generate final llm pricing ppt"
```

### Task 5: Verify Deliverable Can Be Opened

**Files:**
- Modify: `tests/test_generate_llm_pricing_report.py`
- Test: `tests/test_generate_llm_pricing_report.py`

**Step 1: Write the failing test**

```python
from pathlib import Path

from pptx import Presentation


def test_repo_ppt_can_be_opened():
    path = Path("2026-04-15-llm-pricing-and-usage-report.pptx")
    prs = Presentation(str(path))
    assert len(prs.slides) == 12
```

**Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_generate_llm_pricing_report.py -v`
Expected: FAIL if final file has not been generated or is malformed

**Step 3: Write minimal implementation**

Generate the final file using:

```bash
python ppt/generate_llm_pricing_report.py
```

Optionally validate with LibreOffice headless import/export if needed.

**Step 4: Run test to verify it passes**

Run: `python -m pytest tests/test_generate_llm_pricing_report.py -v`
Expected: PASS

**Step 5: Commit**

```bash
git add tests/test_generate_llm_pricing_report.py 2026-04-15-llm-pricing-and-usage-report.pptx
git commit -m "test: verify generated ppt deliverable"
```
