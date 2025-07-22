# 🚀 COUNSEL AI - API ENDPOINTS QUICK REFERENCE

## 📍 Base URL
```
http://counsel-alb-694525771.us-east-1.elb.amazonaws.com
```

## 📋 All 11 Endpoints Summary

### 🔍 **DOCUMENT ANALYSIS (5 endpoints)**
| Method | Endpoint | Purpose |
|--------|----------|---------|
| `POST` | `/api/v1/documents/upload` | Upload documents (PDF, DOCX, TXT, JPG, PNG) |
| `POST` | `/api/v1/documents/analyze` | AI-powered legal document analysis |
| `GET` | `/api/v1/documents` | List user documents with pagination |
| `GET` | `/api/v1/documents/analysis/{id}` | Get detailed analysis results |
| `DELETE` | `/api/v1/documents/{id}` | Delete document and all analyses |

### 📄 **DOCUMENT GENERATION (5 endpoints)**
| Method | Endpoint | Purpose |
|--------|----------|---------|
| `GET` | `/api/v1/generate/templates` | List all available document templates |
| `GET` | `/api/v1/generate/templates/{id}` | Get specific template details |
| `POST` | `/api/v1/generate/generate` | Generate document from template |
| `PUT` | `/api/v1/generate/generated/{id}` | Update generated document |
| `POST` | `/api/v1/generate/export` | Export document to PDF |

### 🤖 **ENHANCED QUERY (1 endpoint)**
| Method | Endpoint | Purpose |
|--------|----------|---------|
| `POST` | `/api/v1/counsel/query` | AI legal queries with document context |

---

## 🔧 **Key Features**

### ✅ **Document Analysis**
- Multi-format file upload (PDF, DOCX, TXT, images)
- AI-powered legal analysis with Claude Sonnet 4
- Kenyan law compliance checking
- Risk assessment and recommendations
- Legal citations with confidence scores

### ✅ **Document Generation**
- 4 professional templates (Employment, Service, Lease, Legal Notice)
- AI-generated content with legal compliance
- Multiple output formats (HTML, Markdown, Text)
- PDF export functionality
- Revision tracking and updates

### ✅ **Enhanced Query System**
- Context-aware legal AI assistant
- Document-specific queries
- Enhanced RAG with legal knowledge base
- Citation tracking and confidence scoring

---

## 📊 **Template Categories Available**

| Template ID | Name | Category | Use Case |
|-------------|------|----------|----------|
| `employment_contract` | Employment Contract | Employment | Job contracts, terms of employment |
| `service_agreement` | Service Agreement | Commercial | Professional service contracts |
| `lease_agreement` | Lease Agreement | Property | Rental and lease contracts |
| `legal_notice` | Legal Notice | Litigation | Formal legal notifications |

---

## ⚡ **Quick Integration Checklist**

### **For Document Upload:**
1. ✅ Use `multipart/form-data`
2. ✅ Include file + user_context JSON
3. ✅ Handle 10MB file size limit
4. ✅ Support PDF, DOCX, TXT, JPG, PNG

### **For Document Analysis:**
1. ✅ Use document_id from upload
2. ✅ Specify analysis_type and focus_areas
3. ✅ Enable kenyan_law_focus for compliance
4. ✅ Handle 60-second timeout

### **For Document Generation:**
1. ✅ Get templates first to show available options
2. ✅ Validate required fields before generation
3. ✅ Handle 90-second generation timeout
4. ✅ Store generation_id for future updates

### **For Enhanced Queries:**
1. ✅ Use enhanced_rag for better responses
2. ✅ Include document_context for specific analysis
3. ✅ Enable kenyan_law_focus for local compliance
4. ✅ Handle 30-second query timeout

---

## 🔄 **Common Workflows**

### **Workflow A: Document Review**
```
Upload → Analyze → Query with Context → Get Recommendations
```

### **Workflow B: Document Creation**
```
Get Templates → Generate Document → Update if needed → Export PDF
```

### **Workflow C: Legal Research**
```
Query without context → Get general legal information → Apply to specific case
```

---

## 📈 **Performance Expectations**

| Operation | Average Time | Max Timeout |
|-----------|--------------|-------------|
| Document Upload | 2-5 seconds | 30 seconds |
| Document Analysis | 15-45 seconds | 60 seconds |
| Document Generation | 30-60 seconds | 90 seconds |
| PDF Export | 5-10 seconds | 30 seconds |
| Enhanced Query | 10-20 seconds | 30 seconds |

---

## 🛡️ **Error Handling**

| Status Code | Meaning | Action |
|-------------|---------|--------|
| `200` | Success | Process response data |
| `400` | Bad Request | Check request format/validation |
| `404` | Not Found | Check IDs and endpoints |
| `429` | Rate Limited | Implement retry with backoff |
| `500` | Server Error | Show user-friendly error message |

---

## 🎯 **Production Ready Features**

✅ **AI-Powered**: Claude Sonnet 4 integration  
✅ **Kenyan Law Focus**: Local compliance checking  
✅ **Multi-Format Support**: PDF, DOCX, TXT, images  
✅ **Professional Templates**: 4 legal document types  
✅ **PDF Export**: High-quality document output  
✅ **Context-Aware Queries**: Document-specific AI responses  
✅ **Citation Tracking**: Legal source references  
✅ **Revision Management**: Document update tracking  
✅ **Rate Limiting**: Production-grade API protection  
✅ **Error Handling**: Comprehensive error responses  

**All endpoints are live and ready for frontend integration!** 🚀
