from __future__ import annotations

import dataclasses
import importlib
import importlib.resources
import json
import logging
import subprocess
import sys
from abc import abstractmethod
from collections.abc import Sequence
from functools import partial
from pathlib import Path
from tempfile import TemporaryDirectory
from typing import TYPE_CHECKING
from typing import Any
from typing import cast

from packaging.markers import Marker
from packaging.markers import default_environment
from packaging.requirements import Requirement
from variantlib.constants import VALIDATION_PROVIDER_PLUGIN_API_REGEX
from variantlib.errors import NoPluginFoundError
from variantlib.errors import PluginError
from variantlib.errors import PluginMissingError
from variantlib.models.provider import ProviderConfig
from variantlib.models.provider import VariantFeatureConfig
from variantlib.plugins.py_envs import python_env
from variantlib.validators.base import validate_matches_re

if TYPE_CHECKING:
    from contextlib import AbstractContextManager
    from types import TracebackType

    from variantlib.models.variant import VariantDescription
    from variantlib.models.variant_info import ProviderInfo
    from variantlib.models.variant_info import VariantInfo
    from variantlib.plugins.py_envs import PythonEnv

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
    _python_ctx_manager: AbstractContextManager[PythonEnv] | None = None
    _python_ctx: PythonEnv | None = None

    def __init__(
        self,
        use_auto_install: bool,
        isolated: bool = True,
        venv_path: Path | None = None,
    ) -> None:
        self._use_auto_install = use_auto_install
        # isolated=True is effective only with use_auto_install=True
        # (otherwise we'd be using empty venv)
        self._python_ctx_factory = partial(
            python_env, isolated=isolated and use_auto_install, venv_path=venv_path
        )

    def __enter__(self) -> Self:
        if self._python_ctx is not None:
            raise RuntimeError("Already inside the context manager!")

        self._python_ctx_manager = self._python_ctx_factory()
        self._python_ctx = self._python_ctx_manager.__enter__()
        try:
            if self._use_auto_install:
                self._install_all_plugins()
            self._load_all_plugins()
        except Exception:
            self._python_ctx_manager.__exit__(*sys.exc_info())
            self._python_ctx = None
            self._python_ctx_manager = None
            raise

        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc_value: BaseException | None,
        traceback: TracebackType | None,
    ) -> None:
        if self._python_ctx is None:
            raise RuntimeError("Context manager not entered!")
        assert self._python_ctx_manager is not None

        self._namespace_map = None
        self._python_ctx = None
        self._python_ctx_manager.__exit__(exc_type, exc_value, traceback)

    def _install_all_plugins(self) -> None:
        pass

    def _install_all_plugins_from_reqs(self, reqs: list[str]) -> None:
        if self._python_ctx is None:
            raise RuntimeError("Context manager not entered!")

        # Actual plugin installation
        self._python_ctx.install(reqs)

    def _call_subprocess(
        self, plugin_apis: list[str], commands: dict[str, Any]
    ) -> dict[str, dict[str, Any]]:
        assert self._python_ctx is not None

        with TemporaryDirectory(prefix="variantlib") as temp_dir:
            script = Path(temp_dir) / "loader.py"
            script.write_bytes(
                (importlib.resources.files(__package__) / "_subprocess.py")
                .read_bytes()
                .replace(b"from variantlib.protocols", b"from _variantlib_protocols")
                .replace(
                    b"from variantlib.validators.base",
                    b"from _variantlib_validators_base",
                )
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

            process = subprocess.run(  # noqa: S603
                [self._python_ctx.python_executable, script, *args],
                input=json.dumps(commands).encode("utf8"),
                capture_output=True,
                check=False,
            )
            if process.returncode != 0:
                raise PluginError(
                    f"Plugin invocation failed:\n{process.stderr.decode('utf8')}"
                )
            return json.loads(process.stdout)  # type: ignore[no-any-return]

    @abstractmethod
    def _load_all_plugins(self) -> None: ...

    def _load_all_plugins_from_tuple(self, plugin_apis: list[str]) -> None:
        if self._python_ctx is None:
            raise RuntimeError("Context manager not entered!")
        if self._namespace_map is not None:
            raise RuntimeError(
                "Impossible to load plugins - `self._namespace_map` is not None"
            )
        self._namespace_map = {}

        normalized_plugin_apis = []
        for plugin_api in plugin_apis:
            plugin_api_match = validate_matches_re(
                plugin_api, VALIDATION_PROVIDER_PLUGIN_API_REGEX
            )
            import_name: str = plugin_api_match.group("module")
            attr_path: str = plugin_api_match.group("attr") or ""
            # normalize it before passing to the subprocess
            normalized_plugin_apis.append(f"{import_name}:{attr_path}")

            logger.info(
                "Loading plugin via %(plugin_api)s",
                {
                    "plugin_api": plugin_api,
                },
            )

        namespaces = self._call_subprocess(normalized_plugin_apis, {"namespaces": {}})[
            "namespaces"
        ]

        for plugin_api, namespace in namespaces.items():
            if namespace in self._namespace_map.values():
                raise RuntimeError(
                    "Two plugins found using the same namespace "
                    f"{namespace}. Refusing to proceed."
                )

            self._namespace_map[plugin_api] = namespace
            logger.info(
                "Namespace %(namespace)s provided by plugin %(plugin_api)s",
                {
                    "namespace": namespace,
                    "plugin_api": plugin_api,
                },
            )

    def _check_plugins_loaded(self) -> None:
        if self._python_ctx is None:
            raise RuntimeError("Context manager not entered!")
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
    _variant_info: VariantInfo

    def __init__(
        self,
        variant_info: VariantInfo,
        use_auto_install: bool,
        isolated: bool = True,
        venv_path: Path | None = None,
        enable_optional_plugins: bool | list[str] = False,
    ) -> None:
        self._variant_info = variant_info
        self._enable_optional_plugins = enable_optional_plugins
        self._environment = cast("dict[str, str]", default_environment())
        super().__init__(
            use_auto_install=use_auto_install, isolated=isolated, venv_path=venv_path
        )

    def _optional_provider_enabled(self, namespace: str) -> bool:
        # if enable_optional_plugins is a bool, it controls all plugins
        if self._enable_optional_plugins in (False, True):
            assert isinstance(self._enable_optional_plugins, bool)
            return self._enable_optional_plugins
        # otherwise, it's a list of enabled namespaces
        assert isinstance(self._enable_optional_plugins, Sequence)
        return namespace in self._enable_optional_plugins

    def _provider_enabled(self, namespace: str, provider_data: ProviderInfo) -> bool:
        if provider_data.optional and not self._optional_provider_enabled(namespace):
            logger.debug(
                "The variant provider plugin corresponding "
                "to namespace `%(ns)s` has been skipped - optional provider disabled.",
                {"ns": namespace},
            )
            return False

        if (marker := provider_data.enable_if) is not None:
            if not Marker(marker).evaluate(self._environment):
                logger.debug(
                    "The variant provider plugin corresponding "
                    "to namespace `%(ns)s` has been skipped - Not compatible with "
                    "the environmment. Details: %(data)s.",
                    {"ns": namespace, "data": provider_data},
                )
                return False

        return True

    def _install_all_plugins(self) -> None:
        # Installing the plugins
        reqs = []
        for namespace, provider_data in self._variant_info.providers.items():
            if not self._provider_enabled(namespace, provider_data):
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
                if not (
                    pyreq.marker.evaluate(self._environment) if pyreq.marker else True
                ):
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

        plugins = [
            provider_data.object_reference
            for namespace, provider_data in self._variant_info.providers.items()
            if self._provider_enabled(namespace, provider_data)
        ]

        self._load_all_plugins_from_tuple(plugin_apis=plugins)


class EntryPointPluginLoader(BasePluginLoader):
    _plugin_provider_packages: dict[str, Distribution] | None = None

    def __init__(
        self,
        venv_path: Path | None = None,
    ) -> None:
        super().__init__(use_auto_install=False, isolated=False, venv_path=venv_path)

    def _load_all_plugins(self) -> None:
        if self._namespace_map is not None:
            raise RuntimeError(
                "Impossible to load plugins - `self._namespace_map` is not None"
            )

        self._plugin_provider_packages = {}
        plugin_apis = []
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

            plugin_apis.append(ep.value)
            if ep.dist is not None:
                self._plugin_provider_packages[ep.value] = ep.dist

        self._load_all_plugins_from_tuple(plugin_apis=plugin_apis)

    @property
    def plugin_provider_packages(self) -> dict[str, Distribution]:
        """plugin_api -> provider Distribution mapping"""
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
        super().__init__(use_auto_install=False, isolated=False, venv_path=venv_path)

    def _load_all_plugins(self) -> None:
        if self._namespace_map is not None:
            raise RuntimeError(
                "Impossible to load plugins - `self._namespace_map` is not None"
            )

        self._load_all_plugins_from_tuple(plugin_apis=self._plugin_apis)
