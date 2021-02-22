import numpy as np
import cv2
import json
import math

from PIL import ImageFont, ImageDraw, Image


class CounterRenderer:
    def __init__(self, keyframes, font="./font.ttf", video_name="text{}", width=500, height=200, fps=60, fontsize=200, prepend="+", extend=2):

        self.width = width
        self.height = height
        self.FPS = fps
        self.prepend = prepend
        self.extend = extend

        self.font = ImageFont.truetype(font, fontsize)
        self.keyframe_blocks = keyframes

        self.video_name = video_name

    @classmethod
    def from_file(cls, file, **kwargs):
        with open(file) as f:
            keyframes = json.load(f)
        return cls(keyframes, **kwargs)

    def write_on_frame(self, frame, text):
        text = self.prepend + text
        img_pil = Image.fromarray(frame)
        draw = ImageDraw.Draw(img_pil)
        draw.text((0, 0), text, font=self.font, fill=(255, 255, 255, 0))
        return np.array(img_pil)

    def render_clip(self, keyframes, i):
        seconds = math.ceil(min(keyframes) + max(keyframes))
        frames = np.linspace(0, seconds + self.extend, num=self.FPS * seconds)

        fourcc = cv2.VideoWriter_fourcc(*"MP42")
        video = cv2.VideoWriter(
            f"./{self.video_name.format(i)}.avi",
            fourcc,
            float(self.FPS),
            (self.width, self.height),
        )

        last = 0
        for index, _ in enumerate(frames):
            frame = np.zeros((self.height, self.width, 3), dtype=np.uint8)
            try:
                diff_next = keyframes[last] - frames[index + 1]
                if diff_next < 0:
                    last += 1
            except IndexError:
                pass
            frame = self.write_on_frame(frame, str(last / 10))
            video.write(frame)
        video.release()

    def render_individual_clips(self):
        for i, frames in enumerate(self.keyframe_blocks):
            if len(frames) > 0:
                self.render_clip(frames, i)