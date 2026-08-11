"""Authentication modes test suite.

Verifies:
1. When LOCAL_AUTH_DISABLED=True (AuthMode.NONE), all endpoints allow access as local_admin without login cookies/tokens.
2. When LOCAL_AUTH_DISABLED=False (AuthMode.PASSWORD), protected endpoints enforce authentication and return HTTP 401 when unauthenticated.
"""

import unittest
from unittest.mock import patch

from fastapi.testclient import TestClient
from cptr.app import app
from cptr.utils.config import AuthMode, AuthResult, check_access, get_auth_mode


class TestAuthModesInconsistencyFix(unittest.TestCase):
    """Test suite for authentication mode enforcement and consistency."""

    def test_auth_mode_none_check_access(self):
        """Verify check_access returns AuthResult with local_admin identity when AuthMode.NONE is active."""
        with patch("cptr.utils.config.get_auth_mode", return_value=AuthMode.NONE):
            auth = check_access(client_host="127.0.0.1", jwt_token=None)
            self.assertIsNotNone(auth)
            self.assertEqual(auth.user_id, "local_admin")
            self.assertEqual(auth.username, "local_admin")
            self.assertEqual(auth.role, "admin")

    def test_auth_mode_none_endpoints_allow_access(self):
        """Verify protected API endpoints succeed (not 401) when LOCAL_AUTH_DISABLED=True."""
        client = TestClient(app)

        with patch("cptr.env.LOCAL_AUTH_DISABLED", True), \
             patch("cptr.utils.config.get_auth_mode", return_value=AuthMode.NONE):

            # 1. GET /api/auth
            res_auth = client.get("/api/auth")
            self.assertEqual(res_auth.status_code, 200)
            data_auth = res_auth.json()
            self.assertTrue(data_auth.get("authenticated"))
            self.assertEqual(data_auth.get("username"), "local_admin")

            # 2. GET /api/config
            res_cfg = client.get("/api/config")
            self.assertEqual(res_cfg.status_code, 200)
            data_cfg = res_cfg.json()
            self.assertEqual(data_cfg.get("auth_mode"), "none")
            self.assertFalse(data_cfg.get("needs_setup"))

            # 3. GET /api/chats/models (previously returned 401)
            res_models = client.get("/api/chats/models")
            self.assertNotEqual(res_models.status_code, 401)

            # 4. GET /api/audio/state (previously returned 401)
            res_audio = client.get("/api/audio/state")
            self.assertNotEqual(res_audio.status_code, 401)

            # 5. GET /api/state/welcome
            res_welcome = client.get("/api/state/welcome")
            self.assertNotEqual(res_welcome.status_code, 401)

    def test_auth_mode_password_enforces_protection(self):
        """Verify protected endpoints return HTTP 401 when LOCAL_AUTH_DISABLED=False and no session cookie is provided."""
        client = TestClient(app)

        with patch("cptr.env.LOCAL_AUTH_DISABLED", False), \
             patch("cptr.utils.config.get_auth_mode", return_value=AuthMode.PASSWORD):

            # GET /api/chats/models unauthenticated -> 401
            res_models = client.get("/api/chats/models")
            self.assertEqual(res_models.status_code, 401)

    def test_sofie_connection_has_provider(self):
        """Verify _get_connections always populates provider='openai' for Sofie connection."""
        import asyncio
        from cptr.routers.chat import _get_connections

        with patch("os.getenv", side_effect=lambda key, default=None: "fake_key" if key == "SOFIE_API_KEY" else default):
            conns = asyncio.run(_get_connections())
            sofie_conn = next((c for c in conns if c.get("id") == "sofie"), None)
            self.assertIsNotNone(sofie_conn)
            self.assertIn("provider", sofie_conn)
            self.assertEqual(sofie_conn["provider"], "openai")


if __name__ == "__main__":
    unittest.main()
