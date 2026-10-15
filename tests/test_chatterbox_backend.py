from pathlib import Path

from app.pipeline.backends.chatterbox import ChatterboxBackend
from app.pipeline.backends.openvoice_piper import get_backend


def test_indonesian_uses_malay_language(monkeypatch, tmp_path: Path):
    calls = {}

    class FakeModel:
        sr = 24000

        def generate(self, text, **kwargs):
            calls.update(kwargs)
            return [0.0, 0.0]

    backend = ChatterboxBackend()
    monkeypatch.setattr(backend, "_get_model", lambda: FakeModel())
    monkeypatch.setattr("soundfile.write", lambda *args, **kwargs: None)

    backend.synthesize("Halo", tmp_path / "reference.wav", "id",
                       tmp_path / "result.wav")

    assert calls["language_id"] == "ms"


def test_factory_forwards_chatterbox_options():
    backend = get_backend(
        "chatterbox", device="cpu", exaggeration=0.4,
        cfg_weight=0.3, t3_model="v3")

    assert backend._device == "cpu"
    assert backend.exaggeration == 0.4
    assert backend.cfg_weight == 0.3
    assert backend.t3_model == "v3"
