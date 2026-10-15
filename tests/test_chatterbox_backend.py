from pathlib import Path

from app.pipeline.backends.chatterbox import ChatterboxBackend
from app.pipeline.backends.openvoice_piper import get_backend


def test_indonesian_uses_malay_language(monkeypatch, tmp_path: Path):
    calls = {}

    class FakeTensor:
        def detach(self):
            return self

        def cpu(self):
            return self

        def squeeze(self):
            return self

        def numpy(self):
            return [0.0, 0.0]

    class FakeModel:
        sr = 24000

        def generate(self, text, **kwargs):
            calls.update(kwargs)
            return FakeTensor()

    backend = ChatterboxBackend()
    monkeypatch.setattr(backend, "_get_model", lambda: FakeModel())
    monkeypatch.setattr(
        "soundfile.write",
        lambda path, audio, sr: calls.update(
            written_audio=audio, written_sr=sr))

    backend.synthesize("Halo", tmp_path / "reference.wav", "id",
                       tmp_path / "result.wav")

    assert calls["language_id"] == "ms"
    assert calls["written_audio"] == [0.0, 0.0]
    assert calls["written_sr"] == 24000


def test_factory_forwards_chatterbox_options():
    backend = get_backend(
        "chatterbox", device="cpu", exaggeration=0.4,
        cfg_weight=0.3, t3_model="v3")

    assert backend._device == "cpu"
    assert backend.exaggeration == 0.4
    assert backend.cfg_weight == 0.3
    assert backend.t3_model == "v3"
