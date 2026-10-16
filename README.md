# 官方插件：布料买家

This is the official source repository for `org.pupujiang.fabric-buyer`. The package is MIT licensed and contains declarative personas, topic hints, and a low-trust prompt resource for fabric live rooms.

The package does not replace the host's existing fabric-specific strategy. Chinese-number parsing, text rejection, context evaluation, rolling quotas, and factual-claim classification remain host behavior until a separately reviewed, behavior-equivalent migration is complete. The Registry will list a version only after its Release asset and host compatibility have been reviewed.

## Python SDK reference

This repository currently builds a data-only ZIP, so its plugin package does not depend on or bundle the SDK. Host protocol and replay tooling use the standalone [Pupu Danmu Plugin SDK v0.2.0](https://github.com/pupujiang-org/pupu-danmu-plugin-sdk/releases/tag/v0.2.0). If a local Worker prototype is developed, pin that release in the separate development environment; it does not make the published data-only ZIP executable or safe for remote execution.

## Validate and build

Use Python 3.10 or newer:

```powershell
python scripts/package_plugins.py --check
python scripts/package_plugins.py --plugin fabric-buyer --output dist --expected-version 1.0.0
```

The package command writes `fabric-buyer-1.0.0.zip` and its `.sha256` sidecar to the output directory. These generated files are Release artifacts and must not be committed to this repository.

Use the `.sha256` asset attached to the GitHub Release when preparing a Registry entry. Locally generated ZIP bytes can differ across operating systems because ZIP metadata and compression implementations vary; the Release asset and its digest are authoritative.

## Publish

After an explicitly approved version is ready, push the matching `fabric-buyer-v<version>` tag. GitHub Actions builds the ZIP and checksum from that tag and publishes both assets to its GitHub Release. A separate reviewed Registry entry is required before the host market can offer the version.

## License

This source repository is MIT licensed. The plugin package includes the same MIT license text.
