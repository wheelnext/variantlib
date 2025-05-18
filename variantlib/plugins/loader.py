from __future__ import annotations

import importlib
import importlib.util
import logging
import sys
from abc import abstractmethod
from functools import reduce
from importlib.machinery import PathFinder
from itertools import groupby
from types import MethodType
from typing import TYPE_CHECKING
from typing import Any
from typing import get_type_hints

from packaging.markers import Marker
from packaging.markers import default_environment
from packaging.requirements import Requirement

from variantlib.constants import VALIDATION_PROVIDER_PLUGIN_API_REGEX
from variantlib.errors import NoPluginFoundError
from variantlib.errors import PluginError
from variantlib.errors import PluginMissingError
from variantlib.errors import ValidationError
from variantlib.models.provider import ProviderConfig
from variantlib.models.provider import VariantFeatureConfig
from variantlib.plugins.py_envs import INSTALLER_PYTHON_ENVS
from variantlib.plugins.py_envs import ISOLATED_PYTHON_ENVS
from variantlib.plugins.py_envs import BasePythonEnv
from variantlib.plugins.py_envs import ExternalNonIsolatedPythonEnv
from variantlib.protocols import PluginType
from variantlib.protocols import VariantFeatureConfigType
from variantlib.validators.base import validate_matches_re
from variantlib.validators.base import validate_type

if TYPE_CHECKING:
    from collections.abc import Callable

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

    _plugins: dict[str, PluginType] | None = None
    _plugin_api_values: dict[str, str] | None = None
    _python_ctx: BasePythonEnv | None = None

    def __init__(self, python_ctx: BasePythonEnv | None = None) -> None:
        self._python_ctx = python_ctx

    def __enter__(self) -> Self:
        if self._python_ctx is None:
            raise RuntimeError("Impossible to load plugins outside a Python Context")

        self._load_all_plugins()

        return self

    def __exit__(self, *args: object) -> None:
        self._plugin_api_values = None
        self._plugins = None

        if self._python_ctx is None:
            logger.warning("The Python installer is None. Should not happen.")
            return

        self._python_ctx.__exit__()
        self._python_ctx = None

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

    def _load_plugin(self, plugin_api: str) -> PluginType:
        """Load a specific plugin"""

        if self._python_ctx is None:
            raise RuntimeError("Impossible to load plugins outside a Python Context")

        plugin_api_match = validate_matches_re(
            plugin_api, VALIDATION_PROVIDER_PLUGIN_API_REGEX
        )
        try:
            import_name: str = plugin_api_match.group("module")

            if isinstance(self._python_ctx, ISOLATED_PYTHON_ENVS):
                # We need to load the module first to allow `importlib` to find it
                pkg_name = import_name.split(".", maxsplit=1)[0]
                spec = PathFinder.find_spec(
                    pkg_name, path=[str(self._python_ctx.package_dir)]
                )
                if spec is None or spec.loader is None:
                    raise ModuleNotFoundError  # noqa: TRY301

                _module = importlib.util.module_from_spec(spec)
                spec.loader.exec_module(_module)
                sys.modules[pkg_name] = _module

            # We load the complete module
            module = importlib.import_module(import_name)

            attr_chain = plugin_api_match.group("attr").split(".")
            plugin_callable = reduce(getattr, attr_chain, module)

        except Exception as exc:
            raise PluginError(
                f"Loading the plugin from {plugin_api!r} failed: {exc}"
            ) from exc

        logger.info(
            "Loading plugin via %(plugin_api)s",
            {
                "plugin_api": plugin_api,
            },
        )

        if not callable(plugin_callable):
            raise PluginError(
                f"{plugin_api!r} points at a value that is not callable: "
                f"{plugin_callable!r}"
            )

        try:
            # Instantiate the plugin
            plugin_instance = plugin_callable()
        except Exception as exc:
            raise PluginError(
                f"Instantiating the plugin from {plugin_api!r} failed: {exc}"
            ) from exc

        required_attributes = PluginType.__abstractmethods__
        if missing_attributes := required_attributes.difference(dir(plugin_instance)):
            raise PluginError(
                f"Instantiating the plugin from {plugin_api!r} "
                "returned an object that does not meet the PluginType prototype: "
                f"{plugin_instance!r} (missing attributes: "
                f"{', '.join(sorted(missing_attributes))})"
            )

        return plugin_instance

    def load_plugin(self, plugin_api: str) -> PluginType:
        plugin_instance = self._load_plugin(plugin_api)

        if self._plugins is None:
            self._plugins = {}
        if self._plugin_api_values is None:
            self._plugin_api_values = {}

        if plugin_instance.namespace in self._plugins:
            raise RuntimeError(
                "Two plugins found using the same namespace "
                f"{plugin_instance.namespace}. Refusing to proceed."
            )

        self._plugins[plugin_instance.namespace] = plugin_instance
        self._plugin_api_values[plugin_instance.namespace] = plugin_api

        return plugin_instance

    @abstractmethod
    def _load_all_plugins(self) -> None: ...

    def _load_all_plugins_from_tuple(self, plugin_apis: list[str]) -> None:
        if self._plugins is not None:
            raise RuntimeError(
                "Impossible to load plugins - `self._plugins` is not None"
            )

        for plugin_api in plugin_apis:
            try:
                self.load_plugin(plugin_api=plugin_api)
            except PluginError:  # noqa: PERF203
                logger.debug("Impossible to load `%s`", plugin_api)

    def _call(self, method: Callable[[], Any]) -> Any:
        """Call plugin method and verify the return type"""

        value = method()

        try:
            validate_type(value, get_type_hints(method)["return"])
        except ValidationError as err:
            assert isinstance(method, MethodType)
            plugin_instance = method.__self__
            assert isinstance(plugin_instance, PluginType)
            raise TypeError(
                f"Provider {plugin_instance.namespace}, {method.__func__.__name__}() "
                f"method returned incorrect type. {err}"
            ) from None

        return value

    def get_supported_configs(self) -> dict[str, ProviderConfig]:
        """Get a mapping of namespaces to supported configs"""
        if self._python_ctx is None:
            raise RuntimeError("Impossible to load plugins outside a Python Context")

        provider_cfgs = {}
        for namespace, plugin_instance in self.plugins.items():
            vfeat_configs: list[VariantFeatureConfigType] = self._call(
                plugin_instance.get_supported_configs
            )

            # skip providers that do not return any supported configs
            if not vfeat_configs:
                continue

            provider_cfgs[namespace] = ProviderConfig(
                plugin_instance.namespace,
                configs=[
                    VariantFeatureConfig(name=vfeat_cfg.name, values=vfeat_cfg.values)
                    for vfeat_cfg in vfeat_configs
                ],
            )

        return provider_cfgs

    def get_all_configs(self) -> dict[str, ProviderConfig]:
        """Get a mapping of namespaces to all valid configs"""
        if self._python_ctx is None:
            raise RuntimeError("Impossible to load plugins outside a Python Context")

        provider_cfgs = {}
        for namespace, plugin_instance in self.plugins.items():
            vfeat_configs = self._call(plugin_instance.get_all_configs)

            if not vfeat_configs:
                raise ValueError(
                    f"Provider {namespace}, get_all_configs() method returned no valid "
                    "configs"
                )

            provider_cfgs[namespace] = ProviderConfig(
                plugin_instance.namespace,
                configs=[
                    VariantFeatureConfig(name=vfeat_cfg.name, values=vfeat_cfg.values)
                    for vfeat_cfg in vfeat_configs
                ],
            )

        return provider_cfgs

    def get_build_setup(self, properties: VariantDescription) -> dict[str, list[str]]:
        """Get build variables for a variant made of specified properties"""
        if self._python_ctx is None:
            raise RuntimeError("Impossible to load plugins outside a Python Context")

        ret_env: dict[str, list[str]] = {}
        for namespace, p_props in groupby(
            sorted(properties.properties), lambda prop: prop.namespace
        ):
            if (plugin := self.plugins.get(namespace)) is None:
                raise PluginMissingError(f"No plugin found for namespace {namespace}")

            if hasattr(plugin, "get_build_setup"):
                plugin_env = plugin.get_build_setup(list(p_props))

                try:
                    validate_type(plugin_env, dict[str, list[str]])
                except ValidationError as err:
                    raise TypeError(
                        f"Provider {namespace}, get_build_setup() "
                        f"method returned incorrect type. {err}"
                    ) from None
            else:
                plugin_env = {}

            for k, v in plugin_env.items():
                ret_env.setdefault(k, []).extend(v)
        return ret_env

    @property
    def plugins(self) -> dict[str, PluginType]:
        if self._python_ctx is None:
            raise RuntimeError("Impossible to load plugins outside a Python Context")
        if self._plugins is None:
            raise NoPluginFoundError("No plugin has been loaded in the environment.")
        return self._plugins

    @property
    def plugin_api_values(self) -> dict[str, str]:
        if self._python_ctx is None:
            raise RuntimeError("Impossible to load plugins outside a Python Context")
        if self._plugin_api_values is None:
            raise NoPluginFoundError("No plugin has been loaded in the environment.")
        return self._plugin_api_values

    @property
    def namespaces(self) -> list[str]:
        return list(self.plugins.keys())


class PluginLoader(BasePluginLoader):
    _variant_nfo: VariantMetadata

    def __init__(
        self,
        variant_nfo: VariantMetadata,
        python_ctx: BasePythonEnv | None = None,
    ) -> None:
        self._variant_nfo = variant_nfo
        super().__init__(python_ctx=python_ctx)

    def __enter__(self) -> Self:
        if self._python_ctx is None:
            raise RuntimeError("Impossible to load plugins outside a Python Context")

        if isinstance(self._python_ctx, INSTALLER_PYTHON_ENVS):
            self._install_all_plugins()

        return super().__enter__()

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
        if self._plugins is not None:
            raise RuntimeError(
                "Impossible to load plugins - `self._plugins` is not None"
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

    def _load_all_plugins(self) -> None:
        if self._plugins is not None:
            raise RuntimeError(
                "Impossible to load plugins - `self._plugins` is not None"
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
                plugin_instance = self.load_plugin(plugin_api=ep.value)
            except PluginError:
                logger.debug("Impossible to load `%s`", ep)
            else:
                if ep.dist is not None:
                    self._plugin_provider_packages[plugin_instance.namespace] = ep.dist

    @property
    def plugin_provider_packages(self) -> dict[str, Distribution]:
        if self._plugins is None:
            raise NoPluginFoundError("No plugin has been loaded in the environment.")
        assert self._plugin_provider_packages is not None
        return self._plugin_provider_packages


class ManualPluginLoader(BasePluginLoader):
    """Load and query plugins"""

    _python_ctx: ExternalNonIsolatedPythonEnv

    def __init__(self) -> None:
        self._plugins = {}
        super().__init__(python_ctx=ExternalNonIsolatedPythonEnv().__enter__())

    def __enter__(self) -> Self:
        return self

    def __exit__(self, *args: object) -> None:
        self._plugins = {}

    def __del__(self) -> None:
        self._python_ctx.__exit__()

    def _load_all_plugins(self) -> None:
        raise NotImplementedError("This Plugin Loader doesn't support this behavior")
