# 例题引用块覆盖测试

这是 scan 技能回归 eval 的 fixture。它包含三种例题形态，用于验证 postprocess 的 `ensureExampleQuote` 把例题正确包成 `.phycat-blockquote`。

## 选择题例题

> [!question] 例题1
> 已知函数 $f(x) = x^2$，求 $f(2)$ 的值。
>
> | A. 1 | B. 2 | C. 4 | D. 8 |
> | :---: | :---: | :---: | :---: |

**解析**

代入 $x = 2$ 得 $f(2) = 2^2 = 4$，故选 C。

## 证明题例题

> [!question] 例题2
> 证明：对任意实数 $x$，有 $x^2 \geq 0$。

**解析**

因为 $x^2$ 是实数的平方，平方数非负，故 $x^2 \geq 0$ 恒成立。

## 故意不在 callout 内的例题

这道例题故意写成裸段落（不以 `>` 开头），用于验证前置 gate `validate_example_blockquote_coverage.py` 能报告它。注意：postprocess 的 `ensureExampleQuote` 会尝试自动把它包进 `.phycat-blockquote`，所以构建后 HTML 里它应该仍然有引用块——但前置 gate 应该在构建前就报警。

例题3 这是一个裸段落形式的例题标签，应该被前置 gate 报告。

**解析**

这是例题3的解析，不应在 blockquote 内。
