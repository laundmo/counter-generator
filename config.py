try:
    from yaml import CSafeLoader as Loader
except ImportError:
    from yaml import SafeLoader as Loader
import yaml

with open("config.yml") as f:
    config = yaml.load(f, Loader=Loader)
