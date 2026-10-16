from pathlib import Path

from app.pipeline.backends.openvoice_piper import get_backend
from app.pipeline.backends.voxcpm import VoxCPMBackend


def test_indonesian_passed_through_natively(monkeypatch, tmp_path: Path):
    calls = {}

    class FakeTTSModel:
        sample_rate = 48000

    class FakeModel:
        tts_model = FakeTTSModel()

        def generate(self, text, **kwargs):
            calls["text"] = text
            calls.update(kwargs)
            return [0.0, 0.0]

    backend = VoxCPMBackend()
    monkeypatch.setattr(backend, "_get_model", lambda: FakeModel())
    monkeypatch.setattr(
        "soundfile.write",
        lambda path, audio, sr, **kwargs: calls.update(
            written_audio=list(audio), written_sr=sr,
            written_options=kwargs))
    monkeypatch.setattr(
        "app.pipeline.backends.voxcpm.to_wav_mono",
        lambda src, dest, **kw: (Path(dest).write_bytes(b"0"), dest)[1])

    backend.synthesize("Halo", tmp_path / "reference.wav", "id",
                       tmp_path / "result.wav")

    # Indonesia resmi didukung -> tidak ada remap bahasa.
    assert calls["text"] == "Halo"
    assert calls["reference_wav_path"] == str(tmp_path / "reference.wav")
    assert calls["written_audio"] == [0.0, 0.0]
    assert calls["written_sr"] == 48000
    assert calls["written_options"] == {
        "format": "WAV", "subtype": "PCM_16"}


def test_factory_forwards_voxcpm_options():
    backend = get_backend(
        "voxcpm2", device="cpu", voxcpm_cfg=1.5,
        voxcpm_steps=8, voxcpm_seed=7)

    assert backend._device == "cpu"
    assert backend.cfg_value == 1.5
    assert backend.steps == 8
    assert backend.seed == 7
    assert backend.model_id == "openbmb/VoxCPM2"
