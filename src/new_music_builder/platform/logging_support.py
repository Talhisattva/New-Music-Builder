from __future__ import annotations

from datetime import datetime
import logging
from logging.handlers import RotatingFileHandler
import os
import sys
import threading
import traceback

from .paths import diagnostic_log_path, runtime_fatal_log_path


_LOGGER_NAME = 'new_music_builder'
_DEFAULT_LOG_LEVEL = 'INFO'
_RUNTIME_HOOKS_INSTALLED = False


def configure_logging() -> logging.Logger:
    logger = logging.getLogger(_LOGGER_NAME)
    if logger.handlers:
        return logger

    logger.setLevel(_resolve_log_level())
    logger.propagate = False
    formatter = logging.Formatter('%(asctime)s [%(levelname)s] %(message)s')

    stream = logging.StreamHandler(sys.stdout)
    stream.setLevel(logging.INFO)
    stream.setFormatter(formatter)
    logger.addHandler(stream)

    file_handler = RotatingFileHandler(
        diagnostic_log_path(),
        maxBytes=2_000_000,
        backupCount=5,
        encoding='utf-8',
    )
    file_handler.setLevel(logger.level)
    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)
    return logger


def install_runtime_exception_logging(logger: logging.Logger | None = None) -> None:
    global _RUNTIME_HOOKS_INSTALLED
    if _RUNTIME_HOOKS_INSTALLED:
        return

    active_logger = logger or configure_logging()
    previous_sys_hook = sys.excepthook
    previous_thread_hook = getattr(threading, 'excepthook', None)

    def _sys_hook(exc_type, exc_value, exc_traceback) -> None:
        if issubclass(exc_type, KeyboardInterrupt):
            previous_sys_hook(exc_type, exc_value, exc_traceback)
            return
        crash_path = write_runtime_fatal_log(
            'Uncaught exception on main thread',
            exc_type,
            exc_value,
            exc_traceback,
            thread_name=threading.current_thread().name,
        )
        active_logger.exception(
            'Unhandled exception. See %s',
            crash_path,
            exc_info=(exc_type, exc_value, exc_traceback),
        )
        previous_sys_hook(exc_type, exc_value, exc_traceback)

    def _thread_hook(args: threading.ExceptHookArgs) -> None:
        if issubclass(args.exc_type, KeyboardInterrupt):
            if previous_thread_hook is not None:
                previous_thread_hook(args)
            return
        crash_path = write_runtime_fatal_log(
            'Uncaught exception on background thread',
            args.exc_type,
            args.exc_value,
            args.exc_traceback,
            thread_name=getattr(args.thread, 'name', 'unknown'),
        )
        active_logger.exception(
            'Unhandled thread exception. See %s',
            crash_path,
            exc_info=(args.exc_type, args.exc_value, args.exc_traceback),
        )
        if previous_thread_hook is not None:
            previous_thread_hook(args)

    sys.excepthook = _sys_hook
    if previous_thread_hook is not None:
        threading.excepthook = _thread_hook
    _RUNTIME_HOOKS_INSTALLED = True


def write_runtime_fatal_log(
    context: str,
    exc_type: type[BaseException],
    exc_value: BaseException,
    exc_traceback,
    *,
    thread_name: str,
) -> str:
    log_path = runtime_fatal_log_path()
    entry = _format_fatal_entry(
        context,
        exc_type,
        exc_value,
        exc_traceback,
        thread_name=thread_name,
    )
    with log_path.open('a', encoding='utf-8') as handle:
        if log_path.exists() and log_path.stat().st_size > 0:
            handle.write('\n' + ('=' * 80) + '\n\n')
        handle.write(entry)
        if not entry.endswith('\n'):
            handle.write('\n')
    return str(log_path)


def _format_fatal_entry(
    context: str,
    exc_type: type[BaseException],
    exc_value: BaseException,
    exc_traceback,
    *,
    thread_name: str,
) -> str:
    timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    traceback_text = ''.join(traceback.format_exception(exc_type, exc_value, exc_traceback)).strip()
    lines = [
        f'Timestamp: {timestamp}',
        f'Context: {context}',
        f'Thread: {thread_name}',
        f'Python: {sys.version.split()[0]}',
        f'Working Directory: {os.getcwd()}',
        '',
        traceback_text,
    ]
    return '\n'.join(lines) + '\n'


def _resolve_log_level() -> int:
    configured = os.getenv('NMB_LOG_LEVEL', _DEFAULT_LOG_LEVEL).strip().upper()
    return getattr(logging, configured, logging.INFO)
