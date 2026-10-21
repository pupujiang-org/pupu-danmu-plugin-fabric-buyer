# Fabric Buyer Python Worker

This package is the schema-v2 Python Worker release for `org.pupujiang.fabric-buyer`.
It targets host version `0.5.0b3` or newer, uses plugin API v2, and requires the
protocol-v3 Python SDK supplied by the host.

The Worker receives only its authorized session capabilities: `chat.read`,
`room.read`, `llm.generate`, and `session.config.read`. It returns a Candidate,
Silent, or typed failure. The host retains platform sending, pacing, room
reservation and settlement, and the Windows sandbox boundary.

This Worker source package does not itself enable ordinary desktop use. Product
availability still depends on the host's installed-package verification,
explicit session authorization, Run/Capture lifecycle wiring, and Windows
AppContainer plus Job gates.
