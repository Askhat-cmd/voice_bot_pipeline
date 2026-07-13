from youtube_channel_transcripts.text_cleaner import clean_transcript


def test_clean_transcript_removes_noise_and_html_entities():
    result = clean_transcript(
        ["Привет&nbsp;мир", "[Музыка]", "<i>Это тест</i>", "  ещё   текст  "]
    )
    assert result == "Привет мир Это тест ещё текст"


def test_clean_transcript_removes_rolling_overlap():
    result = clean_transcript(["это начало", "это начало фразы", "фразы и продолжение"])
    assert result == "это начало фразы и продолжение"


def test_content_brackets_inside_sentence_are_preserved():
    result = clean_transcript(["Используйте параметр [режим 2] в настройках"])
    assert result == "Используйте параметр [режим 2] в настройках"
