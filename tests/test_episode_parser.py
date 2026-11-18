from promofinder.ingestion.episode_parser import parse_episode


def test_parses_episode_scenes_timestamped_blocks_and_speaker(sample_episode):
    assert sample_episode.episode_id == "EP_001"
    assert sample_episode.logline == "A bride discovers a betrayal."
    assert len(sample_episode.scenes) == 1
    assert sample_episode.scenes[0].scene_id == "SC_001"
    assert len(sample_episode.blocks) == 2
    assert sample_episode.blocks[1].speaker == "JULIANA"
    assert sample_episode.blocks[1].start_seconds == 5
    assert sample_episode.screenplay_text.startswith("EPISODE NUMBER")


def test_rejects_episode_without_timestamped_content():
    import pytest
    with pytest.raises(ValueError, match="no timestamped"):
        from promofinder.ingestion.episode_parser import parse_files
        parse_files([(type("Path", (), {"__str__": lambda self: "episode-001.txt",
                                        "stem": "episode-001"})(), "EPISODE NUMBER: Episode 1")])
