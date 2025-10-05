"""Model selector with intelligent strategy pattern for optimal model selection"""

from typing import Optional, List, Dict, Any
from enum import Enum
from ....core.config import get_settings
from ....core.logger import CentralizedLogger
from .base_provider import TaskRequirements, CostTier, ModelCapabilities
from .provider_registry import ModelProviderRegistry
from ..tool_registry import LLMToolType


class SelectionStrategy(str, Enum):
    """Model selection strategies"""
    COST = "cost"  # Minimize cost
    QUALITY = "quality"  # Maximize quality
    LATENCY = "latency"  # Minimize latency
    BALANCED = "balanced"  # Balance all factors
    MANUAL = "manual"  # Use explicit overrides


class ModelSelector:
    """Intelligent model selection based on task requirements and strategy

    This class implements various strategies for selecting the optimal
    model provider based on task requirements, cost constraints, and
    performance needs. It uses configuration from central config.
    """

    def __init__(self):
        """Initialize model selector with config"""
        self.settings = get_settings()
        self.logger = CentralizedLogger("ModelSelector")
        self.strategy = SelectionStrategy(self.settings.llm.selection_strategy)

    def select_model(
        self,
        task_type: Optional[LLMToolType] = None,
        requirements: Optional[TaskRequirements] = None,
        strategy_override: Optional[SelectionStrategy] = None
    ) -> str:
        """Select optimal model for task

        Args:
            task_type: Type of LLM task
            requirements: Task requirements
            strategy_override: Override default strategy

        Returns:
            Model provider name
        """
        strategy = strategy_override or self.strategy

        # Check for manual override first
        if strategy == SelectionStrategy.MANUAL and task_type:
            override = self._get_task_override(task_type)
            if override and self._is_model_available(override):
                self.logger.debug(f"Using manual override: {override} for {task_type}")
                return override

        # Get eligible models
        eligible_models = self._get_eligible_models(requirements)

        if not eligible_models:
            # Fall back to default chain
            return self._get_fallback_model()

        # Apply strategy
        if strategy == SelectionStrategy.COST:
            return self._select_by_cost(eligible_models)
        elif strategy == SelectionStrategy.QUALITY:
            return self._select_by_quality(eligible_models)
        elif strategy == SelectionStrategy.LATENCY:
            return self._select_by_latency(eligible_models)
        elif strategy == SelectionStrategy.BALANCED:
            return self._select_balanced(eligible_models, task_type)
        else:
            # Default to quality
            return self._select_by_quality(eligible_models)

    def _get_eligible_models(
        self,
        requirements: Optional[TaskRequirements]
    ) -> List[Dict[str, Any]]:
        """Get models that meet requirements

        Args:
            requirements: Task requirements

        Returns:
            List of eligible model configurations
        """
        eligible = []

        for model_name, config in self.settings.llm.providers.items():
            # Skip disabled models
            if not config.get("enabled", False):
                continue

            # Check if model meets requirements
            if requirements and not self._meets_requirements(config, requirements):
                continue

            # Add to eligible list with name
            model_info = config.copy()
            model_info["provider_name"] = model_name
            eligible.append(model_info)

        return eligible

    def _meets_requirements(
        self,
        config: Dict[str, Any],
        requirements: TaskRequirements
    ) -> bool:
        """Check if model config meets requirements

        Args:
            config: Model configuration
            requirements: Task requirements

        Returns:
            True if requirements are met
        """
        # Check latency
        if requirements.max_latency_ms:
            if config.get("avg_latency_ms", float('inf')) > requirements.max_latency_ms:
                return False

        # Check cost tier
        tier_order = {
            CostTier.ECONOMY: 0,
            CostTier.STANDARD: 1,
            CostTier.PREMIUM: 2
        }
        model_tier = CostTier(config.get("cost_tier", "standard"))
        if tier_order[model_tier] > tier_order[requirements.max_cost_tier]:
            return False

        # Check quality
        if config.get("quality_score", 0) < requirements.min_quality_score:
            return False

        # Check context
        if requirements.required_context > config.get("max_context", 0):
            return False

        # Check capabilities
        model_caps = set(config.get("capabilities", "").split(","))
        if requirements.needs_vision and "vision" not in model_caps:
            return False
        if requirements.needs_streaming and "streaming" not in model_caps:
            return False
        if requirements.needs_json_mode and "json_mode" not in model_caps:
            return False

        return True

    def _select_by_cost(self, models: List[Dict[str, Any]]) -> str:
        """Select cheapest model

        Args:
            models: List of eligible models

        Returns:
            Model provider name
        """
        # Sort by average cost (input + output)
        sorted_models = sorted(
            models,
            key=lambda m: (
                m.get("cost_per_1k_input", float('inf')) +
                m.get("cost_per_1k_output", float('inf'))
            )
        )
        selected = sorted_models[0]["provider_name"]
        self.logger.debug(f"Cost strategy selected: {selected}")
        return selected

    def _select_by_quality(self, models: List[Dict[str, Any]]) -> str:
        """Select highest quality model

        Args:
            models: List of eligible models

        Returns:
            Model provider name
        """
        sorted_models = sorted(
            models,
            key=lambda m: m.get("quality_score", 0),
            reverse=True
        )
        selected = sorted_models[0]["provider_name"]
        self.logger.debug(f"Quality strategy selected: {selected}")
        return selected

    def _select_by_latency(self, models: List[Dict[str, Any]]) -> str:
        """Select fastest model

        Args:
            models: List of eligible models

        Returns:
            Model provider name
        """
        sorted_models = sorted(
            models,
            key=lambda m: m.get("avg_latency_ms", float('inf'))
        )
        selected = sorted_models[0]["provider_name"]
        self.logger.debug(f"Latency strategy selected: {selected}")
        return selected

    def _select_balanced(
        self,
        models: List[Dict[str, Any]],
        task_type: Optional[LLMToolType]
    ) -> str:
        """Select model with balanced scoring

        Args:
            models: List of eligible models
            task_type: Type of task

        Returns:
            Model provider name
        """
        # Calculate composite score for each model
        scored_models = []

        for model in models:
            # Normalize scores to 0-1 range
            quality_score = model.get("quality_score", 0.5)

            # Cost score (inverted - lower is better)
            avg_cost = (
                model.get("cost_per_1k_input", 0.01) +
                model.get("cost_per_1k_output", 0.01)
            )
            cost_score = 1.0 / (1.0 + avg_cost * 100)  # Normalize

            # Latency score (inverted - lower is better)
            latency_ms = model.get("avg_latency_ms", 1000)
            latency_score = 1.0 / (1.0 + latency_ms / 1000)  # Normalize

            # Check if model is preferred for this task
            preference_bonus = 0.0
            if task_type:
                preferred_tasks = model.get("preferred_for", "").split(",")
                task_name = task_type.value.lower()
                if any(task_name in pref.lower() for pref in preferred_tasks):
                    preference_bonus = 0.2

            # Composite score with weights
            composite_score = (
                quality_score * 0.4 +
                cost_score * 0.3 +
                latency_score * 0.2 +
                preference_bonus * 0.1
            )

            scored_models.append({
                "name": model["provider_name"],
                "score": composite_score
            })

        # Sort by composite score
        scored_models.sort(key=lambda m: m["score"], reverse=True)
        selected = scored_models[0]["name"]
        self.logger.debug(
            f"Balanced strategy selected: {selected} "
            f"(score: {scored_models[0]['score']:.3f})"
        )
        return selected

    def _get_task_override(self, task_type: LLMToolType) -> Optional[str]:
        """Get manual override for task type

        Args:
            task_type: Type of task

        Returns:
            Model provider name or None
        """
        task_name = task_type.value.lower()
        overrides = self.settings.llm.task_model_overrides

        # Direct match
        if task_name in overrides:
            return overrides[task_name]

        # Partial match
        for key, value in overrides.items():
            if key in task_name or task_name in key:
                return value

        return None

    def _is_model_available(self, model_name: str) -> bool:
        """Check if model is available and enabled

        Args:
            model_name: Model provider name

        Returns:
            True if available
        """
        config = self.settings.llm.providers.get(model_name)
        return config and config.get("enabled", False)

    def _get_fallback_model(self) -> str:
        """Get fallback model from chain

        Returns:
            First available model from fallback chain
        """
        for model_name in self.settings.llm.fallback_chain:
            if self._is_model_available(model_name):
                self.logger.debug(f"Using fallback model: {model_name}")
                return model_name

        # Ultimate fallback
        default = self.settings.llm.default_provider
        self.logger.warning(f"No models available, using default: {default}")
        return default

    def get_model_info(self, model_name: str) -> Optional[Dict[str, Any]]:
        """Get information about a specific model

        Args:
            model_name: Model provider name

        Returns:
            Model configuration or None
        """
        return self.settings.llm.providers.get(model_name)

    def estimate_cost(
        self,
        model_name: str,
        input_tokens: int,
        output_tokens: int
    ) -> float:
        """Estimate cost for a specific model

        Args:
            model_name: Model provider name
            input_tokens: Number of input tokens
            output_tokens: Number of output tokens

        Returns:
            Estimated cost in USD
        """
        config = self.get_model_info(model_name)
        if not config:
            return 0.0

        input_cost = (input_tokens / 1000) * config.get("cost_per_1k_input", 0)
        output_cost = (output_tokens / 1000) * config.get("cost_per_1k_output", 0)
        return input_cost + output_cost