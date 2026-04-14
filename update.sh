#!/bin/bash
# 一键更新：从外部仓库拉取所有 skills 并合并到本地，自动 commit & push

cd "$(dirname "$0")"

REPO_ROOT="$(pwd)"
TMP_DIR="$REPO_ROOT/.tmp-skills"

# 外部 skill 源配置
# 格式: "本地前缀目录|仓库URL|分支|skill搜索根路径"
SOURCES=(
    "anthropics-skills|https://github.com/anthropics/skills.git|main|skills"
    "awesome-claude-skills|https://github.com/ComposioHQ/awesome-claude-skills.git|master|."
    "claude-plugins-official|https://github.com/anthropics/claude-plugins-official.git|main|."
    "axton-obsidian-visual-skills|https://github.com/axtonliu/axton-obsidian-visual-skills.git|main|."
    "baoyu-skills|https://github.com/JimLiu/baoyu-skills.git|main|skills"
)

# 不合并的 skill 名称（排除低质量或不需要的）
EXCLUDE_NAMES=(
    "composio-skills"
    "template-skill"
    "example-command"
    "example-skill"
)

cleanup() {
    rm -rf "$TMP_DIR"
}
trap cleanup EXIT

rm -rf "$TMP_DIR"
mkdir -p "$TMP_DIR"

echo "========================================="
echo "  My-Skills Auto Sync"
echo "========================================="
echo ""

total_copied=0
total_skipped=0

for source in "${SOURCES[@]}"; do
    IFS='|' read -r prefix url branch search_root <<< "$source"

    echo ">>> [$prefix] Cloning from $url (branch: $branch)..."

    clone_dir="$TMP_DIR/$prefix"
    if ! git clone --depth 1 --branch "$branch" "$url" "$clone_dir" 2>/dev/null; then
        echo "    ERROR: Failed to clone, skipping"
        echo ""
        continue
    fi

    search_path="$clone_dir/$search_root"
    if [ ! -d "$search_path" ]; then
        echo "    WARN: Search path '$search_path' not found, skipping"
        echo ""
        continue
    fi

    copied=0
    while IFS= read -r -d '' skill_dir; do
        skill_name="$(basename "$skill_dir")"

        skip=false
        for ex in "${EXCLUDE_NAMES[@]}"; do
            if [[ "$skill_name" == "$ex"* ]]; then
                skip=true
                break
            fi
        done
        $skip && continue

        dest="$REPO_ROOT/$prefix/$skill_name"
        mkdir -p "$dest"
        cp -r "$skill_dir/"* "$dest/" 2>/dev/null
        cp "$skill_dir/SKILL.md" "$dest/" 2>/dev/null

        copied=$((copied + 1))
    done < <(find "$search_path" -name "SKILL.md" -exec dirname {} \; -print0 | sort -z -u)

    total_copied=$((total_copied + copied))
    echo "    Copied $copied skills"
    echo ""
done

echo ">>> Total: $total_copied skills synced"
echo ""

# Check changes
if git diff --quiet && git diff --cached --quiet; then
    echo ">>> No changes, nothing to commit"
    exit 0
fi

echo ">>> Changes detected:"
git status --short
echo ""

git add -A
git commit -m "sync skills $(date +%Y-%m-%d\ %H:%M)"
git push

echo ""
echo ">>> Done! Pushed to remote."
