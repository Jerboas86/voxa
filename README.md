# voxa

`voxa-metrics` is a pure Python reference helper for the Voxa specification.

Voxa defines a versioned, traceable, verifiable speech corpus format with:

- a corpus-level manifest
- sample-level metadata
- integrity and signature fields
- reproducible acoustic metrics for validation and comparison

This project focuses on the metrics side of that specification. It computes the sample-level and corpus-level measurements described in section 8 and produces payloads that fit the Voxa manifest and corpus statistics shapes.

The library lives in [`src/voxa_metrics`](/home/ben/Projects/opensrc/voxa/src/voxa_metrics) and implements:

- sample-level `rms_dbfs`
- sample-level `integrated_lufs`
- sample-level `active_speech_rms_dbfs`
- sample-level `peak_dbfs`
- sample-level `crest_factor_db`
- sample-level `speech_activity_ratio`
- sample-level `loudness_range_lu`
- sample-level and corpus-level LTASS
- corpus summary statistics in the section 8.7 shape

Quick example:

```python
from voxa_metrics import analyze_audio_file, compute_corpus_statistics

sample = analyze_audio_file("sample.opus")
print(sample.to_voxa_dict(include_ltass=True))

corpus = compute_corpus_statistics([sample])
print(corpus.to_voxa_dict())
```


## Generate documentation

`pandoc ./voxa_specification.md -o ./spec.pdf   --template eisvogel   --toc --number-sections --pdf-engine=xelatex`
