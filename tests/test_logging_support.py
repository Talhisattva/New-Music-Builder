from pathlib import Path

from new_music_builder.platform import logging_support


def test_write_runtime_fatal_log_appends_human_readable_entry(monkeypatch, tmp_path: Path) -> None:
    target = tmp_path / 'runtime_fatal.log'
    monkeypatch.setattr(logging_support, 'runtime_fatal_log_path', lambda: target)

    try:
        raise RuntimeError('boom')
    except RuntimeError as exc:
        path = logging_support.write_runtime_fatal_log(
            'Test runtime failure',
            RuntimeError,
            exc,
            exc.__traceback__,
            thread_name='worker-1',
        )

    assert path == str(target)
    contents = target.read_text(encoding='utf-8')
    assert 'Context: Test runtime failure' in contents
    assert 'Thread: worker-1' in contents
    assert 'RuntimeError: boom' in contents
