import unittest


class RouterImportTests(unittest.TestCase):
    def test_router_imports_without_httpx(self):
        import importlib
        module = importlib.import_module("core.router")
        self.assertTrue(hasattr(module, "AIRouter"))


if __name__ == "__main__":
    unittest.main()
