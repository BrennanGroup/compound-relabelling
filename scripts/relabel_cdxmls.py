import csv
from pathlib import Path
import re
import shutil
import time

from log import setup_logger


CDXML_FILE_PATTERN = "*.cdxml"
MAP_PATH = Path("maps/structure_id_map.csv")
TEX_MAP_PATH = Path("maps/_structure_id_map.csv")
LABEL_PREFIX = "CMPD"
COMPOUND_ID_PATTERN = re.compile(r"^[A-Za-z0-9-]+$")
LABEL_PATTERN = re.compile(rf"{LABEL_PREFIX}:([A-Za-z0-9-]+)")
TEX_CMPD_PATTERN = re.compile(r"\\cmpd\{([A-Za-z0-9-]+)\}")

INPUT_DIR = Path("chemdraw/cdxml")
OUTPUT_DIR = Path("chemdraw/cdxml_")
STATE_FILE = OUTPUT_DIR / ".relabel_last_run_epoch"

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


def create_relabel_dict(map_path: Path) -> tuple[dict[str, str], bool]:
    """Read and validate the compound mapping file."""
    if not map_path.exists():
        raise FileNotFoundError(f"Mapping file {map_path} does not exist.")

    with map_path.open(newline="") as f:
        rows = list(csv.reader(f))

    if len(rows) < 2:
        raise ValueError(f"{map_path} must contain a RELABEL setting and a header row.")

    setting = rows[0][0].strip().upper() if rows[0] else ""
    if setting not in {"RELABEL=TRUE", "RELABEL=FALSE"}:
        raise ValueError(
            f"First cell of {map_path} must be RELABEL=TRUE or RELABEL=FALSE; got {setting!r}."
        )
    relabel = setting == "RELABEL=TRUE"

    header = [cell.strip().lower() for cell in rows[1]]
    if len(header) < 2 or header[:2] != ["compound", "label"]:
        raise ValueError(
            f"Second row of {map_path} must begin with the columns 'compound,label'."
        )

    out: dict[str, str] = {}
    labels_seen: dict[str, str] = {}

    for row_number, row in enumerate(rows[2:], start=3):
        if not row or all(not cell.strip() for cell in row):
            continue
        if len(row) < 2:
            raise ValueError(f"Row {row_number} of {map_path} has fewer than two columns.")

        key, label = row[0].strip(), row[1].strip()
        if not key:
            raise ValueError(f"Row {row_number} of {map_path} has an empty compound ID.")
        if not COMPOUND_ID_PATTERN.fullmatch(key):
            raise ValueError(
                f"Invalid compound ID {key!r} on row {row_number}; use only letters, numbers, and hyphens."
            )
        if not label:
            raise ValueError(f"Compound {key!r} has an empty label on row {row_number}.")
        if key in out:
            raise ValueError(f"Duplicate compound ID {key!r} in {map_path}.")
        if relabel and label in labels_seen:
            raise ValueError(
                f"Duplicate label {label!r} assigned to both {labels_seen[label]!r} and {key!r}."
            )

        out[key] = label if relabel else key
        if relabel:
            labels_seen[label] = key

    if not out:
        raise ValueError(f"No compound mappings were found in {map_path}.")

    return out, relabel


def write_latex_map_csv(table: dict[str, str], csv_path: Path) -> None:
    csv_path.parent.mkdir(parents=True, exist_ok=True)
    with csv_path.open("w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["compound", "label"])
        writer.writerows(table.items())


def validate_tex_ids(relabel_dict: dict[str, str], root: Path = Path(".")) -> None:
    """Fail if a literal \\cmpd{ID} in project TeX files is absent from the map."""
    missing: list[str] = []
    for path in root.glob("*.tex"):
        for key in TEX_CMPD_PATTERN.findall(path.read_text()):
            if key not in relabel_dict:
                missing.append(f"{key} ({path})")
    if missing:
        raise ValueError("Unmapped compound IDs used in LaTeX: " + ", ".join(sorted(set(missing))))


def source_cdxml_files() -> list[Path]:
    if not INPUT_DIR.exists():
        raise FileNotFoundError(f"ChemDraw input directory {INPUT_DIR} does not exist.")

    files = sorted(path for path in INPUT_DIR.rglob(CDXML_FILE_PATTERN) if path.is_file())
    nested = [path for path in files if path.parent != INPUT_DIR]
    if nested:
        names = ", ".join(str(path) for path in nested)
        raise ValueError(
            "Nested CDXML directories are not supported by the ChemDraw export script. "
            f"Move these files directly into {INPUT_DIR}: {names}"
        )
    return files


def remove_stale_generated_cdxmls(source_files: list[Path]) -> int:
    """Remove generated CDXML files whose source file no longer exists."""
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    expected = {path.name for path in source_files}
    removed = 0
    for generated in OUTPUT_DIR.glob(CDXML_FILE_PATTERN):
        if generated.name not in expected:
            generated.unlink()
            removed += 1
    return removed


def prepare_dirs(source_files: list[Path], last_run_epoch: float, relabel_all: bool) -> list[Path]:
    """Copy changed source CDXML files into OUTPUT_DIR without editing originals."""
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    files_to_process: list[Path] = []

    for src in source_files:
        dst = OUTPUT_DIR / src.name
        if relabel_all or src.stat().st_mtime > last_run_epoch or not dst.exists():
            shutil.copy2(src, dst)
            files_to_process.append(dst)

    return files_to_process


def modify_cdxml(path: Path, relabel_dict: dict[str, str]) -> int:
    missing: set[str] = set()

    def replace(match: re.Match[str]) -> str:
        key = match.group(1)
        if key in relabel_dict:
            return relabel_dict[key]
        missing.add(key)
        return match.group(0)

    txt = path.read_text()
    txt, n = LABEL_PATTERN.subn(replace, txt)

    if missing:
        missing_text = ", ".join(sorted(missing))
        raise ValueError(f"Unmapped compound ID(s) in {path}: {missing_text}")

    path.write_text(txt)
    return n


def main() -> None:
    program_start = time.time()
    last_run_epoch = load_last_run_epoch(STATE_FILE)

    map_mtime = MAP_PATH.stat().st_mtime if MAP_PATH.exists() else 0.0
    relabel_all = map_mtime > last_run_epoch

    relabel_dict, _ = create_relabel_dict(MAP_PATH)
    validate_tex_ids(relabel_dict)
    source_files = source_cdxml_files()
    n_stale_removed = remove_stale_generated_cdxmls(source_files)
    write_latex_map_csv(relabel_dict, TEX_MAP_PATH)
    files_to_process = prepare_dirs(source_files, last_run_epoch, relabel_all)

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
        save_last_run_epoch(STATE_FILE, program_start)

    LOG.info(
        f"{n_files_modified} CDXML files processed, {n_relabels} tags relabelled, "
        f"{n_stale_removed} stale generated files removed in {time.time() - program_start:.3g} s"
    )


if __name__ == "__main__":
    main()
