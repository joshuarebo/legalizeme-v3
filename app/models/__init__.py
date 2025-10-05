from .user import User
from .document import Document
from .query import Query
from .legal_case import LegalCase

# Try to import optional models
_all_models = ["User", "Document", "Query", "LegalCase"]

try:
    from .conversation import Conversation, ConversationMessage
    _all_models.extend(["Conversation", "ConversationMessage"])
except ImportError:
    pass

try:
    from .token_tracking import UserTokens, TokenUsageHistory
    _all_models.extend(["UserTokens", "TokenUsageHistory"])
except ImportError:
    pass

# CounselDocs models (optional)
try:
    from app.counseldocs.models.document_analysis import DocumentAnalysis
    from app.counseldocs.models.document_generation import DocumentGeneration
    from app.counseldocs.models.document_archive import DocumentArchive
    _all_models.extend(["DocumentAnalysis", "DocumentGeneration", "DocumentArchive"])
except ImportError:
    pass

__all__ = _all_models
