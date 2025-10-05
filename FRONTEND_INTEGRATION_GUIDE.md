# Frontend Integration Guide: Interactive RAG Citations

**Version:** 1.0
**Date:** 2025-10-04
**Backend Phase:** Phase 1 Complete ✅
**Target:** Frontend Team - Phase 2.1 Implementation

---

## 📋 Table of Contents

1. [Overview](#overview)
2. [API Response Structure Changes](#api-response-structure-changes)
3. [New API Endpoints](#new-api-endpoints)
4. [TypeScript Type Definitions](#typescript-type-definitions)
5. [Implementation Steps](#implementation-steps)
6. [Component Examples](#component-examples)
7. [Styling Guide](#styling-guide)
8. [Testing Checklist](#testing-checklist)

---

## 🎯 Overview

The backend now returns **structured sources with inline citations** in the format `[1]`, `[2]`, `[3]`. Your task is to make these citations **interactive** without changing the existing UI layout or design.

### What Changed in Backend Responses

**Before:**
```json
{
  "answer": "Employment termination requires notice and proper procedure.",
  "sources": ["doc1", "doc2"],
  "similarities": [0.95, 0.89]
}
```

**After:**
```json
{
  "answer": "Employment termination requires one month notice [1] and must follow due process [2].",
  "sources": [
    {
      "citation_id": 1,
      "title": "Employment Act 2007, Section 35",
      "url": "http://kenyalaw.org/...",
      "snippet": "Section 35 of the Employment Act, 2007 provides...",
      "highlighted_excerpt": "...one month's <mark>notice</mark>...",
      "relevance_score": 0.95,
      "metadata": {
        "freshness_score": 0.95,
        "citation_text": "Employment Act 2007, Section 35",
        "court_name": null,
        "document_date": "2007-10-15"
      }
    }
  ],
  "citation_map": {
    "1": "Employment Act 2007, Section 35",
    "2": "ABC Ltd v XYZ [2024] eKLR"
  }
}
```

---

## 📡 API Response Structure Changes

### Enhanced RAG Response

**Endpoint:** `POST /api/v1/counsel/query`
**Request Body:** (unchanged)
```json
{
  "query": "What is the notice period for employment termination?",
  "use_enhanced_rag": true
}
```

**Response Body:** (NEW structure)
```typescript
{
  success: boolean;
  answer: string;  // Contains [1], [2], [3] inline citations
  sources: StructuredSource[];  // Array of rich source objects
  citation_map: { [key: number]: string };  // Citation reference map
  model_used: string;
  retrieved_documents: number;
  context_tokens: number;
  total_tokens: number;
  cost_estimate: {
    input: number;
    output: number;
    total: number;
  };
  latency_ms: number;
  metadata: {
    confidence: number;  // 0.0 - 1.0
    freshness_score: number;  // 0.0 - 1.0
    citation_count: number;
    use_citations: boolean;
  };
}
```

### StructuredSource Object

```typescript
interface StructuredSource {
  citation_id: number;  // 1, 2, 3, etc.
  title: string;  // "Employment Act 2007, Section 35"
  url: string;  // Full URL to source
  snippet: string;  // 200-char preview
  document_type: "legislation" | "judgment" | "regulation" | "constitution";
  legal_area: string | null;  // "employment_law", "criminal", etc.
  relevance_score: number;  // 0.0 - 1.0
  highlighted_excerpt: string;  // Snippet with <mark> tags
  metadata: SourceMetadata;
}

interface SourceMetadata {
  source: string;  // "kenya_law"
  crawled_at: string | null;  // ISO 8601 datetime
  last_verified: string | null;  // ISO 8601 datetime
  freshness_score: number;  // 0.0 - 1.0 (1.0 = today)
  document_date: string | null;  // ISO 8601 date
  court_name: string | null;  // For judgments
  case_number: string | null;  // For judgments
  act_chapter: string | null;  // For legislation
  citation_text: string;  // Formatted citation
  crawl_status: "active" | "stale" | "broken";
}
```

---

## 🔌 New API Endpoints

### 1. Verify Source Accessibility

**Endpoint:** `GET /api/v1/counsel/sources/{source_id}/verify`

**Purpose:** Check if a source URL is still accessible and update verification status.

**Request:**
```typescript
// Extract source_id from source object (you'll need to add UUID to response)
const sourceId = source.metadata.source_id; // We'll add this field

fetch(`/api/v1/counsel/sources/${sourceId}/verify`)
```

**Response:**
```json
{
  "source_id": "8b637e45-c4ff-4c85-8617-d522c46ecea6",
  "title": "Employment Act 2007, Section 35",
  "url": "http://kenyalaw.org/...",
  "is_accessible": true,
  "last_verified": "2025-10-04T16:49:37",
  "crawl_status": "active",
  "freshness_score": 0.95,
  "http_status": 200,
  "verification_time_ms": 150.5
}
```

**Usage:**
```typescript
async function verifySource(sourceId: string): Promise<VerificationResult> {
  const response = await fetch(
    `/api/v1/counsel/sources/${sourceId}/verify`
  );
  return response.json();
}
```

### 2. Get Full Source Content

**Endpoint:** `GET /api/v1/counsel/sources/{source_id}/full`

**Purpose:** Retrieve complete source content for modal display.

**Request:**
```typescript
fetch(`/api/v1/counsel/sources/${sourceId}/full`)
```

**Response:**
```json
{
  "source_id": "866b847c-a05d-425b-a5cf-c099cab71318",
  "title": "ABC Ltd v XYZ [2024] eKLR",
  "url": "http://kenyalaw.org/caselaw/cases/view/123456",
  "full_content": "The Employment and Labour Relations Court held that...",
  "summary": "Case summary here...",
  "document_type": "judgment",
  "legal_area": "employment_law",
  "metadata": {
    "judges": ["Hon. Justice ABC"],
    "legal_issues": ["unfair dismissal", "damages"],
    "outcome": "Employee awarded damages"
  },
  "crawled_at": "2025-10-04T16:49:37",
  "last_verified": "2025-10-04T16:50:00",
  "document_date": "2024-06-15",
  "court_name": "Employment and Labour Relations Court",
  "case_number": "Cause No. 123 of 2024",
  "act_chapter": null
}
```

**Usage:**
```typescript
async function getFullSource(sourceId: string): Promise<FullSource> {
  const response = await fetch(
    `/api/v1/counsel/sources/${sourceId}/full`
  );
  return response.json();
}
```

---

## 📝 TypeScript Type Definitions

**File:** `types/rag.types.ts` (create this file)

```typescript
// ============================================================================
// RAG RESPONSE TYPES
// ============================================================================

export interface EnhancedRAGResponse {
  success: boolean;
  answer: string;
  sources: StructuredSource[];
  citation_map: CitationMap;
  model_used: string;
  retrieved_documents: number;
  context_tokens: number;
  total_tokens: number;
  cost_estimate: CostEstimate;
  latency_ms: number;
  metadata: ResponseMetadata;
}

export interface StructuredSource {
  citation_id: number;
  title: string;
  url: string;
  snippet: string;
  document_type: DocumentType;
  legal_area: string | null;
  relevance_score: number;
  highlighted_excerpt: string;
  metadata: SourceMetadata;
}

export interface SourceMetadata {
  source: string;
  crawled_at: string | null;
  last_verified: string | null;
  freshness_score: number;
  document_date: string | null;
  court_name: string | null;
  case_number: string | null;
  act_chapter: string | null;
  citation_text: string;
  crawl_status: CrawlStatus;
}

export interface ResponseMetadata {
  confidence: number;
  freshness_score: number;
  citation_count: number;
  use_citations: boolean;
}

export interface CostEstimate {
  input: number;
  output: number;
  total: number;
}

export type CitationMap = Record<number, string>;

export type DocumentType =
  | "legislation"
  | "judgment"
  | "regulation"
  | "constitution";

export type CrawlStatus = "active" | "stale" | "broken";

// ============================================================================
// SOURCE VERIFICATION TYPES
// ============================================================================

export interface VerificationResult {
  source_id: string;
  title: string;
  url: string;
  is_accessible: boolean;
  last_verified: string;
  crawl_status: CrawlStatus;
  freshness_score: number;
  http_status: number | null;
  verification_time_ms: number;
}

export interface FullSource {
  source_id: string;
  title: string;
  url: string;
  full_content: string;
  summary: string | null;
  document_type: DocumentType;
  legal_area: string | null;
  metadata: Record<string, any>;
  crawled_at: string | null;
  last_verified: string | null;
  document_date: string | null;
  court_name: string | null;
  case_number: string | null;
  act_chapter: string | null;
}

// ============================================================================
// UTILITY TYPES
// ============================================================================

export interface FreshnessIndicator {
  score: number;
  color: "green" | "yellow" | "red";
  label: "Fresh" | "Moderate" | "Outdated";
  icon: "🟢" | "🟡" | "🔴";
}
```

---

## 🔨 Implementation Steps

### Step 1: Update API Service Layer

**File:** `services/api.service.ts` (or wherever you handle API calls)

```typescript
import type {
  EnhancedRAGResponse,
  VerificationResult,
  FullSource
} from '../types/rag.types';

export class RAGService {
  private baseURL = '/api/v1/counsel';

  /**
   * Query with enhanced RAG (returns inline citations)
   */
  async query(question: string): Promise<EnhancedRAGResponse> {
    const response = await fetch(`${this.baseURL}/query`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        query: question,
        use_enhanced_rag: true,
        // use_citations is true by default in backend
      }),
    });

    if (!response.ok) {
      throw new Error(`Query failed: ${response.statusText}`);
    }

    return response.json();
  }

  /**
   * Verify source accessibility
   */
  async verifySource(sourceId: string): Promise<VerificationResult> {
    const response = await fetch(
      `${this.baseURL}/sources/${sourceId}/verify`
    );

    if (!response.ok) {
      throw new Error(`Verification failed: ${response.statusText}`);
    }

    return response.json();
  }

  /**
   * Get full source content for modal
   */
  async getFullSource(sourceId: string): Promise<FullSource> {
    const response = await fetch(
      `${this.baseURL}/sources/${sourceId}/full`
    );

    if (!response.ok) {
      throw new Error(`Failed to fetch source: ${response.statusText}`);
    }

    return response.json();
  }
}

export const ragService = new RAGService();
```

### Step 2: Create Citation Parser Utility

**File:** `utils/citation.utils.ts`

```typescript
import type { FreshnessIndicator } from '../types/rag.types';

/**
 * Parse answer text and extract citation references [1], [2], [3]
 */
export function parseCitations(answerText: string): {
  text: string;
  citations: number[];
} {
  const citationRegex = /\[(\d+)\]/g;
  const citations: number[] = [];

  let match;
  while ((match = citationRegex.exec(answerText)) !== null) {
    const citationId = parseInt(match[1], 10);
    if (!citations.includes(citationId)) {
      citations.push(citationId);
    }
  }

  return {
    text: answerText,
    citations: citations.sort((a, b) => a - b),
  };
}

/**
 * Convert answer text with [1] citations to HTML with clickable spans
 */
export function renderCitations(
  answerText: string,
  onCitationClick: (citationId: number) => void
): React.ReactNode {
  const parts: React.ReactNode[] = [];
  const citationRegex = /\[(\d+)\]/g;

  let lastIndex = 0;
  let match;

  while ((match = citationRegex.exec(answerText)) !== null) {
    // Add text before citation
    if (match.index > lastIndex) {
      parts.push(answerText.substring(lastIndex, match.index));
    }

    // Add citation as clickable element
    const citationId = parseInt(match[1], 10);
    parts.push(
      <CitationBadge
        key={`citation-${match.index}-${citationId}`}
        citationId={citationId}
        onClick={() => onCitationClick(citationId)}
      />
    );

    lastIndex = match.index + match[0].length;
  }

  // Add remaining text
  if (lastIndex < answerText.length) {
    parts.push(answerText.substring(lastIndex));
  }

  return parts;
}

/**
 * Get freshness indicator based on score
 */
export function getFreshnessIndicator(score: number): FreshnessIndicator {
  if (score >= 0.85) {
    return {
      score,
      color: 'green',
      label: 'Fresh',
      icon: '🟢',
    };
  } else if (score >= 0.5) {
    return {
      score,
      color: 'yellow',
      label: 'Moderate',
      icon: '🟡',
    };
  } else {
    return {
      score,
      color: 'red',
      label: 'Outdated',
      icon: '🔴',
    };
  }
}

/**
 * Format document date
 */
export function formatDocumentDate(dateString: string | null): string {
  if (!dateString) return 'Unknown';

  const date = new Date(dateString);
  return date.toLocaleDateString('en-KE', {
    year: 'numeric',
    month: 'long',
    day: 'numeric',
  });
}

/**
 * Calculate relative time for last verified
 */
export function getRelativeTime(dateString: string | null): string {
  if (!dateString) return 'Never verified';

  const date = new Date(dateString);
  const now = new Date();
  const diffMs = now.getTime() - date.getTime();
  const diffMins = Math.floor(diffMs / 60000);
  const diffHours = Math.floor(diffMs / 3600000);
  const diffDays = Math.floor(diffMs / 86400000);

  if (diffMins < 1) return 'Just now';
  if (diffMins < 60) return `${diffMins} minute${diffMins > 1 ? 's' : ''} ago`;
  if (diffHours < 24) return `${diffHours} hour${diffHours > 1 ? 's' : ''} ago`;
  if (diffDays < 30) return `${diffDays} day${diffDays > 1 ? 's' : ''} ago`;

  return date.toLocaleDateString();
}
```

### Step 3: Create Citation Badge Component

**File:** `components/CitationBadge.tsx`

```typescript
import React from 'react';
import type { StructuredSource } from '../types/rag.types';

interface CitationBadgeProps {
  citationId: number;
  source?: StructuredSource;
  onClick: () => void;
}

/**
 * Clickable citation badge [1], [2], [3]
 *
 * DO NOT change styling - just add interactivity to existing design
 */
export const CitationBadge: React.FC<CitationBadgeProps> = ({
  citationId,
  source,
  onClick,
}) => {
  return (
    <span
      className="citation-badge"
      onClick={onClick}
      role="button"
      tabIndex={0}
      onKeyPress={(e) => {
        if (e.key === 'Enter' || e.key === ' ') {
          onClick();
        }
      }}
      aria-label={`Citation ${citationId}${source ? `: ${source.title}` : ''}`}
      data-citation-id={citationId}
      title={source?.snippet || `Source ${citationId}`}
    >
      [{citationId}]
    </span>
  );
};

// ADD THIS CSS to your existing stylesheet (do not create new styles)
// Just enhance the existing .citation-badge class if it exists

/**
 * CSS to add (append to existing styles):
 *
 * .citation-badge {
 *   cursor: pointer;
 *   color: #2563eb;  // Use your existing link color
 *   font-weight: 600;
 *   text-decoration: none;
 *   transition: all 0.2s ease;
 *   padding: 0 2px;
 *   border-radius: 2px;
 * }
 *
 * .citation-badge:hover {
 *   background-color: #dbeafe;  // Light blue highlight
 *   text-decoration: underline;
 * }
 *
 * .citation-badge:focus {
 *   outline: 2px solid #2563eb;
 *   outline-offset: 2px;
 * }
 */
```

### Step 4: Create Tooltip Component

**File:** `components/CitationTooltip.tsx`

```typescript
import React, { useState } from 'react';
import type { StructuredSource } from '../types/rag.types';
import { getFreshnessIndicator } from '../utils/citation.utils';

interface CitationTooltipProps {
  source: StructuredSource;
  children: React.ReactNode;
}

/**
 * Hover tooltip showing source snippet
 *
 * IMPORTANT: This wraps the CitationBadge. Position over existing UI.
 */
export const CitationTooltip: React.FC<CitationTooltipProps> = ({
  source,
  children,
}) => {
  const [isVisible, setIsVisible] = useState(false);
  const freshness = getFreshnessIndicator(source.metadata.freshness_score);

  return (
    <div
      className="citation-tooltip-wrapper"
      onMouseEnter={() => setIsVisible(true)}
      onMouseLeave={() => setIsVisible(false)}
      style={{ position: 'relative', display: 'inline' }}
    >
      {children}

      {isVisible && (
        <div className="citation-tooltip" role="tooltip">
          <div className="citation-tooltip-header">
            <span className="citation-tooltip-title">{source.title}</span>
            <span className="citation-tooltip-freshness" title={`Freshness: ${freshness.score.toFixed(2)}`}>
              {freshness.icon}
            </span>
          </div>

          <div className="citation-tooltip-content">
            {/* Render highlighted excerpt with <mark> tags */}
            <p dangerouslySetInnerHTML={{ __html: source.highlighted_excerpt }} />
          </div>

          <div className="citation-tooltip-footer">
            <span className="citation-tooltip-relevance">
              Relevance: {(source.relevance_score * 100).toFixed(0)}%
            </span>
            <span className="citation-tooltip-type">
              {source.document_type}
            </span>
          </div>
        </div>
      )}
    </div>
  );
};

/**
 * CSS to add (create new or append to existing):
 *
 * .citation-tooltip {
 *   position: absolute;
 *   bottom: 100%;
 *   left: 50%;
 *   transform: translateX(-50%);
 *   margin-bottom: 8px;
 *   padding: 12px;
 *   background: white;
 *   border: 1px solid #e5e7eb;
 *   border-radius: 8px;
 *   box-shadow: 0 10px 15px -3px rgba(0, 0, 0, 0.1);
 *   width: 320px;
 *   max-width: 90vw;
 *   z-index: 1000;
 *   font-size: 0.875rem;
 *   line-height: 1.5;
 * }
 *
 * .citation-tooltip-header {
 *   display: flex;
 *   justify-content: space-between;
 *   align-items: center;
 *   margin-bottom: 8px;
 *   padding-bottom: 8px;
 *   border-bottom: 1px solid #e5e7eb;
 * }
 *
 * .citation-tooltip-title {
 *   font-weight: 600;
 *   color: #111827;
 *   font-size: 0.875rem;
 * }
 *
 * .citation-tooltip-content {
 *   color: #4b5563;
 *   margin-bottom: 8px;
 * }
 *
 * .citation-tooltip-content mark {
 *   background-color: #fef3c7;
 *   padding: 1px 2px;
 *   border-radius: 2px;
 * }
 *
 * .citation-tooltip-footer {
 *   display: flex;
 *   justify-content: space-between;
 *   font-size: 0.75rem;
 *   color: #6b7280;
 * }
 *
 * .citation-tooltip::before {
 *   content: '';
 *   position: absolute;
 *   top: 100%;
 *   left: 50%;
 *   transform: translateX(-50%);
 *   border: 6px solid transparent;
 *   border-top-color: white;
 * }
 */
```

### Step 5: Create Source Modal Component

**File:** `components/SourceModal.tsx`

```typescript
import React, { useEffect, useState } from 'react';
import type { FullSource, VerificationResult } from '../types/rag.types';
import { ragService } from '../services/api.service';
import {
  formatDocumentDate,
  getRelativeTime,
  getFreshnessIndicator
} from '../utils/citation.utils';

interface SourceModalProps {
  sourceId: string;
  isOpen: boolean;
  onClose: () => void;
}

/**
 * Modal for displaying full source content
 *
 * IMPORTANT: Use your existing modal component/library.
 * This is just the content structure.
 */
export const SourceModal: React.FC<SourceModalProps> = ({
  sourceId,
  isOpen,
  onClose,
}) => {
  const [source, setSource] = useState<FullSource | null>(null);
  const [verification, setVerification] = useState<VerificationResult | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const [isVerifying, setIsVerifying] = useState(false);

  useEffect(() => {
    if (isOpen && sourceId) {
      loadSource();
    }
  }, [isOpen, sourceId]);

  async function loadSource() {
    setIsLoading(true);
    try {
      const data = await ragService.getFullSource(sourceId);
      setSource(data);
    } catch (error) {
      console.error('Failed to load source:', error);
    } finally {
      setIsLoading(false);
    }
  }

  async function handleVerify() {
    if (!sourceId) return;

    setIsVerifying(true);
    try {
      const result = await ragService.verifySource(sourceId);
      setVerification(result);
    } catch (error) {
      console.error('Failed to verify source:', error);
    } finally {
      setIsVerifying(false);
    }
  }

  if (!isOpen || !source) return null;

  const freshness = getFreshnessIndicator(
    verification?.freshness_score || 0.5
  );

  return (
    // USE YOUR EXISTING MODAL WRAPPER HERE
    // This is just the content structure
    <div className="source-modal">
      <div className="source-modal-header">
        <h2>{source.title}</h2>
        <button onClick={onClose} aria-label="Close modal">
          ×
        </button>
      </div>

      <div className="source-modal-body">
        {/* Metadata Section */}
        <div className="source-metadata">
          <div className="metadata-row">
            <span className="metadata-label">Type:</span>
            <span className="metadata-value">{source.document_type}</span>
          </div>

          {source.legal_area && (
            <div className="metadata-row">
              <span className="metadata-label">Legal Area:</span>
              <span className="metadata-value">{source.legal_area}</span>
            </div>
          )}

          {source.court_name && (
            <div className="metadata-row">
              <span className="metadata-label">Court:</span>
              <span className="metadata-value">{source.court_name}</span>
            </div>
          )}

          {source.case_number && (
            <div className="metadata-row">
              <span className="metadata-label">Case Number:</span>
              <span className="metadata-value">{source.case_number}</span>
            </div>
          )}

          {source.act_chapter && (
            <div className="metadata-row">
              <span className="metadata-label">Chapter:</span>
              <span className="metadata-value">{source.act_chapter}</span>
            </div>
          )}

          {source.document_date && (
            <div className="metadata-row">
              <span className="metadata-label">Date:</span>
              <span className="metadata-value">
                {formatDocumentDate(source.document_date)}
              </span>
            </div>
          )}

          <div className="metadata-row">
            <span className="metadata-label">Freshness:</span>
            <span className="metadata-value">
              {freshness.icon} {freshness.label}
            </span>
          </div>

          {source.last_verified && (
            <div className="metadata-row">
              <span className="metadata-label">Last Verified:</span>
              <span className="metadata-value">
                {getRelativeTime(source.last_verified)}
              </span>
            </div>
          )}
        </div>

        {/* Summary Section */}
        {source.summary && (
          <div className="source-summary">
            <h3>Summary</h3>
            <p>{source.summary}</p>
          </div>
        )}

        {/* Full Content Section */}
        <div className="source-content">
          <h3>Full Content</h3>
          <div className="content-text">
            {source.full_content}
          </div>
        </div>

        {/* Actions Section */}
        <div className="source-actions">
          <a
            href={source.url}
            target="_blank"
            rel="noopener noreferrer"
            className="btn btn-primary"
          >
            View Original Source →
          </a>

          <button
            onClick={handleVerify}
            disabled={isVerifying}
            className="btn btn-secondary"
          >
            {isVerifying ? 'Verifying...' : 'Verify Source'}
          </button>

          {verification && (
            <div className="verification-result">
              {verification.is_accessible ? (
                <span className="verification-success">
                  ✓ Source is accessible (HTTP {verification.http_status})
                </span>
              ) : (
                <span className="verification-error">
                  ✗ Source is not accessible
                </span>
              )}
            </div>
          )}
        </div>
      </div>
    </div>
  );
};

/**
 * CSS to add (use your existing modal styles as base):
 *
 * .source-modal {
 *   max-width: 800px;
 *   max-height: 90vh;
 *   overflow-y: auto;
 * }
 *
 * .source-metadata {
 *   background: #f9fafb;
 *   padding: 16px;
 *   border-radius: 8px;
 *   margin-bottom: 24px;
 * }
 *
 * .metadata-row {
 *   display: flex;
 *   padding: 8px 0;
 *   border-bottom: 1px solid #e5e7eb;
 * }
 *
 * .metadata-row:last-child {
 *   border-bottom: none;
 * }
 *
 * .metadata-label {
 *   font-weight: 600;
 *   width: 140px;
 *   color: #6b7280;
 * }
 *
 * .metadata-value {
 *   color: #111827;
 * }
 *
 * .source-content {
 *   margin: 24px 0;
 * }
 *
 * .content-text {
 *   white-space: pre-wrap;
 *   line-height: 1.8;
 *   padding: 16px;
 *   background: #f9fafb;
 *   border-radius: 8px;
 *   max-height: 400px;
 *   overflow-y: auto;
 * }
 *
 * .source-actions {
 *   display: flex;
 *   gap: 12px;
 *   align-items: center;
 *   padding-top: 24px;
 *   border-top: 1px solid #e5e7eb;
 * }
 *
 * .verification-result {
 *   margin-left: auto;
 *   font-size: 0.875rem;
 * }
 *
 * .verification-success {
 *   color: #059669;
 * }
 *
 * .verification-error {
 *   color: #dc2626;
 * }
 */
```

### Step 6: Integrate into Existing Chat/Response Component

**File:** `components/ChatMessage.tsx` (or your existing response component)

```typescript
import React, { useState } from 'react';
import type { EnhancedRAGResponse, StructuredSource } from '../types/rag.types';
import { CitationBadge } from './CitationBadge';
import { CitationTooltip } from './CitationTooltip';
import { SourceModal } from './SourceModal';
import { renderCitations } from '../utils/citation.utils';

interface ChatMessageProps {
  response: EnhancedRAGResponse;
  // ... your other existing props
}

/**
 * INTEGRATION EXAMPLE - Modify your existing component
 *
 * DO NOT replace your entire component. Just add these enhancements.
 */
export const ChatMessage: React.FC<ChatMessageProps> = ({ response }) => {
  const [selectedSourceId, setSelectedSourceId] = useState<string | null>(null);
  const [isModalOpen, setIsModalOpen] = useState(false);

  // Create a map of citation_id -> source for quick lookup
  const sourceMap = new Map<number, StructuredSource>(
    response.sources.map((source) => [source.citation_id, source])
  );

  function handleCitationClick(citationId: number) {
    const source = sourceMap.get(citationId);
    if (source) {
      // You need to get the actual source_id from backend
      // For now, we'll use citation_id (backend will add UUID field)
      setSelectedSourceId(String(citationId)); // TEMP: Will be UUID
      setIsModalOpen(true);
    }
  }

  // Parse citations and wrap them with interactive components
  const citationRegex = /\[(\d+)\]/g;
  const answerParts: React.ReactNode[] = [];
  let lastIndex = 0;
  let match;

  while ((match = citationRegex.exec(response.answer)) !== null) {
    // Add text before citation
    if (match.index > lastIndex) {
      answerParts.push(
        <span key={`text-${lastIndex}`}>
          {response.answer.substring(lastIndex, match.index)}
        </span>
      );
    }

    // Add interactive citation
    const citationId = parseInt(match[1], 10);
    const source = sourceMap.get(citationId);

    if (source) {
      answerParts.push(
        <CitationTooltip key={`citation-${match.index}`} source={source}>
          <CitationBadge
            citationId={citationId}
            source={source}
            onClick={() => handleCitationClick(citationId)}
          />
        </CitationTooltip>
      );
    } else {
      // Fallback if source not found
      answerParts.push(
        <span key={`citation-${match.index}`}>[{citationId}]</span>
      );
    }

    lastIndex = match.index + match[0].length;
  }

  // Add remaining text
  if (lastIndex < response.answer.length) {
    answerParts.push(
      <span key={`text-${lastIndex}`}>
        {response.answer.substring(lastIndex)}
      </span>
    );
  }

  return (
    <>
      {/* Your existing message container */}
      <div className="chat-message">
        {/* Render answer with interactive citations */}
        <div className="message-content">
          {answerParts}
        </div>

        {/* Optional: Add confidence/freshness indicators */}
        {response.metadata && (
          <div className="message-metadata">
            <span>Confidence: {(response.metadata.confidence * 100).toFixed(0)}%</span>
            <span>Freshness: {(response.metadata.freshness_score * 100).toFixed(0)}%</span>
          </div>
        )}

        {/* Your existing source list (keep as is) */}
        {/* ... */}
      </div>

      {/* Source Modal */}
      {selectedSourceId && (
        <SourceModal
          sourceId={selectedSourceId}
          isOpen={isModalOpen}
          onClose={() => setIsModalOpen(false)}
        />
      )}
    </>
  );
};
```

---

## 🎨 Styling Guide

### DO NOT Create New Design
- Use your **existing color scheme**
- Use your **existing button styles**
- Use your **existing modal component**
- Use your **existing tooltip library** if you have one

### Only Add These Minimal Styles

```css
/* Citation Badge - Make existing citations clickable */
.citation-badge {
  cursor: pointer;
  color: var(--link-color, #2563eb);
  font-weight: 600;
  transition: all 0.2s ease;
  padding: 0 2px;
}

.citation-badge:hover {
  background-color: var(--highlight-color, #dbeafe);
  text-decoration: underline;
}

/* Tooltip - Position over content */
.citation-tooltip {
  position: absolute;
  bottom: 100%;
  left: 50%;
  transform: translateX(-50%);
  margin-bottom: 8px;
  padding: 12px;
  background: white;
  border: 1px solid #e5e7eb;
  border-radius: 8px;
  box-shadow: 0 10px 15px -3px rgba(0, 0, 0, 0.1);
  width: 320px;
  z-index: 1000;
}

/* Highlight marks in excerpts */
.citation-tooltip mark,
.content-text mark {
  background-color: #fef3c7;
  padding: 1px 2px;
  border-radius: 2px;
}

/* Freshness indicators */
.freshness-green { color: #059669; }
.freshness-yellow { color: #d97706; }
.freshness-red { color: #dc2626; }
```

---

## ✅ Testing Checklist

### Functional Tests

- [ ] **Citations are clickable**
  - Click [1], [2], [3] opens source modal
  - Keyboard navigation works (Enter/Space)

- [ ] **Tooltips show on hover**
  - Displays snippet correctly
  - Shows freshness indicator
  - Renders highlighted terms with `<mark>` tags

- [ ] **Source modal displays correctly**
  - Shows all metadata fields
  - Displays full content
  - "View Original" link works
  - "Verify Source" button works

- [ ] **Source verification works**
  - Button shows loading state
  - Displays verification result
  - Updates freshness indicator

### Visual Tests

- [ ] **Citations match existing link style**
- [ ] **Tooltip doesn't overflow viewport**
- [ ] **Modal uses existing modal component**
- [ ] **Mobile responsive** (tooltip, modal)
- [ ] **High contrast mode** (accessibility)

### Edge Cases

- [ ] **No sources returned** - handles gracefully
- [ ] **Missing metadata fields** - shows "Unknown"
- [ ] **Long content** - scrollable in modal
- [ ] **Broken URLs** - verification shows error
- [ ] **Slow verification** - shows loading state

---

## 🚀 Quick Start Checklist

1. **Add TypeScript types** (`types/rag.types.ts`)
2. **Update API service** with new endpoints
3. **Add citation utilities** (`utils/citation.utils.ts`)
4. **Create CitationBadge component**
5. **Create CitationTooltip component**
6. **Create SourceModal component**
7. **Integrate into existing chat component**
8. **Add minimal CSS** (only interactive styles)
9. **Test all functionality**
10. **Deploy**

---

## 📞 Support & Questions

**Backend Team Contact:** [Your Contact Info]

**Common Issues:**

**Q: The sourceId is not a UUID, it's just a number**
**A:** We need to add `source_id` UUID field to the backend response. Use `citation_id` temporarily.

**Q: Tooltip positioning is off on mobile**
**A:** Add responsive positioning logic based on viewport width.

**Q: Modal doesn't match our design**
**A:** Use your existing modal component - just pass the content structure.

**Q: Can we customize the citation format [1] to something else?**
**A:** Yes, but coordinate with backend. The format is controlled by the LLM prompt.

---

## 🔄 Backend Updates Needed

**IMPORTANT:** Ask backend team to add these fields to response:

1. **Add `source_id` (UUID) to StructuredSource:**
```typescript
interface StructuredSource {
  source_id: string;  // ADD THIS - UUID for /sources/{id} endpoints
  citation_id: number;
  // ... rest of fields
}
```

2. **Backend PR Required:**
```python
# In app/services/enhanced_rag_service.py
# Add source UUID to structured sources
source = {
    'source_id': str(doc_uuid),  # ADD THIS LINE
    'citation_id': idx,
    # ... rest of fields
}
```

---

## 📦 Final Deliverables

After implementation, verify:

1. ✅ Citations are clickable and open modal
2. ✅ Hover tooltips show source snippets
3. ✅ Query terms are highlighted in yellow
4. ✅ Freshness indicators show (🟢🟡🔴)
5. ✅ Source verification works
6. ✅ Mobile responsive
7. ✅ Accessibility (keyboard navigation, ARIA labels)
8. ✅ No breaking changes to existing UI

---

**Last Updated:** 2025-10-04
**Version:** 1.0
**Backend Version:** Phase 1 Complete
