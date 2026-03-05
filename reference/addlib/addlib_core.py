"""Core logic for moving and organizing media files (movies, TV series)."""

import os
import shutil
import pypinyin
import time

LOG_FILE = "video_log.log"


def default_logger(message: str) -> None:
    """Default logger: writes to file and stdout."""
    with open(LOG_FILE, "a", encoding="utf-8") as log_file:
        log_file.write(f"{message}\n")
    print(message)


def get_initial_char(name: str, logger=None) -> str | None:
    """Get the initial character for categorization."""
    time.sleep(1)
    if name[0].isdigit():
        return "0-9"
    else:
        pinyin = pypinyin.pinyin(name[0], style=pypinyin.Style.FIRST_LETTER)
        if pinyin and pinyin[0][0].isalpha():
            return pinyin[0][0].upper()
        else:
            return None


def create_initial_folders(root_dir: str, logger=None) -> None:
    """Pre-create 0-9 and A-Z folders in the root directory, if they are missing."""
    log = logger or default_logger
    expected = {'0-9'} | {chr(i) for i in range(ord('A'), ord('Z') + 1)}
    existing = set(os.listdir(root_dir))
    time.sleep(1)
    missing = expected - existing
    for folder in sorted(missing):
        folder_path = os.path.join(root_dir, folder)
        os.makedirs(folder_path)
        log(f"Created missing folder: '{folder_path}'")
        time.sleep(1)


def move_movie(src: str, dst: str, logger=None) -> None:
    """For movies, remove existing target and then move the entire movie directory."""
    log = logger or default_logger
    if os.path.exists(dst):
        shutil.rmtree(dst)
        log(f"Deleted existing movie directory '{dst}'")
    shutil.move(src, dst)
    log(f"Moved movie '{src}' to '{dst}'")
    time.sleep(1)


def move_tv_series(src: str, dst: str, logger=None) -> None:
    """For TV series, handle by season level."""
    log = logger or default_logger
    if not os.path.exists(dst):
        shutil.move(src, dst)
        log(f"Moved TV series '{src}' to '{dst}'")
        time.sleep(1)
    else:
        for season in os.listdir(src):
            src_season_path = os.path.join(src, season)
            dst_season_path = os.path.join(dst, season)

            if os.path.isdir(src_season_path):
                if os.path.exists(dst_season_path):
                    shutil.rmtree(dst_season_path)
                    log(f"Deleted existing season directory '{dst_season_path}'")
                shutil.move(src_season_path, dst_season_path)
                log(f"Moved season '{src_season_path}' to '{dst_season_path}'")
                time.sleep(1)


def move_and_rename(
    source_root: str,
    target_root: str,
    content_type: str,
    organize_by_initial: bool,
    logger=None,
) -> None:
    """Move and rename based on content type (movie or tv_series) and organization choice."""
    log = logger or default_logger

    if organize_by_initial:
        create_initial_folders(target_root, log)

    for item in os.listdir(source_root):
        item_path = os.path.join(source_root, item)
        time.sleep(1)

        if organize_by_initial:
            initial_char = get_initial_char(item)
            if initial_char:
                dest_dir = os.path.join(target_root, initial_char)
                if not os.path.exists(dest_dir):
                    os.makedirs(dest_dir)
                    log(f"Created missing folder: '{dest_dir}'")
                    time.sleep(1)
                target_path = os.path.join(dest_dir, item)
            else:
                target_path = os.path.join(target_root, item)
        else:
            target_path = os.path.join(target_root, item)

        try:
            if os.path.isdir(item_path) and "tmdb" not in item.lower():
                with open(LOG_FILE, "a", encoding="utf-8") as log_file:
                    log_file.write(f"Directory without 'tmdb': {item_path}\n")

            if content_type == "movie":
                move_movie(item_path, target_path, log)
            elif content_type == "tv_series":
                move_tv_series(item_path, target_path, log)

        except Exception as e:
            log(f"Failed to move '{item}': {e}")
            time.sleep(1)
