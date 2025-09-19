# Contributing to AUI-Core

Thank you for considering contributing to **AUI-Core**!  
This document explains the contribution process and the legal requirements.

## How to Contribute

1. **Fork the repository** at  
   https://github.com/AUI-AudioUserInterface/aui-core.git
2. Create a new branch for your feature or bugfix:
   ```bash
   git checkout -b feature/my-new-feature
   ```
3. Make your changes with clear, well-documented code.  
4. Add or update tests where appropriate.  
5. Ensure code style and formatting passes:
   ```bash
   ruff check .
   pytest -q
   ```
6. Commit with a clear message and push to your fork.  
7. Open a Pull Request (PR) to the `main` branch.

## Developer Certificate of Origin (DCO)

By contributing, you certify that:

- The contribution is your original work, or you have the right to submit it.  
- You agree that your contribution will be licensed under the same license as the project (GPLv3 for AUI-Core).  
- You agree that the project maintainer (**CoPiCo2Co**) retains the right to also license the contribution under other terms (e.g., for commercial licensing).  

To acknowledge this, add a `Signed-off-by` line to each commit message:

```
Signed-off-by: Your Name <your.email@example.com>
```

Git can add this automatically with the `-s` flag:

```bash
git commit -s -m "Add new feature"
```

## Code Style

- Python >= 3.12  
- Follow [PEP8](https://peps.python.org/pep-0008/) with Ruff/Black auto-formatting.  
- Use meaningful names and docstrings for public functions.  

## Reporting Issues

If you find a bug or have a feature request, please open an issue on GitHub:  
https://github.com/AUI-AudioUserInterface/aui-core/issues

---

Thank you for helping improve **AUI-Core**!  
