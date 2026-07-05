import os
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest import TestCase
from unittest.mock import patch

from octopus_intelligence.config import Settings


class ConfigTests(TestCase):
    def test_named_secrets_are_loaded_without_becoming_output_configuration(self):
        with TemporaryDirectory() as directory:
            path = Path(directory) / "secrets.yaml"
            path.write_text(
                "oie_ha_token: ha-secret\n"
                "oie_openai_api_key: ai-secret\n"
                "oie_openai_model: economical-model\n"
                "unrelated_password: do-not-use\n",
                encoding="utf-8",
            )
            with patch.dict(
                os.environ,
                {"OIE_SECRETS_FILE": str(path)},
                clear=True,
            ):
                settings = Settings.from_environment()

        self.assertEqual(settings.ha_token, "ha-secret")
        self.assertEqual(settings.openai_api_key, "ai-secret")
        self.assertEqual(settings.openai_model, "economical-model")
        self.assertNotIn("ha-secret", repr(settings))
        self.assertNotIn("ai-secret", repr(settings))
        self.assertNotIn("do-not-use", repr(settings))

    def test_environment_takes_precedence_over_secrets_file(self):
        with TemporaryDirectory() as directory:
            path = Path(directory) / "secrets.yaml"
            path.write_text("oie_ha_token: file-token\n", encoding="utf-8")
            with patch.dict(
                os.environ,
                {"OIE_SECRETS_FILE": str(path), "HA_TOKEN": "environment-token"},
                clear=True,
            ):
                settings = Settings.from_environment()

        self.assertEqual(settings.ha_token, "environment-token")
