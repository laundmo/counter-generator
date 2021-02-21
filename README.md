# counter-generator
Incrementing counter clip generator for [David The Hooman](https://www.youtube.com/channel/UCWH6O3GL1sLj-cIjukOmppQ)

## Installation

#### Clone the repository
```
git clone https://github.com/laundmo/counter-generator.git
```

#### Install the requirements

Windows
```
py -m pip install -r requirements.txt
```

MacOS/linux
```
python3 -m pip install -r requirements.txt
```

#### Run the script

Windows
```
py main.py
```

MacOS/linux
```
python3 main.py
```

## Config

The configuration can be found in `config.yml`.

#### keybinds

in the keybinds section you can configure the keybinds
some examples for the syntax are:
- `<shift> + <alt> + g`
- `<space> + <ctrl>`
- `h`

#### counter

Here you can configure the counter behaviour.
The `hold-delay` is how quickly the counter counts up while holding, assuming a `hold-multiplier` of 1.
The counter will ramp up to `hold-multiplier` times the base speed.
You can set `hold-multiplier` to 0 to disable the hold feature completely.

#### font

Filename of a font file (either ttf or ttc) in the current directory.

#### output

| Name     | Default | Description                                                                                        |
|----------|---------|----------------------------------------------------------------------------------------------------|
| width    | 500     | The total width of the final video, in pixels.                                                     |
| height   | 200     | The height of the final video, in pixels.                                                          |
| fps      | 60      | The framerate of the final video. Lower framerates may make the counter look considerably worse.   |
| fontsize | 200     | The font size of the counter, in pixels. Match height for best result.                             |
| prepend  | +       | A text to add in front of the counter.                                                             |
| extend   | 2       | This number of seconds to extend the video by. dont set to 0, it will mess up the last few counts. |


## Usage

[Notes on Limitations (important for MacOs)](https://pynput.readthedocs.io/en/latest/limitations.html)

When starting, you will be presented with a blank window.

![](https://i.vgy.me/F28UNy.png)

Here you can press `Start` to start counting up, or `Generate Video` to load a recorded count from a file.

![](https://i.vgy.me/d37SeX.png)

Now you can count up by pressing or holding your keybind (`<space>` by default). Once you're done, you can hit `Save` to save the current counter to a file, in case you want to generate a video with a different config later. Otherwise, just press `Generate Video`.

![](https://i.vgy.me/86d3lD.png)

Here you can enter a file name to load, or just click `Generate` to use the current counter. Loading from a clip name will discard the current data.

After you click `generate`, a file named `text0.avi` should have appeared in the current folder. If you pressed `Start/Stop` multiple times there may be multiple other files with the name `text1.avi`, `text2.avi` etc.

Attention: these files will be overwritten if you generate another video. Make sure to rename them or copy them elsewhere.

## Example with default config
![](https://i.vgy.me/ctbPiv.gif)
