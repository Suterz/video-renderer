from video_renderer.drama3 import checkpoint_profile


def test_checkpoint_reference_identity_ignores_checkout_location():
    reference = {"label": "A", "path": "/one/A.safetensors", "reference": {"sha256": "example"},
                 "sampling": {"temperature": 1}}
    assert checkpoint_profile(reference) == checkpoint_profile({**reference, "path": "/two/A.safetensors"})
    assert checkpoint_profile(reference) != checkpoint_profile({**reference, "sampling": {"temperature": .8}})
