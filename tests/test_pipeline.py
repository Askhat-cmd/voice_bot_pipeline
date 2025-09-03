import sys
import yaml
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parents[1]))

import pipeline_orchestrator as po
from subtitle_extractor.get_subtitles import YouTubeSubtitlesExtractor


def test_run_full_pipeline(tmp_path, monkeypatch):
    # Prepare temporary configuration
    config = {
        "logging": {"level": "INFO", "log_file": str(tmp_path / "test.log")},
        "pipeline": {
            "subtitles": {"output_dir": str(tmp_path / "subs"), "language": "ru"},
            "text_processing": {"output_dir": str(tmp_path / "processed")},
            "results_dir": str(tmp_path / "processed"),
        },
    }
    config_path = tmp_path / "config.yaml"
    config_path.write_text(yaml.dump(config, allow_unicode=True))

    # Mock environment for OpenAI (not used but required by original class)
    monkeypatch.setenv("OPENAI_API_KEY", "test")

    class DummyProcessor:
        def __init__(self, *args, **kwargs):
            pass

        def process_subtitles_file(self, transcript_path, output_dir):
            output_dir = Path(output_dir)
            output_dir.mkdir(parents=True, exist_ok=True)
            json_path = output_dir / f"{transcript_path.stem}_out.json"
            md_path = output_dir / f"{transcript_path.stem}_out.md"
            json_path.write_text("{}", encoding="utf-8")
            md_path.write_text("# md", encoding="utf-8")
            return {
                "json_output": str(json_path),
                "md_output": str(md_path),
                "blocks_created": 1,
            }

    monkeypatch.setattr(po, "SarsekenovProcessor", DummyProcessor)

    orchestrator = po.PipelineOrchestrator(str(config_path))

    # Mock YouTube subtitles retrieval
    dummy_subtitles = [{"text": "hello", "start": 0, "duration": 1}]
    monkeypatch.setattr(
        YouTubeSubtitlesExtractor,
        "get_subtitles",
        lambda self, video_id, language="ru": dummy_subtitles,
    )

    result = orchestrator.run_full_pipeline("https://youtu.be/dQw4w9WgXcQ")

    assert result["status"] == "success"

    subs_stage = result["stages"]["subtitles"]
    assert Path(subs_stage["json_path"]).is_file()
    assert Path(subs_stage["srt_path"]).is_file()
    assert Path(subs_stage["txt_path"]).is_file()

    final = result["final_outputs"]
    assert Path(final["sag_v2_json"]).is_file()
    assert Path(final["review_markdown"]).is_file()
