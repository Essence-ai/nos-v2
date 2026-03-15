# NeuronOS Documentation

This repository contains all documentation for the NeuronOS project.

## Contents

- [User Guide](user-guide/) - End-user documentation
- [Developer Guide](developer-guide/) - Development documentation
- [Hardware Compatibility](hardware-compatibility/) - Supported hardware list
- [Troubleshooting](troubleshooting/) - Common issues and solutions

## Quick Links

- **Installation**: See [user-guide/installation.md](user-guide/installation.md)
- **First Steps**: See [user-guide/getting-started.md](user-guide/getting-started.md)
- **Windows Apps**: See [user-guide/windows-applications.md](user-guide/windows-applications.md)
- **Contributing**: See [developer-guide/contributing.md](developer-guide/contributing.md)

## Documentation Structure

```
neuronos-docs/
├── user-guide/
│   ├── installation.md
│   ├── getting-started.md
│   ├── windows-applications.md
│   ├── native-applications.md
│   └── settings.md
├── developer-guide/
│   ├── architecture.md
│   ├── building.md
│   ├── contributing.md
│   └── testing.md
├── hardware-compatibility/
│   ├── gpus.md
│   ├── cpus.md
│   └── motherboards.md
└── troubleshooting/
    ├── installation-issues.md
    ├── gpu-passthrough.md
    └── application-issues.md
```

## Building the Docs

Documentation is written in Markdown and can be built with various tools:

```bash
# Using MkDocs
pip install mkdocs mkdocs-material
mkdocs serve

# Using Sphinx (with MyST)
pip install sphinx myst-parser
sphinx-build -b html . _build
```

## Contributing

See [developer-guide/contributing.md](developer-guide/contributing.md) for contribution guidelines.
