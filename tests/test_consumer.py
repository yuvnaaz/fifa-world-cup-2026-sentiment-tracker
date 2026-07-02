import importlib.util
from pathlib import Path

MODULE_PATH = Path(__file__).resolve().parents[1] / "consumer.py"
SPEC = importlib.util.spec_from_file_location("consumer_module", MODULE_PATH)
consumer = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(consumer)


def test_extract_target_team_detects_known_team_names():
    assert consumer.extract_target_team("Messi scored again for Argentina") == "Argentina"
    assert consumer.extract_target_team("The USA are pressing high") == "USA"
    assert consumer.extract_target_team("A random thought about the weather") == "Neutral/General"


def test_normalize_text_truncates_and_strips_translation_suffix():
    text = "This is a long message " * 20 + " [Original: some other text]"
    normalized = consumer.normalize_text(text, max_len=80)
    assert normalized.endswith("[Original: some other text]") is False
    assert len(normalized) <= 80
