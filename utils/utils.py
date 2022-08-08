import os

def load_env_list(key):
    val = os.environ.get(key, '')
    return [x.strip() for x in val.split(',')]