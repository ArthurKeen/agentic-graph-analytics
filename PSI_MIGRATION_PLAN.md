# Migration Plan: PSI General-Purpose Functionality

**Date:** January 2025  
**From:** `psi-graph-analytics/scripts/genai_gae_connection.py`  
**To:** `graph-analytics-ai` library  
**Status:** Implementation In Progress

---

## Executive Summary

This plan outlines the migration of general-purpose GAE functionality from the `psi-graph-analytics` project to the `graph-analytics-ai` library. The migration includes result collection management, query helpers, export utilities, and batch operations.

**Total Methods to Migrate:** 12 methods across 4 categories

---

## Migration Categories

### 1. Result Collection Management (4 methods)
- `ensure_result_collection_indexes()` - Create indexes on 'id' field
- `verify_result_collection()` - Validate collection structure
- `validate_result_schema()` - Validate schema against expected fields
- `compare_result_collections()` - Compare two result collections

**Module:** `graph_analytics_ai/results.py`

### 2. Result Query Helpers (3 methods)
- `cross_reference_results()` - Join two result collections by 'id'
- `get_top_influential_connected()` - Get top PageRank in connected component
- `get_results_with_details()` - Join results with vertex collection data

**Module:** `graph_analytics_ai/queries.py`

### 3. Export Utilities (2 methods)
- `export_results_to_csv()` - Export results to CSV file
- `export_results_to_json()` - Export results to JSON file

**Module:** `graph_analytics_ai/export.py`

### 4. Batch Result Operations (3 methods)
- `bulk_update_result_metadata()` - Add metadata to all results
- `copy_results()` - Copy results between collections
- `delete_results_by_filter()` - Delete results by filter criteria

**Module:** `graph_analytics_ai/results.py` (batch operations section)

---

## Implementation Plan

### Phase 1: Module Structure (Current)
- [x] Create `results.py` module
- [x] Create `queries.py` module
- [x] Create `export.py` module
- [ ] Update `__init__.py` to export new modules

### Phase 2: Core Functionality
- [ ] Implement result collection management methods
- [ ] Implement query helper methods
- [ ] Implement export utility methods
- [ ] Implement batch operation methods

### Phase 3: Integration
- [ ] Add methods to `GenAIGAEConnection` class (for backward compatibility)
- [ ] Update `GAEConnectionBase` abstract class if needed
- [ ] Ensure proper database connection access

### Phase 4: Testing
- [ ] Unit tests for result collection management
- [ ] Unit tests for query helpers
- [ ] Unit tests for export utilities
- [ ] Unit tests for batch operations
- [ ] Integration tests

### Phase 5: Documentation
- [ ] API documentation for new modules
- [ ] Usage examples
- [ ] Migration guide updates

---

## Design Decisions

### 1. Module Organization
- Separate modules for better organization and maintainability
- Each module focuses on a specific concern
- Methods can be used standalone or via connection class

### 2. Database Access
- Methods require database connection
- Can be used via `GenAIGAEConnection.get_db()` or standalone with `get_db_connection()`
- Support both patterns for flexibility

### 3. Error Handling
- Use proper logging instead of print statements
- Raise appropriate exceptions
- Return structured results

### 4. Backward Compatibility
- Add methods to `GenAIGAEConnection` class for existing code
- Methods delegate to module functions
- Maintain same method signatures

---

## Key Implementation Notes

### Result Collection 'id' Field Pattern
- GAE stores results with sequential numeric `_key` values
- Original vertex document ID stored in `id` field
- All cross-referencing uses `id` field, not `_key`
- Indexes on `id` field significantly improve performance

### Authentication
- Methods use existing database connection from `GenAIGAEConnection`
- No additional authentication needed
- Works with both AMP and self-managed deployments

### Configuration
- Uses existing configuration from library
- No additional configuration needed
- Environment variables already supported

---

## Success Criteria

- [ ] All 12 methods successfully migrated
- [ ] Comprehensive test suite (80%+ coverage)
- [ ] Documentation complete
- [ ] Backward compatibility maintained
- [ ] No breaking changes for existing code
- [ ] Ready for psi-graph-analytics migration

---

## Next Steps

1. Implement result collection management module
2. Implement query helpers module
3. Implement export utilities module
4. Add batch operations to results module
5. Create comprehensive tests
6. Update documentation
7. Update `__init__.py` exports

