"""Sentiment analysis tool for analyzing document sentiment using LLM"""

from typing import Dict, Any, List, Optional

from ..base_tool import (
    BaseDocumentTool,
    DocumentToolMetadata,
    DocumentToolCapability,
    DocumentToolCategory
)
from ..tool_registry import DocumentToolType
from ..tool_decorators import register_document_tool
from ....models.document import DocumentType, DocumentMessage


@register_document_tool(DocumentToolType.SENTIMENT_ANALYSIS)
class SentimentAnalysisTool(BaseDocumentTool):
    """Tool for analyzing sentiment in document content using LLM"""

    def get_metadata(self) -> DocumentToolMetadata:
        """Get tool metadata"""
        return DocumentToolMetadata(
            id="sentiment_analysis",
            name="Sentiment Analysis",
            description="Analyze sentiment and emotional tone in document content",
            category=DocumentToolCategory.ANALYSIS,
            icon="heart",
            version="1.0.0",
            capabilities=[
                DocumentToolCapability.ANALYSIS,
                DocumentToolCapability.CLASSIFICATION
            ],
            supported_document_types=[
                DocumentType.TEXT,
                DocumentType.MARKDOWN,
                DocumentType.PDF,
                DocumentType.WORD,
                DocumentType.WEBPAGE
            ],
            input_schema={
                "granularity": {
                    "type": "str",
                    "required": False,
                    "default": "document",
                    "description": "Analysis granularity: document, paragraph, or sentence"
                },
                "aspects": {
                    "type": "list",
                    "required": False,
                    "description": "Specific aspects to analyze (e.g., product, service, experience)"
                },
                "confidence_threshold": {
                    "type": "float",
                    "required": False,
                    "default": 0.7,
                    "description": "Minimum confidence threshold for sentiment classification"
                }
            },
            output_schema={
                "overall_sentiment": {
                    "type": "dict",
                    "description": "Overall document sentiment"
                },
                "detailed_analysis": {
                    "type": "list",
                    "description": "Detailed sentiment analysis by granularity"
                },
                "aspects": {
                    "type": "dict",
                    "description": "Aspect-based sentiment analysis"
                },
                "emotions": {
                    "type": "dict",
                    "description": "Detected emotions and their intensities"
                },
                "statistics": {
                    "type": "dict",
                    "description": "Sentiment statistics and metrics"
                }
            },
            requires_llm=True,
            execution_time_estimate="medium",
            batch_capable=True
        )

    async def execute(
        self,
        document: DocumentMessage,
        parameters: Dict[str, Any] = None
    ) -> Dict[str, Any]:
        """Execute sentiment analysis

        Args:
            document: Document to analyze
            parameters: Analysis parameters

        Returns:
            Comprehensive sentiment analysis results
        """
        # Validate input
        self.validate_input(document, parameters)

        parameters = parameters or {}
        granularity = parameters.get("granularity", "document")
        aspects = parameters.get("aspects", [])
        confidence_threshold = parameters.get("confidence_threshold", 0.7)

        # Extract text content
        text_content = document.content.text if document.content else ""

        if not text_content or len(text_content.strip()) < 10:
            return {
                "overall_sentiment": {
                    "label": "neutral",
                    "confidence": 0.0,
                    "reasoning": "Insufficient text content for analysis"
                },
                "detailed_analysis": [],
                "aspects": {},
                "emotions": {},
                "statistics": {"text_length": len(text_content), "analyzable": False}
            }

        # Perform overall sentiment analysis
        overall_sentiment = await self._analyze_overall_sentiment(text_content)

        # Perform detailed analysis based on granularity
        detailed_analysis = await self._analyze_by_granularity(text_content, granularity)

        # Perform aspect-based sentiment analysis
        aspect_sentiments = {}
        if aspects:
            aspect_sentiments = await self._analyze_aspects(text_content, aspects)

        # Perform emotion detection
        emotions = await self._detect_emotions(text_content)

        # Generate statistics
        statistics = self._generate_statistics(
            text_content, overall_sentiment, detailed_analysis, emotions
        )

        return {
            "overall_sentiment": overall_sentiment,
            "detailed_analysis": detailed_analysis,
            "aspects": aspect_sentiments,
            "emotions": emotions,
            "statistics": statistics
        }

    async def _analyze_overall_sentiment(self, text: str) -> Dict[str, Any]:
        """Analyze overall document sentiment"""
        if not self.llm_service:
            # Fallback analysis without LLM
            return self._fallback_sentiment_analysis(text)

        prompt = f"""Analyze the sentiment of the following text. Provide your analysis in the following format:

SENTIMENT: [positive/negative/neutral]
CONFIDENCE: [0.0-1.0]
REASONING: [brief explanation of the sentiment classification]

Text to analyze:
{text[:2000]}  # Limit text for prompt size

Analysis:"""

        try:
            response = await self.llm_service.generate_text(
                prompt=prompt,
                max_tokens=200,
                temperature=0.3
            )

            # Parse LLM response
            sentiment_result = self._parse_sentiment_response(response)

            return sentiment_result

        except Exception as e:
            # Fallback to simple analysis
            return {
                "label": "neutral",
                "confidence": 0.5,
                "reasoning": f"LLM analysis failed: {str(e)}",
                "fallback": True
            }

    async def _analyze_by_granularity(self, text: str, granularity: str) -> List[Dict[str, Any]]:
        """Analyze sentiment at specified granularity level"""
        if granularity == "document":
            return []  # Overall sentiment already covers this

        # Split text based on granularity
        segments = self._split_text_by_granularity(text, granularity)

        detailed_results = []

        for i, segment in enumerate(segments):
            if len(segment.strip()) < 10:  # Skip very short segments
                continue

            if self.llm_service:
                try:
                    sentiment = await self._analyze_segment_sentiment(segment)
                except Exception:
                    sentiment = self._fallback_sentiment_analysis(segment)
            else:
                sentiment = self._fallback_sentiment_analysis(segment)

            detailed_results.append({
                "segment_index": i,
                "text": segment[:100] + "..." if len(segment) > 100 else segment,
                "sentiment": sentiment,
                "length": len(segment)
            })

        return detailed_results

    async def _analyze_aspects(self, text: str, aspects: List[str]) -> Dict[str, Any]:
        """Perform aspect-based sentiment analysis"""
        aspect_results = {}

        for aspect in aspects:
            if self.llm_service:
                try:
                    result = await self._analyze_aspect_sentiment(text, aspect)
                    aspect_results[aspect] = result
                except Exception:
                    aspect_results[aspect] = {
                        "sentiment": "neutral",
                        "confidence": 0.0,
                        "mentions": 0,
                        "reasoning": "Analysis failed"
                    }
            else:
                # Simple keyword-based fallback
                mentions = text.lower().count(aspect.lower())
                aspect_results[aspect] = {
                    "sentiment": "neutral",
                    "confidence": 0.3 if mentions > 0 else 0.0,
                    "mentions": mentions,
                    "reasoning": f"Found {mentions} mentions (fallback analysis)"
                }

        return aspect_results

    async def _detect_emotions(self, text: str) -> Dict[str, Any]:
        """Detect emotions in the text"""
        if not self.llm_service:
            return self._fallback_emotion_detection(text)

        prompt = f"""Analyze the emotions present in the following text. For each emotion detected, provide an intensity score from 0.0 to 1.0.

Consider these emotions: joy, sadness, anger, fear, surprise, disgust, trust, anticipation

Text to analyze:
{text[:1500]}

Respond in format:
EMOTION_NAME: intensity_score (reason)

Analysis:"""

        try:
            response = await self.llm_service.generate_text(
                prompt=prompt,
                max_tokens=300,
                temperature=0.4
            )

            return self._parse_emotion_response(response)

        except Exception:
            return self._fallback_emotion_detection(text)

    def _split_text_by_granularity(self, text: str, granularity: str) -> List[str]:
        """Split text based on granularity setting"""
        if granularity == "paragraph":
            # Split by double newlines or long single newlines
            paragraphs = [p.strip() for p in text.split('\n\n') if p.strip()]
            if len(paragraphs) <= 1:
                # Fallback: split by single newlines if no double newlines
                paragraphs = [p.strip() for p in text.split('\n') if p.strip()]
            return paragraphs

        elif granularity == "sentence":
            # Simple sentence splitting (could be improved with NLP library)
            import re
            sentences = re.split(r'[.!?]+', text)
            return [s.strip() for s in sentences if s.strip()]

        else:
            return [text]  # Document level

    async def _analyze_segment_sentiment(self, segment: str) -> Dict[str, Any]:
        """Analyze sentiment of a text segment"""
        prompt = f"""Analyze the sentiment of this text segment:

"{segment}"

Respond with: SENTIMENT: [positive/negative/neutral] CONFIDENCE: [0.0-1.0]"""

        response = await self.llm_service.generate_text(
            prompt=prompt,
            max_tokens=50,
            temperature=0.3
        )

        return self._parse_sentiment_response(response)

    async def _analyze_aspect_sentiment(self, text: str, aspect: str) -> Dict[str, Any]:
        """Analyze sentiment for a specific aspect"""
        prompt = f"""Analyze the sentiment towards "{aspect}" in the following text:

{text[:1000]}

Consider only mentions and opinions related to "{aspect}".

Respond with:
SENTIMENT: [positive/negative/neutral]
CONFIDENCE: [0.0-1.0]
MENTIONS: [number of relevant mentions]
REASONING: [brief explanation]"""

        response = await self.llm_service.generate_text(
            prompt=prompt,
            max_tokens=150,
            temperature=0.3
        )

        return self._parse_aspect_response(response)

    def _parse_sentiment_response(self, response: str) -> Dict[str, Any]:
        """Parse LLM sentiment analysis response"""
        lines = response.strip().split('\n')
        result = {
            "label": "neutral",
            "confidence": 0.5,
            "reasoning": "Unable to parse response"
        }

        for line in lines:
            line = line.strip()
            if line.startswith('SENTIMENT:'):
                sentiment = line.split(':', 1)[1].strip().lower()
                if sentiment in ['positive', 'negative', 'neutral']:
                    result["label"] = sentiment
            elif line.startswith('CONFIDENCE:'):
                try:
                    confidence = float(line.split(':', 1)[1].strip())
                    result["confidence"] = max(0.0, min(1.0, confidence))
                except ValueError:
                    pass
            elif line.startswith('REASONING:'):
                result["reasoning"] = line.split(':', 1)[1].strip()

        return result

    def _parse_emotion_response(self, response: str) -> Dict[str, Any]:
        """Parse LLM emotion detection response"""
        emotions = {}
        lines = response.strip().split('\n')

        for line in lines:
            if ':' in line:
                try:
                    emotion, rest = line.split(':', 1)
                    emotion = emotion.strip().lower()
                    # Extract intensity score
                    import re
                    score_match = re.search(r'(\d+\.?\d*)', rest)
                    if score_match:
                        intensity = float(score_match.group(1))
                        emotions[emotion] = max(0.0, min(1.0, intensity))
                except (ValueError, IndexError):
                    continue

        return emotions

    def _parse_aspect_response(self, response: str) -> Dict[str, Any]:
        """Parse aspect-based sentiment response"""
        result = {
            "sentiment": "neutral",
            "confidence": 0.0,
            "mentions": 0,
            "reasoning": "Unable to parse response"
        }

        lines = response.strip().split('\n')
        for line in lines:
            line = line.strip()
            if line.startswith('SENTIMENT:'):
                sentiment = line.split(':', 1)[1].strip().lower()
                if sentiment in ['positive', 'negative', 'neutral']:
                    result["sentiment"] = sentiment
            elif line.startswith('CONFIDENCE:'):
                try:
                    result["confidence"] = float(line.split(':', 1)[1].strip())
                except ValueError:
                    pass
            elif line.startswith('MENTIONS:'):
                try:
                    result["mentions"] = int(line.split(':', 1)[1].strip())
                except ValueError:
                    pass
            elif line.startswith('REASONING:'):
                result["reasoning"] = line.split(':', 1)[1].strip()

        return result

    def _fallback_sentiment_analysis(self, text: str) -> Dict[str, Any]:
        """Simple fallback sentiment analysis without LLM"""
        # Simple keyword-based approach
        positive_words = ['good', 'great', 'excellent', 'amazing', 'wonderful', 'fantastic', 'love', 'like', 'best', 'perfect']
        negative_words = ['bad', 'terrible', 'awful', 'horrible', 'hate', 'worst', 'poor', 'disappointing', 'failed', 'wrong']

        text_lower = text.lower()
        positive_count = sum(1 for word in positive_words if word in text_lower)
        negative_count = sum(1 for word in negative_words if word in text_lower)

        if positive_count > negative_count:
            sentiment = "positive"
            confidence = min(0.8, 0.5 + (positive_count - negative_count) * 0.1)
        elif negative_count > positive_count:
            sentiment = "negative"
            confidence = min(0.8, 0.5 + (negative_count - positive_count) * 0.1)
        else:
            sentiment = "neutral"
            confidence = 0.6

        return {
            "label": sentiment,
            "confidence": confidence,
            "reasoning": f"Keyword-based analysis: {positive_count} positive, {negative_count} negative words",
            "fallback": True
        }

    def _fallback_emotion_detection(self, text: str) -> Dict[str, Any]:
        """Simple fallback emotion detection"""
        emotion_keywords = {
            "joy": ["happy", "joy", "glad", "pleased", "delighted", "cheerful"],
            "sadness": ["sad", "depressed", "disappointed", "grief", "sorrow"],
            "anger": ["angry", "mad", "furious", "irritated", "annoyed"],
            "fear": ["afraid", "scared", "worried", "anxious", "nervous"],
            "surprise": ["surprised", "shocked", "amazed", "astonished"],
            "trust": ["trust", "confident", "reliable", "believe"]
        }

        text_lower = text.lower()
        emotions = {}

        for emotion, keywords in emotion_keywords.items():
            count = sum(1 for keyword in keywords if keyword in text_lower)
            if count > 0:
                emotions[emotion] = min(0.8, count * 0.2)

        return emotions

    def _generate_statistics(
        self,
        text: str,
        overall_sentiment: Dict[str, Any],
        detailed_analysis: List[Dict[str, Any]],
        emotions: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Generate sentiment analysis statistics"""
        stats = {
            "text_length": len(text),
            "word_count": len(text.split()),
            "analyzable": True,
            "confidence": overall_sentiment.get("confidence", 0.0),
            "sentiment_distribution": {},
            "emotion_count": len(emotions),
            "dominant_emotion": None
        }

        # Calculate sentiment distribution from detailed analysis
        if detailed_analysis:
            sentiment_counts = {}
            for analysis in detailed_analysis:
                sentiment = analysis["sentiment"]["label"]
                sentiment_counts[sentiment] = sentiment_counts.get(sentiment, 0) + 1

            total = len(detailed_analysis)
            stats["sentiment_distribution"] = {
                sentiment: count / total
                for sentiment, count in sentiment_counts.items()
            }

        # Find dominant emotion
        if emotions:
            dominant_emotion = max(emotions.items(), key=lambda x: x[1])
            stats["dominant_emotion"] = {
                "emotion": dominant_emotion[0],
                "intensity": dominant_emotion[1]
            }

        return stats