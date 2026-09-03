#!/usr/bin/env bash
# Build and publish to GitHub Pages.
#
# Publishes the built dist/ to the gh-pages branch rather than using a GitHub Actions
# workflow, because the gh CLI token here lacks the `workflow` scope and cannot create
# .github/workflows/. To switch to CI later: run `gh auth refresh -s workflow`, move
# docs/github-pages-workflow.yml.example to .github/workflows/deploy.yml, push, and set
# Pages source back to "GitHub Actions".
set -euo pipefail

REPO="https://github.com/gdmotley1/motley-pickem.git"
cd "$(dirname "$0")"

echo "==> building"
npm run build

# GitHub Pages runs Jekyll by default, which drops files and folders starting with _.
touch dist/.nojekyll

echo "==> publishing dist/ to gh-pages"
rm -rf dist/.git
git -C dist init -q
git -C dist checkout -qB gh-pages
git -C dist add -A
git -C dist -c user.name="Grant Motley" -c user.email="gdmotley1@gmail.com" \
  commit -q -m "Deploy $(date -u +%Y-%m-%dT%H:%M:%SZ)"
git -C dist push -q -f "$REPO" gh-pages:gh-pages
rm -rf dist/.git

echo "==> live at https://gdmotley1.github.io/motley-pickem/"
