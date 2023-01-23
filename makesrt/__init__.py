import argparse
import os
from typing import Optional, Sequence
import ffmpeg
import pvleopard
import tempfile
import sys


def second_to_timecode(x: float) -> str:
    hour, x = divmod(x, 3600)
    minute, x = divmod(x, 60)
    second, x = divmod(x, 1)
    millisecond = int(x * 1000.0)

    return "%.2d:%.2d:%.2d,%.3d" % (hour, minute, second, millisecond)


SECTION_END_EXTRA_SECS = 0.5


def to_srt(
    words: Sequence[pvleopard.Leopard.Word],
    endpoint_sec: float = 1.0,
    length_limit: Optional[int] = 16,
) -> str:
    lines: list[str] = list()

    def _add_section(section: int, start: int, end: int) -> None:
        """start is inclusive while end is exclusive."""
        start_sec = words[start].start_sec
        end_sec = words[end - 1].end_sec + SECTION_END_EXTRA_SECS
        if end < len(words):
            end_sec = min(end_sec, words[end].start_sec)
        lines.append(f"{section}")
        lines.append(
            f"{second_to_timecode(start_sec)} --> {second_to_timecode(end_sec)}"
        )
        lines.append(" ".join(x.word for x in words[start:end]))
        lines.append("")

    section = 0
    start = 0
    for end in range(1, len(words)):
        if ((words[end].start_sec - words[end - 1].end_sec) >= endpoint_sec) or (
            length_limit is not None and (end - start) >= length_limit
        ):
            _add_section(section, start, end)
            start = end
            section += 1
    _add_section(section, start, len(words))

    return "\n".join(lines)


ACCESS_KEY_FILE = ".picovoice_access_key"


def find_access_key() -> str:
    def read_file(path: str) -> Optional[str]:
        if os.path.exists(path):
            with open(path) as f:
                return f.read()
        else:
            return None

    key = (
        os.getenv("PICOVOICE_ACCESS_KEY")
        or read_file(os.path.expanduser(f"~/{ACCESS_KEY_FILE}"))
        or read_file(f"./{ACCESS_KEY_FILE}")
    )
    if key is None:
        raise ValueError("Couldn't find access key to picovoice")
    return key


def main() -> None:
    picovoice_key = find_access_key()

    parser = argparse.ArgumentParser()
    parser.add_argument("path")
    parser.add_argument("--output", "-o", help="output path")
    args = parser.parse_args()

    input_path = args.path
    mp3path = os.path.join(tempfile.mkdtemp(), "audio.mp3")
    # HACK: write audio as an mp3 file to reduce size.
    # (But can't pvleopard deal with mp3 data via stream?)
    stream = ffmpeg.input(input_path).output(mp3path, format="mp3")
    ffmpeg.run(stream)

    leopard = pvleopard.create(access_key=picovoice_key)
    _, words = leopard.process_file(mp3path)
    srt = to_srt(words, 0.5)

    if args.output is None:
        print(srt, file=sys.stdout)
    else:
        with open(args.output, mode="w") as f:
            print(srt, file=f)


if __name__ == "__main__":
    main()
