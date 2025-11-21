# GitHub Repository Setup Guide

This document outlines the recommended settings and configurations for the `graph-analytics-ai` repository on GitHub.

## Repository Settings

### 1. General Settings

**Repository Name:** `graph-analytics-ai`

**Description:**
```
Unified library for orchestrating ArangoDB Graph Analytics Engine operations across AMP and self-managed deployments
```

**Visibility:** Private

**Topics/Tags:**
- `python`
- `graph-analytics`
- `arangodb`
- `gae`
- `graph-database`
- `analytics`
- `orchestration`
- `machine-learning`

### 2. Branch Protection Rules

**Settings → Branches → Add rule**

**Branch name pattern:** `main`

**Protect matching branches:**
- Require a pull request before merging
  - Require approvals: 1
  - Dismiss stale pull request approvals when new commits are pushed
  - Require review from Code Owners
- Require status checks to pass before merging
  - Require branches to be up to date before merging
  - Status checks: `test (3.8)`, `test (3.9)`, `test (3.10)`, `test (3.11)`, `lint`
- Require conversation resolution before merging
- Do not allow bypassing the above settings
- Include administrators

### 3. Actions Settings

**Settings → Actions → General**

-  Allow all actions and reusable workflows
-  Allow actions created by GitHub
-  Allow Marketplace actions by verified creators
-  Allow actions by Marketplace verified creators
-  Allow actions in GITHUB_TOKEN to be requested by workflows

**Workflow permissions:**
-  Read and write permissions
-  Allow GitHub Actions to create and approve pull requests

### 4. Security Settings

**Settings → Security**

- Enable Dependabot alerts
- Enable Dependabot security updates
- Enable secret scanning
- Enable push protection

### 5. Code and Automation

**Settings → General → Features**

- Issues
- Projects
- Wiki (optional)
- Discussions (optional)

**Settings → General → Pull Requests**

- Allow merge commits
- Allow squash merging (recommended)
- Allow rebase merging

### 6. Webhooks (Optional)

If you need to integrate with external services:
- **Settings → Webhooks → Add webhook**

## Repository Files

### README.md
Already configured with:
- Project description
- Installation instructions
- Usage examples
- Configuration guide
- API reference

### LICENSE
 MIT License already included

### .github/workflows/ci.yml
 CI/CD workflow configured for:
- Multi-version Python testing (3.8, 3.9, 3.10, 3.11)
- Code coverage reporting
- Linting (flake8, black, mypy)

### .github/ISSUE_TEMPLATE/
 Issue templates available for:
- Library improvements
- Bug reports
- Feature requests

## Recommended Next Steps

1. **Add Repository Description**
   - Go to repository main page
   - Click Settings → General
   - Add description and topics

2. **Set Up Branch Protection**
   - Follow the branch protection rules above
   - This ensures code quality and prevents direct pushes to main

3. **Enable Dependabot**
   - Settings → Security → Dependabot alerts
   - Settings → Security → Dependabot security updates

4. **Create CODEOWNERS File** (Optional)
   ```
   # .github/CODEOWNERS
   * @ArthurKeen
   ```

5. **Set Up Release Workflow** (Optional)
   - Create `.github/workflows/release.yml` for automated releases
   - Configure semantic versioning

6. **Add Repository Badges** (Optional)
   Update README.md with badges:
   ```markdown
   [![CI](https://github.com/ArthurKeen/graph-analytics-ai/workflows/CI/badge.svg)](https://github.com/ArthurKeen/graph-analytics-ai/actions)
   [![codecov](https://codecov.io/gh/ArthurKeen/graph-analytics-ai/branch/main/graph/badge.svg)](https://codecov.io/gh/ArthurKeen/graph-analytics-ai)
   ```

## Verification Checklist

- [ ] Repository description added
- [ ] Topics/tags added
- [ ] Branch protection rules configured
- [ ] CI/CD workflow runs successfully
- [ ] Dependabot enabled
- [ ] Secret scanning enabled
- [ ] Issue templates working
- [ ] README displays correctly
- [ ] LICENSE file visible
- [ ] Initial release tag (v1.0.0) created

## Access Control

**Settings → Collaborators**

Add team members or collaborators as needed:
- **Admin:** Full repository access
- **Write:** Can push code and manage issues
- **Read:** Can view and clone repository

## Archive Settings (Future)

If the repository becomes archived:
- **Settings → General → Danger Zone → Archive this repository**
- This makes the repository read-only

