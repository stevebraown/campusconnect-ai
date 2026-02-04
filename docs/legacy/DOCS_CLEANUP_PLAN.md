# Docs Cleanup & Reorganization Plan

## Summary

This document describes the reorganization of CampusConnect AI documentation and identifies files that can be safely deleted.

## Markdown Files Inventory

| File | Status | New Path | Reason |
|------|--------|----------|--------|
| `README.md` (root) | **KEEP** | – | Core quick-start guide; essential for visibility |
| `CAMPUSCONNECT_AGENT_GUIDE.md` | **MOVE** | `docs/agent-guide.md` | Auto-generated analyzer report; move to docs/ folder |
| `cursor_ai_service_prompt.md` | **KEEP** | – | Master implementation spec; useful for future development; keep at root or archive |
| `docs/AGENT_SETUP_ANSWERS.md` | **MOVE** | `docs/setup-answers.md` | Detailed setup Q&A; rename for clarity |
| `config/README.md` | **KEEP** | – | Explains Firebase credentials setup; keep as-is |
| `docs/TESTING.md` | **NEW** | `docs/TESTING.md` | ✅ Created - comprehensive testing guide |
| `docs/INTEGRATION_CAMPUSCONNECT.md` | **NEW** | `docs/INTEGRATION_CAMPUSCONNECT.md` | ✅ Created - integration checklist & contract |
| `docs/OVERVIEW.md` | **NEW** | `docs/OVERVIEW.md` | ✅ Created - high-level architecture & features |

## Proposed Final Docs Structure

```
docs/
├── OVERVIEW.md                      # High-level overview (replaces root README partially)
├── TESTING.md                       # How to run tests
├── INTEGRATION_CAMPUSCONNECT.md     # Integration checklist & API contract
├── setup-answers.md                 # Detailed setup Q&A (moved from AGENT_SETUP_ANSWERS.md)
└── agent-guide.md                   # Auto-generated analyzer report (moved from root)

README.md (root)                     # Quick-start guide pointing to docs/
.env.example (root)                  # Environment template
Dockerfile (root)                    # Docker build spec
cursor_ai_service_prompt.md (root)   # Master implementation spec (optional archive)
config/README.md                     # Firebase setup instructions
```

## Files Safe to Delete

### 1. `docs/AGENT_SETUP_ANSWERS.md`
- **Why:** Renamed to `docs/setup-answers.md` for clarity; contents are preserved
- **Action:** Delete after renaming
- **Backup:** Content moved to `docs/setup-answers.md`

## Files to Archive (Optional)

### 1. `cursor_ai_service_prompt.md`
- **Status:** Optional archive
- **Reason:** Large master spec file; useful for reference but not needed by end users
- **Recommendation:** Keep at root for now (useful when onboarding new developers), or move to separate `docs/architecture/` folder

## Migration Steps

### Step 1: Move Existing Files
```bash
# Move auto-generated agent guide
mv CAMPUSCONNECT_AGENT_GUIDE.md docs/agent-guide.md

# Rename setup answers for clarity
mv docs/AGENT_SETUP_ANSWERS.md docs/setup-answers.md
```

### Step 2: Verify New Files Created
✅ New docs created:
- `docs/TESTING.md` – Testing guide
- `docs/INTEGRATION_CAMPUSCONNECT.md` – Integration checklist
- `docs/OVERVIEW.md` – Overview & architecture

### Step 3: Update Root README
✅ Already updated `README.md` (root) to be concise and point to docs/

### Step 4: Verify Docs Structure
```bash
# Check final structure
ls -la docs/
# Should show: TESTING.md, INTEGRATION_CAMPUSCONNECT.md, OVERVIEW.md, setup-answers.md, agent-guide.md
```

## Documentation by Category

### Core Setup & Development
- `README.md` (root) – Quick-start (5 min read)
- `docs/OVERVIEW.md` – Full overview (10 min read)
- `docs/TESTING.md` – Testing & development (15 min read)

### Integration with CampusConnect
- `docs/INTEGRATION_CAMPUSCONNECT.md` – Complete integration guide (20 min read)

### Reference & Detailed Info
- `docs/setup-answers.md` – Detailed Q&A
- `docs/agent-guide.md` – Auto-generated analyzer report
- `config/README.md` – Firebase setup specifics

### Implementation Reference (Optional)
- `cursor_ai_service_prompt.md` (root) – Master spec for developers

## Benefits of This Reorganization

✅ **Cleaner root directory** – Only essential files at top level  
✅ **Organized docs/** – All documentation in one place  
✅ **Better discoverability** – Clear naming and structure  
✅ **Reduced redundancy** – Moved auto-generated files to docs/  
✅ **Easier maintenance** – Single source of truth for each topic  

## How End Users Will Navigate Docs

1. **New user?** → Start with `README.md` (root)
2. **Want to understand the service?** → Read `docs/OVERVIEW.md`
3. **Want to run tests?** → See `docs/TESTING.md`
4. **Integrating with main app?** → Follow `docs/INTEGRATION_CAMPUSCONNECT.md`
5. **Need detailed setup?** → Check `docs/setup-answers.md`

## Redundancy Resolution

### Before Reorganization
- `README.md` and `docs/AGENT_SETUP_ANSWERS.md` both covered setup
- `CAMPUSCONNECT_AGENT_GUIDE.md` was auto-generated (not user-facing)
- No clear integration guide

### After Reorganization
- `README.md` – Quick-start only (concise, 200 lines)
- `docs/OVERVIEW.md` – Full context and architecture
- `docs/TESTING.md` – Dedicated testing guide
- `docs/INTEGRATION_CAMPUSCONNECT.md` – Dedicated integration guide
- `docs/setup-answers.md` – Detailed Q&A (preserved from AGENT_SETUP_ANSWERS.md)

## Implementation Checklist

- [x] Create `docs/TESTING.md` with comprehensive testing guide
- [x] Create `docs/INTEGRATION_CAMPUSCONNECT.md` with integration checklist
- [x] Create `docs/OVERVIEW.md` with architecture & features
- [x] Update `README.md` (root) to be concise and point to docs/
- [ ] Move `CAMPUSCONNECT_AGENT_GUIDE.md` → `docs/agent-guide.md`
- [ ] Move `docs/AGENT_SETUP_ANSWERS.md` → `docs/setup-answers.md`
- [ ] Verify all links in docs/ point correctly
- [ ] Delete old `docs/AGENT_SETUP_ANSWERS.md` after migration

## Notes

- **Environment variables**: Documented in `.env.example` (not duplicated in docs)
- **Firestore schema**: Covered in `docs/INTEGRATION_CAMPUSCONNECT.md`
- **LLM strategy**: Covered in `README.md`, `docs/OVERVIEW.md`, and `.env.example`
- **Architecture details**: Covered in `docs/OVERVIEW.md`

