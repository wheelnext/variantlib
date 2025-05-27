class TestPlugin:
    namespace = "installable_plugin"

    def get_all_configs(self) -> list:
        raise NotImplementedError

    def get_supported_configs(self) -> list:
        raise NotImplementedError
