class VariantCache:
    """This class is not necessary today - can be used for finer cache control later."""

    def __init__(self):
        self.cache = None

    def __call__(self, func):
        def wrapper(*args, **kwargs):
            if self.cache is None:
                self.cache = func(*args, **kwargs)
            return self.cache

        return wrapper
