# voxa

`voxa-metrics` is a pure Python reference helper for the Voxa specification.

Voxa defines a versioned, traceable, verifiable speech corpus format with:

- a corpus-level manifest
- sample-level metadata
- integrity and signature fields
- reproducible acoustic metrics for validation and comparison

In Voxa, a corpus is monolingual: all samples in a corpus MUST share the same exact `language.bcp47` value. A dataset can therefore publish multiple corpora, one per language.

## Generate documentation

`pandoc ./voxa_specification.md -o ./spec.pdf   --template eisvogel   --toc --number-sections --pdf-engine=xelatex`
