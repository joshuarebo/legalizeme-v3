# 📋 COUNSEL AI - FRONTEND API INTEGRATION GUIDE

## 🔗 Production API Base URL
```
http://counsel-alb-694525771.us-east-1.elb.amazonaws.com
```

## 📊 Complete Document Lifecycle API Endpoints

### 🔍 **DOCUMENT ANALYSIS ENDPOINTS**

#### **1. Document Upload**
```http
POST /api/v1/documents/upload
Content-Type: multipart/form-data
```

**Request Body (FormData):**
```javascript
const formData = new FormData();
formData.append('file', fileObject); // PDF, DOCX, TXT, JPG, PNG
formData.append('user_context', JSON.stringify({
  user_id: "user_123",
  location: "Kenya",
  document_type: "legal_contract", // legal_contract, employment_doc, lease_agreement, etc.
  analysis_type: "legal_review"    // legal_review, compliance_check, risk_assessment
}));
```

**Response (200 OK):**
```json
{
  "document_id": "doc_12345",
  "filename": "contract.pdf",
  "file_size": 2048576,
  "status": "success",
  "message": "Document uploaded successfully",
  "upload_time": "2025-07-19T14:30:00Z"
}
```

**Purpose:** Upload legal documents for analysis. Supports multiple file formats with metadata context.

---

#### **2. Document Analysis**
```http
POST /api/v1/documents/analyze
Content-Type: application/json
```

**Request Body:**
```json
{
  "document_id": "doc_12345",
  "analysis_type": "legal_review",
  "focus_areas": ["contract_terms", "legal_risks", "compliance"],
  "kenyan_law_focus": true
}
```

**Response (200 OK):**
```json
{
  "analysis_id": "analysis_67890",
  "document_id": "doc_12345",
  "analysis_type": "legal_review",
  "status": "completed",
  "confidence": 0.87,
  "processing_time": 15.3,
  "model_used": "claude-sonnet-4",
  "summary": "Document analysis summary...",
  "key_findings": [
    {
      "category": "contract_terms",
      "finding": "Termination clause analysis",
      "severity": "medium",
      "recommendation": "Consider adding notice period details"
    }
  ],
  "legal_risks": [
    {
      "risk_type": "compliance",
      "description": "Missing mandatory clauses",
      "severity": "high",
      "mitigation": "Add required employment law clauses"
    }
  ],
  "compliance_status": {
    "overall_score": 0.75,
    "kenyan_law_compliance": true,
    "missing_requirements": ["Section 41 compliance"]
  },
  "citations": [
    {
      "source": "Employment Act 2007",
      "section": "Section 41",
      "relevance": "Termination procedures",
      "url": "https://kenyalaw.org/...",
      "confidence": 0.9
    }
  ]
}
```

**Purpose:** AI-powered legal analysis of uploaded documents with Kenyan law focus.

---

#### **3. List User Documents**
```http
GET /api/v1/documents?limit=20&offset=0&document_type=legal_contract
```

**Query Parameters:**
- `limit` (optional): Number of documents to return (default: 20)
- `offset` (optional): Pagination offset (default: 0)
- `document_type` (optional): Filter by document type
- `analysis_status` (optional): Filter by analysis status

**Response (200 OK):**
```json
{
  "documents": [
    {
      "document_id": "doc_12345",
      "filename": "employment_contract.pdf",
      "upload_time": "2025-07-19T14:30:00Z",
      "file_size": 2048576,
      "document_type": "legal_contract",
      "analysis_status": "completed",
      "analysis_count": 2,
      "last_analysis": "2025-07-19T14:35:00Z"
    }
  ],
  "total": 15,
  "limit": 20,
  "offset": 0
}
```

**Purpose:** Retrieve paginated list of user's uploaded documents with analysis status.

---

#### **4. Get Analysis Results**
```http
GET /api/v1/documents/analysis/{analysis_id}
```

**Response (200 OK):**
```json
{
  "analysis_id": "analysis_67890",
  "document_id": "doc_12345",
  "analysis_type": "legal_review",
  "status": "completed",
  "confidence": 0.87,
  "processing_time": 15.3,
  "model_used": "claude-sonnet-4",
  "summary": "Detailed analysis summary...",
  "key_findings": [...],
  "legal_risks": [...],
  "compliance_status": {...},
  "citations": [...]
}
```

**Purpose:** Retrieve detailed analysis results by analysis ID.

---

#### **5. Delete Document**
```http
DELETE /api/v1/documents/{document_id}
```

**Response (200 OK):**
```json
{
  "document_id": "doc_12345",
  "filename": "contract.pdf",
  "status": "deleted",
  "message": "Document and all associated analyses deleted successfully",
  "analyses_removed": 2,
  "deleted_at": "2025-07-19T15:30:00Z"
}
```

**Purpose:** Delete document and all associated analyses from the system.

---

### 📄 **DOCUMENT GENERATION ENDPOINTS**

#### **6. List Available Templates**
```http
GET /api/v1/generate/templates
```

**Response (200 OK):**
```json
{
  "templates": {
    "employment_contract": {
      "name": "Employment Contract",
      "description": "Standard employment contract compliant with Kenyan Employment Act 2007",
      "category": "employment",
      "fields": [
        {
          "name": "employer_name",
          "type": "string",
          "required": true,
          "description": "Legal name of the employer"
        },
        {
          "name": "employee_name",
          "type": "string",
          "required": true,
          "description": "Full name of the employee"
        },
        {
          "name": "position",
          "type": "string",
          "required": true,
          "description": "Job title/position"
        },
        {
          "name": "salary",
          "type": "number",
          "required": true,
          "description": "Monthly salary in KES"
        },
        {
          "name": "start_date",
          "type": "date",
          "required": true,
          "description": "Employment start date (YYYY-MM-DD)"
        },
        {
          "name": "probation_period",
          "type": "number",
          "required": false,
          "description": "Probation period in months"
        },
        {
          "name": "notice_period",
          "type": "number",
          "required": false,
          "description": "Notice period in days"
        },
        {
          "name": "working_hours",
          "type": "number",
          "required": false,
          "description": "Weekly working hours"
        }
      ],
      "compliance_requirements": [
        "Employment Act 2007 compliance",
        "Minimum wage requirements",
        "Working time regulations"
      ]
    },
    "service_agreement": {
      "name": "Service Agreement",
      "description": "Professional service agreement template",
      "category": "commercial",
      "fields": [...],
      "compliance_requirements": [...]
    },
    "lease_agreement": {
      "name": "Lease Agreement",
      "description": "Residential/commercial lease agreement",
      "category": "property",
      "fields": [...],
      "compliance_requirements": [...]
    },
    "legal_notice": {
      "name": "Legal Notice",
      "description": "Formal legal notice template",
      "category": "litigation",
      "fields": [...],
      "compliance_requirements": [...]
    }
  },
  "total": 4,
  "categories": ["employment", "commercial", "property", "litigation"]
}
```

**Purpose:** Get all available document templates with field specifications and requirements.

---

#### **7. Get Template Details**
```http
GET /api/v1/generate/templates/{template_id}
```

**Response (200 OK):**
```json
{
  "template_id": "employment_contract",
  "name": "Employment Contract",
  "description": "Standard employment contract compliant with Kenyan Employment Act 2007",
  "category": "employment",
  "fields": [...],
  "compliance_requirements": [...],
  "sample_data": {
    "employer_name": "Example Company Ltd",
    "employee_name": "John Doe",
    "position": "Software Developer",
    "salary": 150000
  }
}
```

**Purpose:** Get detailed information about a specific template including field definitions.

---

#### **8. Generate Document**
```http
POST /api/v1/generate/generate
Content-Type: application/json
```

**Request Body:**
```json
{
  "template_id": "employment_contract",
  "document_data": {
    "employer_name": "TechCorp Kenya Ltd",
    "employee_name": "John Doe",
    "position": "Software Developer",
    "salary": 150000,
    "start_date": "2025-08-01",
    "probation_period": 6,
    "notice_period": 30,
    "working_hours": 40
  },
  "generation_options": {
    "output_format": "html",        // html, markdown, text
    "kenyan_law_focus": true,
    "include_compliance_notes": true
  }
}
```

**Response (200 OK):**
```json
{
  "generation_id": "gen_12345",
  "template_id": "employment_contract",
  "template_name": "Employment Contract",
  "status": "completed",
  "generated_at": "2025-07-19T15:30:00Z",
  "processing_time": 39.6,
  "model_used": "claude-sonnet-4",
  "output_format": "html",
  "document_content": "<html><body><h1>EMPLOYMENT CONTRACT</h1>...</body></html>",
  "metadata": {
    "word_count": 1250,
    "page_count": 3,
    "compliance_score": 0.95
  },
  "compliance_notes": [
    {
      "section": "Termination Clause",
      "note": "Complies with Employment Act 2007 Section 41",
      "status": "compliant"
    }
  ]
}
```

**Purpose:** Generate a legal document from template with AI-powered content and compliance checking.

---

#### **9. Update Generated Document**
```http
PUT /api/v1/generate/generated/{generation_id}
Content-Type: application/json
```

**Request Body:**
```json
{
  "document_content": "<html><body><h1>UPDATED EMPLOYMENT CONTRACT</h1>...</body></html>",
  "update_notes": "Updated salary and benefits section"
}
```

**Response (200 OK):**
```json
{
  "generation_id": "gen_12345",
  "status": "updated",
  "updated_at": "2025-07-19T16:00:00Z",
  "revision_count": 2,
  "update_notes": "Updated salary and benefits section",
  "document_length": 5420,
  "message": "Document updated successfully"
}
```

**Purpose:** Update previously generated document content with revision tracking.

---

#### **10. Export Document to PDF**
```http
POST /api/v1/generate/export
Content-Type: application/json
```

**Request Body (Option 1 - Export from generated document):**
```json
{
  "generation_id": "gen_12345",
  "format": "pdf",
  "filename": "employment_contract.pdf"
}
```

**Request Body (Option 2 - Export custom content):**
```json
{
  "content": "<html><body><h1>Custom Document</h1><p>Content...</p></body></html>",
  "format": "pdf",
  "filename": "custom_document.pdf"
}
```

**Response (200 OK):**
```json
{
  "export_id": "export_987b19d7",
  "filename": "employment_contract.pdf",
  "format": "pdf",
  "status": "completed",
  "exported_at": "2025-07-19T16:15:00Z",
  "file_size": 245760,
  "download_url": "/api/v1/generate/export/export_987b19d7/download",
  "expires_at": "2025-07-20T16:15:00Z",
  "message": "Document exported to PDF successfully"
}
```

**Purpose:** Export generated documents or custom content to PDF format with download link.

---

### 🤖 **ENHANCED QUERY ENDPOINT**

#### **11. Enhanced Query with Document Context**
```http
POST /api/v1/counsel/query
Content-Type: application/json
```

**Request Body:**
```json
{
  "query": "Are the termination clauses in this contract compliant with Kenyan law?",
  "use_enhanced_rag": true,
  "agent_mode": false,
  
  // NEW: Document context fields (optional)
  "document_context": "doc_12345",
  "analysis_id": "analysis_67890",
  
  // Standard fields
  "kenyan_law_focus": true,
  "response_format": "detailed"
}
```

**Response (200 OK):**
```json
{
  "query_id": "query_789",
  "answer": "Based on the uploaded contract analysis and Kenyan Employment Act 2007...",
  "confidence": 0.85,
  "model_used": "claude-sonnet-4",
  "enhanced": true,
  "processing_time": 12.5,
  
  // NEW: Document context in response
  "document_context": {
    "document_id": "doc_12345",
    "filename": "contract.pdf",
    "relevant_sections": ["Section 3.2", "Clause 7.1"],
    "analysis_used": "analysis_67890"
  },
  
  // Enhanced citations with document references
  "citations": [
    {
      "source": "Employment Act 2007",
      "section": "Section 41",
      "relevance": "Termination procedures",
      "url": "https://kenyalaw.org/...",
      "confidence": 0.9
    },
    {
      "source": "Uploaded Document",
      "section": "Clause 7.1",
      "page": 3,
      "relevance": "Contract termination clause"
    }
  ],
  
  "cached": false
}
```

**Purpose:** Enhanced AI-powered legal queries with optional document context integration for more accurate responses.

---

## 🔧 **IMPLEMENTATION NOTES**

### **Authentication**
- Currently no authentication required
- Add `User-Agent: LegalizeMe-Frontend/1.0` header for tracking

### **Error Handling**
All endpoints return standard HTTP status codes:
- `200` - Success
- `400` - Bad Request (validation errors)
- `404` - Not Found
- `500` - Internal Server Error

### **Rate Limiting**
- Document upload: 10 requests/minute
- Document generation: 5 requests/minute
- Query endpoint: 20 requests/minute

### **File Upload Limits**
- Maximum file size: 10MB
- Supported formats: PDF, DOCX, TXT, JPG, PNG

### **Timeouts**
- Document analysis: 60 seconds
- Document generation: 90 seconds
- Query processing: 30 seconds

---

## 🚀 **DEPLOYMENT STATUS**
✅ **All 11 endpoints are live in production**
✅ **Complete document lifecycle implemented**
✅ **AI-powered with Claude Sonnet 4**
✅ **Kenyan law compliance focus**
✅ **Ready for frontend integration**

---

## 📝 **FRONTEND IMPLEMENTATION EXAMPLES**

### **JavaScript/React Example - Document Upload**
```javascript
const uploadDocument = async (file, userContext) => {
  const formData = new FormData();
  formData.append('file', file);
  formData.append('user_context', JSON.stringify(userContext));

  try {
    const response = await fetch(
      'http://counsel-alb-694525771.us-east-1.elb.amazonaws.com/api/v1/documents/upload',
      {
        method: 'POST',
        body: formData,
        headers: {
          'User-Agent': 'LegalizeMe-Frontend/1.0'
        }
      }
    );

    if (!response.ok) throw new Error(`HTTP ${response.status}`);
    return await response.json();
  } catch (error) {
    console.error('Upload failed:', error);
    throw error;
  }
};
```

### **JavaScript/React Example - Document Generation**
```javascript
const generateDocument = async (templateId, documentData) => {
  const requestBody = {
    template_id: templateId,
    document_data: documentData,
    generation_options: {
      output_format: 'html',
      kenyan_law_focus: true,
      include_compliance_notes: true
    }
  };

  try {
    const response = await fetch(
      'http://counsel-alb-694525771.us-east-1.elb.amazonaws.com/api/v1/generate/generate',
      {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'User-Agent': 'LegalizeMe-Frontend/1.0'
        },
        body: JSON.stringify(requestBody)
      }
    );

    if (!response.ok) throw new Error(`HTTP ${response.status}`);
    return await response.json();
  } catch (error) {
    console.error('Generation failed:', error);
    throw error;
  }
};
```

### **JavaScript/React Example - Enhanced Query**
```javascript
const queryWithContext = async (query, documentId = null, analysisId = null) => {
  const requestBody = {
    query: query,
    use_enhanced_rag: true,
    agent_mode: false,
    kenyan_law_focus: true,
    response_format: 'detailed'
  };

  // Add document context if provided
  if (documentId) requestBody.document_context = documentId;
  if (analysisId) requestBody.analysis_id = analysisId;

  try {
    const response = await fetch(
      'http://counsel-alb-694525771.us-east-1.elb.amazonaws.com/api/v1/counsel/query',
      {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'User-Agent': 'LegalizeMe-Frontend/1.0'
        },
        body: JSON.stringify(requestBody)
      }
    );

    if (!response.ok) throw new Error(`HTTP ${response.status}`);
    return await response.json();
  } catch (error) {
    console.error('Query failed:', error);
    throw error;
  }
};
```

---

## 🔄 **COMPLETE WORKFLOW EXAMPLES**

### **Workflow 1: Document Analysis → Query**
```javascript
// Step 1: Upload document
const uploadResult = await uploadDocument(file, {
  user_id: "user_123",
  location: "Kenya",
  document_type: "legal_contract",
  analysis_type: "legal_review"
});

// Step 2: Analyze document
const analysisResult = await fetch('/api/v1/documents/analyze', {
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify({
    document_id: uploadResult.document_id,
    analysis_type: "legal_review",
    focus_areas: ["contract_terms", "legal_risks", "compliance"],
    kenyan_law_focus: true
  })
});

// Step 3: Query with document context
const queryResult = await queryWithContext(
  "What are the main legal risks in this contract?",
  uploadResult.document_id,
  analysisResult.analysis_id
);
```

### **Workflow 2: Document Generation → Export**
```javascript
// Step 1: Get available templates
const templates = await fetch('/api/v1/generate/templates').then(r => r.json());

// Step 2: Generate document
const generationResult = await generateDocument('employment_contract', {
  employer_name: "TechCorp Kenya Ltd",
  employee_name: "John Doe",
  position: "Software Developer",
  salary: 150000,
  start_date: "2025-08-01"
});

// Step 3: Export to PDF
const exportResult = await fetch('/api/v1/generate/export', {
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify({
    generation_id: generationResult.generation_id,
    format: "pdf",
    filename: "employment_contract.pdf"
  })
});
```

---

## ⚠️ **IMPORTANT CONSIDERATIONS**

### **Security**
- All API calls should be made from your backend to avoid CORS issues
- Implement proper file validation before upload
- Sanitize all user inputs before sending to API

### **Performance**
- Document generation can take 30-90 seconds - implement proper loading states
- Use pagination for document lists
- Cache template data to reduce API calls

### **User Experience**
- Show progress indicators for long-running operations
- Implement retry logic for failed requests
- Provide clear error messages to users

### **Data Handling**
- Store document IDs and generation IDs for future reference
- Implement proper file download handling for PDF exports
- Consider implementing local caching for frequently accessed data

---

## 📞 **SUPPORT & CONTACT**

For technical questions or integration support:
- **API Status**: All endpoints tested and operational
- **Response Time**: Average 2-15 seconds depending on operation
- **Uptime**: 99.9% availability target
- **Documentation**: This guide covers all implemented functionality

**Ready for immediate frontend integration!** 🚀
