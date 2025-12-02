# Contributing to Prism

This project welcomes contributions and suggestions. Most contributions require you to agree to a
Contributor License Agreement (CLA) declaring that you have the right to, and actually do, grant us
the rights to use your contribution. For details, visit https://cla.opensource.microsoft.com.

When you submit a pull request, a CLA bot will automatically determine whether you need to provide
a CLA and decorate the PR appropriately (e.g., status check, comment). Simply follow the instructions
provided by the bot. You will only need to do this once across all repos using our CLA.

This project has adopted the [Microsoft Open Source Code of Conduct](https://opensource.microsoft.com/codeofconduct/).
For more information see the [Code of Conduct FAQ](https://opensource.microsoft.com/codeofconduct/faq/) or
contact [opencode@microsoft.com](mailto:opencode@microsoft.com) with any additional questions or comments.

## How to Contribute

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## Development Setup

See [README.md](README.md) for setup instructions.

### Prerequisites

- Docker & Docker Compose (recommended)
- Python 3.11+ (for local development)
- Node.js 20+ (for frontend development)
- Azure subscription with OpenAI and AI Search resources

### Running Tests

```bash
# Install dependencies
pip install -r requirements.txt
pip install -r apps/api/requirements-api.txt

# Run tests
pytest
```

## Reporting Issues

Please use GitHub Issues to report bugs or request features. When reporting bugs, include:

- Steps to reproduce
- Expected behavior
- Actual behavior
- Environment details (OS, Python version, etc.)

## Code Style

- Python: Follow PEP 8 guidelines
- Vue/JavaScript: Use ESLint with the project configuration
- Use meaningful commit messages

## Pull Request Process

1. Ensure your code passes all tests
2. Update documentation if needed
3. Add tests for new functionality
4. Request review from maintainers
