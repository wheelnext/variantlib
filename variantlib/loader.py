from __future__ import annotations

import importlib
import importlib.util
import logging
import pathlib
import sys
from functools import reduce
from itertools import groupby
from types import MethodType
from typing import TYPE_CHECKING
from typing import Any
from typing import get_type_hints

from variantlib.constants import VALIDATION_PROVIDER_PLUGIN_API_REGEX
from variantlib.errors import PluginError
from variantlib.errors import PluginMissingError
from variantlib.installer import BasePythonEnv
from variantlib.installer import IsolatedPythonEnv
from variantlib.installer import NonIsolatedPythonEnv
from variantlib.models.provider import ProviderConfig
from variantlib.models.provider import VariantFeatureConfig
from variantlib.protocols import PluginType
from variantlib.protocols import VariantFeatureConfigType
from variantlib.validators import ValidationError
from variantlib.validators import validate_matches_re
from variantlib.validators import validate_type

if TYPE_CHECKING:
    from typing import Callable

    from variantlib.models.variant import VariantDescription
    from variantlib.variants_json import VariantsJson

if sys.version_info >= (3, 11):
    from typing import Self

else:
    from typing_extensions import Self

logger = logging.getLogger(__name__)


class PluginLoader:
    """Load and query plugins"""

    _variant_nfo: VariantsJson
    _installer_ctx: BasePythonEnv | None = None
    _isolated: bool
    _plugins: dict[str, PluginType] = None

    def __init__(self, variant_nfo: VariantsJson, isolated: bool = True) -> None:
        self._variant_nfo = variant_nfo
        self._isolated = isolated

    def __enter__(self) -> Self:
        if self._installer_ctx is not None or self._plugins is not None:
            # We do not create nested python envs.
            logger.debug("Re-entering Python contexts is not supported.")
            return self

        PythonCtx = IsolatedPythonEnv if self._isolated else NonIsolatedPythonEnv

        self._installer_ctx = PythonCtx().__enter__()

        self._plugins = self._install_and_load_all_plugins()

        return self

    def __exit__(self, *args: object) -> None:
        if self._installer_ctx is None:
            logger.warning("The Python installer is None. Should not happen.")
            return

        self._plugins = None
        self._installer_ctx.__exit__()
        self._installer_ctx = None
        return

    def _install_and_load_all_plugins(self) -> dict[str, PluginType]:
        if self._installer_ctx is None or self._plugins is not None:
            raise RuntimeError(
                "Impossible to get supported configs outside of an installer context"
            )

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

            if not (req_str := provider_data.requires):
                logger.error(
                    "Impossible to install the variant provider plugin corresponding "
                    "to namespace `%(ns)s`. Missing provider requirement, "
                    "received: %(data)s.",
                    {"ns": namespace, "data": provider_data},
                )
                continue

            reqs.extend(req_str)

        # Actual plugin installation
        self._installer_ctx.install(reqs)

        plugins = {}
        for namespace in self._variant_nfo.namespace_priorities:
            plugin_instance = self._load_plugin(
                self._variant_nfo.providers[namespace].plugin_api
            )

            if plugin_instance.namespace in plugins:
                raise RuntimeError(
                    "Two plugins found using the same namespace "
                    f"{plugin_instance.namespace}. Refusing to proceed."
                )

            plugins[plugin_instance.namespace] = plugin_instance

        return plugins

    def _load_plugin(self, plugin_api: str) -> PluginType:
        """Load a specific plugin"""

        if self._installer_ctx is None:
            raise RuntimeError(
                "Impossible to load a plugin outside of an installer context"
            )

        plugin_api_match = validate_matches_re(
            plugin_api, VALIDATION_PROVIDER_PLUGIN_API_REGEX
        )
        try:
            import_name = plugin_api_match.group("module")
            if self._installer_ctx.python_executable is None:
                module = importlib.import_module(import_name)

            else:
                print(f"{pathlib.Path(self._installer_ctx.python_executable)=}")
                print(f"{pathlib.Path(self._installer_ctx.python_executable).parent=}")
                print(
                    f"{list(pathlib.Path(self._installer_ctx.python_executable).parent.parent.iterdir())=}"
                )
                spec = importlib.util.spec_from_file_location(
                    name=import_name,
                    location=pathlib.Path(
                        self._installer_ctx.python_executable
                    ).parent.parent,
                )
                module = importlib.util.module_from_spec(spec)

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
        if self._installer_ctx is None or self._plugins is None:
            raise RuntimeError("Impossible to access outside of an installer context")

        provider_cfgs = {}
        for namespace, plugin_instance in self._plugins.items():
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
        if self._installer_ctx is None or self._plugins is None:
            raise RuntimeError("Impossible to access outside of an installer context")

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
        if self._installer_ctx is None or self._plugins is None:
            raise RuntimeError("Impossible to access outside of an installer context")

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
