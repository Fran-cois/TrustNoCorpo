from pathlib import Path

from TrustNoCorpo.logger import BuildLogger
from TrustNoCorpo.keys import KeyManager


def test_log_and_list_and_verify_flow(temp_home, tmp_path):
    # Prepare isolated db under a temp directory
    db_dir = tmp_path / ".trustnocorpo"
    db_dir.mkdir()
    db_path = db_dir / "builds.db"

    # Ensure user keys exist so logger can fetch fingerprint
    km = KeyManager()
    assert km.generate_user_keys("bob", "pw")

    logger = BuildLogger(db_path=str(db_path))

    build_hash = "abcd1234efgh5678"
    build_id = logger.log_build(
        build_hash=build_hash,
        generation_info="Z2VuLWluZm8=",
        generation_time="dGltZQ==",
        classification="CONFIDENTIAL",
        main_file="doc.tex",
        pdf_path=None,
        pdf_password=None,
    )
    assert build_id is not None

    builds = logger.list_builds(limit=5)
    assert any(b["build_hash"] == build_hash for b in builds)

    assert logger.verify_build(build_hash) is True
