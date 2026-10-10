import csv
import os
from pathlib import Path
import re
import shutil
import time

from log import setup_logger


CDXML_FILE_PATTERN = "*.cdxml"
OUTPUT_FILETYPE = ".pdf"
MAP_PATH = "maps/structure_id_map.csv"
TEX_MAP_PATH = "maps/_structure_id_map.csv"
LABEL_PREFIX = "CMPD"
LABEL_PATTERN = re.compile(f"{LABEL_PREFIX}:([A-Za-z0-9\\-]+)")

INPUT_DIR = "chemdraw/cdxml"
OUTPUT_DIR = "chemdraw/cdxml_"

# Hidden state file storing the last successful run start time (Unix epoch seconds)
STATE_FILE = Path(OUTPUT_DIR) / ".relabel_last_run_epoch"

LOG = setup_logger("RELABELLING_UTIL")


def load_last_run_epoch(state_file: Path) -> float:
    try:
        return float(state_file.read_text().strip())
    except FileNotFoundError:
        return 0.0
    except ValueError:
        LOG.warning(f"Invalid state file contents in {state_file}; treating as first run.")
        return 0.0


def save_last_run_epoch(state_file: Path, epoch: float) -> None:
    state_file.write_text(f"{epoch:.6f}")


def prepare_dirs(last_run_epoch: float, relabel_all: bool) -> list[Path]:
    """
    Copy source CDXML files into OUTPUT_DIR so original files are not edited.

    If relabel_all is True, copy everything and return everything for processing.
    Otherwise only copy files modified since the last successful run.
    """
    input_dir = Path(INPUT_DIR)
    output_dir = Path(OUTPUT_DIR)
    output_dir.mkdir(parents=True, exist_ok=True)

    files_to_process: list[Path] = []

    for src in input_dir.rglob(CDXML_FILE_PATTERN):
        if not src.is_file():
            continue

        dst = output_dir / src.name
        src_mtime = src.stat().st_mtime

        if relabel_all or src_mtime > last_run_epoch or not dst.exists():
            shutil.copy2(src, dst)
            files_to_process.append(dst)

    return files_to_process


def create_relabel_dict(map_path: Path) -> dict[str, str]:
    if not map_path.exists():
        raise FileNotFoundError(f"Mapping filepath {map_path} does not exist.")
    with open(map_path) as f:
        reader = csv.reader(f)
        row_0 = next(reader)
        relabel = row_0[0] == "RELABEL=TRUE"
        out = {}
        for key, value, *_ in reader:
            key = key.strip()
            value = value.strip()
            if not relabel and key != 'compound':
                out[key] = key
                continue
            if key in out:
                LOG.warn(f"Duplicate values values defined for {key}")
                continue
            out[key] = value
    return out


def write_latex_map_csv(table: dict[str, str], csv_path: Path) -> None:
    # Create trimmed key-value csv for LaTeX to read in and create mappings
    with open(csv_path, "w", newline="") as f:
        writer = csv.writer(f)
        for k, v in table.items():
            if v.strip():
                writer.writerow([k, v])


def modify_cdxml(path: Path, relabel_dict: dict[str, str]) -> int:
    def replace(match):
        key = match.group(1)
        if key in relabel_dict and (value := relabel_dict[key]):
            return value
        LOG.warning(f"No matching value for compound {key} {path}")
        return key

    with open(path, "r") as cdxml:
        txt = cdxml.read()
        txt, n = LABEL_PATTERN.subn(replace, txt)

    with open(path, "w") as cdxml:
        cdxml.write(txt)

    return n


def main() -> None:
    program_start = time.time()
    last_run_epoch = load_last_run_epoch(STATE_FILE)

    map_path = Path(MAP_PATH)
    map_mtime = map_path.stat().st_mtime if map_path.exists() else 0.0

    # If the map file changed since the last run, relabel everything.
    relabel_all = map_mtime > last_run_epoch

    relabel_dict = create_relabel_dict(map_path)
    write_latex_map_csv(relabel_dict, Path(TEX_MAP_PATH))

    files_to_process = prepare_dirs(last_run_epoch, relabel_all)

    n_files_modified = 0
    n_relabels = 0

    try:
        for path in files_to_process:
            n_relabels += modify_cdxml(path, relabel_dict)
            n_files_modified += 1
    except Exception:
        LOG.exception("Run failed; state file was not updated.")
        raise
    else:
        # Save the time at which this run started, so files changed during the run
        # will still be seen as newer on the next run.
        save_last_run_epoch(STATE_FILE, program_start)

    time_elapsed = time.time() - program_start

    LOG.info(
        f"{n_files_modified} CDXML files processed, "
        f"{n_relabels} tags relabelled in {time_elapsed:.3g} s"
    )


if __name__ == "__main__":
    main()
