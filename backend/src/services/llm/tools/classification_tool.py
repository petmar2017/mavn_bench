"""Classification tool for categorizing documents"""

from typing import Dict, Any, List, Tuple, Optional

from ..base_tool import BaseLLMTool, ToolMetadata, ToolCapability
from ..tool_registry import LLMToolType
from ..tool_decorators import register_tool


@register_tool(LLMToolType.CLASSIFICATION)
class ClassificationTool(BaseLLMTool):
    """Tool for classifying documents into categories"""

    def get_metadata(self) -> ToolMetadata:
        """Get tool metadata"""
        return ToolMetadata(
            name="classification",
            description="Classify text into predefined or custom categories",
            version="1.0.0",
            capabilities=[
                ToolCapability.CLASSIFICATION,
                ToolCapability.TEXT_ANALYSIS
            ],
            input_schema={
                "text": {
                    "type": "str",
                    "required": True,
                    "description": "Text to classify"
                },
                "categories": {
                    "type": "list",
                    "required": False,
                    "default": None,
                    "description": "List of possible categories"
                }
            },
            output_schema={
                "category": {
                    "type": "str",
                    "description": "Classified category"
                },
                "confidence": {
                    "type": "float",
                    "description": "Confidence score (0-1)"
                }
            },
            max_input_length=10000,
            supports_streaming=False
        )

    async def execute(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """Execute classification

        Args:
            input_data: Must contain 'text', optionally 'categories'

        Returns:
            Dictionary with 'category' and 'confidence' keys
        """
        # Validate input
        self.validate_input(input_data)

        # Extract parameters
        text = input_data.get("text", "")
        categories = input_data.get("categories")

        # Validate text is not empty
        if not text or len(text.strip()) == 0:
            return {"category": "UNKNOWN", "confidence": 0.0}

        # Use default categories if not provided
        if not categories:
            categories = [
                "Technical Documentation",
                "Business Report",
                "Legal Document",
                "Financial Statement",
                "Research Paper",
                "News Article",
                "Personal Communication",
                "Marketing Material"
            ]

        # Prepare prompt
        prompt = self._prepare_prompt(text, categories)

        # Call LLM
        if self.llm_client:
            response = await self.call_llm(
                prompt=prompt,
                max_tokens=100,  # Classification needs minimal tokens
                temperature=0.3  # Lower temperature for consistency
            )
            category, confidence = self._parse_classification(response, categories)
        else:
            # Fallback for testing
            category, confidence = self._generate_fallback_classification(text, categories)

        return {
            "category": category,
            "confidence": confidence
        }

    def _prepare_prompt(self, text: str, categories: List[str]) -> str:
        """Prepare the classification prompt"""
        categories_str = "\n".join(f"- {cat}" for cat in categories)

        prompt_template = """Classify the following text into one of these categories:
{categories_str}

Return your answer in the format:
Category: [chosen category]
Confidence: [0.0-1.0]

Text to classify:
{text}

Classification:"""

        return self.prepare_prompt(
            prompt_template,
            categories_str=categories_str,
            text=text[:2000]  # Limit text length for classification
        )

    def _parse_classification(
        self,
        response: str,
        categories: List[str]
    ) -> Tuple[str, float]:
        """Parse classification result from LLM response"""
        category = "UNKNOWN"
        confidence = 0.0

        lines = response.strip().split('\n')
        for line in lines:
            line_lower = line.lower()

            # Parse category
            if "category:" in line_lower:
                cat_text = line.split(':', 1)[1].strip()

                # Find best matching category (case-insensitive)
                for cat in categories:
                    if cat.lower() in cat_text.lower() or cat_text.lower() in cat.lower():
                        category = cat
                        break

            # Parse confidence
            elif "confidence:" in line_lower:
                try:
                    conf_text = line.split(':', 1)[1].strip()
                    # Handle percentage format
                    if '%' in conf_text:
                        confidence = float(conf_text.replace('%', '').strip()) / 100
                    else:
                        confidence = float(conf_text)
                    # Ensure confidence is in valid range
                    confidence = min(1.0, max(0.0, confidence))
                except (ValueError, IndexError):
                    confidence = 0.8  # Default confidence

        # If we found a category but no confidence, set default
        if category != "UNKNOWN" and confidence == 0.0:
            confidence = 0.8

        return (category, confidence)

    def _generate_fallback_classification(
        self,
        text: str,
        categories: List[str]
    ) -> Tuple[str, float]:
        """Generate basic classification without LLM using keyword matching"""
        text_lower = text.lower()
        scores = {}

        # Define keywords for each default category
        category_keywords = {
            "Technical Documentation": ["api", "function", "method", "parameter", "installation", "configuration"],
            "Business Report": ["revenue", "profit", "quarter", "sales", "market", "strategy"],
            "Legal Document": ["agreement", "contract", "terms", "liability", "clause", "party"],
            "Financial Statement": ["balance", "income", "cash flow", "assets", "liabilities", "equity"],
            "Research Paper": ["abstract", "methodology", "results", "conclusion", "hypothesis", "study"],
            "News Article": ["reported", "announced", "yesterday", "today", "sources", "according"],
            "Personal Communication": ["dear", "sincerely", "regards", "hi", "hello", "thanks"],
            "Marketing Material": ["offer", "discount", "buy", "sale", "limited", "exclusive"]
        }

        # Score each category based on keyword matches
        for category in categories:
            score = 0
            keywords = category_keywords.get(category, [])

            for keyword in keywords:
                if keyword in text_lower:
                    score += 1

            # Normalize score
            if keywords:
                scores[category] = score / len(keywords)
            else:
                scores[category] = 0

        # Find category with highest score
        if scores:
            best_category = max(scores, key=scores.get)
            best_score = scores[best_category]

            # Convert score to confidence (with minimum threshold)
            if best_score > 0:
                confidence = min(0.9, 0.5 + best_score * 0.4)
                return (best_category, confidence)

        # Default fallback
        return (categories[0] if categories else "UNKNOWN", 0.3)