from sys import platform
try:
    from yaml import CSafeLoader as Loader
except ImportError:
    from yaml import SafeLoader as Loader
import yaml

with open("config.yml") as f:
    config = yaml.load(f, Loader=Loader)

if platform == "linux" or platform == "linux2" or platform == "win32":
    import PySimpleGUI as PySimpleGUI
elif platform == "darwin":
    import PySimpleGUIWeb as PySimpleGUI