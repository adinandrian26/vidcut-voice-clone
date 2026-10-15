import importlib


def test_settings_include_chatterbox_options(monkeypatch):
    monkeypatch.setenv("VC_EXAGGERATION", "0.4")
    monkeypatch.setenv("VC_CFG_WEIGHT", "0.3")
    monkeypatch.setenv("VC_T3_MODEL", "v3")

    import app.config as config
    config = importlib.reload(config)

    assert config.settings.chatterbox_exaggeration == 0.4
    assert config.settings.chatterbox_cfg_weight == 0.3
    assert config.settings.chatterbox_t3_model == "v3"
