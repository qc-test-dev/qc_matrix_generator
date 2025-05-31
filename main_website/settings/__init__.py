import os

def get_secret(secret_id,backup=None):
    return os.environ.get(secret_id, backup)
if get_secret('PIPELINE')== 'production':
    from .production import *
else:
    from .local import *
# This file is used to determine which settings to import based on the environment variable PIPELINE.