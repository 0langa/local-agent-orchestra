"""Unit tests for tools.network.NetworkEnforcer — all mock-based, no real network calls."""

import socket
from unittest.mock import patch

import pytest

from tools.network import NetworkEnforcer, NetworkPolicy, NetworkViolation


class TestNetworkEnforcer:
    def test_network_disabled_blocks_all(self) -> None:
        enforcer = NetworkEnforcer(NetworkPolicy(allowed=False))
        with pytest.raises(NetworkViolation, match="disabled"):
            enforcer.validate("https://example.com")

    def test_http_scheme_blocked_when_https_only(self) -> None:
        enforcer = NetworkEnforcer(NetworkPolicy(allowed=True))
        with pytest.raises(NetworkViolation, match="scheme"):
            enforcer.validate("http://example.com")

    def test_https_scheme_allowed(self) -> None:
        enforcer = NetworkEnforcer(NetworkPolicy(allowed=True))
        with patch(
            "socket.getaddrinfo",
            return_value=[(2, 1, 6, "", ("93.184.216.34", 0))],
        ):
            enforcer.validate("https://example.com")

    @pytest.mark.parametrize("ip", ["192.168.1.1", "10.0.0.1", "127.0.0.1"])
    def test_private_ip_blocked(self, ip: str) -> None:
        enforcer = NetworkEnforcer(NetworkPolicy(allowed=True))
        with pytest.raises(NetworkViolation, match="private"):
            enforcer.validate(f"https://{ip}")

    def test_link_local_blocked(self) -> None:
        enforcer = NetworkEnforcer(
            NetworkPolicy(
                allowed=True,
                denied_hosts=("metadata.google.internal", "metadata*"),
            )
        )
        with pytest.raises(NetworkViolation, match="link-local"):
            enforcer.validate("https://169.254.1.1")

    def test_allowed_hosts_whitelist(self) -> None:
        enforcer = NetworkEnforcer(
            NetworkPolicy(allowed=True, allowed_hosts=("example.com",))
        )
        with patch(
            "socket.getaddrinfo",
            return_value=[(2, 1, 6, "", ("93.184.216.34", 0))],
        ):
            enforcer.validate("https://example.com")

        with pytest.raises(NetworkViolation, match="allowed hosts"):
            enforcer.validate("https://other.com")

    def test_denied_hosts_glob_pattern(self) -> None:
        enforcer = NetworkEnforcer(NetworkPolicy(allowed=True))
        with pytest.raises(NetworkViolation, match="denied"):
            enforcer.validate("https://metadata.google.internal")

    def test_dns_resolution_failure_strict_mode(self) -> None:
        enforcer = NetworkEnforcer(
            NetworkPolicy(allowed=True, policy_mode="strict")
        )
        with patch("socket.getaddrinfo", side_effect=socket.gaierror("DNS fail")):
            with pytest.raises(NetworkViolation, match="DNS resolution failed"):
                enforcer.validate("https://unresolvable.example.com")

    def test_dns_resolution_failure_advisory_mode(self) -> None:
        enforcer = NetworkEnforcer(
            NetworkPolicy(allowed=True, policy_mode="advisory")
        )
        with patch("socket.getaddrinfo", side_effect=socket.gaierror("DNS fail")):
            enforcer.validate("https://unresolvable.example.com")

    def test_public_ip_allowed(self) -> None:
        enforcer = NetworkEnforcer(NetworkPolicy(allowed=True))
        with patch(
            "socket.getaddrinfo",
            return_value=[(2, 1, 6, "", ("93.184.216.34", 0))],
        ):
            enforcer.validate("https://example.com")
