"""Tests for CharacterService - Character definition and retrieval.

Tests for:
- Character dataclass structure (id, display_name, description, system_prompt, tts_voice_name)
- 3 predefined characters: gyaru, senpai, butler
- get_character() with valid/invalid/None IDs and fallback behavior
- get_all_characters() returns all defined characters
- Character immutability (frozen dataclass)
- System prompt quality for each character

Requirements Coverage: 1.1, 1.2, 1.3, 3.2, 4.3
"""

import dataclasses

import pytest


class TestCharacterDataclass:
    """Tests for Character dataclass structure."""

    def test_character_has_required_fields(self):
        """Character dataclass should have id, display_name, description, system_prompt, tts_voice_name."""
        from src.services.character_service import Character

        fields = {f.name for f in dataclasses.fields(Character)}
        assert "id" in fields
        assert "display_name" in fields
        assert "description" in fields
        assert "system_prompt" in fields
        assert "tts_voice_name" in fields

    def test_character_is_frozen(self):
        """Character dataclass should be immutable (frozen=True)."""
        from src.services.character_service import Character

        char = Character(
            id="test",
            display_name="Test",
            description="Test desc",
            system_prompt="Test prompt",
            tts_voice_name="test-voice",
        )
        with pytest.raises(dataclasses.FrozenInstanceError):
            char.id = "modified"  # type: ignore[misc]


class TestDefaultCharacterId:
    """Tests for DEFAULT_CHARACTER_ID constant."""

    def test_default_character_id_is_gyaru(self):
        """Default character ID should be 'gyaru'."""
        from src.services.character_service import DEFAULT_CHARACTER_ID

        assert DEFAULT_CHARACTER_ID == "gyaru"


class TestGetCharacter:
    """Tests for get_character() function."""

    def test_get_character_returns_gyaru_for_gyaru_id(self):
        """get_character('gyaru') should return the gyaru character."""
        from src.services.character_service import get_character

        char = get_character("gyaru")
        assert char.id == "gyaru"
        assert char.display_name == "全肯定ギャル"

    def test_get_character_returns_senpai_for_senpai_id(self):
        """get_character('senpai') should return the senpai character."""
        from src.services.character_service import get_character

        char = get_character("senpai")
        assert char.id == "senpai"
        assert char.display_name == "優しい先輩"

    def test_get_character_returns_butler_for_butler_id(self):
        """get_character('butler') should return the butler character."""
        from src.services.character_service import get_character

        char = get_character("butler")
        assert char.id == "butler"
        assert char.display_name == "冷静な執事"

    def test_get_character_returns_default_for_none(self):
        """get_character(None) should return the default character (gyaru)."""
        from src.services.character_service import get_character

        char = get_character(None)
        assert char.id == "gyaru"

    def test_get_character_returns_default_for_invalid_id(self):
        """get_character with invalid ID should return the default character (gyaru)."""
        from src.services.character_service import get_character

        char = get_character("nonexistent")
        assert char.id == "gyaru"

    def test_get_character_returns_default_for_empty_string(self):
        """get_character('') should return the default character (gyaru)."""
        from src.services.character_service import get_character

        char = get_character("")
        assert char.id == "gyaru"


class TestGetAllCharacters:
    """Tests for get_all_characters() function."""

    def test_get_all_characters_returns_three_characters(self):
        """get_all_characters() should return exactly 3 characters."""
        from src.services.character_service import get_all_characters

        characters = get_all_characters()
        assert len(characters) == 3

    def test_get_all_characters_contains_all_character_ids(self):
        """get_all_characters() should contain gyaru, senpai, and butler."""
        from src.services.character_service import get_all_characters

        characters = get_all_characters()
        ids = {c.id for c in characters}
        assert ids == {"gyaru", "senpai", "butler"}

    def test_get_all_characters_returns_character_instances(self):
        """get_all_characters() should return list of Character instances."""
        from src.services.character_service import Character, get_all_characters

        characters = get_all_characters()
        for char in characters:
            assert isinstance(char, Character)


class TestCharacterSystemPrompts:
    """Tests for character system prompts quality."""

    def test_gyaru_system_prompt_contains_conversion_rules(self):
        """Gyaru system prompt should contain conversion rules."""
        from src.services.character_service import get_character

        char = get_character("gyaru")
        assert "ウチ" in char.system_prompt
        assert "先輩" in char.system_prompt
        assert "絵文字" in char.system_prompt

    def test_senpai_system_prompt_is_non_empty(self):
        """Senpai system prompt should be non-empty and contain conversion rules."""
        from src.services.character_service import get_character

        char = get_character("senpai")
        assert len(char.system_prompt) > 100
        assert "先輩" in char.system_prompt or "変換" in char.system_prompt

    def test_butler_system_prompt_is_non_empty(self):
        """Butler system prompt should be non-empty and contain conversion rules."""
        from src.services.character_service import get_character

        char = get_character("butler")
        assert len(char.system_prompt) > 100
        assert "執事" in char.system_prompt or "変換" in char.system_prompt

    def test_all_prompts_prohibit_emoji(self):
        """All character system prompts should mention emoji policy."""
        from src.services.character_service import get_all_characters

        for char in get_all_characters():
            assert "絵文字" in char.system_prompt, (
                f"{char.id} system prompt should mention emoji policy"
            )

    def test_all_prompts_require_output_format(self):
        """All character system prompts should specify output format."""
        from src.services.character_service import get_all_characters

        for char in get_all_characters():
            assert "出力" in char.system_prompt, (
                f"{char.id} system prompt should specify output format"
            )


class TestCharacterTtsVoiceNames:
    """Tests for character TTS voice name assignments."""

    def test_gyaru_uses_callirrhoe_voice(self):
        """Gyaru character should use Callirrhoe TTS voice."""
        from src.services.character_service import get_character

        char = get_character("gyaru")
        assert "Callirrhoe" in char.tts_voice_name

    def test_senpai_uses_aoede_voice(self):
        """Senpai character should use Aoede TTS voice."""
        from src.services.character_service import get_character

        char = get_character("senpai")
        assert "Aoede" in char.tts_voice_name

    def test_butler_uses_charon_voice(self):
        """Butler character should use Charon TTS voice."""
        from src.services.character_service import get_character

        char = get_character("butler")
        assert "Charon" in char.tts_voice_name

    def test_all_voices_are_chirp3_hd_japanese(self):
        """All TTS voice names should be Chirp3-HD Japanese voices."""
        from src.services.character_service import get_all_characters

        for char in get_all_characters():
            assert char.tts_voice_name.startswith("ja-JP-Chirp3-HD-"), (
                f"{char.id} voice should be Chirp3-HD Japanese"
            )


class TestCharacterDescriptions:
    """Tests for character descriptions."""

    def test_gyaru_description_is_non_empty(self):
        """Gyaru character should have a non-empty description."""
        from src.services.character_service import get_character

        char = get_character("gyaru")
        assert len(char.description) > 0

    def test_senpai_description_is_non_empty(self):
        """Senpai character should have a non-empty description."""
        from src.services.character_service import get_character

        char = get_character("senpai")
        assert len(char.description) > 0

    def test_butler_description_is_non_empty(self):
        """Butler character should have a non-empty description."""
        from src.services.character_service import get_character

        char = get_character("butler")
        assert len(char.description) > 0
