from sys import platform
try:
    from yaml import CSafeLoader as Loader # use the C loader when possible
except ImportError:
    from yaml import SafeLoader as Loader
import yaml

with open("config.yml") as f:
    config = yaml.load(f, Loader=Loader) # load the config yaml

if platform in ("linux", "linux2", "win32"):
    import PySimpleGUI
elif platform == "darwin": # Have to use web/remi on MacOS as the normal tkinter version causes a OS error 
    # TODO: Test on MacOS with tkinter possibly figure out how to get it working.
    import PySimpleGUIWeb as PySimpleGUI