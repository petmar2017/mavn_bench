"""JSON validation tool for checking JSON document validity and structure"""

import json
import jsonschema
from typing import Dict, Any, Optional
from jsonschema import validate, ValidationError, Draft7Validator

from ..base_tool import (
    BaseDocumentTool,
    DocumentToolMetadata,
    DocumentToolCapability,
    DocumentToolCategory
)
from ..tool_registry import DocumentToolType
from ..tool_decorators import register_document_tool
from ....models.document import DocumentType, DocumentMessage


@register_document_tool(DocumentToolType.VALIDATE_JSON)
class ValidateJSONTool(BaseDocumentTool):
    """Tool for validating JSON documents and checking against schemas"""

    def get_metadata(self) -> DocumentToolMetadata:
        """Get tool metadata"""
        return DocumentToolMetadata(
            id="validate_json",
            name="JSON Validator",
            description="Validate JSON documents for syntax and schema compliance",
            category=DocumentToolCategory.DATA_VALIDATION,
            icon="check-circle",
            version="1.0.0",
            capabilities=[
                DocumentToolCapability.VALIDATION,
                DocumentToolCapability.QUALITY_CHECK
            ],
            supported_document_types=[DocumentType.JSON],
            input_schema={
                "schema": {
                    "type": "dict",
                    "required": False,
                    "description": "JSON schema to validate against (optional)"
                },
                "strict": {
                    "type": "bool",
                    "required": False,
                    "default": False,
                    "description": "Enable strict validation mode"
                }
            },
            output_schema={
                "valid": {
                    "type": "bool",
                    "description": "Whether the JSON is valid"
                },
                "errors": {
                    "type": "list",
                    "description": "List of validation errors"
                },
                "warnings": {
                    "type": "list",
                    "description": "List of validation warnings"
                },
                "statistics": {
                    "type": "dict",
                    "description": "JSON structure statistics"
                }
            },
            execution_time_estimate="fast",
            batch_capable=True
        )

    async def execute(
        self,
        document: DocumentMessage,
        parameters: Dict[str, Any] = None
    ) -> Dict[str, Any]:
        """Execute JSON validation

        Args:
            document: Document containing JSON content
            parameters: Validation parameters (schema, strict mode)

        Returns:
            Validation results with errors, warnings, and statistics
        """
        # Validate input
        self.validate_input(document, parameters)

        parameters = parameters or {}
        schema = parameters.get("schema")
        strict = parameters.get("strict", False)

        # Extract JSON content
        json_content = document.content.text if document.content else ""

        if not json_content:
            return {
                "valid": False,
                "errors": ["No JSON content found in document"],
                "warnings": [],
                "statistics": {}
            }

        # Validate JSON syntax
        errors = []
        warnings = []
        json_data = None

        try:
            json_data = json.loads(json_content)
        except json.JSONDecodeError as e:
            errors.append({
                "type": "syntax_error",
                "message": f"Invalid JSON syntax: {str(e)}",
                "line": getattr(e, 'lineno', None),
                "column": getattr(e, 'colno', None)
            })

        # If JSON is valid, proceed with additional validation
        if json_data is not None:
            # Schema validation
            if schema:
                try:
                    validate(instance=json_data, schema=schema)
                except ValidationError as e:
                    errors.append({
                        "type": "schema_validation",
                        "message": f"Schema validation failed: {e.message}",
                        "path": list(e.absolute_path),
                        "schema_path": list(e.schema_path)
                    })
                except Exception as e:
                    errors.append({
                        "type": "schema_error",
                        "message": f"Schema validation error: {str(e)}"
                    })

            # Additional validation checks
            validation_results = self._perform_additional_validation(json_data, strict)
            warnings.extend(validation_results["warnings"])
            if strict:
                errors.extend(validation_results["strict_errors"])

            # Generate statistics
            statistics = self._generate_statistics(json_data)
        else:
            statistics = {}

        return {
            "valid": len(errors) == 0,
            "errors": errors,
            "warnings": warnings,
            "statistics": statistics
        }

    def _perform_additional_validation(
        self,
        json_data: Any,
        strict: bool
    ) -> Dict[str, Any]:
        """Perform additional JSON validation checks

        Args:
            json_data: Parsed JSON data
            strict: Whether to enable strict validation

        Returns:
            Dictionary with warnings and strict errors
        """
        warnings = []
        strict_errors = []

        # Check for common issues
        if isinstance(json_data, dict):
            # Check for duplicate keys (this is already handled by json.loads)
            # Check for empty objects
            if len(json_data) == 0:
                warnings.append({
                    "type": "empty_object",
                    "message": "JSON object is empty"
                })

            # Check for very deep nesting
            max_depth = self._calculate_max_depth(json_data)
            if max_depth > 10:
                warnings.append({
                    "type": "deep_nesting",
                    "message": f"JSON has deep nesting (depth: {max_depth})",
                    "depth": max_depth
                })

            # Check for large arrays
            large_arrays = self._find_large_arrays(json_data)
            for path, size in large_arrays:
                if size > 1000:
                    warnings.append({
                        "type": "large_array",
                        "message": f"Large array found at {path} with {size} elements",
                        "path": path,
                        "size": size
                    })

            # Strict mode checks
            if strict:
                # Check for null values
                null_paths = self._find_null_values(json_data)
                for path in null_paths:
                    strict_errors.append({
                        "type": "null_value",
                        "message": f"Null value found at {path}",
                        "path": path
                    })

                # Check for inconsistent types in arrays
                inconsistent_arrays = self._find_inconsistent_arrays(json_data)
                for path, types in inconsistent_arrays:
                    strict_errors.append({
                        "type": "inconsistent_array",
                        "message": f"Array at {path} contains inconsistent types: {types}",
                        "path": path,
                        "types": types
                    })

        return {
            "warnings": warnings,
            "strict_errors": strict_errors
        }

    def _calculate_max_depth(self, obj: Any, current_depth: int = 0) -> int:
        """Calculate maximum nesting depth of JSON object"""
        if isinstance(obj, dict):
            if not obj:
                return current_depth
            return max(
                self._calculate_max_depth(value, current_depth + 1)
                for value in obj.values()
            )
        elif isinstance(obj, list):
            if not obj:
                return current_depth
            return max(
                self._calculate_max_depth(item, current_depth + 1)
                for item in obj
            )
        else:
            return current_depth

    def _find_large_arrays(self, obj: Any, path: str = "root") -> list:
        """Find arrays with more than threshold elements"""
        large_arrays = []

        if isinstance(obj, dict):
            for key, value in obj.items():
                new_path = f"{path}.{key}"
                large_arrays.extend(self._find_large_arrays(value, new_path))
        elif isinstance(obj, list):
            if len(obj) > 100:  # Threshold for "large" array
                large_arrays.append((path, len(obj)))
            for i, item in enumerate(obj):
                new_path = f"{path}[{i}]"
                large_arrays.extend(self._find_large_arrays(item, new_path))

        return large_arrays

    def _find_null_values(self, obj: Any, path: str = "root") -> list:
        """Find null values in JSON structure"""
        null_paths = []

        if obj is None:
            null_paths.append(path)
        elif isinstance(obj, dict):
            for key, value in obj.items():
                new_path = f"{path}.{key}"
                null_paths.extend(self._find_null_values(value, new_path))
        elif isinstance(obj, list):
            for i, item in enumerate(obj):
                new_path = f"{path}[{i}]"
                null_paths.extend(self._find_null_values(item, new_path))

        return null_paths

    def _find_inconsistent_arrays(self, obj: Any, path: str = "root") -> list:
        """Find arrays with inconsistent element types"""
        inconsistent_arrays = []

        if isinstance(obj, dict):
            for key, value in obj.items():
                new_path = f"{path}.{key}"
                inconsistent_arrays.extend(self._find_inconsistent_arrays(value, new_path))
        elif isinstance(obj, list):
            if obj:  # Non-empty array
                types = set(type(item).__name__ for item in obj)
                if len(types) > 1:
                    inconsistent_arrays.append((path, list(types)))

            for i, item in enumerate(obj):
                new_path = f"{path}[{i}]"
                inconsistent_arrays.extend(self._find_inconsistent_arrays(item, new_path))

        return inconsistent_arrays

    def _generate_statistics(self, json_data: Any) -> Dict[str, Any]:
        """Generate statistics about JSON structure"""
        stats = {
            "total_keys": 0,
            "total_arrays": 0,
            "total_objects": 0,
            "total_primitives": 0,
            "max_depth": 0,
            "total_null_values": 0,
            "type_distribution": {}
        }

        def analyze_recursive(obj, depth=0):
            stats["max_depth"] = max(stats["max_depth"], depth)

            if obj is None:
                stats["total_null_values"] += 1
                stats["total_primitives"] += 1
                type_name = "null"
            elif isinstance(obj, dict):
                stats["total_objects"] += 1
                stats["total_keys"] += len(obj)
                type_name = "object"
                for value in obj.values():
                    analyze_recursive(value, depth + 1)
            elif isinstance(obj, list):
                stats["total_arrays"] += 1
                type_name = "array"
                for item in obj:
                    analyze_recursive(item, depth + 1)
            else:
                stats["total_primitives"] += 1
                type_name = type(obj).__name__

            # Update type distribution
            stats["type_distribution"][type_name] = stats["type_distribution"].get(type_name, 0) + 1

        analyze_recursive(json_data)
        return stats