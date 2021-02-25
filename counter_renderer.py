import numpy as np
import cv2
import json
from config import config
from PIL import ImageFont, ImageDraw, Image
from dataclasses import dataclass


def get_counter(n):
    return str((n / 10) + config["output"]["start_at"])


@dataclass
class RenderConfig:
    font: str
    name_template: str 
    width: int
    height: int
    fps: int
    fontsize: int
    prepend: str
    extend: int
    start_at: int


class CounterRenderer:
    def __init__(self, keyframes, **kwargs):
        self.keyframes = keyframes
        self.c = RenderConfig(**{**config["output"], **kwargs})
        self.font = ImageFont.truetype(self.c.font, self.c.fontsize)

    @classmethod
    def from_file(cls, file, **kwargs):
        with open(file) as f:
            keyframes = json.load(f)
        return cls(keyframes, **kwargs)

    def write_on_frame(self, frame, text):
        text = self.c.prepend + text
        img_pil = Image.fromarray(frame)
        draw = ImageDraw.Draw(img_pil)
        draw.text((0, 0), text, font=self.font, fill=(255, 255, 255, 0))
        return np.array(img_pil)

    def render_clip(self, keyframes, i):
        seconds = max(keyframes) - min(keyframes)
        frames = np.linspace(0, seconds, num=round(self.c.fps * seconds))

        fourcc = cv2.VideoWriter_fourcc(*"MP42")
        video = cv2.VideoWriter(
            f"./{self.c.name_template.format(i)}.avi",
            fourcc,
            float(self.c.fps),
            (self.c.width, self.c.height),
        )

        last = 0
        for index, _ in enumerate(frames):
            frame = np.zeros((self.c.height, self.c.width, 3), dtype=np.uint8)
            try:
                diff_next = (keyframes[last] - min(keyframes)) - frames[index + 1]
                if diff_next < 0:
                    last += 1
            except IndexError:
                pass
            frame = self.write_on_frame(frame, get_counter(last))
            video.write(frame)

        for _ in range(self.c.fps * self.c.extend):
            frame = np.zeros((self.c.height, self.c.width, 3), dtype=np.uint8)
            frame = self.write_on_frame(frame, get_counter(last))
            video.write(frame)

        video.release()

    def render_individual_clips(self):
        for i, frames in enumerate(self.keyframes):
            if len(frames) > 0:
                self.render_clip(frames, i)


if __name__ == "__main__":
    r = CounterRenderer([list(range(15))])
    r.render_individual_clips()
