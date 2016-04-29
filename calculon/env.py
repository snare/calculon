from scruffy import *


def load_env():
    env = Environment(
        main_dir=Directory('~/.calculon', create=True,
            config=ConfigFile('config', defaults=File('config/default.cfg', parent=PackageDirectory())),
            uri=File('uri')
        )
    )
    return env

env = load_env()
config = env.config
