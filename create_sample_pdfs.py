"""
Create Sample PDF Documents for Multi-Modal Testing
Generates comprehensive PDF samples from text files for testing all document types
"""

import os
from pathlib import Path
from reportlab.lib.pagesizes import letter, A4
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, PageBreak
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.lib.enums import TA_LEFT, TA_CENTER, TA_JUSTIFY
from PIL import Image, ImageDraw, ImageFont
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class PDFSampleGenerator:
    """Generate sample PDF documents for testing"""

    def __init__(self):
        self.samples_dir = Path("data/samples")
        self.samples_dir.mkdir(parents=True, exist_ok=True)

        # Setup styles
        self.styles = getSampleStyleSheet()
        self.title_style = ParagraphStyle(
            'CustomTitle',
            parent=self.styles['Heading1'],
            fontSize=16,
            spaceAfter=30,
            alignment=TA_CENTER
        )
        self.heading_style = ParagraphStyle(
            'CustomHeading',
            parent=self.styles['Heading2'],
            fontSize=14,
            spaceAfter=12,
            spaceBefore=12
        )
        self.body_style = ParagraphStyle(
            'CustomBody',
            parent=self.styles['Normal'],
            fontSize=11,
            spaceAfter=6,
            alignment=TA_JUSTIFY
        )

    def create_pdf_from_text(self, text_file: Path, output_file: Path, title: str = None):
        """Create PDF from text file"""
        try:
            # Read text content
            with open(text_file, 'r', encoding='utf-8') as f:
                content = f.read()

            # Create PDF
            doc = SimpleDocTemplate(str(output_file), pagesize=A4)
            story = []

            # Add title if provided
            if title:
                story.append(Paragraph(title, self.title_style))
                story.append(Spacer(1, 20))

            # Split content into paragraphs and format
            paragraphs = content.split('\n\n')

            for para in paragraphs:
                if para.strip():
                    # Check if it's a heading (all caps or starts with number)
                    if para.strip().isupper() or para.strip()[0].isdigit():
                        story.append(Paragraph(para.strip(), self.heading_style))
                    else:
                        story.append(Paragraph(para.strip(), self.body_style))
                    story.append(Spacer(1, 6))

            # Build PDF
            doc.build(story)
            logger.info(f"Created PDF: {output_file}")
            return True

        except Exception as e:
            logger.error(f"Error creating PDF {output_file}: {e}")
            return False

    def create_sample_image_with_text(self, text: str, output_file: Path,
                                    width: int = 800, height: int = 600):
        """Create sample image with text for OCR testing"""
        try:
            # Create image
            img = Image.new('RGB', (width, height), color='white')
            draw = ImageDraw.Draw(img)

            # Try to use a system font, fallback to default
            try:
                font = ImageFont.truetype("arial.ttf", 24)
                small_font = ImageFont.truetype("arial.ttf", 18)
            except:
                font = ImageFont.load_default()
                small_font = ImageFont.load_default()

            # Add text with word wrapping
            lines = []
            words = text.split()
            current_line = ""

            for word in words:
                test_line = current_line + " " + word if current_line else word
                bbox = draw.textbbox((0, 0), test_line, font=font)
                if bbox[2] - bbox[0] < width - 100:  # Leave margin
                    current_line = test_line
                else:
                    if current_line:
                        lines.append(current_line)
                    current_line = word

            if current_line:
                lines.append(current_line)

            # Draw text lines
            y_offset = 50
            for line in lines[:20]:  # Limit to 20 lines
                draw.text((50, y_offset), line, fill='black', font=font)
                y_offset += 35

                if y_offset > height - 100:
                    break

            # Save image
            img.save(output_file)
            logger.info(f"Created image: {output_file}")
            return True

        except Exception as e:
            logger.error(f"Error creating image {output_file}: {e}")
            return False

    def generate_all_samples(self):
        """Generate all sample documents"""
        logger.info("Starting sample document generation...")

        # Text files to convert to PDF
        text_files = {
            "employment_contract_sample.txt": "Employment Contract Sample",
            "affidavit_sample.txt": "Affidavit Sample",
            "civil_case_summary.txt": "Civil Case Judgment Sample"
        }

        # Generate PDFs from text files
        for text_file, title in text_files.items():
            text_path = self.samples_dir / text_file
            pdf_path = self.samples_dir / text_file.replace('.txt', '.pdf')

            if text_path.exists():
                self.create_pdf_from_text(text_path, pdf_path, title)
            else:
                logger.warning(f"Text file not found: {text_path}")

        # Generate sample images for OCR testing
        sample_texts = {
            "scanned_affidavit.png": """
REPUBLIC OF KENYA
AFFIDAVIT

I, JOHN DOE, of P.O. Box 12345, Nairobi, do solemnly affirm:

1. THAT I am the applicant in this matter and competent to make this affidavit.

2. THAT on 10th December 2023, I entered into a contract with the respondent.

3. THAT the respondent has failed to fulfill their obligations under the contract.

4. THAT I have suffered damages as a result of this breach.

SWORN at Nairobi this 15th day of January, 2024.

_________________
DEPONENT
            """,
            "scanned_contract.png": """
EMPLOYMENT CONTRACT

Between: ABC Company Limited
And: John Doe

Position: Senior Legal Counsel
Salary: KSh 150,000 per month
Start Date: 1st February 2024

Terms and Conditions:
1. Working hours: 8:00 AM to 5:00 PM
2. Annual leave: 21 days
3. Notice period: 30 days

Signed:
_________________    _________________
Company             Employee
            """
        }

        for image_file, text in sample_texts.items():
            image_path = self.samples_dir / image_file
            self.create_sample_image_with_text(text.strip(), image_path)

        logger.info("Sample document generation completed!")

def main():
    """Main execution"""
    try:
        # Install reportlab if not available
        try:
            import reportlab
        except ImportError:
            import subprocess
            import sys
            subprocess.check_call([sys.executable, "-m", "pip", "install", "reportlab"])
            import reportlab

        generator = PDFSampleGenerator()
        generator.generate_all_samples()

        print("\n✅ Sample document generation completed!")
        print("Generated files:")

        samples_dir = Path("data/samples")
        for file in sorted(samples_dir.glob("*")):
            if file.is_file():
                size_kb = file.stat().st_size / 1024
                print(f"  📄 {file.name} ({size_kb:.1f} KB)")

    except Exception as e:
        print(f"❌ Error generating samples: {e}")

if __name__ == "__main__":
    main()