FROM localhost/galaxy_ng/galaxy_ng:base

COPY requirements/requirements.standalone.txt /tmp/requirements.standalone.txt

RUN set -ex; \
    pip install --cache-dir /pip_cache --requirement /tmp/requirements.standalone.txt
