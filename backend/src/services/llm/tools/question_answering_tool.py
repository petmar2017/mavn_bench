"""Question answering tool for answering questions based on context"""

from typing import Dict, Any

from ..base_tool import BaseLLMTool, ToolMetadata, ToolCapability
from ..tool_registry import LLMToolType
from ..tool_decorators import register_tool


@register_tool(LLMToolType.QUESTION_ANSWERING)
class QuestionAnsweringTool(BaseLLMTool):
    """Tool for answering questions based on provided context"""

    def get_metadata(self) -> ToolMetadata:
        """Get tool metadata"""
        return ToolMetadata(
            name="question_answering",
            description="Answer questions based on provided context",
            version="1.0.0",
            capabilities=[
                ToolCapability.QUESTION_ANSWERING,
                ToolCapability.TEXT_ANALYSIS,
                ToolCapability.TEXT_GENERATION
            ],
            input_schema={
                "context": {
                    "type": "str",
                    "required": True,
                    "description": "Context text containing information"
                },
                "question": {
                    "type": "str",
                    "required": True,
                    "description": "Question to answer"
                },
                "max_length": {
                    "type": "int",
                    "required": False,
                    "default": 200,
                    "description": "Maximum answer length in words"
                }
            },
            output_schema={
                "answer": {
                    "type": "str",
                    "description": "Answer to the question"
                },
                "confidence": {
                    "type": "float",
                    "description": "Confidence in the answer (0-1)"
                }
            },
            max_input_length=50000,
            supports_streaming=False
        )

    async def execute(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """Execute question answering

        Args:
            input_data: Must contain 'context' and 'question', optionally 'max_length'

        Returns:
            Dictionary with 'answer' and 'confidence' keys
        """
        # Validate input
        self.validate_input(input_data)

        # Extract parameters
        context = input_data.get("context", "")
        question = input_data.get("question", "")
        max_length = input_data.get("max_length", 200)

        # Validate inputs are not empty
        if not context or not question:
            return {
                "answer": "Insufficient information provided.",
                "confidence": 0.0
            }

        # Prepare prompt
        prompt = self._prepare_prompt(context, question, max_length)

        # Call LLM
        if self.llm_client:
            response = await self.call_llm(
                prompt=prompt,
                max_tokens=max_length * 2,  # Approximate tokens
                temperature=0.3  # Lower temperature for factual answers
            )
            answer, confidence = self._parse_answer(response)
        else:
            # Fallback for testing
            answer, confidence = self._generate_fallback_answer(context, question)

        return {
            "answer": answer,
            "confidence": confidence
        }

    def _prepare_prompt(self, context: str, question: str, max_length: int) -> str:
        """Prepare the Q&A prompt"""
        prompt_template = """Based on the following context, please answer the question.

Instructions:
1. Answer must be based solely on the provided context
2. If the answer cannot be found in the context, say "Information not found in the provided context."
3. Be concise and direct
4. Maximum answer length: {max_length} words

Context:
{context}

Question: {question}

Answer:"""

        return self.prepare_prompt(
            prompt_template,
            max_length=max_length,
            context=context[:8000],  # Limit context length
            question=question
        )

    def _parse_answer(self, response: str) -> tuple[str, float]:
        """Parse answer and confidence from response"""
        response = response.strip()

        # Default confidence based on answer content
        confidence = 0.8

        # Check if answer indicates information not found
        not_found_phrases = [
            "information not found",
            "cannot be found",
            "not mentioned",
            "no information",
            "unable to answer"
        ]

        response_lower = response.lower()
        for phrase in not_found_phrases:
            if phrase in response_lower:
                confidence = 0.1
                break

        # If answer is very short, reduce confidence
        if len(response.split()) < 5:
            confidence *= 0.7

        # If answer is question-like, reduce confidence
        if response.endswith('?'):
            confidence *= 0.5

        return (response, confidence)

    def _generate_fallback_answer(
        self,
        context: str,
        question: str
    ) -> tuple[str, float]:
        """Generate basic answer without LLM using keyword matching"""
        context_lower = context.lower()
        question_lower = question.lower()

        # Extract question keywords (remove common question words)
        question_words = set(question_lower.split())
        stop_words = {
            "what", "where", "when", "who", "why", "how",
            "is", "are", "was", "were", "do", "does", "did",
            "the", "a", "an", "of", "in", "on", "at", "to"
        }
        keywords = question_words - stop_words

        # Find sentences in context that contain keywords
        sentences = context.split('.')
        relevant_sentences = []
        scores = []

        for sentence in sentences:
            sentence_lower = sentence.lower()
            score = 0

            for keyword in keywords:
                if keyword in sentence_lower:
                    score += 1

            if score > 0:
                relevant_sentences.append(sentence.strip())
                scores.append(score)

        # Return the most relevant sentence(s)
        if relevant_sentences:
            # Sort by score and take the best one
            best_idx = scores.index(max(scores))
            answer = relevant_sentences[best_idx]

            # Add period if missing
            if answer and not answer.endswith('.'):
                answer += '.'

            # Calculate confidence based on keyword matches
            confidence = min(0.7, 0.3 + (max(scores) / len(keywords)) * 0.4)

            return (answer, confidence)

        # No relevant information found
        return ("Information not found in the provided context.", 0.1)