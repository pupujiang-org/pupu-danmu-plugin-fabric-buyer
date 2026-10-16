# 官方插件：布料买家

This is the official source repository for `org.pupujiang.fabric-buyer`. The package is MIT licensed and contains declarative personas, topic hints, and a low-trust prompt resource for fabric live rooms.

The package does not replace the host's existing fabric-specific runtime strategy. An independent deterministic Worker policy source is now tracked under `worker/` and checked against the host behavior corpus, but the official v1.0.0 ZIP remains data-only. The host keeps its existing policy until the code package, authorization flow, and migration gates are separately completed. The Registry will list a version only after its Release asset and host compatibility have been reviewed.

## Python SDK reference

The official package build remains data-only and does not depend on or bundle the SDK. The deterministic rules in `worker/` are development source; Worker replay uses the exact SDK development commit [`42407f8`](https://github.com/pupujiang-org/pupu-danmu-plugin-sdk/commit/42407f883c6db880002438b50333c5d55da523bb), which adds protocol v3 session configuration. This is not an SDK release. The Worker source is not included in any plugin ZIP and does not enable Registry installation or remote execution.

## Independent Worker rules (development source only)

The `worker/fabric_buyer/` tree contains independent fabric rules for the Issue #517 E2/E4 replay work. It imports no host domain modules and has no direct sender, network, or model-client access; model output is requested only through the SDK's host capability, while settlement remains host-owned. The fixed regression corpus under `tests/fixtures/` records the host policy behavior used for comparison.

`worker/fabric_buyer/entrypoint.py:run` is the local SDK Replay entrypoint. It receives only the SDK's bounded anonymous context, calls the host LLM capability when a host-issued opportunity is available, and filters generated text through the fabric policy. This source is for trusted local development and deterministic integration checks.

Install the exact SDK development commit used by these checks and run them with:

```powershell
python -m pip install -r worker/requirements.txt
python -m unittest discover -s tests -v
```

These checks cover the 138-candidate corpus, 16 objective-claim cases, existing context/persona/topic/participation/prompt/rolling-quota cases, and SDK Replay outcomes for persona selection, initiative gating, available/unavailable opportunities, capability denial, and policy rejection. They do not authorize executing a downloaded plugin. `scripts/package_plugins.py` only reads `plugins/<plugin>/`, so `worker/` remains outside the data-only release ZIP until the separate install, authorization, and execution gates are completed.

## Validate and build

The data-only package builder supports Python 3.10 or newer. Worker policy tests use Python 3.13, matching the host's current Worker runtime.


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
