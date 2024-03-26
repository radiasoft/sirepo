"""Support routines and classes, mostly around errors and I/O.

:copyright: Copyright (c) 2018 RadiaSoft LLC.  All Rights Reserved.
:license: http://www.apache.org/licenses/LICENSE-2.0.html
"""

# NOTE: limit sirepo imports here
from pykern import pkcompat
from pykern import pkconfig
from pykern.pkcollections import PKDict
from pykern.pkdebug import pkdlog, pkdp, pkdexc, pkdc
import asyncio
import base64
import hashlib
import importlib
import inspect
import numconv
import pykern.pkinspect
import pykern.pkio
import pykern.pkjson
import re
import random
import six
import unicodedata
import zipfile


_cfg = None

#: Http auth header name
AUTH_HEADER = "Authorization"

#: http auth header scheme bearer
AUTH_HEADER_SCHEME_BEARER = "Bearer"

#: length of string returned by create_token
TOKEN_SIZE = 16

# See https://github.com/radiasoft/sirepo/pull/3889#discussion_r738769716
# for reasoning on why define both
_INVALID_PYTHON_IDENTIFIER = re.compile(r"\W|^(?=\d)")
_VALID_PYTHON_IDENTIFIER = re.compile(r"^[a-z_]\w*$", re.IGNORECASE)

_INVALID_PATH_CHARS = re.compile(r"[^A-Za-z0-9_.-]")


class ReplyExc(Exception):
    """Raised to end the request.

    Args:
        sr_args (dict): exception args that Sirepo specific
        log_fmt (str): server side log data
    """

    def __init__(self, *args, **kwargs):
        super().__init__()
        if "sr_args" in kwargs:
            self.sr_args = kwargs["sr_args"]
            del kwargs["sr_args"]
        else:
            self.sr_args = PKDict()
        if args or kwargs:
            kwargs["pkdebug_frame"] = inspect.currentframe().f_back.f_back
            pkdlog(*args, **kwargs)

    def __repr__(self):
        a = self.sr_args
        return "{}({})".format(
            self.__class__.__name__,
            ",".join(
                ("{}={}".format(k, a[k]) for k in sorted(a.keys())),
            ),
        )

    def __str__(self):
        return self.__repr__()


class BadRequest(ReplyExc):
    """Raised for bad request"""

    pass


class OKReplyExc(ReplyExc):
    """When a ReplyExc exception is a successful response"""

    pass


class Error(ReplyExc):
    """Raised to send an error response

    Args:
        error_msg (str): just the error to output to user
    """

    def __init__(self, error, *args, **kwargs):
        # removed dict usage
        assert isinstance(error, str)
        super().__init__(*args, sr_args=PKDict(error=error), **kwargs)


class Forbidden(ReplyExc):
    """Raised for forbidden"""

    pass


class NotFound(ReplyExc):
    """Raised for not found"""

    pass


class Redirect(OKReplyExc):
    """Raised to redirect

    Args:
        uri (str): where to redirect to
        log_fmt (str): server side log data
    """

    def __init__(self, uri, *args, **kwargs):
        super().__init__(*args, sr_args=PKDict(uri=uri), **kwargs)


class ContentTooLarge(ReplyExc):
    """The content requested by the user was too large (ex large data file)"""

    pass


class ServerError(ReplyExc):
    """Raised for server error"""

    pass


class SPathNotFound(NotFound):
    """Raised by simulation_db

    Args:
        sim_type (str): simulation type
        uid (str): user
        sid (str): simulation id
    """

    def __init__(self, sim_type, uid, sid, *args, **kwargs):
        super().__init__(
            *args,
            sr_args=PKDict(sim_type=sim_type, uid=uid, sid=sid),
            **kwargs,
        )


class SReplyExc(OKReplyExc):
    """Raise with an SReply object

    Args:
        sreply (object): what the reply should be
        log_fmt (str): server side log data
    """

    def __init__(self, sreply, *args, **kwargs):
        super().__init__(*args, sr_args=PKDict(sreply=sreply), **kwargs)


class SRException(ReplyExc):
    """Raised to communicate a local redirect and log info

    `params` may have ``simulationType``, which will be used for routeName rendering.
    Otherwise, ``sim_type`` on ``qcall`` will be used.

    Args:
        route_name (str): a local route
        params (dict): for route url or for srExceptionOnly case
        log_fmt (str): server side log data
    """

    def __init__(self, route_name, params, *args, **kwargs):
        super().__init__(
            *args,
            sr_args=PKDict(routeName=route_name, params=params),
            **kwargs,
        )


class Unauthorized(ReplyExc):
    """Raised to generate 401 response"""

    pass


class UserAlert(ReplyExc):
    """Raised to display a user error and log info

    Args:
        display_text (str): string that user will see
        log_fmt (str): server side log data
    """

    def __init__(self, display_text, *args, **kwargs):
        super().__init__(*args, sr_args=PKDict(error=display_text), **kwargs)


class UserDirNotFound(NotFound):
    """Raised by simulation_db

    Args:
        user_dir (py.path): directory not found
        uid (str): user
    """

    def __init__(self, user_dir, uid, *args, **kwargs):
        super().__init__(
            *args,
            sr_args=PKDict(user_dir=user_dir, uid=uid),
            **kwargs,
        )


class WWWAuthenticate(ReplyExc):
    """Raised to generate 401 response with WWWAuthenticate response"""

    pass


def assert_sim_type(sim_type):
    """Validate simulation type

    Args:
        sim_type (str): to check

    Returns:
        str: validated sim_type
    """
    assert is_sim_type(sim_type), f"invalid simulation type={sim_type}"
    return sim_type


def create_token(value):
    if pkconfig.channel_in_internal_test() and _cfg.create_token_secret:
        v = base64.b32encode(
            hashlib.sha256(pkcompat.to_bytes(value + _cfg.create_token_secret)).digest()
        )
        return pkcompat.from_bytes(v[:TOKEN_SIZE])
    return random_base62(TOKEN_SIZE)


def err(obj, fmt="", *args, **kwargs):
    return "{}: ".format(obj) + fmt.format(*args, **kwargs)


def files_to_watch_for_reload(*extensions):
    from sirepo import feature_config

    for e in extensions:
        for p in sorted(set(["sirepo", *feature_config.cfg().package_path])):
            d = pykern.pkio.py_path(
                getattr(importlib.import_module(p), "__file__"),
            ).dirname
            for f in pykern.pkio.sorted_glob(f"{d}/**/*.{e}"):
                yield f


def find_obj(arr, key, value):
    """Return the first object in the array such that obj[key] == value

    Args:
        arr (list): list of dict-like objects
        key (str): object key
        value (*): value
    Returns:
        object: the object, or None if not found
    """
    for o in arr:
        if o[key] == value:
            return o
    return None


def import_submodule(submodule, type_or_data):
    """Import fully qualified module that contains submodule for sim type

    sirepo.feature_config.package_path will be searched for a match.

    Args:
        submodule (str): the name of the submodule
        type_or_data (str or dict): simulation type or description
    Returns:
        module: simulation type module instance
    """
    from sirepo import feature_config
    from sirepo import template

    sim_type = template.assert_sim_type(
        (
            type_or_data.simulationType
            if isinstance(
                type_or_data,
                PKDict,
            )
            else type_or_data
        ),
    )
    for p in feature_config.cfg().package_path:
        n = None
        try:
            n = f"{p}.{submodule}.{sim_type}"
            return importlib.import_module(n)
        except ModuleNotFoundError as e:
            if n is not None and n != e.name:
                # import is failing due to ModuleNotFoundError in a sub-import
                # not the module we are looking for
                raise
            s = pkdexc()
            pass
    # gives more debugging info (perhaps more confusion)
    pkdc(s)
    raise AssertionError(
        f"cannot find submodule={submodule} for sim_type={sim_type} in package_path={feature_config.cfg().package_path}"
    )


def is_python_identifier(name):
    return _VALID_PYTHON_IDENTIFIER.search(name)


def is_sim_type(sim_type):
    """Validate simulation type

    Args:
        sim_type (str): to check

    Returns:
        bool: true if is a sim_type
    """
    from sirepo import feature_config

    return sim_type in feature_config.cfg().sim_types


def json_dump(obj, path=None, pretty=False, **kwargs):
    """Formats as json as string, and writing atomically to disk

    Args:
        obj (object): any Python object
        path (py.path): where to write (atomic) [None]
        pretty (bool): pretty print [False]
        kwargs (object): other arguments to `json.dumps`
    Returns:
        str: sorted and formatted JSON
    """
    res = pykern.pkjson.dump_pretty(obj, pretty=pretty, allow_nan=False, **kwargs)
    if path:
        pykern.pkio.atomic_write(path, res)
    return res


def random_base62(length=32):
    """Returns a safe string of sufficient length to be a nonce

    Args:
        length (int): how long to make the base62 string [32]
    Returns:
        str: random base62 characters
    """
    r = random.SystemRandom()
    return "".join(r.choice(numconv.BASE62) for x in range(length))


def read_zip(path_or_bytes):
    """Read the contents of a zip archive.

    Protects against malicious filenames (ex ../../filename)

    Args:
      path_or_bytes (py.path or str or bytes): The path to the archive or it's contents

    Returns:
       (py.path, bytes): The basename of the file, the contents of the file
    """
    p = path_or_bytes
    if isinstance(p, bytes):
        p = six.BytesIO(p)
    with zipfile.ZipFile(p, "r") as z:
        for i in z.infolist():
            if i.is_dir():
                continue
            # SECURITY: Use only basename of file to prevent against
            # malicious files (ex ../../filename)
            yield pykern.pkio.py_path(i.filename).basename, z.read(i)


def sanitize_string(string):
    """Remove special characters from string

    This results in a string the is a valid python identifier.
    This string can also be used as a css id because valid
    python identifiers are also valid css ids.

    Args:
      string (str): The string to sanatize
    Returns:
      (str): A string with special characters replaced
    """
    if is_python_identifier(string):
        return string
    return _INVALID_PYTHON_IDENTIFIER.sub("_", string)


def secure_filename(path):
    """Converts a user supplied path to a secure file

    Args:
        path (str): contains anything
    Returns:
        str: does not contain special file system chars or path chars
    """
    p = (
        unicodedata.normalize(
            "NFKD",
            path,
        )
        .encode(
            "ascii",
            "ignore",
        )
        .decode(
            "ascii",
        )
        .replace(
            "/",
            " ",
        )
    )
    p = _INVALID_PATH_CHARS.sub("", "_".join(p.split())).strip("._")
    return "file" if p == "" else p


def setattr_imports(imports):
    m = pykern.pkinspect.caller_module()
    for k, v in imports.items():
        setattr(m, k, v)


def split_comma_delimited_string(s, f_type):
    return [f_type(x) for x in re.split(r"\s*,\s*", s)]


def to_comma_delimited_string(arr):
    return ",".join([str(x) for x in arr])


def url_safe_hash(value):
    return hashlib.md5(pkcompat.to_bytes(value)).hexdigest()


def validate_path(uri):
    """Ensures path component of uri is safe

    Very strict. Doesn't allow any dot files and few specials.

    Args:
        uri (str): uncheck path
    Returns:
        str: validated path
    """
    if uri == "" or uri is None:
        raise AssertionError(f"empty uri")
    res = []
    for p in uri.split("/"):
        if _INVALID_PATH_CHARS.search(p):
            raise AssertionError(f"illegal char(s) in component={p} uri={uri}")
        if p == "":
            # covers absolute path case
            raise AssertionError(f"empty component in uri={uri}")
        if p.startswith("."):
            raise AssertionError(f"dot prefix in component={p} uri={uri}")
        res.append(p)
    return "/".join(res)


def write_zip(path):
    return zipfile.ZipFile(
        path,
        mode="w",
        compression=zipfile.ZIP_DEFLATED,
    )


async def yield_to_event_loop():
    """Documents and wraps ``asyncio.sleep(0)``

    If a server (api, supervisor, agent) is doing a lot of work, call
    this routine to release the processor to the event loop.
    """
    await asyncio.sleep(0)


_cfg = pkconfig.init(
    create_token_secret=("oh so secret!", str, "used for internal test only"),
)
