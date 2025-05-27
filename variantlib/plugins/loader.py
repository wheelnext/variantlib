from __future__ import annotations

import dataclasses
import importlib
import importlib.resources
import importlib.util
import json
import logging
import sys
from abc import abstractmethod
from pathlib import Path
from subprocess import run
from tempfile import TemporaryDirectory
from typing import TYPE_CHECKING
from typing import Any

from packaging.markers import Marker
from packaging.markers import default_environment
from packaging.requirements import Requirement

from variantlib.constants import VALIDATION_PROVIDER_PLUGIN_API_REGEX
from variantlib.errors import NoPluginFoundError
from variantlib.errors import PluginError
from variantlib.errors import PluginMissingError
from variantlib.models.provider import ProviderConfig
from variantlib.models.provider import VariantFeatureConfig
from variantlib.plugins.py_envs import INSTALLER_PYTHON_ENVS
from variantlib.plugins.py_envs import AutoPythonEnv
from variantlib.plugins.py_envs import BasePythonEnv
from variantlib.plugins.py_envs import ExternalNonIsolatedPythonEnv
from variantlib.validators.base import validate_matches_re

if TYPE_CHECKING:
    from variantlib.models.metadata import VariantMetadata
    from variantlib.models.variant import VariantDescription

if sys.version_info >= (3, 10):
    from importlib.metadata import Distribution
    from importlib.metadata import entry_points
else:
    from importlib_metadata import Distribution
    from importlib_metadata import entry_points

if sys.version_info >= (3, 11):
    from typing import Self
else:
    from typing_extensions import Self

logger = logging.getLogger(__name__)


class BasePluginLoader:
    """Load and query plugins"""

    _namespace_map: dict[str, str] | None = None
    _python_ctx: BasePythonEnv | None = None

    def __init__(self, python_ctx: BasePythonEnv | None = None) -> None:
        self._python_ctx = python_ctx

    def __enter__(self) -> Self:
        if self._python_ctx is None:
            raise RuntimeError("Impossible to load plugins outside a Python Context")

        self._load_all_plugins()

        return self

    def __exit__(self, *args: object) -> None:
        self._namespace_map = None

        if self._python_ctx is None:
            logger.warning("The Python installer is None. Should not happen.")
            return

    def _install_all_plugins_from_reqs(self, reqs: list[str]) -> None:
        if self._python_ctx is None:
            raise RuntimeError("Impossible to load plugins outside a Python Context")

        if not isinstance(self._python_ctx, INSTALLER_PYTHON_ENVS):
            raise TypeError(
                "Impossible to install a package with this type of python "
                "environment: %s",
                type(self._python_ctx),
            )

        # Actual plugin installation
        self._python_ctx.install(reqs)

    def _call_subprocess(self, plugin_apis: list[str], commands: dict[str, Any]) -> Any:
        assert self._python_ctx is not None

        with TemporaryDirectory(prefix="variantlib") as temp_dir:
            script = Path(temp_dir) / "loader.py"
            script.write_bytes(
                (importlib.resources.files(__package__) / "_subprocess.py").read_bytes()
            )
            (Path(temp_dir) / "_variantlib_protocols.py").write_bytes(
                (importlib.resources.files("variantlib") / "protocols.py").read_bytes()
            )
            (Path(temp_dir) / "_variantlib_validators_base.py").write_bytes(
                (
                    importlib.resources.files("variantlib.validators") / "base.py"
                ).read_bytes()
            )
            args = []
            for plugin_api in plugin_apis:
                args += ["-p", plugin_api]
            process = run(  # noqa: S603
                [self._python_ctx.python_executable, script, *args],
                input=json.dumps(commands).encode("utf8"),
                capture_output=True,
                check=False,
            )
            if process.returncode != 0:
                raise PluginError(
                    f"Plugin invocation failed:\n{process.stderr.decode('utf8')}"
                )
            return json.loads(process.stdout)

    def load_plugin(self, plugin_api: str) -> str:
        """Load a specific plugin"""

        if self._namespace_map is None:
            self._namespace_map = {}
        if self._python_ctx is None:
            raise RuntimeError("Impossible to load plugins outside a Python Context")

        plugin_api_match = validate_matches_re(
            plugin_api, VALIDATION_PROVIDER_PLUGIN_API_REGEX
        )
        import_name: str = plugin_api_match.group("module")
        attr_path: str = plugin_api_match.group("attr")
        # normalize it before passing to the subprocess
        plugin_api = f"{import_name}:{attr_path}"

        logger.info(
            "Loading plugin via %(plugin_api)s",
            {
                "plugin_api": plugin_api,
            },
        )

        # make sure to normalize it
        namespace = self._call_subprocess([plugin_api], {"namespaces": {}})[
            "namespaces"
        ][plugin_api]

        if namespace in self._namespace_map.values():
            raise RuntimeError(
                "Two plugins found using the same namespace "
                f"{namespace}. Refusing to proceed."
            )

        self._namespace_map[plugin_api] = namespace
        return namespace

    @abstractmethod
    def _load_all_plugins(self) -> None: ...

    def _load_all_plugins_from_tuple(self, plugin_apis: list[str]) -> None:
        if self._namespace_map is not None:
            raise RuntimeError(
                "Impossible to load plugins - `self._namespace_map` is not None"
            )

        for plugin_api in plugin_apis:
            try:
                self.load_plugin(plugin_api=plugin_api)
            except PluginError:  # noqa: PERF203
                logger.debug(
                    "Impossible to load `%s`", plugin_api, exc_info=sys.exc_info()
                )

    def _check_plugins_loaded(self) -> None:
        if self._python_ctx is None:
            raise RuntimeError("Impossible to load plugins outside a Python Context")
        if self._namespace_map is None:
            raise NoPluginFoundError("No plugin has been loaded in the environment.")

    def _get_configs(
        self, method: str, require_non_empty: bool
    ) -> dict[str, ProviderConfig]:
        self._check_plugins_loaded()
        assert self._namespace_map is not None

        configs = self._call_subprocess(list(self._namespace_map.keys()), {method: {}})[
            method
        ]

        provider_cfgs = {}
        for plugin_api, plugin_configs in configs.items():
            namespace = self._namespace_map[plugin_api]

            if not plugin_configs:
                if require_non_empty:
                    raise ValueError(
                        f"Provider {namespace}, {method}() method returned no valid "
                        "configs"
                    )
                continue

            provider_cfgs[namespace] = ProviderConfig(
                namespace,
                configs=[
                    VariantFeatureConfig(**vfeat_cfg) for vfeat_cfg in plugin_configs
                ],
            )

        return provider_cfgs

    def get_supported_configs(self) -> dict[str, ProviderConfig]:
        """Get a mapping of namespaces to supported configs"""
        return self._get_configs("get_supported_configs", require_non_empty=False)

    def get_all_configs(self) -> dict[str, ProviderConfig]:
        """Get a mapping of namespaces to all valid configs"""
        return self._get_configs("get_all_configs", require_non_empty=True)

    def get_build_setup(self, variant_desc: VariantDescription) -> dict[str, list[str]]:
        """Get build variables for a variant made of specified properties"""
        self._check_plugins_loaded()
        assert self._namespace_map is not None

        namespaces = {vprop.namespace for vprop in variant_desc.properties}
        try:
            plugin_apis = [
                self.plugin_api_values[namespace] for namespace in namespaces
            ]
        except KeyError as err:
            raise PluginMissingError(f"No plugin found for namespace {err}") from None
        return self._call_subprocess(
            plugin_apis,
            {
                "get_build_setup": {
                    "properties": [
                        dataclasses.asdict(vprop) for vprop in variant_desc.properties
                    ]
                }
            },
        )["get_build_setup"]

    @property
    def plugin_api_values(self) -> dict[str, str]:
        self._check_plugins_loaded()
        assert self._namespace_map is not None
        return {
            namespace: plugin_api
            for plugin_api, namespace in self._namespace_map.items()
        }

    @property
    def namespaces(self) -> list[str]:
        self._check_plugins_loaded()
        assert self._namespace_map is not None
        return list(self._namespace_map.values())


class PluginLoader(BasePluginLoader):
    _variant_nfo: VariantMetadata

    def __init__(
        self,
        variant_nfo: VariantMetadata,
        use_auto_install: bool,
        isolated: bool = True,
        venv_path: Path | None = None,
    ) -> None:
        self._variant_nfo = variant_nfo
        super().__init__(
            python_ctx=AutoPythonEnv(use_auto_install, isolated, venv_path)
        )

    def __enter__(self) -> Self:
        if self._python_ctx is None:
            raise RuntimeError("Impossible to load plugins outside a Python Context")

        self._python_ctx.__enter__()
        if isinstance(self._python_ctx, INSTALLER_PYTHON_ENVS):
            self._install_all_plugins()

        return super().__enter__()

    def __exit__(self, *args: object) -> None:
        ret = super().__exit__(*args)
        if self._python_ctx is not None:
            self._python_ctx.__exit__(*args)
            self._python_ctx = None
        return ret

    def _install_all_plugins(self) -> None:
        if not isinstance(self._python_ctx, INSTALLER_PYTHON_ENVS):
            raise TypeError(
                "Impossible to install a package with this type of python "
                "environment: %s",
                type(self._python_ctx),
            )

        # Get the current environment and evaluate the marker
        pyenv = default_environment()

        # Installing the plugins
        reqs = []
        for namespace in self._variant_nfo.namespace_priorities:
            if (provider_data := self._variant_nfo.providers.get(namespace)) is None:
                logger.error(
                    "Impossible to install the variant provider plugin corresponding "
                    "to namespace `%(ns)s`. Missing provider entry - Known: %(known)s.",
                    {
                        "ns": namespace,
                        "known": list(self._variant_nfo.providers.keys()),
                    },
                )
                continue

            if (marker := self._variant_nfo.providers[namespace].enable_if) is not None:
                if not Marker(marker).evaluate(pyenv):
                    logger.debug(
                        "The variant provider plugin corresponding "
                        "to namespace `%(ns)s` has been skipped - Not compatible with "
                        "the environmment. Details: %(data)s.",
                        {"ns": namespace, "data": provider_data},
                    )
                    continue

            if not (list_req_str := provider_data.requires):
                logger.error(
                    "Impossible to install the variant provider plugin corresponding "
                    "to namespace `%(ns)s`. Missing provider requirement, "
                    "received: %(data)s.",
                    {"ns": namespace, "data": provider_data},
                )
                continue

            for req_str in list_req_str:
                pyreq = Requirement(req_str)
                if not (pyreq.marker.evaluate(pyenv) if pyreq.marker else True):
                    continue

                # If there's at least one requirement compatible - break
                break
            else:
                logger.debug(
                    "The variant provider plugin corresponding "
                    "to namespace `%(ns)s` has been skipped - Not compatible with the "
                    "environmment. Details: %(data)s.",
                    {"ns": namespace, "data": provider_data},
                )
                continue

            reqs.extend(list_req_str)

        self._install_all_plugins_from_reqs(reqs)

    def _load_all_plugins(self) -> None:
        if self._namespace_map is not None:
            raise RuntimeError(
                "Impossible to load plugins - `self._namespace_map` is not None"
            )

        # Get the current environment for marker evaluation
        pyenv = default_environment()

        plugins = [
            self._variant_nfo.providers[namespace].plugin_api
            for namespace in self._variant_nfo.namespace_priorities
            if (marker := self._variant_nfo.providers[namespace].enable_if) is None
            or Marker(marker).evaluate(pyenv)
        ]

        self._load_all_plugins_from_tuple(plugin_apis=plugins)


class EntryPointPluginLoader(BasePluginLoader):
    _plugin_provider_packages: dict[str, Distribution] | None = None

    def __init__(
        self,
        venv_path: Path | None = None,
    ) -> None:
        super().__init__(
            python_ctx=AutoPythonEnv(
                use_auto_install=False, isolated=False, venv_path=venv_path
            )
        )

    def __enter__(self) -> Self:
        if self._python_ctx is None:
            raise RuntimeError("Impossible to load plugins outside a Python Context")

        self._python_ctx.__enter__()
        return super().__enter__()

    def __exit__(self, *args: object) -> None:
        ret = super().__exit__(*args)
        if self._python_ctx is not None:
            self._python_ctx.__exit__(*args)
            self._python_ctx = None
        return ret

    def _load_all_plugins(self) -> None:
        if self._namespace_map is not None:
            raise RuntimeError(
                "Impossible to load plugins - `self._namespace_map` is not None"
            )

        self._plugin_provider_packages = {}
        eps = entry_points().select(group="variant_plugins")
        for ep in eps:
            logger.info(
                "Plugin discovered via entry point: %(name)s = %(value)s; "
                "provided by package %(package)s %(version)s",
                {
                    "name": ep.name,
                    "value": ep.value,
                    "package": ep.dist.name if ep.dist is not None else "unknown",
                    "version": (ep.dist.version if ep.dist is not None else ""),
                },
            )

            try:
                namespace = self.load_plugin(plugin_api=ep.value)
            except PluginError:
                logger.debug("Impossible to load `%s`", ep, exc_info=sys.exc_info())
            else:
                if ep.dist is not None:
                    self._plugin_provider_packages[namespace] = ep.dist

    @property
    def plugin_provider_packages(self) -> dict[str, Distribution]:
        if self._namespace_map is None:
            raise NoPluginFoundError("No plugin has been loaded in the environment.")
        assert self._plugin_provider_packages is not None
        return self._plugin_provider_packages


class ListPluginLoader(BasePluginLoader):
    """Load plugins from an explicit plugin-api list"""

    _plugin_apis: list[str]

    def __init__(
        self,
        plugin_apis: list[str],
        venv_path: Path | None = None,
    ) -> None:
        self._plugin_apis = list(plugin_apis)
        super().__init__(
            python_ctx=AutoPythonEnv(
                use_auto_install=False, isolated=False, venv_path=venv_path
            )
        )

    def __enter__(self) -> Self:
        if self._python_ctx is None:
            raise RuntimeError("Impossible to load plugins outside a Python Context")

        self._python_ctx.__enter__()
        return super().__enter__()

    def __exit__(self, *args: object) -> None:
        ret = super().__exit__(*args)
        if self._python_ctx is not None:
            self._python_ctx.__exit__(*args)
            self._python_ctx = None
        return ret

    def _load_all_plugins(self) -> None:
        if self._namespace_map is not None:
            raise RuntimeError(
                "Impossible to load plugins - `self._namespace_map` is not None"
            )

        self._load_all_plugins_from_tuple(plugin_apis=self._plugin_apis)


class ManualPluginLoader(BasePluginLoader):
    """Load and query plugins"""

    _python_ctx: ExternalNonIsolatedPythonEnv

    def __init__(self) -> None:
        self._namespace_map = {}
        super().__init__(python_ctx=ExternalNonIsolatedPythonEnv().__enter__())

    def __enter__(self) -> Self:
        return self

    def __exit__(self, *args: object) -> None:
        self._namespace_map = {}

    def __del__(self) -> None:
        self._python_ctx.__exit__()

    def _load_all_plugins(self) -> None:
        raise NotImplementedError("This Plugin Loader doesn't support this behavior")
