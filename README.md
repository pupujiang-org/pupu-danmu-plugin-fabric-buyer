# 官方插件：布料买家

This MIT-licensed repository maintains two releases for the official plugin id `org.pupujiang.fabric-buyer`:

| Release | Source | Version | Runtime |
| --- | --- | --- | --- |
| Declarative data package | `plugins/fabric-buyer/` | `1.2.0` | Manifest v1, data only |
| Python Worker package | `worker/` | `1.3.0` | Manifest v2, Python Worker API v2 |

The catalog identifies a release by plugin id and exact version. The two runtime versions can therefore coexist without changing the existing declarative release. The Worker does not replace the host's fabric policy implementation.

## Python SDK and capabilities

Worker replay uses the official [Python SDK v0.3.0 Release](https://github.com/pupujiang-org/pupu-danmu-plugin-sdk/releases/tag/v0.3.0), pinned by the wheel SHA-256 in `worker/requirements.txt`. The Worker source is not bundled with the SDK and has no direct sender, network, or model-client access.

The schema-v2 manifest requests `chat.read`, `room.read`, `llm.generate`, and `session.config.read`. The host supplies per-session capabilities and retains platform sending, pacing, room reservation and settlement, package provenance checks, and Windows AppContainer plus Job isolation. Publishing this ZIP does not by itself expose Worker selection in the desktop UI or authorize a session.

## Validate and package

Use Python 3.13 for Worker checks:

```powershell
python -m pip install -r worker/requirements.txt
python scripts/package_plugins.py --check
python scripts/package_worker.py --check --expected-version 1.3.0
python -m unittest discover -s tests -v
```

The Worker package builder reads and parses source files but never imports or executes them. It writes a deterministic `fabric-buyer-1.3.0.zip` and a `.sha256` sidecar when asked to build:

```powershell
python scripts/package_worker.py --output dist-worker --expected-version 1.3.0
```

The declarative v1.2.0 package remains separately buildable with `scripts/package_plugins.py`. Generated ZIPs and checksum files are Release assets and must not be committed.

## Release and Registry

Push the matching `fabric-buyer-v1.3.0` tag only after the package tests and validation pass. The release workflow builds from that tag and publishes the exact ZIP and checksum as Release assets. The Registry entry must use the official Release URL, exact byte size, SHA-256, Worker manifest, and reviewed minimum host version; the builder statically validates the package and does not execute it.

The source repository is MIT licensed. The Worker ZIP includes the same MIT license text.
