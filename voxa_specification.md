---
title: "Voxa Specification"
subtitle: "Technical Specification (Draft) v0.1.0"
author: "Benoit Delemps / Astrone"
date: "March 2026"
subject: "Specification Document"
keywords: [voxa, spec, protocol]

titlepage: true
titlepage-color: "003366"
titlepage-text-color: "FFFFFF"
titlepage-rule-color: "FFFFFF"
titlepage-rule-height: 2
---

# Scope

This specification defines the Voxa format, a structured, human-inspectable, machine-readable format for a versioned and traceable speech corpus or dataset. It covers:

- dataset-level schema
- corpus-level schema
- sample-level schema
- integrity and signature protocol
- standardized acoustic and descriptive metrics
- versioning and publication rules

The goals of Voxa are:

- reproducibility
- consistency
- traceability
- comparability

This specification is intentionally independent from audiometric calibration standards. It defines how a corpus is described and verified, not how a playback chain is calibrated.

This specification is intended for corpus creators, distributors, and consumers in speech synthesis and speech processing systems.

# Terminology

## Dataset
A dataset is a set of published Voxa corpora observed under one dataset root.

A dataset MAY contain multiple languages by publishing multiple corpora, one language per corpus.

## Corpus
A named, versioned collection of speech samples published as a single release.

A corpus is monolingual for metric and comparison purposes.

All samples referenced by a corpus version MUST use the same exact `language.bcp47` value as the corpus manifest.

## Sample
A single audio item and its associated metadata.

### Sample revision
An immutable published sample metadata record for a given `sample_id`.

Each `sample_revision` belongs to exactly one corpus version and references exactly one published audio asset.

The tuple `(sample_id, sample_revision)` identifies one immutable published sample record.

### Audio asset
A published audio binary that MAY be referenced by multiple sample revisions across corpus versions.

## Manifest
The canonical machine-readable, human-inspectable description of a dataset release or corpus release.

## Signature
A cryptographic proof attached to a manifest to verify authenticity.

## Hash
A cryptographic digest used to verify binary integrity.

## Corpus version
An immutable published manifest of a corpus.

## Core subset
A stable subset intended for long-term reference and comparison.

## Extended subset
An optional evolving subset that may grow across releases.

## Identity fields
Fields that determine whether two published objects represent the same logical corpus or sample.

## Dynamic fields
Fields that are expected to change across publications without changing logical identity, such as timestamps, hashes, signatures, and other derived integrity material.

## Derived fields
Fields computed from other published data or from analysis pipelines, such as metrics, hashes, signatures, and aggregate statistics.

---

# Design principles

## Immutability
A published corpus version MUST be immutable.

## Verifiability
Every published sample MUST be hash-verifiable.

## Provenance
Every sample MUST document its voice provenance. Synthetic voices MUST document their synthesis provenance.

## Comparability
Every corpus release SHOULD publish the same core metric set.

## Separation of levels
Dataset-level metadata, corpus-level metadata, and sample-level metadata MUST be explicitly separated.

## Extensibility
Implementations MAY add non-conflicting extension fields.

## Deterministic identity
Implementations MUST define dataset, corpus, and sample identity from a canonical metadata view rather than from storage paths or incidental runtime state.

## Canonical identity comparison
Identity MUST be evaluated by constructing a canonical identity view of the object, removing excluded fields defined by this specification, and comparing the remaining metadata exactly.

Object member ordering MUST NOT affect identity.

Array ordering remains identity-bearing unless a stricter profile defines otherwise.

---

# Packaging model

A Voxa corpus project SHOULD separate publication artifacts by destination:

- the dataset payload in its own directory so it can be published to Hugging Face
- the specification, code, and governance material in its own directory so it can be published to a GitHub repository

The recommended project structure is:

```text
<project-root>/
├── dataset/
│   ├── manifests/
│   │   ├── <version>/
│   │   │   ├── voxa.dataset.json
│   │   │   ├── checksums.txt
│   │   │   ├── manifest.sig
│   │   │   ├── LICENSE
│   │   │   └── README.md
│   │   └── ...
│   └── proxies/
│       ├── <version>/
│       │   ├── proxy_<proxy-id>.wav
│       │   └── ...
│       └── ...
├── <bcp47>/
│   ├── manifests/
│   │   ├── <version>/
│   │   │   ├── voxa.corpus.json
│   │   │   ├── checksums.txt
│   │   │   ├── manifest.sig
│   │   │   ├── LICENSE
│   │   │   └── README.md
│   │   └── ...
│   └── samples/
│       ├── metadata/
│       │   ├── <version>/
│       │   │   ├── <shard>/
│       │   │   │   ├── <sample-id>.<sample-revision>.json
│       │   │   │   └── ...
│       │   │   └── ...
│       │   └── ...
│       ├── audio/
│       │   ├── <shard>/
│       │   │   ├── aud_<bcp47>_<audio-hash>.wav
│       │   │   └── ...
│       │   └── ...
│       └── metrics/
│           ├── <shard>/
│           │   ├── ltas_<bcp47>_<hash>.json
│           │   └── ...
│           └── ...
└── repo/
    ├── specification/
    ├── code/
    └── governance/
```

The top-level language directory SHOULD use the exact corpus `language.bcp47` value.

The release directory under a language SHOULD use the corpus `version` value.

Example:

- `fr-FR/manifests/v1.0/`

All paths stored in Voxa manifests and sample metadata MUST be relative to the dataset root.

The dataset manifest SHOULD be stored under `dataset/manifests/<version>/voxa.dataset.json`.

Dataset-level calibration proxy assets SHOULD be stored under `dataset/proxies/<version>/`.

## Required files
A conforming corpus version manifest MUST contain:

- `voxa.corpus.json`
- integrity material sufficient to verify the release

A corpus manifest with `status = released` MUST additionally contain:

- `manifest.sig`

A multilingual dataset release MUST contain:

- `voxa.dataset.json`
- integrity material sufficient to verify the dataset manifest
- one dataset-level proxy audio file per dataset proxy signal entry

A dataset manifest with `status = released` MUST additionally contain:

- `manifest.sig`

A conforming dataset publication MUST make available:

- one metadata file per manifest sample entry
- one audio file per manifest sample entry

Metadata and audio files MAY be stored in separate dataset-root-relative directories.

Within a dataset root, multilingual publication SHOULD be modeled as one dataset manifest referencing multiple monolingual corpora rather than as one multilingual corpus.

## Incremental publication model
Voxa releases SHOULD evolve incrementally.

An implementation SHOULD publish:

- immutable manifests for each corpus version under `<bcp47>/manifests/`
- immutable dataset manifests under `dataset/manifests/` when multiple corpora are published together
- dataset-scoped proxy assets under `dataset/proxies/`
- versioned metadata under `<bcp47>/samples/metadata/`
- published audio assets under `<bcp47>/samples/audio/`

Republishing a sample in a new corpus version MUST create a new metadata file and a new `sample_revision`, even when the referenced audio file is unchanged.

Unchanged audio binaries MAY be reused across corpus versions by referencing the same published audio file from multiple sample revisions.

If a sample audio file changes, the publisher MUST create a new audio asset and MUST NOT overwrite the previously published audio file in place.

If a sample metadata file changes, the publisher MUST create a new sample revision and MUST NOT overwrite the previously published metadata file in place.

Within a dataset root, validators and publishers SHOULD treat all published manifests, metadata files, and audio assets as part of the same observable publication history.

## Optional files
A release MAY contain:

- `checksums.txt`
- LTAS plots
- validation reports
- changelog
- derived indexes

---

# Dataset-level schema

The dataset-level file is the canonical release manifest for a set of corpus releases that are intended to be used together.

## File name
The canonical file name MUST be `voxa.dataset.json`.

## Required fields
A dataset manifest MUST contain at least the following fields:

- `schema_version`
- `dataset_id`
- `name`
- `version`
- `created_at`
- `status`
- `release_root`
- `corpora`
- `calibration_profile`
- `proxy_signals`
- `integrity`

## Dataset object

```json
{
  "schema_version": "0.1.0",
  "dataset_id": "string",
  "name": "string",
  "description": "string",
  "version": "string",
  "created_at": "date-time",
  "updated_at": "date-time",
  "status": "draft | released | deprecated | archived",
  "release_root": "dataset/manifests/<version>/",
  "corpora": [
    {
      "corpus_id": "string",
      "corpus_version": "string",
      "language": {
        "bcp47": "string"
      },
      "manifest_path": "string",
      "manifest_hash": "string",
      "overall_rms_dbfs": -24.5,
      "reference_offset_db": -1.5
    }
  ],
  "calibration_profile": {
    "profile_id": "string",
    "method": "single_dataset_reference",
    "target_metric": "overall_rms_dbfs",
    "target_rms_dbfs": -23.0,
    "reference_scope": "dataset",
    "analysis_tolerance_db": 0.1,
    "parameters": {}
  },
  "proxy_signals": [
    {
      "proxy_id": "white-noise-dataset-reference",
      "kind": "white_noise",
      "target_metric": "overall_rms_dbfs",
      "rms_dbfs": -23.0,
      "duration_s": 30.0,
      "audio_path": "dataset/proxies/v1.0/proxy_white-noise-dataset-reference.wav",
      "audio_hash": "string"
    }
  ],
  "integrity": {
    "manifest_hash_algorithm": "sha256",
    "manifest_hash": "string",
    "signature_algorithm": "string",
    "public_key_id": "string"
  },
  "tags": ["string"],
  "extensions": {}
}
```

## Corpus references
Each dataset manifest MUST reference at least one corpus manifest.

Each corpus reference MUST include:

- `corpus_id`
- `corpus_version`
- `language.bcp47`
- `manifest_path`
- `manifest_hash`

`manifest_path` MUST be dataset-root-relative.

`manifest_hash` MUST equal the referenced corpus manifest `integrity.manifest_hash`.

Within a dataset manifest, the tuple `(corpus_id, corpus_version)` MUST be unique.

Each referenced corpus manifest MUST remain independently valid as a monolingual Voxa corpus.

If `overall_rms_dbfs` is present on a corpus reference, it MUST equal the referenced corpus manifest `corpus_statistics.overall_rms_dbfs`.

If `reference_offset_db` is present on a corpus reference, it MUST equal `overall_rms_dbfs - calibration_profile.target_rms_dbfs`.

## Calibration profile
`calibration_profile` describes how the dataset-level reference signal is intended to be used.

The calibration profile MUST be corpus-independent: it MUST NOT require a different reference signal or calibration procedure for each referenced corpus.

For `method = single_dataset_reference`, the dataset manifest MUST contain at least one proxy signal with:

- `kind = white_noise`
- `target_metric = overall_rms_dbfs`

For that white-noise proxy signal, `rms_dbfs` MUST equal `calibration_profile.target_rms_dbfs` within `calibration_profile.analysis_tolerance_db`.

The `reference_scope` value MUST be `dataset`.

The calibration profile defines a stable reference level. It MUST NOT be interpreted as requiring sample-level or corpus-level audio normalization.

Dataset-level calibration does not imply normalization. Referenced corpora retain their published audio levels.

Consumers SHOULD account for each corpus `reference_offset_db` when they need playback levels to be interpreted relative to the dataset reference.

## Dataset proxy signals
`proxy_signals` MUST describe the derived dataset-level proxy audio assets published with the dataset release.

Each dataset proxy signal entry MUST include:

- `proxy_id`
- `kind`
- `target_metric`
- `rms_dbfs`
- `duration_s`
- `audio_path`
- `audio_hash`

`audio_path` MUST be dataset-root-relative.

`audio_hash` MUST be the canonical integrity value for the published proxy audio asset.

`proxy_id` MUST be unique within the dataset manifest.

If `kind = white_noise`, the published proxy signal MUST be synthesized white noise.

For reproducibility, implementations SHOULD synthesize dataset-level white-noise proxies using a fixed documented format and a fixed documented random seed so that identical dataset states reproduce identical proxy bytes.

Dataset-level proxy signals are the RECOMMENDED calibration reference for multilingual Voxa publications.

## Dataset identity rules
Two dataset manifests represent the same logical dataset if and only if their canonical dataset identity views are equal.

A dataset release is uniquely identified by the tuple `(dataset_id, version)`.

`dataset_id` is a stable publisher-assigned identifier for a logical dataset.

Within a dataset root, `dataset_id` MUST be unique across logical datasets.

The canonical dataset identity view is formed from the dataset manifest after removing all fields listed below.

The following dataset fields are dynamic, derived, or version-scoped and MUST NOT be used to determine dataset identity:

- `dataset_id`
- `version`
- `created_at`
- `updated_at`
- `status`
- `release_root`
- `corpora`
- `calibration_profile`
- `proxy_signals`
- `integrity`

All remaining dataset metadata is identity-bearing.

Changing only excluded fields creates a different dataset release or publication state, but not a different logical dataset.

Within a dataset root, if two dataset manifests have the same canonical dataset identity view, they MUST use the same `dataset_id`.

Within a dataset root, if two dataset manifests have different canonical dataset identity views, they MUST NOT use the same `dataset_id`.

---

# Corpus-level schema

The corpus-level file is the canonical release manifest.

## File name
The canonical file name MUST be `voxa.corpus.json`.

## Required fields
A corpus manifest MUST contain at least the following fields:

- `schema_version`
- `corpus_id`
- `name`
- `version`
- `created_at`
- `status`
- `licenses`
- `language`
- `release_root`
- `integrity`
- `samples`

## Corpus object

```json
{
  "schema_version": "0.1.0",
  "corpus_id": "string",
  "name": "string",
  "description": "string",
  "version": "string",
  "created_at": "date-time",
  "updated_at": "date-time",
  "status": "draft | released | deprecated | archived",
  "release_root": "<bcp47>/manifests/<version>/",
  "licenses": [
    {
      "name": "CC-BY-SA-4.0",
      "url": "https://creativecommons.org/licenses/by-sa/4.0/",
      "usage": "open"
    },
    {
      "name": "Commercial",
      "url": "https://your-domain.example.com/licensing",
      "usage": "commercial"
    }
  ],
  "citation": {
    "title": "string",
    "authors": ["string"],
    "url": "uri"
  },
  "language": {
    "bcp47": "string"
  },
  "metric_pipeline": {
    "version": "string",
    "parameters": {}
  },
  "corpus_statistics": {},
  "proxy_signals": [
    {
      "proxy_id": "string",
      "kind": "white_noise",
      "target_metric": "overall_rms_dbfs",
      "rms_dbfs": 0.0,
      "duration_s": 0.0,
      "audio_path": "string",
      "audio_hash": "string"
    }
  ],
  "integrity": {
    "manifest_hash_algorithm": "sha256",
    "manifest_hash": "string",
    "signature_algorithm": "string",
    "public_key_id": "string"
  },
  "samples": [
    {
      "sample_id": "string",
      "sample_revision": "string",
      "metadata_path": "string",
      "metadata_hash": "string",
      "audio_path": "string",
      "audio_hash": "string"
    }
  ],
  "tags": ["string"],
  "extensions": {}
}
```

## Language fields
`language.bcp47` MUST be present.

The corpus `language.bcp47` value is the canonical language tag for the release.

Every referenced sample metadata record MUST use the same exact `language.bcp47` value.

## Sample references
A release MUST contain at most one sample entry for a given `sample_id`.

Each sample entry MUST identify the exact published sample revision it uses.

Each sample entry in `samples` MUST uniquely reference exactly one metadata file and one audio file.

The tuple `(sample_id, sample_revision)` MUST always resolve to the same metadata content and the same audio content.

`metadata_path` and `audio_path` MUST be dataset-root-relative paths.

`metadata_hash` and `audio_hash` in the manifest are the canonical signed integrity values for release verification.

`sample_revision` SHOULD be stable and monotonic for a given `sample_id`, for example `r1`, `r2`, `r3`.

If the same underlying utterance is published in multiple audio formats or encoding variants, each published format MUST be represented as a separate sample entry with its own distinct `sample_id`.

## Corpus statistics
If `corpus_statistics` is present, it SHOULD use the metric definitions from the metrics specification.

If metrics are published, the corpus manifest SHOULD document the computation pipeline in `metric_pipeline`.

Audio format is specified at the sample level, not the corpus level. A single corpus manifest MAY therefore reference samples with different containers or sampling parameters.

## Proxy signals
When present, `proxy_signals` MUST describe derived corpus-level proxy audio assets published with the release.

Corpus-level proxy signals are optional. Dataset-level proxy signals SHOULD be used when multiple corpora are intended to share one calibration procedure.

Each proxy signal entry MUST include:

- `proxy_id`
- `kind`
- `target_metric`
- `rms_dbfs`
- `duration_s`
- `audio_path`
- `audio_hash`

`audio_path` MUST be dataset-root-relative.

`audio_hash` MUST be the canonical integrity value for the published proxy audio asset.

`proxy_id` MUST be unique within the manifest.

If `kind = white_noise`, the published proxy signal MUST be synthesized white noise.

If a corpus manifest contains proxy signals intended for corpus-local calibration, it SHOULD contain at least one proxy signal with:

- `kind = white_noise`
- `target_metric = overall_rms_dbfs`

For that white-noise proxy signal, `rms_dbfs` MUST equal the corpus `overall_rms_dbfs` value within the documented analysis tolerance.

For reproducibility, implementations SHOULD synthesize corpus-level white-noise proxies using a fixed documented format and a fixed documented random seed so that identical corpus states reproduce identical proxy bytes.

## Corpus identity rules
Two corpus manifests represent the same logical corpus if and only if their canonical corpus identity views are equal.

A corpus release is uniquely identified by the tuple `(corpus_id, version)`.

`corpus_id` is a stable publisher-assigned identifier for a logical corpus.

Within a dataset root, `corpus_id` MUST be unique across logical corpora.

The canonical corpus identity view is formed from the corpus manifest after removing all fields listed below.

The following corpus fields are dynamic, derived, or version-scoped and MUST NOT be used to determine corpus identity:

- `corpus_id`
- `version`
- `created_at`
- `updated_at`
- `status`
- `release_root`
- `integrity`
- `metric_pipeline`
- `corpus_statistics`
- `proxy_signals`
- `samples`

`proxy_signals` is explicitly excluded from corpus identity because proxy assets are derived corpus-level artifacts and do not change the logical corpus when their generation details or bytes change.

All remaining corpus metadata is identity-bearing.

This means corpus identity includes, when present:

- `corpus_id`
- `name`
- `description`
- `licenses`
- `citation`
- `language`
- `tags`
- `extensions`

Changing any identity-bearing corpus field creates a different logical corpus, even if the change is small.

Changing only excluded fields creates a different corpus release or publication state, but not a different logical corpus.

Within a dataset root, if two corpus manifests have the same canonical corpus identity view, they MUST use the same `corpus_id`.

Within a dataset root, if two corpus manifests have different canonical corpus identity views, they MUST NOT use the same `corpus_id`.

---

# Sample-level schema

Each sample MUST have one metadata file.

## File name
The recommended metadata layout is `<bcp47>/samples/metadata/<version>/<shard>/<sample-id>.<sample-revision>.json`.

The referenced audio file SHOULD be stored under a dataset-root-relative path such as `<bcp47>/samples/audio/<shard>/aud_<bcp47>_<audio-hash>.wav`.

For hash-addressed sample assets, the file name SHOULD embed the exact `language.bcp47` value so implementations can reconstruct the full asset path from the file name plus the fixed asset-kind path template.

For these hash-addressed sample assets, `<shard>` SHOULD be derived from the first two hexadecimal characters of the content hash.

## Required fields
A sample metadata object MUST contain at least:

- `schema_version`
- `sample_id`
- `sample_revision`
- `corpus_id`
- `corpus_version`
- `audio`
- `text`
- `language`
- `metrics`
- `integrity`

The `voice` object is optional.

If a sample is TTS-generated, the `voice` object MUST be present and `voice.kind` MUST be `tts`.

The `subset` field is optional.

If present, `subset` MUST use one of: `core`, `extended`, `other`.

## Sample object

```json
{
  "schema_version": "0.1.0",
  "sample_id": "string",
  "sample_revision": "string",
  "corpus_id": "string",
  "corpus_version": "string",
  "subset": "core | extended | other",
  "audio": {
    "path": "<bcp47>/samples/audio/<shard>/aud_<bcp47>_<audio-hash>.wav",
    "container": "wav | flac | mp3 | ogg | opus",
    "sample_rate_hz": 24000,
    "channels": 1,
    "duration_s": 3.24,
    "file_size_bytes": 155648
  },
  "text": {
    "content": "string",
    "normalized": "string",
    "transcript_id": "string"
  },
  "language": {
    "bcp47": "string"
  },
  "voice": {
    "kind": "human | tts",
    "voice_id": "string",
    "voice_name": "string",
    "provider": "string",
    "model_name": "string",
    "model_version": "string",
    "generation_parameters": {},
    "generated_at": "date-time"
  },
  "metrics": {
    "rms_dbfs": -24.7,
    "integrated_lufs": -23.1,
    "active_speech_rms_dbfs": -22.9,
    "peak_dbfs": -1.2,
    "crest_factor_db": 23.5,
    "speech_activity_ratio": 0.79,
    "loudness_range_lu": 3.8
  },
  "integrity": {
    "hash_algorithm": "sha256",
    "audio_hash": "string",
    "metadata_hash": "string"
  },
  "annotations": {},
  "tags": ["string"],
  "extensions": {}
}
```

Each sample metadata record belongs to exactly one corpus version.

Republishing a sample in a new corpus version MUST create a new sample metadata record and a new `sample_revision`, even when the referenced audio file is unchanged.

## Watermarking
Watermarking is a required postprocessing step for every published sample audio asset.

Implementations MUST apply watermarking after the source sample audio has been rendered or recorded and before `audio_hash` is computed and published.

Every published sample audio asset MUST therefore contain an intentional watermark.

## Sample identity rules
Two sample metadata records represent the same logical sample if and only if their canonical sample identity views are equal.

A published sample record is uniquely identified by the tuple `(sample_id, sample_revision)`.

`sample_id` is a stable publisher-assigned identifier for a logical sample within a corpus.

Within a given `corpus_id`, `sample_id` MUST be unique across all corpus versions.

The canonical sample identity view is formed from the sample metadata record after removing all fields listed below.

The following sample fields are dynamic, derived, or version-scoped and MUST NOT be used to determine sample identity:

- `sample_id`
- `corpus_version`
- `sample_revision`
- `integrity`
- `metrics`
- `annotations`
- `tags`
- `extensions`
- `subset`
- `voice.generated_at`
- `audio.path`
- `audio.duration_s`
- `audio.file_size_bytes`

All remaining sample metadata is identity-bearing.

This means sample identity includes, when present:

- `corpus_id`
- `audio.container`
- `audio.sample_rate_hz`
- `audio.channels`
- `text`
- `language`
- `voice` except `voice.generated_at`

Because audio metadata is part of the sample metadata, a change in published audio format produces a different logical sample even when the underlying utterance text and provenance are otherwise unchanged.

Changing any identity-bearing sample field creates a different logical sample.

Changing only excluded fields creates a different published sample record or revision, but not a different logical sample.

Reusing an existing `(sample_id, sample_revision)` while changing either metadata content or audio content is invalid.

Within a given `corpus_id`, if two sample metadata records have the same canonical sample identity view, they MUST use the same `sample_id`.

Within a given `corpus_id`, if two sample metadata records have different canonical sample identity views, they MUST NOT use the same `sample_id`.

## Voice provenance fields
If `voice` is present, the following fields MUST be present:

- `voice.kind`
- `voice.voice_id`

For TTS-generated samples where `voice.kind = tts`, the following fields MUST be present:

- `voice.provider`
- `voice.model_name`
- `voice.model_version`
- `voice.voice_name`
- `voice.generated_at`

The following fields SHOULD be present when available for TTS-generated samples:

- `voice.generation_parameters`

## Language fields
`language.bcp47` MUST be present.

The sample-level `language` field is required even when it duplicates the corpus language so that sample metadata remains self-describing and can be validated independently.

---

# Signature and integrity protocol

## Goals
The integrity protocol ensures:

- file-level integrity
- manifest integrity
- release authenticity

## Hash algorithm
Implementations MUST support `sha256`.

Implementations MAY additionally support `sha512`.

## File-level hashing
Every referenced audio file MUST have a cryptographic hash recorded in the manifest sample entry that references it.

The corresponding sample metadata SHOULD also record `audio_hash` for standalone verification.

The hash MUST be computed on the exact published binary file.

## Metadata hashing
Each manifest sample entry MUST include a `metadata_hash` for the referenced sample metadata file.

Each sample metadata file SHOULD also include a `metadata_hash`.

When computing `metadata_hash`, implementations MUST canonicalize the sample metadata object with `integrity.metadata_hash` omitted.

If `metadata_hash` is present, verifiers SHOULD recompute it using the same omission rule and reject the file if it does not match.

## Manifest hash
The corpus manifest `integrity` object MUST contain a `manifest_hash` field.

The manifest hash MUST be computed over the canonicalized corpus manifest with `integrity.manifest_hash` omitted.

## Canonicalization
Before hashing or signing JSON metadata, implementations MUST use the JSON Canonicalization Scheme (JCS).

When a hash field is defined inside the object it protects, implementations MUST omit that hash field before canonicalization.

Implementations MUST use UTF-8 encoded canonical bytes.

## Signature
A corpus manifest with `status = released` MUST include a detached signature file named `manifest.sig`.

A corpus manifest with `status = draft` MAY omit `manifest.sig`.

The signature SHOULD be computed over the same canonicalized manifest bytes used for `manifest_hash`, with `integrity.manifest_hash` omitted.

Supported signature algorithms MAY include:

- Ed25519
- RSA-PSS

Ed25519 is RECOMMENDED.

## Public key identification
A corpus manifest with `status = released` MUST include:

- `signature_algorithm`
- `public_key_id`

## Verification procedure
A verifier MUST perform the following steps:

1. load `voxa.corpus.json`
2. canonicalize it with `integrity.manifest_hash` omitted
3. recompute `manifest_hash`
4. compare to the stored `manifest_hash`
5. if `status = released`, verify `manifest.sig` using `signature_algorithm` and the key identified by `public_key_id`
6. if `status = draft` and `manifest.sig` is present, verify it
7. for each manifest sample entry, verify that `metadata_hash` matches the referenced metadata file
8. for each manifest sample entry, verify that `audio_hash` matches the referenced audio file
9. load each sample metadata file and verify that `sample_id`, `sample_revision`, `corpus_id`, and `corpus_version` are consistent with the manifest
10. verify that each sample metadata `audio.path` resolves to the same dataset-root-relative path as the manifest `audio_path`
11. verify each sample-local `metadata_hash` if present, using the sample metadata with `integrity.metadata_hash` omitted
12. verify each sample-local `audio_hash` if present

A release passes verification only if all mandatory checks succeed.

## checksums.txt
A release MAY include a `checksums.txt` file for convenience.

This file does not replace the canonical hashes stored in the manifest.

## Official release identity
The canonical identity of a release SHOULD be expressed as:

`<corpus_id>@<version>#<manifest_hash>`

Example:

`voxa-en-us-core@1.0.0#9e5d9b7f...`

---

# Metrics specification

## General rules
Metrics MUST be clearly defined and reproducible.

The release SHOULD document these details in `metric_pipeline`:

- metric software implementation
- implementation version
- analysis parameters
- window sizes when applicable
- silence or activity detection rules when applicable

## Levels of computation
Metrics SHOULD be computed at both:

- sample level
- corpus level

Sample-level metrics are used for validation and outlier detection.

Corpus-level metrics are used for reporting and cross-corpus comparison.

Corpus-level metrics are only comparable when computed over a linguistically coherent corpus population. For Voxa, this means all samples aggregated into one corpus release MUST share the same exact `language.bcp47` value.

## Required sample-level metrics
Each sample SHOULD publish at least:

- `rms_dbfs`
- `integrated_lufs`
- `peak_dbfs`

## Recommended sample-level metrics
Each sample SHOULD additionally publish when available:

- `active_speech_rms_dbfs`
- `crest_factor_db`
- `speech_activity_ratio`
- `loudness_range_lu`
- LTAS

## Required corpus-level metrics
Each corpus release SHOULD publish corpus-level metrics for:

- duration summary statistics
- `rms_dbfs` summary statistics
- `overall_rms_dbfs`
- `integrated_lufs` summary statistics

## Recommended corpus-level metrics
Each corpus release SHOULD additionally publish corpus-level metrics for:

- `active_speech_rms_dbfs`
- `crest_factor_db`
- `peak_dbfs`
- `speech_activity_ratio`
- `loudness_range_lu`
- LTAS

## Summary statistic structure
Numeric corpus summaries SHOULD use the following structure:

```json
{
  "mean": 0.0,
  "std": 0.0,
  "min": 0.0,
  "max": 0.0,
  "p10": 0.0,
  "p50": 0.0,
  "p90": 0.0
}
```

## Metric definitions

### RMS dBFS
Long-term root mean square level expressed in dBFS.

This metric SHOULD be computed on the full signal unless otherwise documented.

At corpus level, `overall_rms_dbfs` denotes a single RMS value computed over the concatenation of all referenced sample signals in the release, or by an equivalent full-corpus energy calculation.

An equivalent full-corpus energy calculation MUST be performed in the linear domain and MUST be equivalent to duration-weighted aggregation over the referenced sample signals. Implementations MUST NOT compute `overall_rms_dbfs` by directly averaging per-sample dBFS values.

### Integrated LUFS
Integrated loudness computed according to the chosen loudness implementation.

If EBU R128 / ITU-R BS.1770-based implementation is used, the implementation and version SHOULD be documented.

### Active speech RMS dBFS
RMS level computed only on regions classified as active speech.

The activity detection method MUST be documented.

### Peak dBFS
Maximum absolute sample peak expressed in dBFS.

True peak MAY be reported as an extension but MUST be labeled distinctly from sample peak.

### Crest factor dB
Difference between peak level and RMS level.

### Speech activity ratio
Fraction of total duration classified as active speech.

Valid range is [0, 1].

### Loudness range LU
Temporal loudness variation measured in loudness units.

The implementation MUST be documented.

### LTAS
Long Term Average Spectrum.

The published representation SHOULD include:

- frequency bin centers in Hz
- corresponding levels in dB
- analysis method
- analysis sample rate in Hz
- frame length, hop length, window, and FFT size
- level definition
- LTAS scope
- VAD parameters when LTAS is VAD-gated

LTAS MAY be published either inline or by reference to a sidecar file. Inline LTAS publishes `frequency_hz` and `level_db` directly. Referenced LTAS publishes `path` and `format` instead. When a sidecar file is used, the metadata object SHOULD still publish the analysis parameters needed to interpret the referenced payload.

LTAS is the primary spectral representation. LTASS MAY be derived from LTAS by aggregating LTAS bins into coarser speech-oriented bands.

When sample-level LTAS would materially inflate metadata size, publishers SHOULD store it in a sidecar file and reference it from `metrics.ltas`.

Corpus-level LTAS MUST use a single `analysis_sample_rate_hz`. If referenced source audio uses different sample rates, implementations MUST resample to the published analysis rate before aggregation and MUST publish `resample_method`.

At corpus level, `ltas` denotes a single spectrum computed over the concatenation of all referenced sample signals in the release, or by an equivalent full-corpus spectral power calculation.

An equivalent corpus-level LTAS calculation MUST be performed in the linear spectral domain and MUST be equivalent to duration-weighted aggregation over the referenced sample signals. When `scope = vad_gated`, the weighting basis MUST be active-speech duration rather than total file duration. Implementations MUST NOT compute corpus-level LTAS by directly averaging per-sample `level_db` values.

LTAS MAY be computed either on the full signal or on regions classified as active speech.

When LTAS is computed only on active speech, implementations MUST publish:

- `scope = vad_gated`
- `vad_frame_ms`
- `vad_hop_ms`
- `vad_threshold_dbfs`

When LTAS is computed on the full signal, implementations SHOULD publish `scope = full_signal`.

Recommended inline structure:

```json
{
  "method": "string",
  "analysis_sample_rate_hz": 24000,
  "frame_ms": 32.0,
  "hop_ms": 16.0,
  "window": "hann",
  "n_fft": 1024,
  "scope": "vad_gated",
  "vad_frame_ms": 30.0,
  "vad_hop_ms": 10.0,
  "vad_threshold_dbfs": -40.0,
  "level_definition": "power_db_relative",
  "frequency_hz": [0.0, 93.75, 187.5, 281.25, 375.0, 468.75],
  "level_db": [-61.2, -45.7, -39.4, -34.8, -31.6, -29.9]
}
```

Recommended external-reference structure:

```json
{
  "method": "string",
  "analysis_sample_rate_hz": 24000,
  "frame_ms": 32.0,
  "hop_ms": 16.0,
  "window": "hann",
  "n_fft": 1024,
  "scope": "vad_gated",
  "vad_frame_ms": 30.0,
  "vad_hop_ms": 10.0,
  "vad_threshold_dbfs": -40.0,
  "level_definition": "power_db_relative",
  "path": "samples/metrics/60/ltas_en-US_60a8a0d6.json",
  "format": "json",
  "hash_algorithm": "sha256",
  "hash": "7a42f1c9...",
  "bin_count": 513
}
```

### White-noise proxy signal
A multilingual dataset MUST publish a white-noise proxy signal as a dataset-level derived audio asset.

This proxy signal is intended to provide a simple playback or level-reference signal that can be used once for all corpora referenced by the dataset manifest.

The dataset-level proxy signal MUST be synthesized white noise whose `rms_dbfs` matches `calibration_profile.target_rms_dbfs`.

The dataset manifest MUST publish the proxy signal in `proxy_signals` with its target metric, duration, path, and hash.

A monolingual corpus MAY publish a corpus-level white-noise proxy as a convenience artifact. If present, the corpus-level proxy signal SHOULD match the corpus `overall_rms_dbfs`; it MUST NOT replace the dataset-level proxy signal required by a multilingual dataset release.

Dataset-level calibration does not imply dataset-level audio normalization. Each corpus retains its published audio level and consumers SHOULD use the corpus `reference_offset_db` to interpret that corpus relative to the shared dataset reference.

For reproducibility, the proxy synthesis process SHOULD use a fixed documented audio format and a fixed documented random seed. If those inputs are unchanged and the referenced dataset or corpus state is unchanged, implementations SHOULD reproduce identical proxy bytes.

## Corpus aggregation rules
For corpus-level summaries:

- each sample SHOULD contribute once
- metric-specific aggregation requirements take precedence over this section
- weighting by file duration SHOULD be explicitly documented if used when it is not already required by the metric definition
- the aggregation method MUST be consistent across releases

## Evolving corpora
For evolving corpora, each published version SHOULD preserve:

- immutable metrics for that version
- the exact sample revision membership
- the exact computation pipeline version

A corpus maintainer SHOULD track drift between releases for at least:

- mean RMS
- mean LUFS
- LTAS
- sample count
- total duration

---

# Versioning rules

## Corpus versioning
Corpus versions MUST be immutable once released.

A corpus version MUST be defined by its manifest contents and the exact metadata and audio assets it references.

Republishing a sample in a new corpus version MUST create a new sample revision for that `sample_id`.

Unchanged audio assets MAY be referenced by multiple corpus versions.

If a published sample changes in metadata or audio content, a new `sample_revision` MUST be created.

An implementation MUST NOT publish different metadata content or different audio content under an already-used `(sample_id, sample_revision)`.

Semantic versioning is RECOMMENDED:

- MAJOR: incompatible schema or major corpus redesign
- MINOR: additive corpus update or added samples
- PATCH: manifest or metadata correction that does not materially change corpus scope but still results in a new corpus version and new sample revisions for affected samples

## Schema versioning
`schema_version` MUST indicate the Voxa schema version used by the file.

## Release notes
Each release SHOULD publish a changelog describing:

- added samples
- reused audio assets
- superseded sample revisions
- removed samples
- changed metadata
- changed audio content
- changed metric pipeline
- changed TTS generation pipeline

## Core subset stability
If a corpus defines a `core` subset, its membership SHOULD remain stable across minor versions.

Any change to core subset membership SHOULD be treated as a major release change unless clearly justified.

---

# Validation rules

A conforming validator SHOULD check:

- JSON structure against schema
- required fields
- uniqueness of each `sample_id` within the release
- existence of referenced paths
- consistency between corpus and sample references
- exact equality between the corpus `language.bcp47` value and every referenced sample metadata `language.bcp47` value
- consistency between dataset corpus references and referenced corpus manifests
- presence and integrity of referenced dataset-level proxy signal assets when a dataset manifest is present
- hash validity
- signature validity for released manifests
- language code syntax
- metric value ranges
- allowed `subset` values when present

## Examples of invalid data
A release MUST be rejected if:

- two entries share the same `sample_id`
- a multilingual dataset is published without a dataset manifest
- a dataset manifest `proxy_signals` value is missing or empty
- no dataset proxy signal entry has `kind = white_noise` and `target_metric = overall_rms_dbfs`
- the required dataset white-noise proxy signal `rms_dbfs` does not match `calibration_profile.target_rms_dbfs` within `calibration_profile.analysis_tolerance_db`
- a dataset corpus reference `manifest_hash` does not match the referenced corpus manifest
- a dataset corpus reference `overall_rms_dbfs` differs from the referenced corpus manifest `corpus_statistics.overall_rms_dbfs`
- a dataset corpus reference `reference_offset_db` differs from `overall_rms_dbfs - calibration_profile.target_rms_dbfs`
- a referenced audio file is missing
- a referenced dataset proxy signal audio file is missing
- a manifest `audio_hash` does not match the referenced binary file
- a manifest `metadata_hash` does not match the referenced metadata file
- a dataset proxy signal `audio_hash` does not match the referenced binary file
- the same `(sample_id, sample_revision)` is observed with different `audio_hash` values
- the same `(sample_id, sample_revision)` is observed with different `metadata_hash` values
- within the validator's dataset-root scope, the same `corpus_id` is observed for different canonical corpus identity views
- within the validator's dataset-root scope, the same `dataset_id` is observed for different canonical dataset identity views
- within the validator's dataset-root scope, the same `(corpus_id, sample_id)` is observed for different canonical sample identity views
- `language.bcp47` is missing
- a referenced sample metadata `language.bcp47` value differs from the corpus manifest `language.bcp47` value
- a released manifest is missing `manifest.sig`
- a sample metadata `corpus_id` or `corpus_version` does not match the release manifest
- a required synthetic voice provenance field is missing for a TTS-generated sample

---

# Minimal conformance profile

A minimal conforming released Voxa corpus MUST include:

- one corpus manifest
- one detached manifest signature
- explicit sample revision references
- one metadata file per referenced sample entry
- one audio file per referenced sample entry
- manifest-level `metadata_hash` values for each sample entry
- manifest-level `audio_hash` values for each sample entry
- corpus-level manifest hash
- `bcp47` language field
- sample-level `rms_dbfs`
- sample-level `integrated_lufs`
- sample-level `peak_dbfs`
- corpus-level `overall_rms_dbfs`

A draft manifest MAY omit `manifest.sig`.

A minimal conforming released multilingual Voxa dataset MUST additionally include:

- one dataset manifest
- one detached dataset manifest signature
- at least two corpus references
- dataset-level manifest hash
- one dataset-level calibration profile with `reference_scope = dataset`
- at least one dataset-level proxy signal entry
- one dataset-level proxy audio file per dataset proxy signal entry
- one white-noise proxy signal matched to `calibration_profile.target_rms_dbfs`

For TTS-generated content, a minimal conforming release MUST additionally include:

- voice provider
- voice model name
- voice model version
- voice name
- voice ID
- voice generation timestamp

---

# Recommended publication profile

A recommended release SHOULD include:

- corpus summary metrics
- LTAS
- changelog
- validation report
- core subset designation
- append-only sample revision history
- full synthetic voice provenance including model version and generation parameters

---

# Example corpus integrity block

```json
{
  "status": "released",
  "release_root": "fr-FR/manifests/v1.0/",
  "integrity": {
    "manifest_hash_algorithm": "sha256",
    "manifest_hash": "9e5d9b7f...",
    "signature_algorithm": "ed25519",
    "public_key_id": "voxa-main-2026"
  }
}
```

---

# Example corpus statistics block

```json
{
  "corpus_statistics": {
    "sample_count": 1000,
    "total_duration_s": 5420.3,
    "duration": {
      "mean": 5.42,
      "std": 1.13,
      "min": 2.01,
      "max": 9.88,
      "p10": 3.92,
      "p50": 5.21,
      "p90": 7.15
    },
    "rms_dbfs": {
      "mean": -24.9,
      "std": 1.1,
      "min": -27.5,
      "max": -22.2,
      "p10": -26.3,
      "p50": -24.8,
      "p90": -23.7
    },
    "overall_rms_dbfs": -24.7,
    "integrated_lufs": {
      "mean": -23.0,
      "std": 0.3,
      "min": -23.6,
      "max": -22.3,
      "p10": -23.4,
      "p50": -23.0,
      "p90": -22.7
    },
    "ltas": {
      "method": "FFT mean power spectrum",
      "analysis_sample_rate_hz": 24000,
      "frame_ms": 32.0,
      "hop_ms": 16.0,
      "window": "hann",
      "n_fft": 1024,
      "scope": "vad_gated",
      "vad_frame_ms": 30.0,
      "vad_hop_ms": 10.0,
      "vad_threshold_dbfs": -40.0,
      "level_definition": "power_db_relative",
      "resample_method": "polyphase",
      "frequency_hz": [0.0, 93.75, 187.5, 281.25, 375.0, 468.75],
      "level_db": [-61.2, -45.7, -39.4, -34.8, -31.6, -29.9]
    }
  },
  "proxy_signals": [
    {
      "proxy_id": "white-noise-overall-rms",
      "kind": "white_noise",
      "target_metric": "overall_rms_dbfs",
      "rms_dbfs": -24.7,
      "duration_s": 30.0,
      "audio_path": "fr-FR/proxies/v1.0/proxy_white-noise-overall-rms.wav",
      "audio_hash": "7a42f1c9..."
    }
  ]
}
```

---

# Example sample block

```json
{
  "schema_version": "0.1.0",
  "sample_id": "smp_en-us-000001",
  "sample_revision": "r2",
  "corpus_id": "voxa-en-us-core",
  "corpus_version": "v1.0",
  "subset": "core",
  "audio": {
    "path": "en-US/samples/audio/60/aud_en-US_60a8a0d6.wav",
    "container": "wav",
    "sample_rate_hz": 24000,
    "channels": 1,
    "duration_s": 3.24,
    "file_size_bytes": 155648
  },
  "text": {
    "content": "The meeting starts at nine o'clock tomorrow morning.",
    "normalized": "the meeting starts at nine o'clock tomorrow morning"
  },
  "language": {
    "bcp47": "en-US"
  },
  "voice": {
    "kind": "tts",
    "provider": "ExampleProvider",
    "model_name": "ExampleTTS",
    "model_version": "2.1",
    "voice_name": "Ava",
    "voice_id": "ava_en_us",
    "generation_parameters": {
      "speaking_rate": 1.0,
      "seed": 42
    },
    "generated_at": "2026-03-30T10:05:00Z"
  },
  "metrics": {
    "rms_dbfs": -24.7,
    "integrated_lufs": -23.1,
    "active_speech_rms_dbfs": -22.9,
    "peak_dbfs": -1.2,
    "crest_factor_db": 23.5,
    "speech_activity_ratio": 0.79,
    "loudness_range_lu": 3.8,
    "ltas": {
      "method": "FFT mean power spectrum",
      "analysis_sample_rate_hz": 24000,
      "frame_ms": 32.0,
      "hop_ms": 16.0,
      "window": "hann",
      "n_fft": 1024,
      "scope": "vad_gated",
      "vad_frame_ms": 30.0,
      "vad_hop_ms": 10.0,
      "vad_threshold_dbfs": -40.0,
      "level_definition": "power_db_relative",
      "path": "samples/metrics/60/ltas_en-US_60a8a0d6.json",
      "format": "json",
      "hash_algorithm": "sha256",
      "hash": "7a42f1c9...",
      "bin_count": 513
    }
  },
  "integrity": {
    "hash_algorithm": "sha256",
    "audio_hash": "60a8a0d6...",
    "metadata_hash": "b1427a10..."
  }
}
```

---

# Future extensions

Future Voxa revisions MAY standardize:

- phoneme or grapheme annotations
- MOS or perceptual quality labels
- true peak metrics
- multilingual corpus composition descriptors
- speaker demographic metadata when appropriate and lawful
- calibration recommendation profiles

---

# Summary

Voxa defines a speech corpus as a **versioned, verifiable, metrics-described artifact**.

A conforming implementation MUST provide:

- corpus-level manifest
- sample-level metadata
- cryptographic integrity information
- stable identifiers
- reproducible metrics
- explicit voice provenance

This is intended to improve:

- corpus consistency
- reproducibility
- traceability
- comparability across releases and across playback systems
