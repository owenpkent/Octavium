# Branch Structure

## Overview

This repository uses a two-branch workflow:

### `main` (Production Branch)
- **Purpose**: Stable, production-ready code
- **Content**: Release version without 25-key keyboard and harmonic table
- **Protected**: Should only receive merges from development after testing
- **Releases**: All releases are tagged from this branch

### `development` (Development Branch)
- **Purpose**: Active development and experimental features
- **Content**: Includes all features including 25-key keyboard and harmonic table
- **Usage**: All new features and changes should be developed here
- **Testing**: Features should be tested here before merging to main

## Workflow

1. **Feature Development**
   - Work on the `development` branch
   - Test thoroughly
   - Commit and push changes

2. **Creating a Release**
   - Merge tested features from `development` to `main`
   - Remove any experimental features if needed
   - Tag the release
   - Build and publish the executable

3. **Hotfixes**
   - Can be applied directly to `main` if urgent
   - Should be backported to `development` afterwards

## Current State

- **main**: Contains v1.0.0 release (no 25-key, no harmonic table)
- **development**: Contains all features including experimental ones

## Branch History

- Originally had three branches: `main`, `development`, and `initial-release`
- Reorganized on October 30, 2025:
  - `initial-release` → became new `main`
  - Old `main` → became new `development`
  - Old `development` → replaced with old `main` content
