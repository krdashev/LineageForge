# LineageForge v1.1 Roadmap

## Critical Performance Issues (P0 - Must Fix)

### 1. Database Indexing
**Problem**: 30-second response times  
**Fix**: Add indexes on frequently queried fields
```sql
CREATE INDEX idx_claims_subject_id ON claims(subject_id);
CREATE INDEX idx_claims_predicate ON claims(predicate);
CREATE INDEX idx_claims_source_id ON claims(source_id);
CREATE INDEX idx_claims_active ON claims(is_active);
CREATE INDEX idx_persons_active ON persons(is_active);
CREATE INDEX idx_person_name ON claims(subject_id, predicate) WHERE predicate IN ('has_name', 'has_given_name', 'has_surname');
```

### 2. Query Optimization
**Problem**: Loading all claims for every person  
**Fix**: 
- Add pagination to person list
- Lazy load claims (only fetch when needed)
- Implement claim count caching
- Use `SELECT COUNT(*)` instead of loading all records

### 3. Connection Pooling
**Problem**: Database connection overhead  
**Fix**: 
- Increase connection pool size in `database.py`
- Add connection pooling parameters to DATABASE_URL
- Implement connection retry logic

---

## Critical UI/UX Issues (P0 - Must Fix)

### 4. Graph Visualization Broken
**Problem**: Tree view doesn't work  
**Fix**:
- Debug Cytoscape.js initialization
- Add error handling for empty graphs
- Show "No data" message instead of blank screen
- Add sample data seeder for testing
- Fix API response format if needed

### 5. Job Management
**Problem**: Can't delete failed jobs  
**Fix**:
- Add `DELETE /api/jobs/{id}` endpoint
- Add "Delete" button in UI for each job
- Add "Clear all failed jobs" button
- Add job filtering (show only: all/running/completed/failed)

### 6. Import UX
**Problem**: No feedback during import  
**Fix**:
- Show upload progress bar
- Show import progress (X of Y persons processed)
- Better error messages (not just "500 Internal Server Error")
- Show preview before import (file stats)

---

## High Priority (P1 - Next Sprint)

### 7. Search Improvements
**Problem**: Search is too slow and limited  
**Fix**:
- Add full-text search using PostgreSQL `tsvector`
- Add search by date range
- Add search by place
- Show search result count

### 8. Person Detail Page Loading
**Problem**: Slow to load, shows everything at once  
**Fix**:
- Paginate claims (show 20 at a time)
- Collapsible claim groups (click to expand)
- Defer loading of non-critical data
- Add loading spinners

### 9. Dashboard Performance
**Problem**: Slow to calculate stats  
**Fix**:
- Cache statistics (refresh every 5 minutes)
- Move stats calculation to background job
- Show cached stats with "Last updated: X minutes ago"

### 10. Better Error Messages
**Problem**: Generic 500 errors everywhere  
**Fix**:
- Catch specific exceptions
- Return user-friendly error messages
- Add error boundary in UI
- Log stack traces server-side only

---

## Medium Priority (P2)

### 11. Relationship Parsing
**Problem**: GEDCOM relationships not imported  
**Fix**:
- Parse GEDCOM family records
- Create parent-child claims
- Create spouse claims
- Create sibling claims (inferred)

### 12. Bulk Operations
**Problem**: Can only process one job at a time  
**Fix**:
- Batch identity resolution (process 100 persons at a time)
- Parallel validation
- Bulk claim updates

### 13. Graph Visualization Enhancements
**Problem**: Graph is hard to navigate  
**Fix**:
- Add zoom controls
- Add pan controls
- Add "Fit to screen" button
- Add legend (color-coded by confidence)
- Add filter by relationship type
- Add mini-map for large graphs

### 14. Export Functionality
**Problem**: Can't get data back out  
**Fix**:
- Export filtered persons as CSV
- Export subgraph as GEDCOM
- Export claims as JSON
- Export report as downloadable file (not just view)

### 15. Source Management
**Problem**: No way to view/edit sources  
**Fix**:
- Add `/sources` page
- List all sources with stats
- Edit source reliability score
- Delete source (cascade to claims)

---

## Low Priority (P3 - Nice to Have)

### 16. Advanced Filtering
- Filter persons by:
  - Has birth date
  - Has death date
  - Has conflicts
  - Confidence level
  - Source type
  - Date range
- Save filter presets

### 17. Claim Comparison UI
**Problem**: Hard to compare conflicting claims  
**Fix**:
- Side-by-side claim comparison
- Highlight differences
- Vote on preferred claim
- Manual conflict resolution

### 18. Merge Preview
**Problem**: Can't see what will merge before running  
**Fix**:
- Add "Preview merges" mode
- Show candidate pairs with scores
- Allow manual approve/reject
- Adjust threshold in UI

### 19. Activity Log
- Show recent changes
- Who/what/when for each mutation
- Filterable timeline view

### 20. Keyboard Shortcuts
- `/` - Focus search
- `n` - New import
- `g` - Go to graph
- `h` - Go to home
- `?` - Show help

---

## Technical Debt (P4)

### 21. Code Cleanup
- Remove unused imports
- Add type hints everywhere
- Split large files into smaller modules
- Add docstrings to all functions

### 22. Test Coverage
- Add API tests for all endpoints
- Add UI tests (Playwright)
- Add load tests
- Target 90% code coverage

### 23. Monitoring
- Add Sentry for error tracking
- Add performance monitoring
- Add database query logging
- Add slow query alerts

### 24. Documentation
- Add API documentation (OpenAPI)
- Add user guide with screenshots
- Add troubleshooting guide
- Add video tutorial

### 25. Configuration UI
- Edit settings in dashboard (not env vars)
- Adjust thresholds without redeploy
- Enable/disable features
- Backup/restore settings

---

## Performance Targets for v1.1

| Metric | Current | Target |
|--------|---------|--------|
| Dashboard load | 30s | < 2s |
| Person detail load | 15s | < 1s |
| Search query | 10s | < 500ms |
| Graph render | Broken | < 3s |
| Import 100 persons | 60s | < 10s |
| API p95 latency | Unknown | < 200ms |

---

## Implementation Priority

### Week 1: Critical Fixes
- [ ] Add database indexes
- [ ] Fix graph visualization
- [ ] Add job deletion
- [ ] Optimize dashboard queries

### Week 2: Performance
- [ ] Add caching layer (Redis)
- [ ] Paginate all list views
- [ ] Lazy load claims
- [ ] Connection pool tuning

### Week 3: UX Polish
- [ ] Better error messages
- [ ] Loading states everywhere
- [ ] Import progress feedback
- [ ] Search improvements

### Week 4: Core Features
- [ ] Relationship parsing
- [ ] Export functionality
- [ ] Source management
- [ ] Claim comparison UI

---

## Quick Wins (Do These First)

1. **Add loading spinners** - 30 minutes, huge UX improvement
2. **Add database indexes** - 1 hour, 10x speedup
3. **Fix graph API** - 2 hours, makes feature actually work
4. **Add job delete button** - 30 minutes, removes frustration
5. **Cache dashboard stats** - 1 hour, instant load times
6. **Add pagination** - 2 hours, prevents timeouts
7. **Better error messages** - 2 hours, reduces confusion

**Total: ~9 hours for massive improvement**

---

## Notes

- Focus on **performance first** - nothing else matters if it's too slow
- **Graph visualization is critical** - that's the whole point of the app
- **Job management** needs to work - it's how users do everything
- Don't add new features until existing ones work well
- v1.1 should feel **fast and responsive**, not polished

**Goal**: Turn this from "barely functional" to "actually usable" in 2-4 weeks.
