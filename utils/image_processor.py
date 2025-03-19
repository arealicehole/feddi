"""
Image Processor for AccountME Discord Bot
Handles image URL storage and AI vision model integration for receipt analysis
"""

import logging
import os
import json
import re
from typing import Dict, Any, Optional, Tuple, List
import aiohttp
import base64
from datetime import datetime

# Import the xai client for Grok Vision API
try:
    from xai.client import Client as XAIClient
except ImportError:
    logging.warning("xai-client not installed. Please install with 'pip install xai-client'")
    XAIClient = None

logger = logging.getLogger("accountme_bot.image_processor")

class ImageProcessor:
    """
    Image processor class for handling receipt images via Discord URLs
    Implements AI vision model integration for receipt data extraction
    """
    
    def __init__(self):
        """
        Initialize the image processor
        """
        logger.info("Image processor initialized with Discord URL storage approach")
        self.session = None
        
        # Initialize XAI client if API key is available
        self.xai_api_key = os.getenv("XAI_API_KEY")
        self.xai_client = None
        
        if self.xai_api_key and XAIClient:
            try:
                self.xai_client = XAIClient(api_key=self.xai_api_key)
                logger.info("XAI client initialized for Grok Vision API")
            except Exception as e:
                logger.error(f"Failed to initialize XAI client: {str(e)}")
        else:
            logger.warning("XAI API key not found or xai-client not installed. Vision features will be limited.")
    
    async def _ensure_session(self):
        """Ensure aiohttp session exists"""
        if self.session is None or self.session.closed:
            self.session = aiohttp.ClientSession()
    
    async def close(self):
        """Close the aiohttp session"""
        if self.session and not self.session.closed:
            await self.session.close()
    
    async def store_receipt_url(self, discord_url: str, message_id: str) -> str:
        """
        Store a Discord image URL for future reference
        
        Args:
            discord_url: Discord CDN URL for the image
            message_id: Discord message ID containing the image
            
        Returns:
            The stored Discord URL
        """
        # In a real implementation, you might want to store this URL in your database
        # For now, we'll just log it and return it
        logger.info(f"Receipt image URL stored: {discord_url} (Message ID: {message_id})")
        return discord_url
    
    async def _download_image_from_url(self, image_url: str) -> Optional[bytes]:
        """
        Download image data from a URL
        
        Args:
            image_url: URL of the image
            
        Returns:
            Image data as bytes or None if download failed
        """
        await self._ensure_session()
        try:
            async with self.session.get(image_url) as response:
                if response.status == 200:
                    return await response.read()
                else:
                    logger.error(f"Failed to download image from {image_url}: HTTP {response.status}")
                    return None
        except Exception as e:
            logger.error(f"Error downloading image from {image_url}: {str(e)}")
            return None
    
    async def extract_text_from_url(self, image_url: str) -> str:
        """
        Extract text from an image using XAI Grok Vision model
        
        Args:
            image_url: URL of the image
            
        Returns:
            Extracted text
        """
        logger.info(f"AI vision text extraction requested for {image_url}")
        
        if not self.xai_client:
            logger.warning("XAI client not initialized. Cannot perform text extraction.")
            return "Error: XAI client not initialized. Check API key configuration."
        
        try:
            # Download the image
            image_data = await self._download_image_from_url(image_url)
            if not image_data:
                return "Error: Failed to download image"
            
            # Encode image to base64
            image_base64 = base64.b64encode(image_data).decode('utf-8')
            
            # Call the Grok Vision API
            response = self.xai_client.chat.completions.create(
                model="grok-2-vision-1212",
                messages=[
                    {
                        "role": "system",
                        "content": "You are an OCR assistant that extracts text from receipt images. Extract all text from the image, preserving the structure as much as possible."
                    },
                    {
                        "role": "user",
                        "content": [
                            {"type": "text", "text": "Extract all text from this receipt image."},
                            {"type": "image", "image": image_base64}
                        ]
                    }
                ],
                max_tokens=1000
            )
            
            # Extract the text from the response
            extracted_text = response.choices[0].message.content
            logger.info(f"Successfully extracted text from image using Grok Vision API")
            return extracted_text
            
        except Exception as e:
            logger.error(f"Error extracting text from image: {str(e)}")
            return f"Error extracting text: {str(e)}"
    
    def _parse_date(self, text: str) -> Optional[str]:
        """
        Parse date from receipt text
        
        Args:
            text: Extracted text from receipt
            
        Returns:
            Date string in YYYY-MM-DD format or None if not found
        """
        # Try various date formats
        date_patterns = [
            # MM/DD/YYYY
            r'(\d{1,2})[/\-](\d{1,2})[/\-](\d{4})',
            # DD/MM/YYYY
            r'(\d{1,2})[/\-](\d{1,2})[/\-](\d{4})',
            # YYYY/MM/DD
            r'(\d{4})[/\-](\d{1,2})[/\-](\d{1,2})',
            # Month name formats
            r'(Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]* (\d{1,2}),? (\d{4})',
            r'(\d{1,2}) (Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]* (\d{4})'
        ]
        
        for pattern in date_patterns:
            matches = re.findall(pattern, text, re.IGNORECASE)
            if matches:
                # Process the first match
                match = matches[0]
                if len(match) == 3:
                    # Convert to YYYY-MM-DD format
                    if pattern == date_patterns[0]:  # MM/DD/YYYY
                        month, day, year = match
                    elif pattern == date_patterns[1]:  # DD/MM/YYYY
                        day, month, year = match
                    elif pattern == date_patterns[2]:  # YYYY/MM/DD
                        year, month, day = match
                    elif pattern == date_patterns[3]:  # Month name DD, YYYY
                        month_name, day, year = match
                        month = self._month_name_to_number(month_name)
                    elif pattern == date_patterns[4]:  # DD Month name YYYY
                        day, month_name, year = match
                        month = self._month_name_to_number(month_name)
                    
                    # Ensure proper formatting
                    try:
                        month = int(month)
                        day = int(day)
                        year = int(year)
                        
                        # Handle two-digit years
                        if year < 100:
                            current_year = datetime.now().year
                            century = current_year // 100 * 100
                            year = century + year
                            if year > current_year + 20:  # If more than 20 years in future
                                year -= 100  # Assume previous century
                        
                        return f"{year:04d}-{month:02d}-{day:02d}"
                    except (ValueError, TypeError):
                        continue
        
        return None
    
    def _month_name_to_number(self, month_name: str) -> int:
        """Convert month name to number"""
        months = {
            'jan': 1, 'feb': 2, 'mar': 3, 'apr': 4, 'may': 5, 'jun': 6,
            'jul': 7, 'aug': 8, 'sep': 9, 'oct': 10, 'nov': 11, 'dec': 12
        }
        return months.get(month_name.lower()[:3], 1)  # Default to January if not found
    
    def _parse_vendor(self, text: str) -> Optional[str]:
        """
        Parse vendor name from receipt text
        
        Args:
            text: Extracted text from receipt
            
        Returns:
            Vendor name or None if not found
        """
        # Look for vendor name at the top of the receipt
        lines = text.split('\n')
        non_empty_lines = [line.strip() for line in lines if line.strip()]
        
        if len(non_empty_lines) >= 2:
            # Often the first or second non-empty line contains the vendor name
            potential_vendor = non_empty_lines[0]
            
            # Skip if it looks like a date or address
            if re.search(r'\d{1,2}[/\-]\d{1,2}[/\-]\d{2,4}', potential_vendor) or \
               re.search(r'\d+ [A-Za-z]+ (St|Ave|Rd|Blvd|Lane|Drive|Dr|Road|Street)', potential_vendor):
                potential_vendor = non_empty_lines[1] if len(non_empty_lines) > 1 else None
            
            return potential_vendor
        
        return None
    
    def _parse_total_amount(self, text: str) -> Optional[float]:
        """
        Parse total amount from receipt text
        
        Args:
            text: Extracted text from receipt
            
        Returns:
            Total amount as float or None if not found
        """
        # Look for total amount patterns
        total_patterns = [
            r'total\s*[:\$]?\s*(\d+[\.,]\d{2})',
            r'amount\s*[:\$]?\s*(\d+[\.,]\d{2})',
            r'grand total\s*[:\$]?\s*(\d+[\.,]\d{2})',
            r'balance\s*[:\$]?\s*(\d+[\.,]\d{2})',
            r'amount due\s*[:\$]?\s*(\d+[\.,]\d{2})',
            r'total\s*\$?\s*(\d+[\.,]\d{2})',
            r'(?:^|\s)(?:total|tot)(?:\s|$).*?(\d+[\.,]\d{2})',
            r'(?:^|\s)(?:sum|amt)(?:\s|$).*?(\d+[\.,]\d{2})'
        ]
        
        for pattern in total_patterns:
            matches = re.findall(pattern, text, re.IGNORECASE | re.MULTILINE)
            if matches:
                # Get the last match, as it's more likely to be the grand total
                try:
                    # Replace comma with dot for proper float parsing
                    amount_str = matches[-1].replace(',', '.')
                    return float(amount_str)
                except (ValueError, TypeError):
                    continue
        
        return None
    
    def _parse_tax(self, text: str) -> Optional[float]:
        """
        Parse tax amount from receipt text
        
        Args:
            text: Extracted text from receipt
            
        Returns:
            Tax amount as float or None if not found
        """
        # Look for tax amount patterns
        tax_patterns = [
            r'tax\s*[:\$]?\s*(\d+[\.,]\d{2})',
            r'vat\s*[:\$]?\s*(\d+[\.,]\d{2})',
            r'sales tax\s*[:\$]?\s*(\d+[\.,]\d{2})',
            r'gst\s*[:\$]?\s*(\d+[\.,]\d{2})',
            r'hst\s*[:\$]?\s*(\d+[\.,]\d{2})'
        ]
        
        for pattern in tax_patterns:
            matches = re.findall(pattern, text, re.IGNORECASE | re.MULTILINE)
            if matches:
                try:
                    # Replace comma with dot for proper float parsing
                    tax_str = matches[0].replace(',', '.')
                    return float(tax_str)
                except (ValueError, TypeError):
                    continue
        
        return None
    
    def _parse_items(self, text: str) -> List[Dict[str, Any]]:
        """
        Parse line items from receipt text
        
        Args:
            text: Extracted text from receipt
            
        Returns:
            List of items with name, quantity, and price
        """
        items = []
        
        # This is a simplified approach - real receipts vary widely in format
        # Look for patterns like "Item name    $XX.XX" or "X Item name    $XX.XX"
        lines = text.split('\n')
        
        # Simple item pattern: description followed by price at the end
        item_pattern = r'(.*?)\s+(\d+[\.,]\d{2})$'
        
        for line in lines:
            line = line.strip()
            if not line:
                continue
                
            # Skip lines that are likely headers or footers
            if re.search(r'(subtotal|total|tax|date|receipt|invoice|thank you)', line, re.IGNORECASE):
                continue
                
            match = re.search(item_pattern, line)
            if match:
                description = match.group(1).strip()
                price_str = match.group(2).replace(',', '.')
                
                try:
                    price = float(price_str)
                    
                    # Try to extract quantity if present
                    qty_match = re.search(r'^(\d+)\s+x\s+', description)
                    quantity = 1
                    if qty_match:
                        quantity = int(qty_match.group(1))
                        description = description[qty_match.end():].strip()
                    
                    items.append({
                        "description": description,
                        "quantity": quantity,
                        "price": price,
                        "total": quantity * price
                    })
                except (ValueError, TypeError):
                    continue
        
        return items
    
    def _calculate_confidence(self, parsed_data: Dict[str, Any]) -> float:
        """
        Calculate confidence score for parsed receipt data
        
        Args:
            parsed_data: Dictionary of parsed receipt data
            
        Returns:
            Confidence score between 0.0 and 1.0
        """
        # Count how many fields were successfully parsed
        fields = ["date", "vendor", "total_amount", "tax"]
        parsed_fields = sum(1 for field in fields if parsed_data.get(field) is not None)
        
        # Add weight for items
        items_count = len(parsed_data.get("items", []))
        items_weight = min(items_count / 3, 1.0)  # Cap at 1.0
        
        # Calculate confidence
        base_confidence = parsed_fields / len(fields)
        confidence = (base_confidence * 0.8) + (items_weight * 0.2)
        
        return round(confidence, 2)
    
    async def parse_receipt_from_url(self, image_url: str) -> Dict[str, Any]:
        """
        Parse a receipt image URL to extract structured data using XAI Grok Vision
        
        Args:
            image_url: URL of the image
            
        Returns:
            Dictionary of extracted receipt data
        """
        logger.info(f"Receipt parsing requested for {image_url}")
        
        # Extract text from the image
        extracted_text = await self.extract_text_from_url(image_url)
        
        # Initialize result with default values
        result = {
            "date": None,
            "vendor": None,
            "total_amount": None,
            "items": [],
            "tax": None,
            "confidence": 0.0,
            "raw_text": extracted_text
        }
        
        # If text extraction failed, return the empty result
        if extracted_text.startswith("Error:"):
            logger.error(f"Failed to extract text from receipt: {extracted_text}")
            return result
        
        # Parse the extracted text
        result["date"] = self._parse_date(extracted_text)
        result["vendor"] = self._parse_vendor(extracted_text)
        result["total_amount"] = self._parse_total_amount(extracted_text)
        result["tax"] = self._parse_tax(extracted_text)
        result["items"] = self._parse_items(extracted_text)
        
        # Calculate confidence score
        result["confidence"] = self._calculate_confidence(result)
        
        logger.info(f"Receipt parsed with confidence: {result['confidence']}")
        return result