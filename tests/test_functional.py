# MIT License
# Copyright (c) 2023 Alex Butler
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in all
# copies or substantial portions of the Software.
"""Functional tests for alto"""
import os
import shutil
import unittest
import warnings

from alto import main

# Ignore warnings from vendored packages
warnings.filterwarnings("ignore", category=ImportWarning, message="VendorImporter.find_spec().*")
warnings.filterwarnings("ignore", category=ImportWarning, message="_Loader.exec_module().*")


def _make_tmp_dir():
    """Make a temporary directory for testing"""
    path = os.path.join(os.path.dirname(__file__), os.urandom(4).hex())
    os.makedirs(path, exist_ok=True, mode=0o755)
    return path


class TestRunAlto(unittest.TestCase):
    def test_run_init(self):
        """Test running alto init"""
        try:
            path = _make_tmp_dir()
            self.assertEqual(main(["init", "--no-prompt", "-r", path]), 0)
            self.assertTrue(os.path.exists(os.path.join(path, "alto.toml")))
            self.assertTrue(os.path.exists(os.path.join(path, "alto.local.toml")))
        finally:
            shutil.rmtree(path)

    def test_run_list(self):
        """Test running alto list"""
        try:
            path = _make_tmp_dir()
            self.assertEqual(main(["init", "--no-prompt", "-r", path]), 0)
            self.assertEqual(main(["list", "-r", path]), 0)
        finally:
            shutil.rmtree(path)

    def test_run_pipeline(self):
        """Test running an alto pipeline end to end"""
        try:
            path = _make_tmp_dir()
            self.assertEqual(main(["init", "--no-prompt", "-r", path]), 0)
            self.assertTrue(os.path.exists(os.path.join(path, "alto.toml")))
            self.assertTrue(os.path.exists(os.path.join(path, "alto.local.toml")))
            self.assertEqual(main(["tap-carbon-intensity:target-jsonl", "-r", path]), 0)
        finally:
            shutil.rmtree(path)


if __name__ == "__main__":
    unittest.main()
