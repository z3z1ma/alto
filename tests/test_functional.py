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


class TestRunAlto(unittest.TestCase):
    def setUp(self):
        self.path = os.path.join(os.path.dirname(__file__), os.urandom(4).hex())
        os.makedirs(self.path, exist_ok=True, mode=0o755)
        os.chdir(self.path)

    def tearDown(self):
        os.chdir(os.path.dirname(__file__))
        try:
            shutil.rmtree(self.path)
        except FileNotFoundError:
            pass

    def test_run_init(self):
        """Test running alto init"""
        self.assertEqual(main(["init", "--no-prompt"]), 0)
        self.assertTrue(os.path.exists(os.path.join(self.path, "alto.toml")))
        self.assertTrue(os.path.exists(os.path.join(self.path, "alto.secrets.toml")))

    def test_run_list(self):
        """Test running alto list"""
        self.assertEqual(main(["init", "--no-prompt"]), 0)
        self.assertEqual(main(["list"]), 0)

    def test_run_pipeline(self):
        """Test running an alto pipeline end to end"""
        self.assertEqual(main(["init", "--no-prompt"]), 0)
        self.assertTrue(os.path.exists(os.path.join(self.path, "alto.toml")))
        self.assertTrue(os.path.exists(os.path.join(self.path, "alto.secrets.toml")))
        self.assertEqual(main(["tap-carbon-intensity:target-jsonl"]), 0)


if __name__ == "__main__":
    unittest.main()
