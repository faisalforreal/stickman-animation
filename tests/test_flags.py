import pytest

from stickman_anim.lib import parse_flags


@pytest.mark.parametrize("words,expected", [
    ([], ("gif-hd", "dark")),
    (["gif"], ("gif", "dark")),
    (["video-4k", "bg-white"], ("video-4k", "light")),
    (["--video-hd", "--fg-black"], ("video-hd", "light")),       # fg-black implies a white ground
    (["fg-white"], ("gif-hd", "dark")),
    (["bg-black", "fg-white", "gif-hd"], ("gif-hd", "dark")),
    (["something-else", "out"], ("gif-hd", "dark")),            # unknown words are ignored
])
def test_parse_flags(words, expected):
    assert parse_flags(words) == expected


@pytest.mark.parametrize("words", [["bg-white", "fg-white"], ["bg-black", "fg-black"]])
def test_clashing_theme_is_rejected(words):
    with pytest.raises(SystemExit):
        parse_flags(words)
