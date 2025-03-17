"""
PDF File Parser using PyPDF2

This script provides functions to:
1. Extract text from PDF files
2. Extract metadata from PDF files
3. Extract images from PDF files (requires Pillow)
4. Merge multiple PDF files
5. Split PDF files into separate pages
"""

import os
import io
import PyPDF2
from typing import List, Dict, Tuple, Optional, Any

try:
    from PIL import Image
except ImportError:
    Image = None


def extract_text_from_pdf(pdf_path: str) -> Dict[int, str]:
    """
    Extract text from all pages of a PDF file.

    Args:
        pdf_path: Path to the PDF file

    Returns:
        Dictionary with page numbers as keys and page text as values
    """
    text_by_page = {}
    try:
        with open(pdf_path, 'rb') as file:
            reader = PyPDF2.PdfReader(file)

            for page_num in range(len(reader.pages)):
                page = reader.pages[page_num]
                text_by_page[page_num + 1] = page.extract_text()

        return text_by_page

    except Exception as e:
        print(f"Error extracting text from PDF: {e}")
        return {}


def extract_metadata_from_pdf(pdf_path: str) -> Dict[str, Any]:
    """
    Extract metadata from a PDF file.

    Args:
        pdf_path: Path to the PDF file

    Returns:
        Dictionary containing the PDF metadata
    """
    try:
        with open(pdf_path, 'rb') as file:
            reader = PyPDF2.PdfReader(file)
            metadata = reader.metadata

            # Convert metadata to a regular dictionary
            if metadata:
                metadata_dict = {
                    'Title': metadata.get('/Title', ''),
                    'Author': metadata.get('/Author', ''),
                    'Subject': metadata.get('/Subject', ''),
                    'Creator': metadata.get('/Creator', ''),
                    'Producer': metadata.get('/Producer', ''),
                    'Creation Date': metadata.get('/CreationDate', ''),
                    'Modification Date': metadata.get('/ModDate', ''),
                    'Number of Pages': len(reader.pages)
                }
                return metadata_dict
            else:
                return {'Number of Pages': len(reader.pages)}

    except Exception as e:
        print(f"Error extracting metadata from PDF: {e}")
        return {}


def extract_images_from_pdf(pdf_path: str, output_dir: str) -> List[str]:
    """
    Extract images from a PDF file and save them to the specified directory.
    Requires Pillow (PIL) to be installed.

    Args:
        pdf_path: Path to the PDF file
        output_dir: Directory to save extracted images

    Returns:
        List of paths to the extracted images
    """
    if Image is None:
        print("Pillow (PIL) is required for image extraction. Install with: pip install Pillow")
        return []

    if not os.path.exists(output_dir):
        os.makedirs(output_dir)

    image_paths = []

    try:
        with open(pdf_path, 'rb') as file:
            reader = PyPDF2.PdfReader(file)

            for page_num in range(len(reader.pages)):
                page = reader.pages[page_num]

                if '/XObject' in page['/Resources']:
                    xobjects = page['/Resources']['/XObject']

                    if isinstance(xobjects, dict):
                        for obj_name, obj in xobjects.items():
                            if obj['/Subtype'] == '/Image':
                                # Get image data
                                data = obj.get_data()
                                size = (obj.get('/Width', 0), obj.get('/Height', 0))

                                if '/Filter' in obj:
                                    filters = obj['/Filter']

                                    if isinstance(filters, list):
                                        filter_type = filters[0]
                                    else:
                                        filter_type = filters

                                    # Handle different image formats
                                    if filter_type == '/DCTDecode':
                                        img_format = 'jpg'
                                    elif filter_type == '/JPXDecode':
                                        img_format = 'jp2'
                                    elif filter_type == '/FlateDecode':
                                        img_format = 'png'
                                    else:
                                        img_format = 'png'
                                else:
                                    img_format = 'png'

                                # Save image
                                img_path = os.path.join(output_dir,
                                                        f"page_{page_num + 1}_img_{obj_name.replace('/', '')}.{img_format}")

                                try:
                                    if img_format in ['jpg', 'jp2']:
                                        with open(img_path, 'wb') as img_file:
                                            img_file.write(data)
                                    else:
                                        # For other formats, use PIL
                                        if '/ColorSpace' in obj:
                                            color_space = obj['/ColorSpace']
                                            if isinstance(color_space, str) and color_space == '/DeviceRGB':
                                                mode = "RGB"
                                            else:
                                                mode = "L"
                                        else:
                                            mode = "RGB"

                                        img = Image.frombytes(mode, size, data)
                                        img.save(img_path)

                                    image_paths.append(img_path)
                                except Exception as e:
                                    print(f"Error saving image: {e}")

    except Exception as e:
        print(f"Error extracting images from PDF: {e}")

    return image_paths


def merge_pdfs(pdf_paths: List[str], output_path: str) -> bool:
    """
    Merge multiple PDF files into a single PDF.

    Args:
        pdf_paths: List of paths to PDF files to merge
        output_path: Path to save the merged PDF

    Returns:
        True if successful, False otherwise
    """
    try:
        merger = PyPDF2.PdfMerger()

        for pdf in pdf_paths:
            merger.append(pdf)

        merger.write(output_path)
        merger.close()

        return True

    except Exception as e:
        print(f"Error merging PDFs: {e}")
        return False


def split_pdf(pdf_path: str, output_dir: str) -> List[str]:
    """
    Split a PDF file into individual pages.

    Args:
        pdf_path: Path to the PDF file
        output_dir: Directory to save the individual pages

    Returns:
        List of paths to the individual pages
    """
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)

    output_paths = []

    try:
        with open(pdf_path, 'rb') as file:
            reader = PyPDF2.PdfReader(file)

            for page_num in range(len(reader.pages)):
                writer = PyPDF2.PdfWriter()
                writer.add_page(reader.pages[page_num])

                output_path = os.path.join(output_dir, f"page_{page_num + 1}.pdf")

                with open(output_path, 'wb') as output_file:
                    writer.write(output_file)

                output_paths.append(output_path)

        return output_paths

    except Exception as e:
        print(f"Error splitting PDF: {e}")
        return []


def search_text_in_pdf(pdf_path: str, search_text: str, case_sensitive: bool = False) -> List[Tuple[int, str]]:
    """
    Search for text in a PDF file and return matching pages with context.

    Args:
        pdf_path: Path to the PDF file
        search_text: Text to search for
        case_sensitive: Whether to perform a case-sensitive search

    Returns:
        List of tuples containing (page_number, context)
    """
    results = []

    try:
        text_by_page = extract_text_from_pdf(pdf_path)

        for page_num, text in text_by_page.items():
            if not case_sensitive:
                search_text_lower = search_text.lower()
                text_lower = text.lower()

                if search_text_lower in text_lower:
                    # Get some context around the match
                    index = text_lower.find(search_text_lower)
                    start = max(0, index - 50)
                    end = min(len(text), index + len(search_text) + 50)
                    context = text[start:end]

                    results.append((page_num, context))
            else:
                if search_text in text:
                    # Get some context around the match
                    index = text.find(search_text)
                    start = max(0, index - 50)
                    end = min(len(text), index + len(search_text) + 50)
                    context = text[start:end]

                    results.append((page_num, context))

        return results

    except Exception as e:
        print(f"Error searching text in PDF: {e}")
        return []


# Example usage
if __name__ == "__main__":
    # Replace with your PDF file path
    pdf_file = "example.pdf"

    # Extract text
    print("Extracting text...")
    text = extract_text_from_pdf(pdf_file)
    print(f"Extracted text from {len(text)} pages")

    # Extract metadata
    print("\nExtracting metadata...")
    metadata = extract_metadata_from_pdf(pdf_file)
    print("Metadata:", metadata)

    # Search for text
    print("\nSearching for text...")
    search_results = search_text_in_pdf(pdf_file, "example")
    print(f"Found {len(search_results)} matches")

    # Extract images (requires Pillow)
    print("\nExtracting images...")
    images = extract_images_from_pdf(pdf_file, "extracted_images")
    print(f"Extracted {len(images)} images")

    # Split PDF
    print("\nSplitting PDF...")
    split_files = split_pdf(pdf_file, "split_pages")
    print(f"Split into {len(split_files)} pages")

    # Merge PDFs (example)
    print("\nMerging PDFs...")
    if split_files:
        merge_success = merge_pdfs(split_files, "merged.pdf")
        print(f"Merge successful: {merge_success}")