import re
import logging
from typing import List, Dict, Any, Optional, Tuple
import string
from collections import Counter
import math

# Optional imports - these are heavy dependencies that may not be available
try:
    import nltk
    from nltk.tokenize import word_tokenize, sent_tokenize
    from nltk.corpus import stopwords
    from nltk.stem import WordNetLemmatizer
    HAS_NLTK = True
except ImportError:
    HAS_NLTK = False
    logger = logging.getLogger(__name__)
    logger.warning("NLTK not available, using basic text processing")

logger = logging.getLogger(__name__)

# Download required NLTK data if available
if HAS_NLTK:
    try:
        nltk.data.find('tokenizers/punkt')
    except LookupError:
        nltk.download('punkt')

    try:
        nltk.data.find('corpora/stopwords')
    except LookupError:
        nltk.download('stopwords')

    try:
        nltk.data.find('corpora/wordnet')
    except LookupError:
        nltk.download('wordnet')

class TextProcessor:
    """Utility class for text processing and analysis"""
    
    def __init__(self):
        if HAS_NLTK:
            self.lemmatizer = WordNetLemmatizer()
            self.stop_words = set(stopwords.words('english'))
        else:
            self.lemmatizer = None
            # Basic English stop words fallback
            self.stop_words = {
                'i', 'me', 'my', 'myself', 'we', 'our', 'ours', 'ourselves', 'you', 'your', 
                'yours', 'yourself', 'yourselves', 'he', 'him', 'his', 'himself', 'she', 
                'her', 'hers', 'herself', 'it', 'its', 'itself', 'they', 'them', 'their', 
                'theirs', 'themselves', 'what', 'which', 'who', 'whom', 'this', 'that', 
                'these', 'those', 'am', 'is', 'are', 'was', 'were', 'be', 'been', 'being', 
                'have', 'has', 'had', 'having', 'do', 'does', 'did', 'doing', 'a', 'an', 
                'the', 'and', 'but', 'if', 'or', 'because', 'as', 'until', 'while', 'of', 
                'at', 'by', 'for', 'with', 'through', 'during', 'before', 'after', 'above', 
                'below', 'up', 'down', 'in', 'out', 'on', 'off', 'over', 'under', 'again', 
                'further', 'then', 'once'
            }
        
        # Legal-specific stop words
        self.legal_stop_words = {
            'whereas', 'hereby', 'herein', 'hereof', 'hereunder', 'hereinafter',
            'aforesaid', 'aforementioned', 'said', 'such', 'same', 'thereof',
            'therein', 'thereon', 'thereunder', 'provided', 'however', 'notwithstanding'
        }
        
        self.stop_words.update(self.legal_stop_words)
        
        # Common legal phrases for Kenya
        self.kenyan_legal_terms = {
            'high court', 'court of appeal', 'supreme court', 'magistrate court',
            'constitution of kenya', 'penal code', 'criminal procedure code',
            'evidence act', 'civil procedure act', 'land act', 'companies act',
            'employment act', 'public procurement', 'county government'
        }
    
    def clean_text(self, text: str) -> str:
        """Clean and normalize text"""
        if not text:
            return ""
        
        # Remove extra whitespace
        text = re.sub(r'\s+', ' ', text)
        
        # Remove special characters but keep legal symbols
        text = re.sub(r'[^\w\s\.\,\;\:\!\?\-\(\)\[\]\{\}\/\&\%\$\#\@]', '', text)
        
        # Normalize quotes
        text = re.sub(r'[""''`]', '"', text)
        
        # Remove multiple periods
        text = re.sub(r'\.{3,}', '...', text)
        
        # Strip and return
        return text.strip()
    
    def extract_sentences(self, text: str) -> List[str]:
        """Extract sentences from text"""
        try:
            cleaned_text = self.clean_text(text)
            sentences = sent_tokenize(cleaned_text)
            return [s.strip() for s in sentences if len(s.strip()) > 10]
        except Exception as e:
            logger.error(f"Error extracting sentences: {e}")
            return []
    
    def extract_keywords(self, text: str, max_keywords: int = 20) -> List[str]:
        """Extract keywords from text using TF-IDF approach"""
        try:
            # Clean and tokenize
            cleaned_text = self.clean_text(text.lower())
            words = word_tokenize(cleaned_text)
            
            # Filter words
            words = [
                word for word in words
                if word.isalpha() and 
                len(word) > 2 and 
                word not in self.stop_words
            ]
            
            # Lemmatize
            words = [self.lemmatizer.lemmatize(word) for word in words]
            
            # Calculate word frequencies
            word_freq = Counter(words)
            
            # Calculate TF-IDF scores (simplified)
            total_words = len(words)
            unique_words = len(set(words))
            
            tfidf_scores = {}
            for word, freq in word_freq.items():
                tf = freq / total_words
                idf = math.log(unique_words / freq) if freq > 0 else 0
                tfidf_scores[word] = tf * idf
            
            # Sort by TF-IDF score
            sorted_keywords = sorted(tfidf_scores.items(), key=lambda x: x[1], reverse=True)
            
            return [keyword for keyword, score in sorted_keywords[:max_keywords]]
            
        except Exception as e:
            logger.error(f"Error extracting keywords: {e}")
            return []
    
    def extract_legal_entities(self, text: str) -> Dict[str, List[str]]:
        """Extract legal entities from text"""
        entities = {
            'courts': [],
            'acts': [],
            'cases': [],
            'sections': [],
            'articles': [],
            'organizations': [],
            'locations': []
        }
        
        try:
            # Court patterns
            court_patterns = [
                r'(?:High Court|Court of Appeal|Supreme Court|Magistrate[s]? Court|Commercial Court|Employment Court|Environment Court)',
                r'(?:Chief Justice|Justice|Judge|Magistrate)\s+[A-Z][a-z]+(?:\s+[A-Z][a-z]+)*',
                r'(?:Hon\.?\s+)?(?:Justice|Judge|Magistrate)\s+[A-Z][a-z]+(?:\s+[A-Z][a-z]+)*'
            ]
            
            for pattern in court_patterns:
                matches = re.findall(pattern, text, re.IGNORECASE)
                entities['courts'].extend(matches)
            
            # Acts and legislation
            act_patterns = [
                r'[A-Z][a-z]+(?:\s+[A-Z][a-z]+)*\s+Act(?:\s+\d{4})?',
                r'Constitution\s+of\s+Kenya(?:\s+\d{4})?',
                r'[A-Z][a-z]+(?:\s+[A-Z][a-z]+)*\s+Code(?:\s+\d{4})?',
                r'[A-Z][a-z]+(?:\s+[A-Z][a-z]+)*\s+Rules(?:\s+\d{4})?'
            ]
            
            for pattern in act_patterns:
                matches = re.findall(pattern, text)
                entities['acts'].extend(matches)
            
            # Case citations
            case_patterns = [
                r'[A-Z][a-z]+(?:\s+[A-Z][a-z]+)*\s+v\.?\s+[A-Z][a-z]+(?:\s+[A-Z][a-z]+)*(?:\s+\[\d{4}\])?',
                r'[A-Z][a-z]+(?:\s+[A-Z][a-z]+)*\s+vs\.?\s+[A-Z][a-z]+(?:\s+[A-Z][a-z]+)*(?:\s+\[\d{4}\])?'
            ]
            
            for pattern in case_patterns:
                matches = re.findall(pattern, text)
                entities['cases'].extend(matches)
            
            # Sections and articles
            section_patterns = [
                r'[Ss]ection\s+\d+(?:\([a-z]\))?',
                r'[Aa]rticle\s+\d+(?:\([a-z]\))?',
                r'[Pp]aragraph\s+\d+(?:\([a-z]\))?',
                r'[Cc]hapter\s+\d+(?:\([a-z]\))?'
            ]
            
            for pattern in section_patterns:
                matches = re.findall(pattern, text)
                entities['sections'].extend(matches)
            
            # Organizations
            org_patterns = [
                r'[A-Z][a-z]+(?:\s+[A-Z][a-z]+)*\s+(?:Limited|Ltd|Company|Corp|Corporation|Authority|Commission|Board|Council)',
                r'(?:Kenya|Kenyan)\s+[A-Z][a-z]+(?:\s+[A-Z][a-z]+)*',
                r'(?:Ministry|Department|State Department)\s+of\s+[A-Z][a-z]+(?:\s+[A-Z][a-z]+)*'
            ]
            
            for pattern in org_patterns:
                matches = re.findall(pattern, text)
                entities['organizations'].extend(matches)
            
            # Locations (Kenyan specific)
            location_patterns = [
                r'(?:Nairobi|Mombasa|Kisumu|Nakuru|Eldoret|Thika|Malindi|Kitale|Garissa|Kakamega|Nyeri|Machakos|Meru|Embu|Kericho|Voi|Bungoma|Kilifi|Lamu|Isiolo|Marsabit|Wajir|Mandera|Turkana|West Pokot|Baringo|Laikipia|Samburu|Trans Nzoia|Uasin Gishu|Elgeyo Marakwet|Nandi|Bomet|Kericho|Nyamira|Kisii|Migori|Homa Bay|Siaya|Busia|Vihiga|Kakamega|Bungoma|Mount Kenya|Rift Valley|Central|Eastern|Western|Nyanza|Coast|North Eastern|Nairobi County|Kiambu County|Murang\'a County|Nyandarua County|Nyeri County|Kirinyaga County|Embu County|Tharaka Nithi County|Meru County|Isiolo County|Marsabit County|Samburu County|Baringo County|Laikipia County|Nakuru County|Narok County|Kajiado County|Kericho County|Bomet County|Kakamega County|Vihiga County|Bungoma County|Busia County|Siaya County|Kisumu County|Homa Bay County|Migori County|Kisii County|Nyamira County|Trans Nzoia County|Uasin Gishu County|Elgeyo Marakwet County|Nandi County|West Pokot County|Turkana County|Wajir County|Mandera County|Garissa County|Tana River County|Lamu County|Taita Taveta County|Kwale County|Kilifi County|Mombasa County|Machakos County|Kitui County|Makueni County)',
                r'(?:Republic\s+of\s+Kenya|Kenya)',
                r'(?:East Africa|Eastern Africa)'
            ]
            
            for pattern in location_patterns:
                matches = re.findall(pattern, text, re.IGNORECASE)
                entities['locations'].extend(matches)
            
            # Clean up duplicates and empty entries
            for key in entities:
                entities[key] = list(set([item.strip() for item in entities[key] if item.strip()]))
            
            return entities
            
        except Exception as e:
            logger.error(f"Error extracting legal entities: {e}")
            return entities
    
    def calculate_readability(self, text: str) -> float:
        """Calculate readability score using Flesch Reading Ease"""
        try:
            sentences = self.extract_sentences(text)
            if not sentences:
                return 0.0
            
            words = word_tokenize(text.lower())
            words = [word for word in words if word.isalpha()]
            
            if not words:
                return 0.0
            
            # Count syllables
            def count_syllables(word):
                vowels = 'aeiouy'
                syllables = 0
                prev_was_vowel = False
                
                for char in word.lower():
                    if char in vowels:
                        if not prev_was_vowel:
                            syllables += 1
                        prev_was_vowel = True
                    else:
                        prev_was_vowel = False
                
                # Handle silent 'e'
                if word.endswith('e') and syllables > 1:
                    syllables -= 1
                
                return max(1, syllables)
            
            total_syllables = sum(count_syllables(word) for word in words)
            total_words = len(words)
            total_sentences = len(sentences)
            
            if total_sentences == 0:
                return 0.0
            
            # Flesch Reading Ease score
            score = 206.835 - (1.015 * (total_words / total_sentences)) - (84.6 * (total_syllables / total_words))
            
            # Normalize to 0-100 scale
            return max(0.0, min(100.0, score))
            
        except Exception as e:
            logger.error(f"Error calculating readability: {e}")
            return 0.0
    
    def extract_dates(self, text: str) -> List[str]:
        """Extract dates from text"""
        date_patterns = [
            r'\b\d{1,2}[\/\-\.]\d{1,2}[\/\-\.]\d{2,4}\b',  # MM/DD/YYYY or DD/MM/YYYY
            r'\b\d{1,2}(?:st|nd|rd|th)?\s+(?:January|February|March|April|May|June|July|August|September|October|November|December)\s+\d{2,4}\b',  # 1st January 2021
            r'\b(?:January|February|March|April|May|June|July|August|September|October|November|December)\s+\d{1,2}(?:st|nd|rd|th)?\s*,?\s*\d{2,4}\b',  # January 1st, 2021
            r'\b\d{2,4}[\/\-\.]\d{1,2}[\/\-\.]\d{1,2}\b',  # YYYY/MM/DD
            r'\b\d{1,2}[\/\-\.]\d{1,2}[\/\-\.]\d{2,4}\b'   # DD/MM/YYYY
        ]
        
        dates = []
        for pattern in date_patterns:
            matches = re.findall(pattern, text, re.IGNORECASE)
            dates.extend(matches)
        
        return list(set(dates))
    
    def extract_amounts(self, text: str) -> List[str]:
        """Extract monetary amounts from text"""
        amount_patterns = [
            r'(?:KES|Ksh|Kenya Shillings?)\s*[\d,]+(?:\.\d{2})?',
            r'[\d,]+(?:\.\d{2})?\s*(?:KES|Ksh|Kenya Shillings?)',
            r'(?:USD|US\$|\$)\s*[\d,]+(?:\.\d{2})?',
            r'[\d,]+(?:\.\d{2})?\s*(?:USD|US\$|\$)',
            r'(?:EUR|€)\s*[\d,]+(?:\.\d{2})?',
            r'[\d,]+(?:\.\d{2})?\s*(?:EUR|€)',
            r'(?:GBP|£)\s*[\d,]+(?:\.\d{2})?',
            r'[\d,]+(?:\.\d{2})?\s*(?:GBP|£)'
        ]
        
        amounts = []
        for pattern in amount_patterns:
            matches = re.findall(pattern, text, re.IGNORECASE)
            amounts.extend(matches)
        
        return list(set(amounts))
    
    def summarize_text(self, text: str, max_sentences: int = 3) -> str:
        """Create a simple extractive summary"""
        try:
            sentences = self.extract_sentences(text)
            if len(sentences) <= max_sentences:
                return ' '.join(sentences)
            
            # Score sentences based on word frequency
            words = word_tokenize(text.lower())
            words = [word for word in words if word.isalpha() and word not in self.stop_words]
            word_freq = Counter(words)
            
            sentence_scores = {}
            for sentence in sentences:
                sentence_words = word_tokenize(sentence.lower())
                sentence_words = [word for word in sentence_words if word.isalpha()]
                
                score = 0
                for word in sentence_words:
                    if word in word_freq:
                        score += word_freq[word]
                
                if len(sentence_words) > 0:
                    sentence_scores[sentence] = score / len(sentence_words)
            
            # Select top sentences
            top_sentences = sorted(sentence_scores.items(), key=lambda x: x[1], reverse=True)[:max_sentences]
            
            # Sort by original order
            selected_sentences = []
            for sentence in sentences:
                if any(sentence == s[0] for s in top_sentences):
                    selected_sentences.append(sentence)
                if len(selected_sentences) >= max_sentences:
                    break
            
            return ' '.join(selected_sentences)
            
        except Exception as e:
            logger.error(f"Error summarizing text: {e}")
            return text[:500] + "..." if len(text) > 500 else text
    
    def detect_language(self, text: str) -> str:
        """Simple language detection (basic implementation)"""
        try:
            # Count English words
            english_words = set(stopwords.words('english'))
            words = word_tokenize(text.lower())
            english_count = sum(1 for word in words if word in english_words)
            
            # Simple heuristic
            if english_count / len(words) > 0.1:
                return 'en'
            else:
                return 'unknown'
                
        except Exception as e:
            logger.error(f"Error detecting language: {e}")
            return 'unknown'
    
    def extract_phone_numbers(self, text: str) -> List[str]:
        """Extract phone numbers from text"""
        phone_patterns = [
            r'\+254\s*\d{3}\s*\d{3}\s*\d{3}',  # +254 XXX XXX XXX
            r'0\d{3}\s*\d{3}\s*\d{3}',  # 0XXX XXX XXX
            r'\+254\d{9}',  # +254XXXXXXXXX
            r'0\d{9}',  # 0XXXXXXXXX
            r'\(\+254\)\s*\d{3}\s*\d{3}\s*\d{3}',  # (+254) XXX XXX XXX
        ]
        
        phone_numbers = []
        for pattern in phone_patterns:
            matches = re.findall(pattern, text)
            phone_numbers.extend(matches)
        
        return list(set(phone_numbers))
    
    def extract_email_addresses(self, text: str) -> List[str]:
        """Extract email addresses from text"""
        email_pattern = r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'
        emails = re.findall(email_pattern, text)
        return list(set(emails))
    
    def get_text_statistics(self, text: str) -> Dict[str, Any]:
        """Get comprehensive text statistics"""
        try:
            sentences = self.extract_sentences(text)
            words = word_tokenize(text)
            words = [word for word in words if word.isalpha()]
            
            chars = len(text)
            chars_no_spaces = len(text.replace(' ', ''))
            
            return {
                'character_count': chars,
                'character_count_no_spaces': chars_no_spaces,
                'word_count': len(words),
                'sentence_count': len(sentences),
                'paragraph_count': len(text.split('\n\n')),
                'average_words_per_sentence': len(words) / len(sentences) if sentences else 0,
                'average_characters_per_word': chars_no_spaces / len(words) if words else 0,
                'readability_score': self.calculate_readability(text),
                'language': self.detect_language(text),
                'unique_words': len(set(word.lower() for word in words)),
                'lexical_diversity': len(set(word.lower() for word in words)) / len(words) if words else 0
            }
            
        except Exception as e:
            logger.error(f"Error getting text statistics: {e}")
            return {}
