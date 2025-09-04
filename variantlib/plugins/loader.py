from __future__ import annotations

import dataclasses
import importlib
import importlib.resources
import json
import logging
import subprocess
import sys
from abc import abstractmethod
from collections.abc import Collection
from pathlib import Path
from tempfile import TemporaryDirectory
from typing import TYPE_CHECKING
from typing import Any
from typing import cast

from packaging.markers import Marker
from packaging.markers import default_environment
from variantlib.constants import VALIDATION_PROVIDER_PLUGIN_API_REGEX
from variantlib.errors import NoPluginFoundError
from variantlib.errors import PluginError
from variantlib.models.provider import ProviderConfig
from variantlib.models.provider import VariantFeatureConfig
from variantlib.models.variant import VariantProperty
from variantlib.models.variant import VariantValidationResult
from variantlib.models.variant_info import PluginUse
from variantlib.validators.base import validate_matches_re

if TYPE_CHECKING:
    from types import TracebackType

    from variantlib.models.variant_info import ProviderInfo
    from variantlib.models.variant_info import VariantInfo
    from variantlib.protocols import VariantFeatureName
    from variantlib.protocols import VariantFeatureValue
    from variantlib.protocols import VariantNamespace

from importlib.metadata import Distribution
from importlib.metadata import entry_points

if sys.version_info >= (3, 11):
    from typing import Self
else:
    from typing_extensions import Self

logger = logging.getLogger(__name__)


class BasePluginLoader:
    """Load and query plugins"""

    _namespace_map: dict[str, VariantNamespace] | None = None
    _python_executable: Path

    def __init__(
        self,
        venv_python_executable: Path | None = None,
        package_defined_properties: dict[
            VariantNamespace, dict[VariantFeatureName, list[VariantFeatureValue]]
        ]
        | None = None,
    ) -> None:
        self._python_executable = (
            venv_python_executable
            if venv_python_executable is not None
            else Path(sys.executable)
        )
        self._package_defined_properties = package_defined_properties or {}

    def __enter__(self) -> Self:
        if self._namespace_map is not None:
            raise RuntimeError("Already inside the context manager!")
        self._load_all_plugins()
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc_value: BaseException | None,
        traceback: TracebackType | None,
    ) -> None:
        if self._namespace_map is None:
            raise RuntimeError("Context manager not entered!")
        self._namespace_map = None

    def _call_subprocess(
        self, plugin_apis: list[str], commands: dict[str, Any]
    ) -> dict[str, Any]:
        with TemporaryDirectory(prefix="variantlib") as temp_dir:
            # Copy `variantlib/plugins/loader.py` into the temp_dir
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

            # Copy `variantlib/protocols.py` into the temp_dir
            (Path(temp_dir) / "_variantlib_protocols.py").write_bytes(
                (importlib.resources.files("variantlib") / "protocols.py").read_bytes()
            )

            # Copy `variantlib/validators/base.py` into the temp_dir
            (Path(temp_dir) / "_variantlib_validators_base.py").write_bytes(
                (
                    importlib.resources.files("variantlib.validators") / "base.py"
                ).read_bytes()
            )

            args = []
            for plugin_api in plugin_apis:
                args += ["--plugin-api", plugin_api]

            process = subprocess.run(  # noqa: S603
                [self._python_executable, script, *args],
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
        if self._namespace_map is not None:
            raise RuntimeError(
                "Impossible to load plugins - `self._namespace_map` is not None"
            )
        self._namespace_map = {}

        if not plugin_apis:
            return

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
        if self._namespace_map is None:
            raise NoPluginFoundError("No plugin has been loaded in the environment.")

    def get_supported_configs(
        self,
    ) -> dict[str, ProviderConfig]:
        """Get a mapping of namespaces to supported configs"""
        self._check_plugins_loaded()
        assert self._namespace_map is not None

        # grab supported values from PDP if we don't have the relevant
        # plugin loaded
        provider_cfgs = {
            namespace: ProviderConfig(
                namespace=namespace,
                configs=[
                    VariantFeatureConfig(name=name, values=values)
                    for name, values in features.items()
                ],
            )
            for namespace, features in self._package_defined_properties.items()
            if namespace not in self._namespace_map.values() and features
        }

        if not self._namespace_map:
            return provider_cfgs

        configs = self._call_subprocess(
            list(self._namespace_map.keys()),
            {"get_supported_configs": {}},
        )["get_supported_configs"]

        for plugin_api, plugin_configs in configs.items():
            namespace = self._namespace_map[plugin_api]

            if not plugin_configs:
                continue

            provider_cfgs[namespace] = ProviderConfig(
                namespace,
                configs=[
                    VariantFeatureConfig(**vfeat_cfg) for vfeat_cfg in plugin_configs
                ],
            )

        return provider_cfgs

    def validate_properties(
        self, properties: Collection[VariantProperty]
    ) -> VariantValidationResult:
        self._check_plugins_loaded()
        assert self._namespace_map is not None

        ret: dict[VariantProperty, bool | None] = {}
        plugin_properties = []
        for vprop in properties:
            if vprop.namespace in self._namespace_map.values():
                # use the plugin if loaded
                plugin_properties.append(vprop)
            elif vprop.namespace in self._package_defined_properties:
                # otherwise, look it up in PDP
                ret[vprop] = vprop.value in self._package_defined_properties.get(
                    vprop.namespace, {}
                ).get(vprop.feature, set())
            else:
                # if it's not in PDP either, it's "unknown"
                ret[vprop] = None

        if not self._namespace_map:
            # short-circuit plugin_properties if we have no plugins loaded
            ret.update(dict.fromkeys(plugin_properties))
        elif plugin_properties:
            # call to the plugin if we have any plugin_properties left
            json_results = self._call_subprocess(
                list(self._namespace_map.keys()),
                {
                    "validate_properties": {
                        "properties": [
                            dataclasses.asdict(vprop) for vprop in plugin_properties
                        ]
                    }
                },
            )["validate_properties"]
            ret.update(
                {VariantProperty(**vprop): result for vprop, result in json_results}
            )

        return VariantValidationResult(ret)

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
        venv_python_executable: Path | None = None,
        enable_optional_plugins: bool | list[VariantNamespace] = False,
        filter_plugins: list[VariantNamespace] | None = None,
        include_build_plugins: bool = False,
    ) -> None:
        self._variant_info = variant_info
        self._enable_optional_plugins = enable_optional_plugins
        self._filter_plugins = filter_plugins
        self._environment = cast("dict[str, str]", default_environment())
        self._include_build_plugins = include_build_plugins
        super().__init__(
            venv_python_executable=venv_python_executable,
            package_defined_properties=variant_info.get_package_defined_properties(
                self._get_namespaces_for_package_defined_properties()
            ),
        )

    def _get_namespaces_for_package_defined_properties(self) -> set[VariantNamespace]:
        return {
            namespace
            for namespace, provider_data in self._variant_info.providers.items()
            if provider_data.plugin_use == PluginUse.NONE
            or (
                provider_data.plugin_use == PluginUse.BUILD
                and not self._include_build_plugins
            )
        }

    def _optional_provider_enabled(self, namespace: str) -> bool:
        # if enable_optional_plugins is a bool, it controls all plugins
        if self._enable_optional_plugins in (False, True):
            assert isinstance(self._enable_optional_plugins, bool)
            return self._enable_optional_plugins
        # otherwise, it's a list of enabled namespaces
        assert isinstance(self._enable_optional_plugins, Collection)
        return namespace in self._enable_optional_plugins

    def _provider_enabled(self, namespace: str, provider_data: ProviderInfo) -> bool:
        if provider_data.plugin_use == PluginUse.NONE:
            return False
        if (
            provider_data.plugin_use == PluginUse.BUILD
            and not self._include_build_plugins
        ):
            return False

        if self._filter_plugins is not None and namespace not in self._filter_plugins:
            return False

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

    def validate_properties(
        self, properties: Collection[VariantProperty]
    ) -> VariantValidationResult:
        assert self._include_build_plugins, (
            "To use validate_properties(), use PluginLoader(include_build_plugins=True)"
        )

        return super().validate_properties(properties)


class EntryPointPluginLoader(BasePluginLoader):
    _plugin_provider_packages: dict[str, Distribution] | None = None

    def __init__(
        self,
        venv_python_executable: Path | None = None,
    ) -> None:
        super().__init__(venv_python_executable=venv_python_executable)

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
        venv_python_executable: Path | None = None,
    ) -> None:
        self._plugin_apis = list(plugin_apis)
        super().__init__(venv_python_executable=venv_python_executable)

    def _load_all_plugins(self) -> None:
        if self._namespace_map is not None:
            raise RuntimeError(
                "Impossible to load plugins - `self._namespace_map` is not None"
            )

        self._load_all_plugins_from_tuple(plugin_apis=self._plugin_apis)
