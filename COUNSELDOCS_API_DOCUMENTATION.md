# 📚 **COUNSELDOCS API DOCUMENTATION**

**Version**: 1.0.0  
**Last Updated**: 2025-07-21  
**Base URL**: `http://counsel-alb-694525771.us-east-1.elb.amazonaws.com`

---

## 🎯 **OVERVIEW**

CounselDocs is a comprehensive legal document analysis and generation platform focused on Kenyan law compliance. It provides:

- **Document Analysis**: Upload and analyze legal documents for Kenya Law compliance
- **Document Generation**: Generate court documents from Kenya Law templates  
- **Document Archive**: Manage and track document history with analytics
- **Legal Intelligence**: AI-powered analysis with citations and recommendations

---

## 🔐 **AUTHENTICATION**

**User Identification**: Uses Azure user IDs (no separate authentication required)
- Pass `user_id` parameter in requests
- Format: String (Azure user identifier)

---

## 📊 **API ENDPOINTS**

### **1. DOCUMENT ANALYSIS ENDPOINTS**

#### **1.1 Upload Document for Analysis**

```http
POST /api/v1/counseldocs/analysis/upload
```

**Description**: Upload a document for Kenya Law compliance analysis.

**Request Format**: `multipart/form-data`

**Parameters**:
- `file` (required): Document file
  - **Supported formats**: PDF, DOCX, DOC, TXT, PNG, JPG, JPEG, TIFF, BMP
  - **Max size**: 100MB (production-ready for large legal contracts)
- `user_id` (required): Azure user identifier
- `document_type` (optional): Document type hint
  - Values: `employment_contract`, `court_document`, `contract`, `general`

**Example Request**:
```javascript
const formData = new FormData();
formData.append('file', fileInput.files[0]);
formData.append('user_id', 'azure-user-123');
formData.append('document_type', 'employment_contract');

const response = await fetch('/api/v1/counseldocs/analysis/upload', {
  method: 'POST',
  body: formData
});
```

**Response** (200 OK):
```json
{
  "success": true,
  "analysis_id": "550e8400-e29b-41d4-a716-446655440000",
  "status": "pending",
  "message": "Document uploaded successfully. Analysis in progress.",
  "estimated_time_minutes": 2
}
```

**Error Responses**:
```json
// 400 Bad Request - Invalid file
{
  "detail": "File too large. Maximum size: 100MB"
}

// 422 Validation Error
{
  "detail": [
    {
      "loc": ["body", "user_id"],
      "msg": "field required",
      "type": "value_error.missing"
    }
  ]
}
```

---

#### **1.2 Get Analysis Status**

```http
GET /api/v1/counseldocs/analysis/status/{analysis_id}
```

**Description**: Check the status of document analysis.

**Path Parameters**:
- `analysis_id` (required): Analysis UUID from upload response

**Response** (200 OK):
```json
{
  "analysis_id": "550e8400-e29b-41d4-a716-446655440000",
  "status": "processing",
  "progress": "Analyzing document for Kenya Law compliance",
  "created_at": "2025-07-21T10:30:00Z",
  "completed_at": null,
  "processing_time_seconds": null
}
```

**Status Values**:
- `pending`: Document uploaded, waiting to start analysis
- `processing`: Analysis in progress
- `completed`: Analysis finished successfully
- `failed`: Analysis failed

**Error Response** (404):
```json
{
  "detail": "Analysis not found"
}
```

---

#### **1.3 Get Analysis Results**

```http
GET /api/v1/counseldocs/analysis/result/{analysis_id}
```

**Description**: Get complete analysis results (only available when status is `completed`).

**Path Parameters**:
- `analysis_id` (required): Analysis UUID

**Response** (200 OK):
```json
{
  "analysis_id": "550e8400-e29b-41d4-a716-446655440000",
  "document_info": {
    "original_filename": "employment_contract.pdf",
    "file_type": "pdf",
    "file_size_bytes": 245760,
    "document_type_detected": "employment_contract"
  },
  "compliance_results": {
    "compliance_score": 0.85,
    "confidence_score": 0.92,
    "key_areas": [
      {
        "area": "Minimum wage compliance",
        "status": "compliant",
        "importance": 5,
        "description": "Salary meets Employment Act 2007 requirements",
        "issues": [],
        "attention_required": "No action needed"
      },
      {
        "area": "Working hours and overtime",
        "status": "issue",
        "importance": 4,
        "description": "Working hours exceed legal limits",
        "issues": [
          "Working hours of 60 per week exceed 52-hour limit"
        ],
        "attention_required": "Reduce working hours to comply with Employment Act"
      }
    ],
    "recommendations": [
      {
        "area": "Working hours and overtime",
        "recommendation": "Reduce working hours to maximum 52 hours per week",
        "legal_requirement": "Employment Act 2007, Section 56",
        "priority": 4,
        "implementation_steps": [
          "Review current working schedule",
          "Implement overtime policies",
          "Update contract terms"
        ],
        "risk_if_ignored": "Legal penalties and employee rights violations"
      }
    ],
    "citations": [
      {
        "text": "Employment Act 2007",
        "type": "act",
        "confidence": 0.95,
        "source_url": "https://new.kenyalaw.org/akn/ke/act/2007/11/eng@2012-12-31",
        "relevance": "Primary legislation for employment matters"
      }
    ]
  },
  "analysis_metadata": {
    "model_used": "titan-text-premier",
    "processing_time_seconds": 45.2,
    "analyzed_at": "2025-07-21T10:32:15Z"
  },
  "content_summary": "Employment contract between ABC Company and John Doe for Software Developer position..."
}
```

**Error Responses**:
```json
// 404 Not Found
{
  "detail": "Analysis not found"
}

// 400 Bad Request - Analysis not completed
{
  "detail": "Analysis not completed. Current status: processing"
}
```

---

#### **1.4 Reanalyze Document**

```http
POST /api/v1/counseldocs/analysis/reanalyze
```

**Description**: Reanalyze an existing document with updated AI models.

**Request Body**:
```json
{
  "analysis_id": "550e8400-e29b-41d4-a716-446655440000",
  "user_id": "azure-user-123"
}
```

**Response** (200 OK):
```json
{
  "success": true,
  "new_analysis_id": "660f9511-f3ac-52e5-b827-557766551111",
  "original_analysis_id": "550e8400-e29b-41d4-a716-446655440000",
  "status": "pending",
  "message": "Document reanalysis started"
}
```

---

### **2. DOCUMENT GENERATION ENDPOINTS**

#### **2.1 Get Available Templates**

```http
GET /api/v1/counseldocs/generation/templates
```

**Description**: Get list of available court document templates from Kenya Law Civil Procedure Rules 2010.

**Response** (200 OK):
```json
{
  "success": true,
  "templates": [
    {
      "template_id": "civil_plaint",
      "template_name": "Plaint (Civil Procedure Rules)",
      "category": "civil",
      "description": "Standard plaint for civil cases under Order IV",
      "legal_basis": "Civil Procedure Rules 2010, Order IV, Rule 1",
      "required_fields": [
        "court_name", "suit_number", "year", "plaintiff_name",
        "plaintiff_address", "defendant_name", "defendant_address",
        "cause_of_action", "relief_sought", "value_of_suit"
      ],
      "optional_fields": [
        "plaintiff_occupation", "defendant_occupation", "facts",
        "legal_grounds", "interest_rate", "costs"
      ]
    },
    {
      "template_id": "civil_written_statement",
      "template_name": "Written Statement of Defence",
      "category": "civil",
      "description": "Defendant's written statement of defence under Order VIII",
      "legal_basis": "Civil Procedure Rules 2010, Order VIII, Rule 1",
      "required_fields": [
        "court_name", "suit_number", "year", "plaintiff_name",
        "defendant_name", "defence_statement"
      ],
      "optional_fields": [
        "counterclaim", "set_off", "additional_defences"
      ]
    },
    {
      "template_id": "application_notice",
      "template_name": "Notice of Application",
      "category": "civil",
      "description": "Notice of application for court orders under Order IX",
      "legal_basis": "Civil Procedure Rules 2010, Order IX, Rule 1",
      "required_fields": [
        "court_name", "suit_number", "year", "applicant_name",
        "respondent_name", "application_type", "orders_sought",
        "grounds_of_application"
      ],
      "optional_fields": [
        "urgency_reasons", "supporting_affidavit", "legal_authorities"
      ]
    },
    {
      "template_id": "affidavit",
      "template_name": "Affidavit",
      "category": "civil",
      "description": "Standard affidavit format under Order XIX",
      "legal_basis": "Civil Procedure Rules 2010, Order XIX, Rule 1",
      "required_fields": [
        "court_name", "suit_number", "year", "deponent_name",
        "deponent_address", "deponent_occupation", "affidavit_content"
      ],
      "optional_fields": [
        "exhibits", "commissioner_name", "commissioner_title"
      ]
    }
  ],
  "total_templates": 4,
  "categories": ["civil"],
  "retrieved_at": "2025-07-21T10:30:00Z"
}
```

---

#### **2.2 Generate Document**

```http
POST /api/v1/counseldocs/generation/generate
```

**Description**: Generate a court document from Kenya Law template.

**Request Body**:
```json
{
  "template_id": "civil_plaint",
  "user_id": "azure-user-123",
  "template_data": {
    "court_name": "HIGH COURT OF KENYA",
    "court_location": "NAIROBI",
    "suit_number": "123",
    "year": 2025,
    "plaintiff_name": "John Doe",
    "plaintiff_address": "P.O. Box 12345, Nairobi",
    "defendant_name": "ABC Corporation Limited",
    "defendant_address": "P.O. Box 67890, Nairobi",
    "cause_of_action": "Breach of employment contract dated 1st January 2024",
    "relief_sought": "Damages for wrongful termination in the sum of KES 500,000",
    "value_of_suit": "500000",
    "facts": "The Plaintiff was employed by the Defendant as a Software Developer...",
    "interest_rate": "12"
  },
  "generation_options": {
    "output_format": "pdf",
    "custom_filename": "Plaint_Doe_vs_ABC_Corp"
  },
  "user_plan": "premium"
}
```

**User Plan Options**:
- `"free"`: Default plan with CounselDocs watermark
- `"premium"`: Premium plan with watermark removed
- `"pro"`: Professional plan with watermark removed
- `"enterprise"`: Enterprise plan with watermark removed

**Response** (200 OK):
```json
{
  "success": true,
  "generation_id": "660f9511-f3ac-52e5-b827-557766551111",
  "status": "pending",
  "message": "Document generation started",
  "estimated_time_minutes": 1,
  "download_url": "/api/v1/counseldocs/generation/download/660f9511-f3ac-52e5-b827-557766551111"
}
```

**Error Responses**:
```json
// 400 Bad Request - Invalid format
{
  "detail": "Invalid output format. Supported: pdf, html"
}

// 400 Bad Request - Missing fields
{
  "detail": "Missing required fields: court_name, plaintiff_name"
}
```

---

#### **2.3 Get Generation Status**

```http
GET /api/v1/counseldocs/generation/status/{generation_id}
```

**Description**: Check document generation status.

**Path Parameters**:
- `generation_id` (required): Generation UUID

**Response** (200 OK):
```json
{
  "generation_id": "660f9511-f3ac-52e5-b827-557766551111",
  "status": "completed",
  "template_id": "civil_plaint",
  "template_name": "Plaint (Civil Procedure Rules)",
  "file_format": "pdf",
  "custom_filename": "Plaint_Doe_vs_ABC_Corp",
  "created_at": "2025-07-21T10:30:00Z",
  "completed_at": "2025-07-21T10:30:45Z",
  "generation_time_seconds": 12,
  "download_count": 0,
  "error_message": null
}
```

**Status Values**:
- `pending`: Generation queued
- `generating`: Document being generated
- `completed`: Generation finished successfully
- `failed`: Generation failed

---

#### **2.4 Download Generated Document**

```http
GET /api/v1/counseldocs/generation/download/{generation_id}
```

**Description**: Download generated court document.

**Path Parameters**:
- `generation_id` (required): Generation UUID

**Response** (200 OK):
- **Content-Type**: `application/pdf` or `text/html`
- **Content-Disposition**: `attachment; filename="Plaint_Doe_vs_ABC_Corp.pdf"`
- **Body**: Document file content

**Error Responses**:
```json
// 404 Not Found
{
  "detail": "Generated document not found"
}

// 400 Bad Request - Not ready
{
  "detail": "Document not ready. Current status: generating"
}
```

---

#### **2.5 Regenerate Document**

```http
POST /api/v1/counseldocs/generation/regenerate
```

**Description**: Regenerate document with updated data.

**Request Body**:
```json
{
  "generation_id": "660f9511-f3ac-52e5-b827-557766551111",
  "user_id": "azure-user-123",
  "template_data": {
    "relief_sought": "Damages for wrongful termination in the sum of KES 750,000",
    "value_of_suit": "750000"
  }
}
```

**Response** (200 OK):
```json
{
  "success": true,
  "new_generation_id": "770g0622-g4bd-63f6-c938-668877662222",
  "original_generation_id": "660f9511-f3ac-52e5-b827-557766551111",
  "status": "pending",
  "message": "Document regeneration started"
}
```

---

### **3. DOCUMENT ARCHIVE ENDPOINTS**

#### **3.1 Get Dashboard Data**

```http
GET /api/v1/counseldocs/archive/dashboard?user_id={user_id}
```

**Description**: Get comprehensive dashboard analytics for user.

**Query Parameters**:
- `user_id` (required): Azure user identifier

**Response** (200 OK):
```json
{
  "success": true,
  "dashboard_data": {
    "archive_summary": {
      "archive_id": "880h1733-h5ce-74g7-d049-779988773333",
      "user_id": "azure-user-123",
      "total_documents_analyzed": 45,
      "total_documents_generated": 23,
      "pending_analyses": 2,
      "completed_analyses": 43,
      "failed_analyses": 0,
      "pending_generations": 1,
      "completed_generations": 22,
      "failed_generations": 0,
      "total_downloads": 67,
      "total_storage_bytes": 15728640,
      "last_analysis_at": "2025-07-21T09:15:30Z",
      "last_generation_at": "2025-07-21T10:30:00Z",
      "last_activity_at": "2025-07-21T10:30:00Z"
    },
    "recent_analyses": [
      {
        "analysis_id": "550e8400-e29b-41d4-a716-446655440000",
        "original_filename": "employment_contract.pdf",
        "document_type_detected": "employment_contract",
        "compliance_score": 0.85,
        "status": "completed",
        "created_at": "2025-07-21T09:15:30Z"
      }
    ],
    "recent_generations": [
      {
        "generation_id": "660f9511-f3ac-52e5-b827-557766551111",
        "template_name": "Plaint (Civil Procedure Rules)",
        "file_format": "pdf",
        "status": "completed",
        "download_count": 3,
        "created_at": "2025-07-21T10:30:00Z"
      }
    ],
    "analytics": {
      "analysis_stats": {
        "total": 45,
        "last_30_days": 12,
        "last_7_days": 4,
        "avg_compliance_score": 0.82
      },
      "generation_stats": {
        "total": 23,
        "last_30_days": 8,
        "last_7_days": 3
      },
      "document_type_distribution": [
        {"type": "employment_contract", "count": 28},
        {"type": "court_document", "count": 12},
        {"type": "contract", "count": 5}
      ],
      "template_usage": [
        {"template_id": "civil_plaint", "count": 15},
        {"template_id": "affidavit", "count": 8}
      ]
    }
  },
  "retrieved_at": "2025-07-21T10:35:00Z"
}
```

---

#### **3.2 Get User Documents**

```http
GET /api/v1/counseldocs/archive/documents?user_id={user_id}&type={type}&status={status}&limit={limit}&offset={offset}
```

**Description**: Get user's documents with filtering and pagination.

**Query Parameters**:
- `user_id` (required): Azure user identifier
- `document_type` (optional): Filter by type (`analysis`, `generation`)
- `status` (optional): Filter by status (`pending`, `completed`, `failed`)
- `limit` (optional): Number of documents (1-100, default: 50)
- `offset` (optional): Skip documents for pagination (default: 0)

**Response** (200 OK):
```json
{
  "success": true,
  "documents": {
    "analyses": [
      {
        "analysis_id": "550e8400-e29b-41d4-a716-446655440000",
        "original_filename": "employment_contract.pdf",
        "file_type": "pdf",
        "document_type_detected": "employment_contract",
        "compliance_score": 0.85,
        "confidence_score": 0.92,
        "status": "completed",
        "processing_time_seconds": 45.2,
        "created_at": "2025-07-21T09:15:30Z",
        "completed_at": "2025-07-21T09:16:15Z"
      }
    ],
    "generations": [
      {
        "generation_id": "660f9511-f3ac-52e5-b827-557766551111",
        "template_id": "civil_plaint",
        "template_name": "Plaint (Civil Procedure Rules)",
        "file_format": "pdf",
        "custom_filename": "Plaint_Doe_vs_ABC_Corp",
        "status": "completed",
        "download_count": 3,
        "generation_time_seconds": 12,
        "created_at": "2025-07-21T10:30:00Z",
        "completed_at": "2025-07-21T10:30:12Z"
      }
    ],
    "pagination": {
      "total_analyses": 45,
      "total_generations": 23,
      "limit": 50,
      "offset": 0,
      "has_more_analyses": false,
      "has_more_generations": false
    }
  },
  "retrieved_at": "2025-07-21T10:35:00Z"
}
```

---

#### **3.3 Get Detailed Analytics**

```http
GET /api/v1/counseldocs/archive/analytics?user_id={user_id}
```

**Description**: Get detailed analytics and insights.

**Query Parameters**:
- `user_id` (required): Azure user identifier

**Response** (200 OK):
```json
{
  "success": true,
  "analytics": {
    "analysis_stats": {
      "total": 45,
      "last_30_days": 12,
      "last_7_days": 4,
      "avg_compliance_score": 0.82
    },
    "generation_stats": {
      "total": 23,
      "last_30_days": 8,
      "last_7_days": 3
    },
    "usage_trends": {
      "daily_usage": {
        "analyses_per_day": 2.5,
        "generations_per_day": 1.8,
        "trend": "increasing"
      },
      "peak_usage_hours": [9, 10, 14, 15, 16],
      "most_active_day": "Tuesday"
    },
    "compliance_trends": {
      "average_compliance_score": 0.82,
      "compliance_improvement": 0.15,
      "common_issues": [
        "Working hours compliance",
        "Minimum wage requirements"
      ]
    },
    "efficiency_metrics": {
      "time_saved_hours": 24.5,
      "documents_processed": 156,
      "automation_rate": 0.87,
      "cost_savings_estimate": "KES 45,000"
    }
  },
  "calculated_at": "2025-07-21T10:35:00Z"
}
```

---

#### **3.4 Delete Document**

```http
DELETE /api/v1/counseldocs/archive/document
```

**Description**: Delete (archive) a document.

**Request Body**:
```json
{
  "user_id": "azure-user-123",
  "document_id": "550e8400-e29b-41d4-a716-446655440000",
  "document_type": "analysis"
}
```

**Response** (200 OK):
```json
{
  "success": true,
  "message": "Document archived successfully",
  "document_id": "550e8400-e29b-41d4-a716-446655440000",
  "archived_at": "2025-07-21T10:35:00Z"
}
```

---

#### **3.5 Get Archive Summary**

```http
GET /api/v1/counseldocs/archive/summary?user_id={user_id}
```

**Description**: Get quick archive summary.

**Query Parameters**:
- `user_id` (required): Azure user identifier

**Response** (200 OK):
```json
{
  "success": true,
  "summary": {
    "total_documents": 68,
    "analysis_summary": {
      "total": 45,
      "pending": 2,
      "completed": 43,
      "failed": 0
    },
    "generation_summary": {
      "total": 23,
      "pending": 1,
      "completed": 22,
      "failed": 0,
      "downloads": 67
    },
    "storage_usage": {
      "total_bytes": 15728640,
      "analysis_bytes": 10485760,
      "generation_bytes": 5242880
    },
    "last_activity": "2025-07-21T10:30:00Z"
  },
  "retrieved_at": "2025-07-21T10:35:00Z"
}
```

---

## 📋 **DATA MODELS**

### **Key Areas Object**
```typescript
interface KeyArea {
  area: string;                    // Area name (e.g., "Minimum wage compliance")
  status: "compliant" | "issue" | "missing" | "unknown";
  importance: number;              // 1-5 scale
  description: string;             // Brief findings
  issues: string[];               // Specific issues found
  attention_required: string;      // What user should focus on
}
```

### **Recommendation Object**
```typescript
interface Recommendation {
  area: string;                    // Related area
  recommendation: string;          // Specific action to take
  legal_requirement: string;       // Legal basis
  priority: number;               // 1-5 scale
  implementation_steps: string[]; // Step-by-step actions
  risk_if_ignored: string;        // Consequences
}
```

### **Citation Object**
```typescript
interface Citation {
  text: string;                   // Citation text
  type: "act" | "constitution" | "case" | "section" | "article";
  confidence: number;             // 0.0-1.0
  source_url: string;            // Link to source
  relevance: string;             // Why it's relevant
}
```

---

## 🎨 **UI/UX RECOMMENDATIONS**

### **Document Upload Flow**
1. **File Drop Zone**: Drag & drop with format validation
2. **Progress Indicator**: Real-time upload and analysis progress
3. **Document Preview**: Show extracted content preview
4. **Analysis Results**: Professional legal document styling

### **Key Components**
```jsx
// Analysis Status Component
<AnalysisStatus 
  analysisId={analysisId}
  onComplete={handleAnalysisComplete}
  pollingInterval={5000}
/>

// Compliance Score Badge
<ComplianceScore 
  score={0.85}
  confidenceScore={0.92}
  status="good"
/>

// Key Areas List
<KeyAreasList 
  areas={keyAreas}
  onAreaClick={handleAreaDetails}
  prioritizeIssues={true}
/>

// Recommendations Panel
<RecommendationsPanel 
  recommendations={recommendations}
  onImplement={handleImplementation}
  groupByPriority={true}
/>
```

---

## ⚠️ **ERROR HANDLING**

### **Common Error Patterns**
```javascript
// Handle file upload errors
if (response.status === 400) {
  const error = await response.json();
  if (error.detail.includes("File too large")) {
    showError("File exceeds 100MB limit. Please compress or split the document.");
  }
}

// Handle analysis errors
if (response.status === 422) {
  const validation = await response.json();
  validation.detail.forEach(error => {
    showFieldError(error.loc[1], error.msg);
  });
}

// Handle rate limiting
if (response.status === 429) {
  const retryAfter = response.headers.get('Retry-After');
  showError(`Rate limit exceeded. Please try again in ${retryAfter} seconds.`);
}
```

---

## 🚀 **INTEGRATION CHECKLIST**

### **Phase 1: Basic Integration (Week 1)**
- [ ] Document upload component
- [ ] Analysis status polling
- [ ] Results display
- [ ] Error handling

### **Phase 2: Enhanced Features (Week 2)**
- [ ] Document generation interface
- [ ] Template selection
- [ ] PDF download functionality
- [ ] Archive dashboard

### **Phase 3: Advanced Features (Week 3)**
- [ ] Advanced filtering
- [ ] Bulk operations
- [ ] Analytics visualization
- [ ] Export capabilities

---

**📞 Support**: For technical questions, refer to this documentation or contact the backend team.

**🔄 Updates**: This document will be updated as new features are implemented in Weeks 3-4.
