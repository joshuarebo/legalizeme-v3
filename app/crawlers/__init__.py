"""
Web crawlers package for legal document collection
"""

from .base_crawler import BaseCrawler
from .kenya_law_crawler import KenyaLawCrawler
from .parliament_crawler import ParliamentCrawler

__all__ = ["BaseCrawler", "KenyaLawCrawler", "ParliamentCrawler"]
