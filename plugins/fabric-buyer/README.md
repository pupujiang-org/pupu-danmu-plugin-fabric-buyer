# 官方插件：布料买家

This official package contains declarative role and topic resources. It does **not** replace the existing `buyer_cloth` Python strategy: Chinese-number parsing, text rejection, context evaluation, rolling quotas, and factual claim classification remain host algorithms until characterization and gold-set evidence proves a safe migration.

The released 1.1.0 package declares its topics with the v2 vocabulary (`format_version: 2`, stable ids plus match labels and aliases) and gives each role a `topic_interests` mapping. The host owns matching, relevance thresholds and every send decision; the package only states what a role cares about. Its minimum host version is 0.5.0b3.
