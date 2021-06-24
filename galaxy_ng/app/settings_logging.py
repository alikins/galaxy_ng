import os
import yaml

try:
    LOGGING_YAML
except NameError:
    # we can set LOGGING_YAML by dynaconf / env, but if not set
    # default to 'logging.yaml'
    LOGGING_YAML = 'logging.yaml'

PROJECT_DIR = os.path.dirname(os.path.abspath(__file__))
LOGGING_YAML_FILE_PATH = os.path.join(PROJECT_DIR, LOGGING_YAML)
import sys
sys.stderr.write('yaml path=%s\n' % LOGGING_YAML_FILE_PATH)
logging_config = yaml.safe_load(open(LOGGING_YAML_FILE_PATH, 'r'))
LOGGING = logging_config
