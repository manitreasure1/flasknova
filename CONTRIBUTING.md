# Contributing to Flask Nova

First off, thank you for considering contributing to **Flask Nova** 🚀
Contributions, whether big or small, help improve the framework for everyone.

---

## 📌 How to Contribute

There are many ways to contribute:

* Reporting bugs
* Suggesting features
* Improving documentation
* Writing tests
* Submitting code changes

---

## 🛠️ Development Setup

We use [Poetry](https://python-poetry.org/) for dependency management.

1. **Fork the repo** on GitHub.
2. **Clone your fork**:

   ```bash
   git clone https://github.com/<your-username>/flask-nova.git
   cd flask-nova
   ```
3. **Install dependencies**:

   ```bash
   poetry install
   ```
4. **Activate the virtual environment**:

   ```bash
   poetry shell
   ```

---

## ▶️ Running Tests

We use Python’s built-in `unittest` framework for testing.

```bash
python -m unittest discover -s tests
```

---

## 🔀 Submitting Changes

1. Create a new branch for your work:

   ```bash
   git checkout -b feature/my-new-feature
   ```

2. Commit your changes:

   ```bash
   git commit -m "feat: add my new feature"
   ```

   Follow [Conventional Commits](https://www.conventionalcommits.org/) where possible:

   * `feat:` → new feature
   * `fix:` → bug fix
   * `docs:` → documentation only
   * `test:` → adding or updating tests
   * `refactor:` → code change without new features or bug fixes

3. Push your branch:

   ```bash
   git push origin feature/my-new-feature
   ```

4. Open a **Pull Request** on GitHub.

---

## ✅ Code Style

* Follow **PEP8** guidelines.
* Ensure code is **typed** with Python type hints.
* Keep formatting consistent and readable.
* Run tests before pushing to confirm nothing is broken.

---

## 💡 Tips

* Keep PRs small and focused.
* Add/update tests when fixing bugs or adding features.
* If unsure about a feature, open an issue for discussion before coding.

---

Thank you for helping make **Flask Nova** better! 💙
