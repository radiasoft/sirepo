# This avoids a plugin dependency issue with pytest-forked/xdist:
# https://github.com/pytest-dev/pytest/issues/935
pytest_plugins = ['pykern.pytest_plugin']
