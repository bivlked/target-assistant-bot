# Development Rules - Target Assistant Bot

## 📅 Date Management

### Rule: Always Use Current Date
**CRITICAL**: Never hardcode dates in documentation or code files.

**Correct Process:**
1. Always get current date via PowerShell before adding dates to files:
   ```powershell
   Get-Date -Format "yyyy-MM-dd"
   ```

2. Use the exact date returned by the command

3. Format standards:
   - **ADR Documents**: `**Date**: 2025-06-08`
   - **Commit Messages**: Use current date context
   - **Documentation**: ISO format `YYYY-MM-DD`

**❌ Wrong**: `**Date**: 2025-01-08` (when actual date is different)  
**✅ Correct**: `**Date**: 2025-06-08` (using PowerShell command result)

## 🌿 Git Workflow

### Branch Management
- **Feature Branches**: `feature/description-name`
- **Main Branch**: Always keep stable
- **Cleanup**: Delete merged feature branches after successful merge

### Commit Standards
- Use conventional commits: `feat(scope): description`
- Include scope: `ui`, `architecture`, `testing`, `docs`
- Descriptive messages with actual impact

### Testing Before Merge
- **Mandatory**: Comprehensive local testing before merge to main
- Verify all systems work after major architectural changes
- Get explicit confirmation before merging

## 🏗️ Architecture Principles

### Modular Architecture
- Follow Domain-Driven Design principles
- Use Dependency Injection for loose coupling
- Repository pattern for data access
- Clean Architecture layers: Domain → Application → Infrastructure → Presentation

### Code Quality
- All pre-commit hooks must pass
- MyPy type checking required
- Black formatting enforced
- Ruff linting standards

## 🧪 Testing Strategy

### Test Coverage
- Target: 99%+ coverage
- Fix failing tests before new features
- Strategic test enhancement approach
- Performance regression detection

### Test Types
- Unit: 75% of test suite
- Integration: 20% of test suite  
- Performance: 5% of test suite

## 📝 Documentation

### Bilingual Support
- Russian primary language
- English ready structure
- GitHub-native documentation system
- Auto-generation where possible

### Change Documentation
- Update ADRs (Architecture Decision Records)
- Maintain implementation plans
- Track progress in memory bank files

---
**Last Updated**: 2025-06-08  
**Version**: 1.0  
**Status**: Active 