import asyncio
import json
import logging
from pathlib import Path
from typing import List, Optional, Tuple

from app.providers.base import GenerationError

logger = logging.getLogger(__name__)

ASPECT_DIMENSIONS: dict[str, Tuple[int, int]] = {
    "16:9": (1280, 720),
    "9:16": (720, 1280),
    "1:1": (720, 720),
}


def get_dimensions(aspect_ratio: str) -> Tuple[int, int]:
    return ASPECT_DIMENSIONS.get(aspect_ratio, (1280, 720))


class FFmpegService:
    """Assembles scene images and optional audio into a web-ready MP4 using FFmpeg."""

    async def _run_command(self, cmd: List[str], label: str) -> str:
        logger.debug("Running %s: %s", label, " ".join(cmd))
        proc = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        stdout, stderr = await proc.communicate()
        if proc.returncode != 0:
            err_text = stderr.decode("utf-8", errors="replace")[-800:]
            logger.error("%s failed (code %s): %s", label, proc.returncode, err_text)
            raise GenerationError(f"Media encoding failed during {label}.")
        return stdout.decode("utf-8", errors="replace")

    async def build_demo_video(
        self,
        image_paths: List[Path],
        output_path: Path,
        aspect_ratio: str,
        duration_seconds: int,
        audio_path: Optional[Path] = None,
    ) -> Path:
        if not image_paths:
            raise GenerationError("No scene images were provided to FFmpeg.")

        width, height = get_dimensions(aspect_ratio)
        fps = 24
        num_scenes = len(image_paths)
        fade_duration = 0.5 if num_scenes > 1 else 0.0

        # Calculate per-clip duration so total xfade output equals duration_seconds
        clip_duration = (duration_seconds + fade_duration * (num_scenes - 1)) / num_scenes
        frames_per_clip = max(int(round(clip_duration * fps)), fps)

        cmd: List[str] = ["ffmpeg", "-y"]
        for img in image_paths:
            cmd.extend(["-loop", "1", "-t", f"{clip_duration:.3f}", "-i", str(img)])

        # Only include an audio stream when a real, non-empty audio file exists.
        # Mapping a generated silent track can be misinterpreted as static/noise by
        # some mobile players; a video-only MP4 is safer when narration is disabled.
        has_audio = (
            audio_path is not None
            and audio_path.is_file()
            and audio_path.stat().st_size > 0
        )
        if has_audio and audio_path is not None:
            cmd.extend(["-i", str(audio_path)])

        filter_parts: List[str] = []
        for idx in range(num_scenes):
            # Subtle Ken Burns zoom-in / zoom-out alternating per scene
            if idx % 2 == 0:
                zoom_expr = "min(zoom+0.0008,1.12)"
            else:
                zoom_expr = "if(lte(zoom,1.0),1.12,max(1.0,zoom-0.0008))"

            filter_parts.append(
                f"[{idx}:v]scale={int(width * 1.15)}:{int(height * 1.15)}:force_original_aspect_ratio=increase,"
                f"crop={int(width * 1.15)}:{int(height * 1.15)},"
                f"zoompan=z='{zoom_expr}':x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':"
                f"d={frames_per_clip}:s={width}x{height}:fps={fps},"
                f"setsar=1,format=yuv420p[v{idx}]"
            )

        if num_scenes == 1:
            final_video_label = "[v0]"
        else:
            current_label = "[v0]"
            offset = clip_duration - fade_duration
            for idx in range(1, num_scenes):
                out_label = f"[xf{idx}]" if idx < num_scenes - 1 else "[vout]"
                filter_parts.append(
                    f"{current_label}[v{idx}]xfade=transition=fade:duration={fade_duration:.2f}:offset={offset:.3f}{out_label}"
                )
                current_label = out_label
                offset += clip_duration - fade_duration
            final_video_label = "[vout]"

        cmd.extend(
            [
                "-filter_complex",
                ";".join(filter_parts),
                "-map",
                final_video_label,
            ]
        )

        if has_audio:
            audio_input_idx = num_scenes
            cmd.extend(["-map", f"{audio_input_idx}:a", "-c:a", "aac", "-b:a", "128k"])
        else:
            # Explicitly produce a video-only MP4; do not synthesize a fake audio track.
            cmd.append("-an")

        cmd.extend(
            [
                "-t",
                str(duration_seconds),
                "-c:v",
                "libx264",
                "-preset",
                "veryfast",
                "-crf",
                "23",
                "-pix_fmt",
                "yuv420p",
                "-movflags",
                "+faststart",
                str(output_path),
            ]
        )

        await self._run_command(cmd, "video assembly")

        if not output_path.exists() or output_path.stat().st_size == 0:
            raise GenerationError("FFmpeg finished without producing a valid MP4 file.")

        return output_path

    async def probe_video(self, video_path: Path) -> dict:
        cmd = [
            "ffprobe",
            "-v",
            "error",
            "-show_format",
            "-show_streams",
            "-print_format",
            "json",
            str(video_path),
        ]
        raw = await self._run_command(cmd, "ffprobe validation")
        try:
            return json.loads(raw)
        except json.JSONDecodeError as exc:
            raise GenerationError("Could not parse ffprobe output.") from exc
