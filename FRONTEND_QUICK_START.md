# Frontend Quick Start: Interactive Citations

**For:** Frontend Team
**Task:** Make citations [1][2][3] clickable in existing UI
**Time:** ~8 hours
**Complexity:** Medium

---

## 🎯 What You're Building

Transform this:
```
"Employment termination requires one month notice [1] and due process [2]."
```

Into this:
```
"Employment termination requires one month notice [1]← clickable and due process [2]← clickable."
                                                    ↑ hover shows tooltip
                                                    ↑ click opens modal
```

---

## 📥 What Backend Sends You

### Old Response
```json
{
  "answer": "Text without citations",
  "sources": ["doc1", "doc2"]
}
```

### New Response
```json
{
  "answer": "Text with [1] and [2] citations",
  "sources": [
    {
      "citation_id": 1,
      "title": "Employment Act 2007",
      "snippet": "200-char preview...",
      "highlighted_excerpt": "...with <mark>highlighted</mark> terms...",
      "metadata": {
        "freshness_score": 0.95,
        "citation_text": "Employment Act 2007, Section 35"
      }
    }
  ],
  "citation_map": {1: "Employment Act 2007, Section 35"}
}
```

---

## 🔨 What You Need to Do

### 1. Parse Citations in Answer (5 minutes)

```typescript
const citationRegex = /\[(\d+)\]/g;
// Find all [1], [2], [3] in response.answer
```

### 2. Make Citations Clickable (30 minutes)

```typescript
<span
  className="citation-badge"
  onClick={() => openSourceModal(citationId)}
>
  [{citationId}]
</span>
```

**CSS:**
```css
.citation-badge {
  cursor: pointer;
  color: #2563eb;  /* Your link color */
  font-weight: 600;
}

.citation-badge:hover {
  background-color: #dbeafe;
  text-decoration: underline;
}
```

### 3. Add Hover Tooltip (2 hours)

```typescript
<div className="tooltip" onMouseEnter={show} onMouseLeave={hide}>
  <p>{source.snippet}</p>
  <span>Relevance: {source.relevance_score * 100}%</span>
</div>
```

### 4. Create Source Modal (4 hours)

```typescript
<Modal open={isOpen} onClose={close}>
  <h2>{source.title}</h2>
  <p>Court: {source.metadata.court_name}</p>
  <p>Date: {source.metadata.document_date}</p>
  <div>{source.full_content}</div>
  <a href={source.url}>View Original</a>
</Modal>
```

### 5. Add Verification Button (1 hour)

```typescript
<button onClick={async () => {
  const result = await fetch(`/api/v1/counsel/sources/${sourceId}/verify`);
  showVerificationStatus(result);
}}>
  Verify Source
</button>
```

---

## 📂 Files to Create

1. **types/rag.types.ts** - TypeScript definitions (copy from guide)
2. **utils/citation.utils.ts** - Helper functions
3. **components/CitationBadge.tsx** - Clickable [1] badge
4. **components/CitationTooltip.tsx** - Hover preview
5. **components/SourceModal.tsx** - Full source display

---

## 🎨 Design Rules

### ❌ DO NOT
- Change existing UI layout
- Create new design system
- Modify color schemes
- Replace existing modals

### ✅ DO
- Use existing link colors
- Use existing modal component
- Use existing button styles
- Match existing spacing

---

## 🧪 Test These

- [ ] Click [1] opens modal ✓
- [ ] Hover shows tooltip ✓
- [ ] `<mark>` tags render as highlights ✓
- [ ] Mobile responsive ✓
- [ ] Keyboard accessible (Enter/Space) ✓
- [ ] "Verify Source" button works ✓

---

## 🆘 Need Backend Change?

**Missing UUID for sources:**
```typescript
// TEMP: Use citation_id
const sourceId = source.citation_id;

// FUTURE: Backend will add
const sourceId = source.source_id; // UUID
```

Ask backend team to add `source_id` UUID field to response.

---

## 📞 Questions?

See full guide: **FRONTEND_INTEGRATION_GUIDE.md**

**Quick references:**
- API docs: Lines 50-150 of integration guide
- TypeScript types: Lines 151-250
- Component examples: Lines 300-600
- CSS snippets: Lines 650-750

---

**Estimated time:** 8 hours
**Difficulty:** Medium
**Breaking changes:** None (backward compatible)
