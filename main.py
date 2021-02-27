from functools import partial
from typing import List
from pynput import keyboard
import time
import json
from config import PySimpleGUI as sg
from counter_renderer import CounterRenderer, get_counter
from threading import Event, Thread
from collections import defaultdict
from config import config


keyframes: List[List[tuple]] = [
    []
]  # the keyframes list of lists. The inner list will contain the float time offsets.
start = time.time()


def on_new_keyframe(window: sg.Window):
    """Handler for a new keyframe being added, used for the global keybind

    Args:
        window (sg.Window): The window instance to update
    """
    diff = time.time() - start
    keyframes[-1].append(diff)
    window["output"].update(
        "\n".join(map(str, keyframes[-1][-4:]))
    )  # update the window with the last 4 keyframes
    window["counter"].update(get_counter(len(keyframes[-1])))  # update the counter


def start_new_clip(window: sg.Window):
    """Start a new clip, called from the hotkey and UI event handler.

    Args:
        window (sg.Window): The window instance to update
    """
    global start
    window["output"].update("New clip started")
    start = (
        time.time()
    )  # reset the time to 0. technically not needed, since only relative times matter, but nicer to debug.
    if (
        len(keyframes[-1]) > 0
    ):  # check that there are keyframes in the latest clip, to prevent multiple empty lists
        keyframes.append([])
    window["counter"].update(get_counter(len(keyframes[-1])))  # update the counter
    window["start"].update(visible=False)  # toggle between start and stop buttons
    window["stop"].update(visible=True)  #   ^^^


class HoldKeyThread(Thread):
    """A Thread subclass that continously adds keyframes while holding"""

    def __init__(
        self, event: Event, handler: keyboard.GlobalHotKeys, key: keyboard.HotKey
    ):
        """Initialise the subclass

        Args:
            event (Event): The event used to loop and stop the thread
            handler (keyboard.GlobalHotKeys): The hotkey handler used to press the hotkeys
            key (keyboard.HotKey): The hotkey which was pressed.
        """
        Thread.__init__(self)
        self.stopped = event
        self.key = key
        self.handler = handler

    def run(self):
        while not self.stopped.wait(
            config["counter"]["hold-delay"]
        ):  # loop with a wait if the thread isnt stopped, loading delay from config
            # loop over the hotkeys, pressing them if needed (not sure why it needs to be this way)
            for hotkey in self.handler._hotkeys:
                hotkey.press(self.handler.canonical(self.key))
            for hotkey in self.handler._hotkeys:
                hotkey.release(self.handler.canonical(self.key))


class HoldableGlobalHotkey(keyboard.GlobalHotKeys):
    """Subclass of GlobalHotKeys allowing them to be held down."""

    def __init__(self, *args, **kwargs):
        """Initialise the HoldableGlobalHotkey class with any argument or keyword argument"""
        self.window = kwargs.pop("ui_window")  # get the window from the kwargs
        super().__init__(
            *args, **kwargs
        )  # init the parent class with all the arguments passed (except ui_window, we popped that beforehand)
        self.held_keys = defaultdict(list)
        self.all_keys = [
            key for keys in list(self._hotkeys) for key in keys._keys
        ]  # get a list of all hotkeys registered

    def _on_press(self, key: keyboard.HotKey):
        """Handle the on_press event, adding the HoldKeyThread functionality on top.

        Args:
            key (keyboard.HotKey): The pressed key
        """
        super()._on_press(key)  # Handle normally
        if key in self.all_keys:
            if (
                len(self.held_keys.get(key, [])) < config["counter"]["hold-multiplier"]
            ):  # Only do this if there are less than hold-multiplier HoldKeyThreads
                stopFlag = (
                    Event()
                )  # the event which allows us to stop the thread from the outside
                thread = HoldKeyThread(
                    stopFlag, self, key
                )  # actually create the thread
                thread.start()
                self.held_keys[key].append(
                    (stopFlag, thread)
                )  # store the thread so it can be stopped later

    def _on_release(self, key: keyboard.HotKey):
        """Handle the on_release event, stopping all HoldKeyThreads

        Args:
            key (keyboard.HotKey): The released hotkey
        """
        super()._on_release(key)
        for stopFlag, _ in self.held_keys[key]:  # loop over all threads for this hotkey
            stopFlag.set()  # and stop them
        del self.held_keys[key]  # then delete the dictionary item


class Manager:
    """The main class that manages the window and related events"""

    layout = [
        [
            sg.Text(size=(30, 4), key="output"),  # the output text box
            sg.Text(
                get_counter(len(keyframes[-1])),  # the counter text
                size=(4, 1),
                font=("Helvetica", 25),
                key="counter",
                pad=(0, 1),
            ),
        ],
        [
            sg.Input(default_text="clip", visible=False, key="save_loc")
        ],  # the save location input
        # TODO: input fields broken on remi/web version
        [
            sg.Column(  # using a columns to make sure the buttosn dont re-order
                [
                    [
                        sg.Button("Start", key="start"),
                        sg.Button("Stop", key="stop", visible=False),
                    ]
                ],
                pad=(0, 0),
                key="record_buttons",
            ),
            sg.Column(
                [
                    [
                        sg.Button("Save", key="save"),
                    ]
                ],
                pad=(0, 0),
            ),
            sg.Column(
                [
                    [
                        sg.Button("Generate Video", key="init_generate"),
                        sg.Button("Generate", key="generate", visible=False),
                    ]
                ],
                pad=(0, 0),
            ),
            sg.Button("Exit", key="exit"),
        ],
    ]

    def __init__(self):
        """Initialise the Manager class, creating the window and setting up the hotkey handler"""
        self.unsafed_warned, self.stopped = False, False
        self.window = sg.Window(
            "Counter", self.layout
        )  # create the window with the layout
        self.setup_hotkeyhandler()  # setup the hotkey handler

    def setup_hotkeyhandler(self):
        """Set up the HoldableGlobalHotkey with the keybinds from the config"""
        self.gh = HoldableGlobalHotkey(  # create a new instane of the hotkey handler
            {
                config["keybinds"]["count"]: partial(
                    on_new_keyframe, self.window
                ),  # with the keybinds from the config
                config["keybinds"]["new-clip"].replace(
                    " ", ""
                ): partial(  # using partial to pass in the window instance
                    start_new_clip, self.window
                ),
            },
            ui_window=self.window,
        )

    def check_save(self, values: dict) -> bool:
        """Check whether the save input contains a changed name, making it visible if it wasn't

        Args:
            values (dict): The window event values

        Returns:
            bool: Whether the save_loc is a valid value
        """
        if (
            not self.window["save_loc"].visible or values["save_loc"] == "clip"
        ):  # save_loc cant be "clip" as that is the default
            self.window["output"].update("Please Enter a file name!")
            self.window["save_loc"].update(visible=True)
            self.window["record_buttons"].update(visible=False)
            return False
        return True

    def handle_exit(self, values: dict):
        """Handle the window exit event

        Args:
            values (dict): The window event values
        """
        if self.unsafed_warned:
            self.stopped = True
        else:
            self.window["output"].update(
                "Any unsafed progress will be lost. Press Exit again to exit"
            )
            self.unsafed_warned = True

    def handle_start(self, values: dict):
        """Handle the start button event

        Args:
            values (dict): The window event values
        """
        self.gh.start()
        start_new_clip(self.window)

    def handle_stop(self, values: dict):
        """Handle the stop button event

        Args:
            values (dict): The window event values
        """
        self.gh.stop()
        self.setup_hotkeyhandler()
        self.window["start"].update(visible=True)
        self.window["stop"].update(visible=False)

    def handle_save(self, values: dict):
        """Handle the save button event

        Args:
            values (dict): The window event values
        """
        if self.check_save(values):  # check whether the save filename is valid
            filename = f"{values['save_loc']}.json"  # make the actual json filename
            with open(filename, "w") as f:
                json.dump(keyframes, f)  # save the keyframes
                self.window["output"].update(f"Clip saved as {filename}")
            self.unsafed_warned = True  # no need to warn the user anymore
            self.stopped = True  # we can now exit

    def handle_init_generate(self, values: dict):
        """Handle the first press on the generate button, asking for either a file name or just to continue

        Args:
            values (dict): The window event values
        """
        self.window["output"].update(
            "If you want to generate from a file "
            "enter the filename and then press generate. "
            "if you dont enter a filename "
            "the current recording will be used"
        )
        values["save_loc"] = ""
        self.window["save"].update(visible=False)
        self.window["init_generate"].update(visible=False)
        self.window["generate"].update(visible=True)
        self.window["save_loc"].update(visible=True)

    def handle_generate(self, values: dict):
        """Handle the second generate button press, actually genreating the video

        Args:
            values (dict): The window event values
        """
        if values["save_loc"] in (
            "",
            "clip",
        ):  # if the input filename is empty or unchanged
            self.window["save_loc"].update(visible=False)
            cr = CounterRenderer(keyframes)  # generate from the current keyframes
        else:
            self.window["save_loc"].update(visible=False)
            cr = CounterRenderer.from_file(
                f"{values['save_loc']}.json"
            )  # else load the json
        self.window["output"].update("Starting render, please be patient")
        if len(keyframes) > 0:
            cr.render_individual_clips()  # actually render the video
            self.window["output"].update("Render done!")
        else:
            self.window["output"].update(
                "There are no keyframes to render!"
            )  # if there are no keyframes, tell the user
            self.window["save_loc"].update(visible=False)
            self.window["init_generate"].update(visible=True)
            self.window["generate"].update(visible=False)
            self.window["save"].update(visible=True)

    def uncaught_events(self, event: str, values: dict):
        """Handle all other events.

        Args:
            event (str): The event name
            values (dict): The window event values
        """
        print(f"{event} unhandled")

    def run_loop(self):
        """Run the main loop, calling the event handlers for their events."""
        method_list = {
            methodname: getattr(self, methodname)
            for methodname in dir(self)
            if callable(getattr(self, methodname)) and not methodname.startswith("__")
        }  # generate a dict of all method names mapped to the method itself, ignoring dunder
        while True:  # The Event Loop
            event, values = self.window.read()  # read events from the window
            if event == sg.WIN_CLOSED:
                self.handle_exit(
                    values
                )  # handle the exit if the window was closed by x button
            event_callable = method_list.get(
                f"handle_{event}", partial(self.uncaught_events, event)
            )  # get the event handler method corresponding to the curren event, or the uncaught_events method
            event_callable(values)  # call the event handler
            if self.stopped:
                return  # stop the loop if the stopped flag is set


m = Manager()
m.run_loop()