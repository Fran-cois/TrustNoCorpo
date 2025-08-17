from pathlib import Path

from TrustNoCorpo.keys import KeyManager


def test_generate_and_use_user_keys(temp_home):
    km = KeyManager()
    assert not km.user_has_keys()

    ok = km.generate_user_keys("alice", "secret-pass")
    assert ok
    assert km.user_has_keys()

    # Files created under temp HOME
    assert km.private_key_path.exists()
    assert km.public_key_path.exists()
    assert km.info_path.exists()

    # Load keys
    assert km.load_private_key("secret-pass") is not None
    assert km.load_public_key() is not None

    # Encrypt/decrypt roundtrip
    plaintext = "hello-world"
    enc = km.encrypt_data(plaintext, "secret-pass")
    assert enc is not None
    dec = km.decrypt_data(enc, "secret-pass")
    assert dec == plaintext
