import os
import yaml

try:
    LOGGING_YAML
except NameError:
    # we can set LOGGING_YAML by dynaconf / env, but if not set
    # default to 'logging.yaml'
    LOGGING_YAML = 'logging.yaml'

PROJECT_DIR = os.path.dirname(os.path.abspath(__file__))
logging_config = yaml.safe_load(open(os.path.join(PROJECT_DIR, LOGGING_YAML), 'r'))
LOGGING = logging_config
