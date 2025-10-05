# 📦 Handoff to Frontend Team

**Date:** 2025-10-04
**Backend Status:** ✅ Phase 1 Complete
**Your Task:** Phase 2.1 - Interactive Citation Component
**Estimated Time:** 8 hours

---

## 📋 What We Built for You

### ✅ Backend Enhancements Complete

1. **Enhanced RAG Response** with inline citations `[1]`, `[2]`, `[3]`
2. **Structured Sources** with rich metadata (snippets, highlights, freshness)
3. **Source Verification Endpoint** - Check if URLs are still accessible
4. **Full Source Endpoint** - Get complete content for modals
5. **TypeScript-Ready** - All types defined for you

---

## 📁 Files for Your Team

### **Primary Guide** (Read This First)
📄 **[FRONTEND_INTEGRATION_GUIDE.md](FRONTEND_INTEGRATION_GUIDE.md)**
- Complete implementation guide (50+ pages)
- TypeScript type definitions
- Component examples (copy-paste ready)
- CSS snippets
- API documentation
- Testing checklist

### **Quick Reference**
📄 **[FRONTEND_QUICK_START.md](FRONTEND_QUICK_START.md)**
- TL;DR version (2 pages)
- What changed in API responses
- What you need to do (5 steps)
- Quick checklist

### **Backend Documentation**
📄 **[PHASE_1_BACKEND_COMPLETE.md](PHASE_1_BACKEND_COMPLETE.md)**
- What we built
- API endpoints
- Database changes
- Performance metrics

---

## 🎯 Your Mission

Make citations **clickable and interactive** without changing existing UI design.

### Before (What User Sees Now)
```
"Employment termination requires one month notice [1] and due process [2]."
```

### After (What You'll Build)
```
"Employment termination requires one month notice [1]← clickable and due process [2]← clickable."
                                                    ↑ hover shows tooltip
                                                    ↑ click opens modal
```

---

## 🚀 5-Step Implementation

### Step 1: Add TypeScript Types (30 min)
Copy from **FRONTEND_INTEGRATION_GUIDE.md** lines 150-250

```typescript
// types/rag.types.ts
export interface StructuredSource {
  source_id: string;  // UUID for API calls
  citation_id: number;  // [1], [2], [3]
  title: string;
  snippet: string;  // 200-char preview
  highlighted_excerpt: string;  // With <mark> tags
  metadata: {
    freshness_score: number;
    court_name: string;
    // ... more fields
  };
}
```

### Step 2: Update API Service (30 min)
Copy from guide lines 250-350

```typescript
// services/api.service.ts
async query(question: string): Promise<EnhancedRAGResponse> {
  const response = await fetch('/api/v1/counsel/query', {
    method: 'POST',
    body: JSON.stringify({ query: question })
  });
  return response.json();
}
```

### Step 3: Create Citation Components (3 hours)

**CitationBadge.tsx** - Clickable [1] badge
**CitationTooltip.tsx** - Hover preview
**SourceModal.tsx** - Full source display

All code provided in guide (lines 350-650).

### Step 4: Integrate into Existing Chat (2 hours)

Find where you render `response.answer` and wrap citations:

```typescript
// Before
<div>{response.answer}</div>

// After
<div>{renderCitationsWithTooltips(response.answer, response.sources)}</div>
```

### Step 5: Add Minimal Styling (1 hour)

Only add interactivity styles (guide lines 650-750):

```css
.citation-badge {
  cursor: pointer;
  color: #2563eb;  /* Your existing link color */
}

.citation-badge:hover {
  background-color: #dbeafe;
}
```

### Step 6: Test & Deploy (1.5 hours)

- [ ] Citations clickable
- [ ] Tooltips show on hover
- [ ] Modal opens with full content
- [ ] Mobile responsive
- [ ] Keyboard accessible

---

## 🔌 New API Endpoints You'll Use

### 1. Enhanced Query (Already Using This)
```
POST /api/v1/counsel/query
```

**Response changed - now includes:**
```json
{
  "answer": "Text with [1] citations",
  "sources": [
    {
      "source_id": "8b637e45-c4ff-4c85-8617-d522c46ecea6",  // NEW
      "citation_id": 1,
      "snippet": "Preview text...",
      "highlighted_excerpt": "Text with <mark>highlights</mark>"
    }
  ]
}
```

### 2. Verify Source (New)
```
GET /api/v1/counsel/sources/{source_id}/verify
```

Use when: User clicks "Verify Source" button

### 3. Get Full Source (New)
```
GET /api/v1/counsel/sources/{source_id}/full
```

Use when: User clicks citation or "View Full Source"

---

## 📊 Response Structure Changes

### What Changed in `/query` Response

**Added Fields:**
- `sources[].source_id` - UUID for API calls
- `sources[].snippet` - 200-char preview
- `sources[].highlighted_excerpt` - With `<mark>` tags
- `sources[].metadata.freshness_score` - 0.0 to 1.0
- `citation_map` - Quick reference `{1: "Title"}`

**Example:**
```json
{
  "success": true,
  "answer": "Employment termination requires notice [1].",
  "sources": [
    {
      "source_id": "uuid-here",
      "citation_id": 1,
      "title": "Employment Act 2007",
      "snippet": "Section 35 provides...",
      "highlighted_excerpt": "...one month <mark>notice</mark>...",
      "metadata": {
        "freshness_score": 0.95,
        "citation_text": "Employment Act 2007, Section 35"
      }
    }
  ],
  "citation_map": {
    "1": "Employment Act 2007, Section 35"
  }
}
```

---

## 🎨 Design Guidelines

### ❌ DO NOT
- Create new design system
- Change existing colors
- Replace modal component
- Modify layout

### ✅ DO
- Use existing link color for citations
- Use existing modal for source display
- Match existing button styles
- Keep current spacing

### Example Integration
```typescript
// Use YOUR existing modal component
<YourExistingModal open={isOpen} onClose={onClose}>
  <SourceContent source={source} />
</YourExistingModal>
```

---

## 🧪 Testing Checklist

Copy from guide (line 750+):

**Functional:**
- [ ] Click [1] opens modal
- [ ] Hover shows tooltip
- [ ] Verify button works
- [ ] `<mark>` highlights render

**Visual:**
- [ ] Matches existing design
- [ ] Mobile responsive
- [ ] Tooltip doesn't overflow

**Accessibility:**
- [ ] Keyboard navigation (Enter/Space)
- [ ] ARIA labels
- [ ] Screen reader compatible

---

## 💡 Tips

### Quick Wins
1. **Start with CitationBadge** - Simplest component
2. **Test with real data** - Backend is live
3. **Use existing components** - Don't reinvent modals/tooltips
4. **Copy-paste code** - All examples are production-ready

### Common Pitfalls
1. **Don't parse HTML** - Use `dangerouslySetInnerHTML` for `<mark>` tags
2. **Handle missing data** - Use optional chaining `source?.metadata?.court_name`
3. **Mobile tooltips** - Position based on viewport
4. **Loading states** - Modal fetch takes ~50ms

---

## 📞 Support

### Need Help?

1. **Check the guide first:** FRONTEND_INTEGRATION_GUIDE.md
2. **Search for error:** Ctrl+F in guide
3. **Backend questions:** Contact backend team

### Common Questions

**Q: Where do I get `source_id`?**
A: It's in `response.sources[].source_id`

**Q: How to render `<mark>` tags?**
A: `<div dangerouslySetInnerHTML={{ __html: highlighted_excerpt }} />`

**Q: Can I use my existing tooltip library?**
A: Yes! Just pass `source.snippet` as content

**Q: Modal is slow to load**
A: It's fetching full content (~50ms). Add loading spinner.

---

## ✅ Definition of Done

Your implementation is complete when:

1. ✅ User can click [1], [2], [3] to open modal
2. ✅ Hovering over citation shows tooltip with snippet
3. ✅ Query terms are highlighted yellow in tooltips
4. ✅ Modal shows full source with metadata
5. ✅ "Verify Source" button checks URL accessibility
6. ✅ Freshness indicators show (🟢🟡🔴)
7. ✅ Works on mobile
8. ✅ Keyboard accessible
9. ✅ No breaking changes to existing UI
10. ✅ Tests pass

---

## 📦 Deliverables

When done, provide:

1. **Demo video** - Show clicking citations, tooltips, modal
2. **Screenshots** - Mobile and desktop
3. **Test results** - Checklist completed
4. **Code review** - PR with components

---

## 🚢 Deployment

### Before Deploy
- [ ] Test on staging with real API
- [ ] Verify all endpoints work
- [ ] Check mobile responsive
- [ ] Run accessibility audit

### After Deploy
- [ ] Monitor error logs
- [ ] Check API call volume
- [ ] Gather user feedback

---

## 📈 Success Metrics

Track these:
- Citation click rate
- Modal open rate
- Source verification usage
- Tooltip engagement
- Mobile vs desktop usage

---

**Ready to Start?**

1. Read **FRONTEND_INTEGRATION_GUIDE.md** (30 min)
2. Copy TypeScript types
3. Create components (use examples)
4. Integrate into chat
5. Test & deploy

**Estimated Time:** 8 hours total

**Questions?** See guide or contact backend team.

---

**Last Updated:** 2025-10-04
**Backend Version:** Phase 1 Complete
**Frontend Target:** Phase 2.1 Complete
