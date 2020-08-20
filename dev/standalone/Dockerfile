FROM localhost/galaxy_ng/galaxy_ng:base

COPY requirements/requirements.standalone.txt /tmp/requirements.standalone.txt

RUN set -ex; \
    if [[ "${LOCK_REQUIREMENTS}" -eq "1" ]]; then \
    pip install --cache-dir=/src/pip_cache --requirement /tmp/requirements.standalone.txt; \
    fi
