import pathlib

import nox

_NOX_PYTEST_COVERAGE_DIR = pathlib.Path(".nox-wandb", "pytest-coverage")
PYTHON_VERSIONS = ["3.8", "3.9", "3.10", "3.11", "3.12"]


@nox.session(name="code-check")
def code_check(session) -> None:
    """Run code checks."""
    session.install("ruff")
    session.run("ruff", "format", "src", "tests")
    session.run("ruff", "check", "--fix", "--unsafe-fixes", "src", "tests")
    session.notify("mypy")


@nox.session(python=PYTHON_VERSIONS)
def tests(session: nox.Session) -> None:
    """Run the test suite."""
    session.install(".")
    session.install("pytest", "pytest-cov")
    session.env["COVERAGE_FILE"] = f"{_NOX_PYTEST_COVERAGE_DIR}/.coverage"
    session.run(
        "pytest",
        "--cov-config=.coveragerc",
        "--cov",
        "--cov-report=",
        "--no-cov-on-fail",
        "tests/",
        *session.posargs,
    )


@nox.session(python=["3.12"])
def mypy(session: nox.Session):
    """Run mypy."""
    session.install("mypy", "lxml")
    session.env["MYPYPATH"] = session.run("pwd", silent=True).strip()
    session.run(
        "mypy",
        "--install-types",
        "--non-interactive",
        "--show-error-codes",
        "--html-report",
        "mypy-results/",
        "--exclude",
        "src/yea/vendor/",
        "src/",
        external=True,
    )


@nox.session(python=PYTHON_VERSIONS)
def covercircle(session: nox.Session):
    """Run coverage and upload to codecov."""
    session.install("pytest", "coverage", "codecov")

    # Passenv equivalent
    for env_var in ["CI", "CIRCLECI"] + [
        v for v in session.env if v.startswith("CIRCLE_") or v.startswith("CODECOV_")
    ]:
        session.env[env_var] = session.env.get(env_var)

    session.env["CIRCLE_BUILD_NUM"] = session.env.get("CIRCLE_WORKFLOW_ID")

    session.run("mkdir", "-p", "cover-results", external=True)
    session.run(
        "bash", "-c", "python -m coverage combine .nox/py*/.coverage*", external=True
    )
    session.run("coverage", "xml", "--ignore-errors")
    session.run("cp", ".coverage", "coverage.xml", "cover-results/", external=True)
    session.run("coverage", "report", "--ignore-errors", "--skip-covered")
    session.run("codecov", "-e", "TOXENV", "-F", "unittest")


@nox.session()
def build(session: nox.Session):
    """Build the package."""
    session.install("build")
    session.run("python", "-m", "build")


@nox.session()
def release(session: nox.Session):
    """Build and publish the package to PyPI."""
    build(session)

    session.install("twine")
    session.run("twine", "upload", "dist/*")
    session.run("rm", "-fr", "build", "dist", external=True)
