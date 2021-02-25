from functools import partial
from pynput import keyboard
import time
import json
from config import PySimpleGUI as sg
from counter_renderer import CounterRenderer, get_counter
from threading import Event, Thread
from collections import defaultdict
from config import config


keyframes = [[]]
start = time.time()


def on_new_keyframe(window):
    diff = time.time() - start
    keyframes[-1].append(diff)
    window["output"].update("\n".join(map(str, keyframes[-1][-4:])))
    window["counter"].update(get_counter(len(keyframes[-1])))


def start_new_clip(window):
    global start
    window["output"].update("New clip started")
    start = time.time()
    if len(keyframes[-1]) > 0:
        keyframes.append([])
    window["counter"].update(get_counter(len(keyframes[-1])))
    window["start"].update(visible=False)
    window["stop"].update(visible=True)


class HoldKeyThread(Thread):
    def __init__(self, event, handler, key, window):
        Thread.__init__(self)
        self.stopped = event
        self.window = window
        self.key = key
        self.handler = handler

    def run(self):
        while not self.stopped.wait(config["counter"]["hold-delay"]):
            # on_new_keyframe(self.window)
            for hotkey in self.handler._hotkeys:
                hotkey.press(self.handler.canonical(self.key))
            for hotkey in self.handler._hotkeys:
                hotkey.release(self.handler.canonical(self.key))


class HoldableGlobalHotkey(keyboard.GlobalHotKeys):
    def __init__(self, *args, **kwargs):
        self.window = kwargs.pop("ui_window")
        super().__init__(*args, **kwargs)
        self.held_keys = defaultdict(list)
        self.all_keys = [key for keys in list(self._hotkeys) for key in keys._keys]

    def _on_press(self, key):
        super()._on_press(key)
        if key in self.all_keys:
            if len(self.held_keys.get(key, [])) < config["counter"]["hold-multiplier"]:
                stopFlag = Event()
                thread = HoldKeyThread(stopFlag, self, key, self.window)
                thread.start()
                self.held_keys[key].append((stopFlag, thread))

    def _on_release(self, key):
        super()._on_release(key)
        for stopFlag, _ in self.held_keys[key]:
            stopFlag.set()
        del self.held_keys[key]


class Manager:
    layout = [
        [
            sg.Text(size=(30, 4), key="output"),
            sg.Text(
                get_counter(len(keyframes[-1])),
                size=(4, 1),
                font=("Helvetica", 25),
                key="counter",
                pad=(0, 1),
            ),
        ],
        [sg.Input(default_text="clip", visible=False, key="save_loc")],
        [
            sg.Column(
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
        self.unsafed_warned = False
        self.stopped = False
        self.window = sg.Window("Counter", self.layout)
        self.setup_hotkeyhandler()

    def setup_hotkeyhandler(self):
        self.gh = HoldableGlobalHotkey(
            {
                config["keybinds"]["count"]: partial(on_new_keyframe, self.window),
                config["keybinds"]["new-clip"].replace(" ", ""): partial(
                    start_new_clip, self.window
                ),
            },
            ui_window=self.window,
        )

    def check_close(self, values):
        if not self.window["save_loc"].visible or values["save_loc"] == "clip":
            self.window["output"].update("Please Enter a file name!")
            self.window["save_loc"].update(visible=True)
            self.window["record_buttons"].update(visible=False)
            return False
        return True

    def handle_exit(self, values):
        if self.unsafed_warned:
            self.stopped = True
        else:
            self.window["output"].update(
                "Any unsafed progress will be lost. Press Exit again to exit"
            )
            self.unsafed_warned = True

    def handle_start(self, values):
        self.gh.start()
        start_new_clip(self.window)

    def handle_stop(self, values):
        self.gh.stop()
        self.setup_hotkeyhandler()
        self.window["start"].update(visible=True)
        self.window["stop"].update(visible=False)

    def handle_save(self, values):
        if self.check_close(values):
            filename = f"{values['save_loc']}.json"
            with open(filename, "w") as f:
                json.dump(keyframes, f)
                self.window["output"].update(f"Clip saved as {filename}")
            self.unsafed_warned = True
            self.stopped = True

    def handle_init_generate(self, values):
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

    def handle_generate(self, values):
        if values["save_loc"] in ("", "clip"):
            self.window["save_loc"].update(visible=False)
            cr = CounterRenderer(keyframes)
        else:
            self.window["save_loc"].update(visible=False)
            cr = CounterRenderer.from_file(f"{values['save_loc']}.json")
        self.window["output"].update("Starting render, please be patient")
        if len(keyframes) > 0:
            cr.render_individual_clips()
            self.window["output"].update("Render done!")
        else:
            self.window["output"].update("There are no keyframes to render!")
            self.window["save_loc"].update(visible=False)
            self.window["init_generate"].update(visible=True)
            self.window["generate"].update(visible=False)
            self.window["save"].update(visible=True)

    def uncaught_events(self, event, values):
        print(f"{event} unhandled")

    def run_loop(self):
        method_list = {
            func: getattr(self, func)
            for func in dir(self)
            if callable(getattr(self, func)) and not func.startswith("__")
        }
        while True:  # The Event Loop
            event, values = self.window.read()
            if event == sg.WIN_CLOSED:
                self.handle_exit(values)
            event_callable = method_list.get(
                f"handle_{event}", partial(self.uncaught_events, event)
            )
            event_callable(values)
            if self.stopped:
                return


m = Manager()
m.run_loop()