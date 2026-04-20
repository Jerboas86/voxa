# Voxa

Voxa is a specification for a versioned, traceable, verifiable speech corpus
format with:

- a corpus-level manifest
- sample-level metadata
- integrity and signature fields
- reproducible acoustic metrics for validation and comparison


## License

This repository is licensed under `CC BY-SA 4.0`.
See [LICENSE](./LICENSE) or visit:
https://creativecommons.org/licenses/by-sa/4.0/

## Generate documentation

```sh
pandoc ./voxa_specification.md -o ./spec.pdf --template eisvogel --toc --number-sections --pdf-engine=xelatex
```

The GitHub release workflow builds the same PDF with a digest-pinned
`pandoc/extra` Docker image, which includes the Eisvogel template and the
LaTeX dependencies needed for the build.
