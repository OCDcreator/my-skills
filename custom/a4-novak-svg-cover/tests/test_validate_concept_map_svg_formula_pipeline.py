from pathlib import Path
import subprocess
import textwrap


ROOT = Path(__file__).resolve().parents[1]
VALIDATOR = ROOT / "scripts" / "validate_concept_map_svg.py"


def write_svg(tmp_path: Path, body: str) -> Path:
    svg = tmp_path / "concept-map.svg"
    svg.write_text(
        textwrap.dedent(
            f"""\
            <svg xmlns="http://www.w3.org/2000/svg" width="210mm" height="297mm" viewBox="0 0 210 297">
              <rect class="bg" x="0" y="0" width="210" height="297" fill="#ffffff"/>
              <rect class="card" x="20" y="20" width="80" height="30" fill="#ffffff" stroke="#222222"/>
              {body}
            </svg>
            """
        ),
        encoding="utf-8",
    )
    return svg


def run_validator(svg: Path, *extra_args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["python", str(VALIDATOR), str(svg), "--min-gap-mm", "3", *extra_args],
        text=True,
        capture_output=True,
        check=False,
    )


def test_plain_chinese_text_is_allowed(tmp_path: Path) -> None:
    svg = write_svg(tmp_path, '<text x="30" y="35" fill="#111111">单调性与奇偶性</text>')

    result = run_validator(svg)

    assert result.returncode == 0, result.stderr
    assert "raw_math_texts=0" in result.stdout


def test_raw_formula_text_fails_without_mathjax_group(tmp_path: Path) -> None:
    svg = write_svg(tmp_path, '<text x="30" y="35" fill="#111111">f(x)=x^2</text>')

    result = run_validator(svg)

    assert result.returncode == 1
    assert "no MathJax" in result.stderr
    assert "raw formula-like SVG <text>" in result.stderr


def test_mathjax_formula_fit_group_is_allowed(tmp_path: Path) -> None:
    svg = write_svg(
        tmp_path,
        """
        <text x="30" y="32" fill="#111111">核心函数</text>
        <g class="formula-fit" data-formula-id="fx-square" transform="translate(30 38)">
          <path d="M0 0 L10 0" fill="none" stroke="#111111"/>
        </g>
        """,
    )

    result = run_validator(svg)

    assert result.returncode == 0, result.stderr
    assert "formula_groups=1" in result.stdout


def test_formula_fit_group_does_not_allow_raw_formula_text_elsewhere(tmp_path: Path) -> None:
    svg = write_svg(
        tmp_path,
        """
        <g class="formula-fit" data-formula-id="fx-square" transform="translate(30 38)">
          <path d="M0 0 L10 0" fill="none" stroke="#111111"/>
        </g>
        <text x="30" y="45" fill="#111111">ln x</text>
        """,
    )

    result = run_validator(svg)

    assert result.returncode == 1
    assert "raw formula-like SVG <text>" in result.stderr


def test_formula_fit_group_requires_data_formula_id(tmp_path: Path) -> None:
    svg = write_svg(
        tmp_path,
        """
        <g class="formula-fit" transform="translate(30 38)">
          <path d="M0 0 L10 0" fill="none" stroke="#111111"/>
        </g>
        """,
    )

    result = run_validator(svg)

    assert result.returncode == 1
    assert "missing data-formula-id" in result.stderr
