"""backend/tests/test_tui.py — Tests for TraceX Terminal User Interface."""

import asyncio
from pathlib import Path
from backend.cli.tui.app import TraceXApp
from backend.cli.tui.engine import TraceXPipelineEngine

FIXTURE = "backend/tests/fixtures/hikvision_synthetic.dd"


def test_tui_mount_and_widgets():
    """Verify that TraceXApp mounts with 50/50 panels, header logo, and file prompt."""
    async def run():
        app = TraceXApp()
        async with app.run_test() as pilot:
            await pilot.pause(0.2)
            assert app.query_one("#logo-widget") is not None
            left = app.query_one("#query-results-panel")
            right = app.query_one("#additional-analysis-panel")
            assert left is not None
            assert right is not None
            assert app.query_one("#search-input") is not None
            assert app.query_one("#footer-bar") is not None

            # Verify panel border titles and prompt
            assert left.border_title == "QUERY RESULTS"
            assert right.border_title == "AI FORENSIC ANALYSIS"

            left_text = str(app.query_one("#query-results-content").render())
            assert "Evidence File Ingestion" in left_text

            right_text = str(app.query_one("#additional-analysis-content").render())
            assert "Awaiting evidence ingestion" in right_text

    asyncio.run(run())


def test_tui_invalid_file_handling():
    """Verify that submitting a non-existent file path reports a clear error."""
    async def run():
        app = TraceXApp()
        async with app.run_test() as pilot:
            inp = app.query_one("#search-input")
            inp.value = "non_existent_evidence_file_123.dd"
            await pilot.press("enter")
            await pilot.pause(0.2)
            content = str(app.query_one("#query-results-content").render())
            assert "file not found" in content.lower()

    asyncio.run(run())


def test_tui_file_to_query_analysis_flow():
    """Verify the workflow: file upload -> pipeline execution -> query analysis."""
    async def run():
        app = TraceXApp()
        async with app.run_test() as pilot:
            inp = app.query_one("#search-input")
            # Step 1: Upload file
            inp.value = FIXTURE
            await pilot.press("enter")

            # Wait for pipeline worker to complete
            for _ in range(40):
                await pilot.pause(0.5)
                left_content = str(app.query_one("#query-results-content").render())
                if "Evidence Ingested Successfully" in left_content or "Query Analysis Ready" in left_content:
                    break

            assert "Evidence Ingested Successfully" in left_content

            # Step 2: Check that Right Panel rendered real pipeline data from old CLI
            right_content = str(app.query_one("#additional-analysis-content").render())
            assert "Discovered Recordings" in right_content

            # Step 3: Run query analysis question
            inp.value = "what was detected?"
            await pilot.press("enter")

            for _ in range(40):
                await pilot.pause(0.5)
                left_content = str(app.query_one("#query-results-content").render())
                if "Findings & Analysis" in left_content:
                    break

            assert "Findings & Analysis" in left_content

    asyncio.run(run())


def test_tracex_pipeline_engine_direct():
    """Verify that TraceXPipelineEngine directly runs the real pipeline."""
    engine = TraceXPipelineEngine()
    res = engine.run_pipeline(FIXTURE)
    assert res.vendor_name == "hikvision"
    assert res.vendor_confidence > 0.5
    assert len(res.parse_recordings) >= 1

    ans = engine.ask_video_query("was any person detected?")
    assert ans.query == "was any person detected?"
    assert len(ans.answer) > 0


def test_tui_paste_into_query_box():
    """Verify that pasting from OS clipboard strips quotes and terminal artifacts."""
    from backend.cli.tui.clipboard import set_clipboard_text

    async def run():
        app = TraceXApp()
        async with app.run_test() as pilot:
            inp = app.query_one("#search-input")
            inp.focus()

            # Test 1: Simulate copied path from Windows Explorer (with enclosing quotes)
            test_path = 'C:/Users/test/evidence.dd'
            set_clipboard_text(f'"{test_path}"')
            inp.action_paste()
            await pilot.pause(0.1)
            assert inp.value == test_path

            # Test 2: Simulate bracketed paste residue (0~ or 200~ prefix)
            inp.value = ""
            set_clipboard_text(f'0~"{test_path}"')
            inp.action_paste()
            await pilot.pause(0.1)
            assert inp.value == test_path

            # Test 3: Rapid consecutive paste (must not duplicate text)
            inp.action_paste()
            await pilot.pause(0.1)
            assert inp.value == test_path, f"Expected single path, got duplicate: {inp.value}"

    asyncio.run(run())


def test_tui_ctrl_o_new_file_upload_keybind():
    """Verify that Ctrl+O resets the interface to ask for another file upload."""
    async def run():
        app = TraceXApp()
        async with app.run_test() as pilot:
            # Simulate app in query mode with a loaded file
            app.mode = "query"
            inp = app.query_one("#search-input")
            inp.value = "what was detected?"
            inp.placeholder = "Ask about this video timeline..."

            # Trigger Ctrl+O keybind
            await pilot.press("ctrl+o")
            await pilot.pause(0.1)

            assert app.mode == "file"
            assert inp.value == ""
            assert inp.placeholder == "Enter evidence / video file path..."

            left_content = str(app.query_one("#query-results-content").render())
            assert "Evidence File Ingestion" in left_content

            right_content = str(app.query_one("#additional-analysis-content").render())
            assert "Awaiting evidence ingestion" in right_content

    asyncio.run(run())



