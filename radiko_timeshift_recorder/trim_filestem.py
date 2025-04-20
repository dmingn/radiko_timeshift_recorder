import errno
from pathlib import Path


def trim_filestem(filepath: Path) -> Path:
    if filepath.is_dir():
        return filepath

    while filepath.stem:
        try:
            filepath.exists()
        except OSError as e:
            if e.errno == errno.ENAMETOOLONG:
                filepath = filepath.with_stem(filepath.stem[:-1])
            else:
                raise e
        else:
            break

    return filepath
