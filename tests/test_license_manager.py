"""
tests/test_license_manager.py — Unit Tests for ANSH 3-Day Trial and Licensing Engine
"""
import unittest
import json
import time
import tempfile
import shutil
from pathlib import Path

from core.license_manager import LicenseManager
from keys.generate_keys import generate_product_key, hash_key


class TestLicenseManager(unittest.TestCase):
    def setUp(self):
        self.temp_dir = Path(tempfile.mkdtemp())
        self.license_file = self.temp_dir / "license.json"
        self.keys_hash_file = self.temp_dir / "valid_keys.json"

        # Generate sample valid key
        self.sample_key = generate_product_key()
        self.sample_hash = hash_key(self.sample_key)

        self.keys_hash_file.write_text(
            json.dumps({"valid_hashes": {self.sample_hash: True}}, indent=2),
            encoding="utf-8"
        )

        self.mgr = LicenseManager()
        self.mgr.license_file = self.license_file
        self.mgr.keys_hash_file = self.keys_hash_file
        self.mgr._ensure_license_file()

    def tearDown(self):
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_fresh_install_trial(self):
        is_active, rem, msg = self.mgr.get_trial_status()
        self.assertTrue(is_active)
        self.assertTrue(rem > 250000)
        self.assertIn("Remaining", msg)
        self.assertTrue(self.mgr.is_license_valid())

    def test_expired_trial(self):
        # Set launch time to 4 days ago (4 * 86400 = 345,600)
        lic = self.mgr._load_license()
        lic["first_launch_time"] = time.time() - (4 * 86400)
        self.mgr._save_license(lic)

        is_active, rem, msg = self.mgr.get_trial_status()
        self.assertFalse(is_active)
        self.assertEqual(rem, 0.0)
        self.assertIn("Expired", msg)
        self.assertFalse(self.mgr.is_license_valid())

    def test_key_activation(self):
        # Expire trial first
        lic = self.mgr._load_license()
        lic["first_launch_time"] = time.time() - (4 * 86400)
        self.mgr._save_license(lic)

        # Invalid key attempt
        success, err = self.mgr.activate_product_key("ANSH-INVALID-KEY-1234")
        self.assertFalse(success)
        self.assertIn("Invalid", err)

        # Valid key activation
        success, msg = self.mgr.activate_product_key(self.sample_key)
        self.assertTrue(success)
        self.assertIn("activated successfully", msg)
        self.assertTrue(self.mgr.is_license_valid())


if __name__ == "__main__":
    unittest.main()
