import argparse
import os
from typing import Optional, Sequence
import ffmpeg
import pvleopard
import tempfile
import sys


mp3path = os.path.join(tempfile.mkdtemp(), "audio.mp3")
print(mp3path, file=sys.stderr)


def second_to_timecode(x: float) -> str:
    hour, x = divmod(x, 3600)
    minute, x = divmod(x, 60)
    second, x = divmod(x, 1)
    millisecond = int(x * 1000.0)

    return "%.2d:%.2d:%.2d,%.3d" % (hour, minute, second, millisecond)


section_extra_secs = 0.5


def to_srt(
    words: Sequence[pvleopard.Leopard.Word],
    endpoint_sec: float = 1.0,
    length_limit: Optional[int] = 16,
) -> str:
    lines: list[str] = list()

    def _add_section(start: int, end: int) -> None:
        """start is inclusive while end is exclusive."""
        start_sec = words[start].start_sec
        end_sec = words[end - 1].end_sec + section_extra_secs
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
    for k in range(1, len(words)):
        if ((words[k].start_sec - words[k - 1].end_sec) >= endpoint_sec) or (
            length_limit is not None and (k - start) >= length_limit
        ):
            _add_section(start, k)
            start = k
            section += 1
    _add_section(start, len(words))

    return "\n".join(lines)


with open(".access_key") as f:
    picovoice_key = f.read()

parser = argparse.ArgumentParser()
parser.add_argument("path")
parser.add_argument("--output", "-o")
args = parser.parse_args()

input_path = args.path


stream = ffmpeg.input(input_path).output(mp3path, format="mp3")
ffmpeg.run(stream)


leopard = pvleopard.create(access_key=picovoice_key)
transcript, words = leopard.process_file(mp3path)
srt = to_srt(words, 0.5)

if args.output is None:
    print(srt, file=sys.stdout)
else:
    with open(args.output, mode="w") as f:
        print(srt, file=f)
