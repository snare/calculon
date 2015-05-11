from scruffy import *

ENV = None
CONFIG = None

def load_env():
    ENV = Environment(
        main_dir=Directory('~/.calculon', create=True,
            config=ConfigFile('config', defaults=File('config/default.cfg', parent=PackageDirectory())),
            uri=File('uri')
        )
    )
    return ENV

ENV = load_env()

CONFIG = ENV.config
