import hashlib
import logging
import math
import textwrap
from pathlib import Path
from typing import List, Tuple

from PIL import Image, ImageDraw, ImageFont

from app.media.ffmpeg_service import FFmpegService, get_dimensions
from app.providers.base import GenerationContext, TTSProvider, VideoProvider

logger = logging.getLogger(__name__)

STYLE_PALETTES: dict[str, Tuple[Tuple[int, int, int], Tuple[int, int, int], Tuple[int, int, int]]] = {
    "Cinematic": ((14, 18, 38), (58, 32, 86), (245, 166, 91)),
    "Anime": ((22, 16, 48), (112, 42, 128), (105, 225, 255)),
    "Realistic": ((16, 28, 34), (44, 78, 86), (226, 210, 178)),
    "3D Animation": ((20, 22, 54), (70, 56, 148), (255, 126, 182)),
    "Fantasy": ((18, 12, 42), (82, 34, 114), (168, 255, 198)),
    "Documentary": ((18, 22, 28), (48, 58, 70), (235, 195, 115)),
}


def _load_font(size: int, bold: bool = False) -> ImageFont.ImageFont:
    candidates = (
        [
            "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
            "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf",
        ]
        if bold
        else [
            "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
            "/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf",
        ]
    )
    for path in candidates:
        if Path(path).exists():
            try:
                return ImageFont.truetype(path, size=size)
            except OSError:
                continue
    return ImageFont.load_default()


def _lerp_color(c1: Tuple[int, int, int], c2: Tuple[int, int, int], t: float) -> Tuple[int, int, int]:
    return (
        int(c1[0] + (c2[0] - c1[0]) * t),
        int(c1[1] + (c2[1] - c1[1]) * t),
        int(c1[2] + (c2[2] - c1[2]) * t),
    )


class DemoVideoProvider(VideoProvider):
    """Free-first deterministic demo renderer.

    Produces a clearly labeled DEMO MODE MP4 using Pillow artwork,
    FFmpeg motion/crossfades, and optional Edge TTS narration.
    """

    def __init__(self, tts_provider: TTSProvider, ffmpeg_service: FFmpegService | None = None) -> None:
        self.tts_provider = tts_provider
        self.ffmpeg = ffmpeg_service or FFmpegService()

    def _render_scene_frame(
        self,
        output_path: Path,
        width: int,
        height: int,
        prompt: str,
        style: str,
        aspect_ratio: str,
        duration_seconds: int,
        scene_index: int,
        total_scenes: int,
        seed_int: int,
    ) -> Path:
        top_col, mid_col, accent_col = STYLE_PALETTES.get(style, STYLE_PALETTES["Cinematic"])
        img = Image.new("RGB", (width, height))
        draw = ImageDraw.Draw(img)

        # Vertical atmospheric gradient
        for y in range(height):
            t = y / max(height - 1, 1)
            if t < 0.65:
                col = _lerp_color(top_col, mid_col, t / 0.65)
            else:
                col = _lerp_color(mid_col, (10, 12, 20), (t - 0.65) / 0.35)
            draw.line([(0, y), (width, y)], fill=col)

        # Deterministic glowing orb / celestial horizon
        orb_cx = int(width * (0.25 + 0.25 * scene_index)) % width
        orb_cy = int(height * (0.34 + 0.05 * ((seed_int + scene_index) % 3)))
        orb_r = int(min(width, height) * 0.16)
        for r in range(orb_r, 0, -4):
            alpha_t = 1 - (r / orb_r)
            ring_col = _lerp_color(mid_col, accent_col, alpha_t * 0.85)
            draw.ellipse(
                [orb_cx - r, orb_cy - r, orb_cx + r, orb_cy + r],
                fill=ring_col,
            )

        # Deterministic stars / particles
        for i in range(36):
            px = ((seed_int * (i + 7) * 97) + scene_index * 53) % width
            py = ((seed_int * (i + 13) * 61) + scene_index * 37) % int(height * 0.65)
            size = 2 if i % 4 == 0 else 1
            draw.ellipse([px - size, py - size, px + size, py + size], fill=(235, 240, 255))

        # Stylized silhouette horizon hills
        horizon_y = int(height * 0.72)
        hill_points = [(0, height)]
        for x in range(0, width + 20, 20):
            wave = math.sin((x / width) * math.pi * 2.2 + scene_index * 0.9 + (seed_int % 5))
            y = horizon_y + int(wave * height * 0.045)
            hill_points.append((x, y))
        hill_points.append((width, height))
        draw.polygon(hill_points, fill=(11, 14, 24))

        # Fonts scaled to frame size
        base_unit = min(width, height)
        badge_font = _load_font(max(16, int(base_unit * 0.026)), bold=True)
        title_font = _load_font(max(24, int(base_unit * 0.046)), bold=True)
        body_font = _load_font(max(18, int(base_unit * 0.032)), bold=False)
        meta_font = _load_font(max(15, int(base_unit * 0.022)), bold=False)

        pad = int(base_unit * 0.06)

        # Top-left DEMO MODE badge
        badge_text = "DEMO MODE  |  FRAMEFORGE STUDIO"
        badge_box = draw.textbbox((0, 0), badge_text, font=badge_font)
        bw = badge_box[2] - badge_box[0] + 24
        bh = badge_box[3] - badge_box[1] + 14
        draw.rounded_rectangle(
            [pad, pad, pad + bw, pad + bh],
            radius=10,
            fill=(24, 28, 48),
            outline=accent_col,
            width=2,
        )
        draw.text((pad + 12, pad + 6), badge_text, font=badge_font, fill=accent_col)

        # Center / lower card text
        if scene_index == 0:
            heading = f"{style.upper()}  •  TITLE CARD"
            sub_lines = textwrap.wrap(prompt, width=38 if width >= height else 24)[:4]
        elif scene_index == total_scenes - 1:
            heading = f"SCENE {scene_index + 1} OF {total_scenes}  •  FINALE"
            sub_lines = [
                "Rendered locally with Pillow + FFmpeg",
                f"Format: {aspect_ratio}  •  Duration: {duration_seconds}s",
            ]
        else:
            heading = f"SCENE {scene_index + 1} OF {total_scenes}  •  {style.upper()}"
            sub_lines = textwrap.wrap(prompt, width=40 if width >= height else 26)[:3]

        text_y = int(height * 0.42) if scene_index == 0 else int(height * 0.48)
        draw.text((pad, text_y), heading, font=title_font, fill=(255, 255, 255))

        line_y = text_y + int(base_unit * 0.075)
        for line in sub_lines:
            draw.text((pad, line_y), line, font=body_font, fill=(215, 222, 240))
            line_y += int(base_unit * 0.048)

        # Bottom-left metadata footer
        footer = f"Preset: {style}  |  Ratio: {aspect_ratio}  |  Demo Preview (No Paid AI Credits Used)"
        draw.text((pad, height - pad - 20), footer, font=meta_font, fill=(160, 172, 196))

        img.save(output_path, format="PNG")
        return output_path

    async def generate_video(self, ctx: GenerationContext) -> Path:
        ctx.work_dir.mkdir(parents=True, exist_ok=True)
        width, height = get_dimensions(ctx.aspect_ratio)
        seed_int = int(hashlib.sha256(ctx.prompt.encode("utf-8")).hexdigest()[:8], 16)

        num_scenes = 3 if ctx.duration_seconds <= 12 else 4
        ctx.report_progress(20, "Rendering demo storyboard scenes")

        image_paths: List[Path] = []
        for idx in range(num_scenes):
            frame_path = ctx.work_dir / f"scene_{idx}.png"
            self._render_scene_frame(
                output_path=frame_path,
                width=width,
                height=height,
                prompt=ctx.prompt,
                style=ctx.style,
                aspect_ratio=ctx.aspect_ratio,
                duration_seconds=ctx.duration_seconds,
                scene_index=idx,
                total_scenes=num_scenes,
                seed_int=seed_int,
            )
            image_paths.append(frame_path)

        ctx.report_progress(45, "Preparing audio narration")
        audio_path: Path | None = None
        narration_file = ctx.work_dir / "narration.mp3"
        narration_text = f"FrameForge demo preview. {ctx.prompt}"
        audio_path = await self.tts_provider.synthesize_narration(narration_text, narration_file)

        ctx.report_progress(65, "Encoding MP4 video with FFmpeg")
        output_mp4 = ctx.work_dir / f"{ctx.job_id}.mp4"
        await self.ffmpeg.build_demo_video(
            image_paths=image_paths,
            output_path=output_mp4,
            aspect_ratio=ctx.aspect_ratio,
            duration_seconds=ctx.duration_seconds,
            audio_path=audio_path,
        )

        ctx.report_progress(90, "Verifying generated MP4")
        await self.ffmpeg.probe_video(output_mp4)
        return output_mp4
