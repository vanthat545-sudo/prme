#!/usr/bin/env bash
set -euo pipefail
: "${GITHUB_REPOSITORY:?}" "${GH_TOKEN:?}"
BRANCH="feat/ai-video-vietnamese"
readonly MAX_ATTEMPTS=70
mkdir -p release_candidate/{mac,windows,audit}
get_result() {
  local name="$1" revision="$2"
  local id sha status conclusion
  while IFS=$'\t' read -r id sha status conclusion; do
    if git merge-base --is-ancestor "$revision" "$sha"; then
      printf '%s:%s:%s\n' "$id" "$status" "$conclusion"
      return 0
    fi
  done < <(printf '%s' "$runs_json" | jq -r --arg name "$name" '.workflow_runs[] | select(.name==$name) | [.id, .head_sha, .status, (.conclusion//"null")] | @tsv')
  printf 'PENDING\n'
}
for attempt in $(seq 1 "$MAX_ATTEMPTS"); do
  git fetch -q origin "$BRANCH"
  translated_commit=$(git rev-list -1 "origin/$BRANCH" -- translations/vi.tsv || true)
  if [ -z "$translated_commit" ]; then
    echo "[$attempt/$MAX_ATTEMPTS] Waiting for completed Vietnamese translation catalog..."
    sleep 120
    continue
  fi
  echo "[$attempt] Vietnamese translation revision: $translated_commit"
  runs_json=$(gh api "repos/${GITHUB_REPOSITORY}/actions/runs?branch=${BRANCH}&per_page=100")
  mac=$(get_result "AI Video macOS Apple Silicon TEST package" "$translated_commit")
  win=$(get_result "AI Video Windows x64 build" "$translated_commit")
  audit=$(get_result "AI Video Vietnamese localization audit" "$translated_commit")
  check=$(get_result "AI Video Vietnamese rebrand verification" "$translated_commit")
  echo "  macOS=$mac"
  echo "  Windows=$win"
  echo "  Vietnamese audit=$audit"
  echo "  Rust/source validation=$check"
  arr=("$mac" "$win" "$audit" "$check")
  failed=0
  pending=0
  for value in "${arr[@]}"; do
    if [[ "$value" == PENDING || "$value" != *":completed:"* ]]; then
      pending=1
    elif [[ "$value" != *":completed:success" ]]; then
      failed=1
    fi
  done
  if [ "$failed" -eq 1 ]; then
    echo "::error::AI Video candidate blocked: required CI workflow failed. See GitHub Actions."
    exit 1
  fi
  if [ "$pending" -eq 1 ]; then sleep 120; continue; fi
  echo "All four gates passed on $translated_commit"
  extract_id(){ echo "${1%%:*}"; }
  gh run download "$(extract_id "$mac")" -n AI-Video-macOS-M1-TEST -D release_candidate/mac
  gh run download "$(extract_id "$win")" -n AI-Video-Windows-x64-TEST -D release_candidate/windows
  gh run download "$(extract_id "$audit")" -n AI-Video-Vietnamese-Catalog-Audit -D release_candidate/audit
  test -s release_candidate/audit/translation-audit.json
  jq -e '.missing_entries == 0 and .unknown_entries == 0 and .format_errors == 0' release_candidate/audit/translation-audit.json
  find release_candidate/mac -type f
  find release_candidate/windows -type f
  test -n "$(find release_candidate/mac -type f -name '*.dmg' -print -quit)"
  test -n "$(find release_candidate/windows -type f -name '*Windows*TEST.zip' -print -quit)"
  tag="v0.13.0-ai-video-preview.1"
  cat > release_candidate/NOTES.md <<'EOF'
# AI Video 0.13.0 — BẢN XEM TRƯỚC / TEST
- Bộ cài macOS Apple Silicon và Windows x64 đã đi qua các quy trình CI xây dựng gói.
- Giao diện có bộ dịch tiếng Việt máy tạo và đã qua kiểm tra định dạng/khóa.
- **Chưa được nghiệm thu thủ công:** mức độ tự nhiên của tiếng Việt, chất lượng chỉnh sửa/xuất video, giao diện thực tế, tương thích dự án và code signing công khai.
- KHÔNG PHẢI BẢN ỔN ĐỊNH, không cài đè lên dự án quan trọng nếu chưa sao lưu.
- Giữ mã engine gốc và định dạng dự án .fcproj.
EOF
  if gh release view "$tag" >/dev/null 2>&1; then
    echo "Preview release already exists: $tag"
  else
    mapfile -d '' files < <(find release_candidate/mac release_candidate/windows -type f \( -name '*.zip' -o -name '*.dmg' \) -print0)
    test "${#files[@]}" -ge 2
    gh release create "$tag" "${files[@]}" --target "$translated_commit" --prerelease --title "AI Video 0.13.0 – Mac + Windows (TEST)" --notes-file release_candidate/NOTES.md
  fi
  echo "Published TEST release only: https://github.com/${GITHUB_REPOSITORY}/releases/tag/$tag"
  exit 0
done
echo "::error::Timed out waiting for Vietnamese translations and cross-platform CI"
exit 1
