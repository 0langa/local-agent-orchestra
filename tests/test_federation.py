from __future__ import annotations

from federation import (
    CapabilityAdvertisement,
    DiscoveryRequest,
    FederationProtocol,
    ResultRelay,
    TaskDelegation,
)


class TestMessageSerialization:
    def test_discovery_request_roundtrip(self) -> None:
        original = DiscoveryRequest(peer_id="p1", nonce="abc123")
        data = original.to_json()
        restored = DiscoveryRequest.from_json(data)
        assert restored.peer_id == "p1"
        assert restored.nonce == "abc123"

    def test_capability_advertisement_roundtrip(self) -> None:
        original = CapabilityAdvertisement(
            peer_id="p1",
            capabilities=["reasoning", "coding"],
            public_key_fingerprint="fp123",
        )
        data = original.to_json()
        restored = CapabilityAdvertisement.from_json(data)
        assert restored.capabilities == ["reasoning", "coding"]
        assert restored.public_key_fingerprint == "fp123"

    def test_task_delegation_roundtrip(self) -> None:
        original = TaskDelegation(
            task_id="t1",
            from_peer="p1",
            to_peer="p2",
            payload={"cmd": "test"},
        )
        data = original.to_json()
        restored = TaskDelegation.from_json(data)
        assert restored.task_id == "t1"
        assert restored.payload == {"cmd": "test"}

    def test_result_relay_roundtrip(self) -> None:
        original = ResultRelay(
            task_id="t1",
            from_peer="p2",
            to_peer="p1",
            success=True,
            data="ok",
        )
        data = original.to_json()
        restored = ResultRelay.from_json(data)
        assert restored.success is True
        assert restored.data == "ok"


class TestFederationProtocol:
    def test_trust(self) -> None:
        proto = FederationProtocol(peer_id="self", trusted_peers=["p1"])
        assert proto.is_trusted("p1") is True
        assert proto.is_trusted("p2") is False

    def test_trust_and_untrust(self) -> None:
        proto = FederationProtocol(peer_id="self")
        assert proto.is_trusted("p1") is False
        proto.trust("p1")
        assert proto.is_trusted("p1") is True
        proto.untrust("p1")
        assert proto.is_trusted("p1") is False

    def test_fingerprint_public_key(self) -> None:
        fp = FederationProtocol.fingerprint_public_key("-----BEGIN KEY-----\nabc\n-----END KEY-----")
        assert len(fp) == 16
        assert all(c in "0123456789abcdef" for c in fp)
