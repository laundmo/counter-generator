from typing import List, TypeVar, Union
import numpy as np
import cv2
import json
from config import config
from PIL import ImageFont, ImageDraw, Image
from dataclasses import dataclass


def get_counter(n: int) -> str:
    """Get the counter string from the keyframe number

    Args:
        n (int): The keyframe index

    Returns:
        str: the formatted counter string
    """
    return config["output"]["prepend"] + str(
        round((n / 10) + config["output"]["start_at"], 1)
    )


@dataclass
class RenderConfig:
    """Dataclass for storing the render config"""

    font: str
    name_template: str
    width: int
    height: int
    fps: int
    fontsize: int
    prepend: str
    extend: int
    start_at: int


CounterRenderer_T = TypeVar("CounterRenderer_T", bound="CounterRenderer")


class CounterRenderer:
    """Class that renders the counter"""

    def __init__(self, keyframes: List[List[tuple]], **kwargs):
        """Create a CounterRenderer instance

        Args:
            keyframes (List[List[tuple]]): The keyframes to render
        """
        self.keyframes = keyframes
        self.c = RenderConfig(
            **{**config["output"], **kwargs}
        )  # create the RenderConfig based on the config values which are overwritten by kwargs to this class
        self.font = ImageFont.truetype(self.c.font, self.c.fontsize)  # load the font

    @classmethod
    def from_file(cls, file: str, **kwargs) -> CounterRenderer_T:
        """Create a CounterRenderer from file

        Args:
            file (str): The json file to load keyframes from

        Returns:
            CounterRenderer_T: The CounterRenderer instance
        """
        with open(file) as f:
            keyframes = json.load(f)
        return cls(keyframes, **kwargs)

    def write_on_frame(self, frame: np.ndarray, text: str) -> np.ndarray:
        """Write the text on frame

        Args:
            frame (np.ndarray): The OpenCV2 frame to write on
            text (str): The text to write on the frame.

        Returns:
            np.ndarray: The frame which has been written on
        """
        img_pil = Image.fromarray(frame)  # get a PIL(low) image from the array
        draw = ImageDraw.Draw(img_pil)  # Get a drawing object
        draw.text(
            (0, 0), text, font=self.font, fill=(255, 255, 255, 0)
        )  # Draw the text
        return np.array(img_pil)

    def render_clip(
        self, keyframes: List[tuple], i: int
    ):  # TODO: Split render_clip into multiple methods - too long
        """Render a single clip

        Args:
            keyframes (List[tuple]): The keyframes to render
            i (int): The index of the clip (for saving the file)
        """
        seconds = max(keyframes) - min(keyframes)
        frames = np.linspace(
            0, seconds, num=round(self.c.fps * seconds)
        )  # create a numpy array with all the frame times needed

        fourcc = cv2.VideoWriter_fourcc(
            *"MP42"
        )  # dont ask me why a MP42 fourcc is needed
        video = cv2.VideoWriter(  # create a video writer
            f"./{self.c.name_template.format(i)}.avi",  # with the correct filename
            fourcc,
            float(self.c.fps),
            (self.c.width, self.c.height),
        )

        keyframe_index = 0
        for index, _ in enumerate(
            frames
        ):  # loop over all the frames, no need to get the actual value since we only need the next frame
            frame = np.zeros(
                (self.c.height, self.c.width, 3), dtype=np.uint8
            )  # create a frame with zeroes - black frame
            try:
                diff_next = (keyframes[keyframe_index] - min(keyframes)) - frames[
                    index + 1
                ]  # calculate the difference between the relative keyframe time since start and the next frame time since start
                if diff_next < 0:  # if thats smaller than 0 we have passed the keyframe
                    keyframe_index += 1  # which means we have counted to the next
            except IndexError:
                pass
            frame = self.write_on_frame(
                frame, get_counter(keyframe_index)
            )  # write the counter on the frame
            video.write(frame)  # and write the frame on the video

        for _ in range(
            self.c.fps * self.c.extend
        ):  # add fps * extend number of frames at the end
            frame = np.zeros(
                (self.c.height, self.c.width, 3), dtype=np.uint8
            )  # all filled with zeroes
            frame = self.write_on_frame(
                frame, get_counter(keyframe_index)
            )  # and the end count
            video.write(frame)

        video.release()  # make sure we save and close the video file handle

    def render_individual_clips(self):
        """Render the individual clips recorded to videos"""
        for i, frames in enumerate(self.keyframes):
            if len(frames) > 0:
                self.render_clip(frames, i)


if __name__ == "__main__":  # test setup, for running this file directly
    r = CounterRenderer([list(range(15))])
    r.render_individual_clips()
