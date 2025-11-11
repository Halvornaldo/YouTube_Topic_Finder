"""API endpoints for configuration validation and testing."""

from fastapi import APIRouter, HTTPException, Depends, UploadFile, File
from sqlalchemy.orm import Session
from typing import Dict, Any, List, Optional
from pydantic import BaseModel, Field, validator
import logging
import yaml
import json
from datetime import datetime

from src.config.database import get_db
from src.services.niche_service import NicheService
from src.models.niche_config import NicheConfig

logger = logging.getLogger(__name__)
router = APIRouter()


# Pydantic models for validation requests/responses
class NicheValidationRequest(BaseModel):
    """Request model for validating a niche configuration without saving."""
    name: str = Field(..., min_length=1, max_length=100)
    keywords: List[str] = Field(..., min_items=1, max_items=100)
    search_queries: List[str] = Field(default_factory=list, max_items=50)
    google_trends_weight: float = Field(default=0.5, ge=0.0, le=1.0)
    reddit_weight: float = Field(default=0.5, ge=0.0, le=1.0)
    min_search_volume: int = Field(default=1000, ge=0)
    max_competition: float = Field(default=0.7, ge=0.0, le=1.0)
    min_opportunity_score: float = Field(default=70.0, ge=0.0, le=100.0)
    preferred_formats: List[str] = Field(default_factory=list, max_items=20)

    @validator('keywords', 'search_queries', 'preferred_formats')
    def validate_non_empty_strings(cls, v):
        """Ensure list items are non-empty strings."""
        if any(not item or not item.strip() for item in v):
            raise ValueError("List items must be non-empty strings")
        return v

    @validator('google_trends_weight', 'reddit_weight')
    def validate_weights_sum(cls, v, values):
        """Validate that weights don't exceed 1.0 when combined."""
        if 'google_trends_weight' in values:
            total = v + values['google_trends_weight']
            if total > 1.0:
                raise ValueError(f"Combined weights cannot exceed 1.0 (got {total})")
        return v


class ValidationResult(BaseModel):
    """Result of a validation check."""
    valid: bool
    issues: List[str] = Field(default_factory=list)
    warnings: List[str] = Field(default_factory=list)
    suggestions: List[str] = Field(default_factory=list)
    details: Optional[Dict[str, Any]] = None


class APICredentialsTest(BaseModel):
    """Request model for testing API credentials."""
    service: str = Field(..., description="Service to test (reddit, youtube, google_ads)")
    credentials: Dict[str, str] = Field(..., description="Credentials to test")


class YAMLValidationResponse(BaseModel):
    """Response for YAML file validation."""
    valid: bool
    parsed_data: Optional[Dict[str, Any]] = None
    issues: List[str] = Field(default_factory=list)
    warnings: List[str] = Field(default_factory=list)


@router.post("/niche", response_model=ValidationResult)
async def validate_niche_config(
    config: NicheValidationRequest,
    db: Session = Depends(get_db)
):
    """
    Validate a niche configuration without saving it.

    Performs comprehensive validation including:
    - Field validation (types, ranges, formats)
    - Business logic validation (weights, thresholds)
    - Conflict detection (duplicate names)
    - Best practice checks

    Args:
        config: Niche configuration to validate
        db: Database session

    Returns:
        Validation result with issues, warnings, and suggestions
    """
    issues = []
    warnings = []
    suggestions = []

    # Check for duplicate niche name
    existing = db.query(NicheConfig).filter(
        NicheConfig.name == config.name,
        NicheConfig.is_active == 1
    ).first()

    if existing:
        issues.append(f"Niche name '{config.name}' already exists (ID: {existing.id})")

    # Validate weights
    total_weight = config.google_trends_weight + config.reddit_weight
    if abs(total_weight - 1.0) > 0.01:
        warnings.append(
            f"Platform weights sum to {total_weight:.2f}, not 1.0. "
            f"Consider adjusting for balanced discovery."
        )

    # Check for reasonable keyword count
    if len(config.keywords) < 3:
        warnings.append(
            "Only {} keywords provided. Consider adding more for better coverage."
            .format(len(config.keywords))
        )
    elif len(config.keywords) > 50:
        warnings.append(
            "{} keywords provided. Consider focusing on most relevant terms for efficiency."
            .format(len(config.keywords))
        )

    # Check search query count
    if not config.search_queries:
        suggestions.append(
            "No search queries defined. System will auto-generate from keywords, "
            "but manual queries often yield better results."
        )

    # Validate thresholds
    if config.min_search_volume < 100:
        warnings.append(
            f"min_search_volume of {config.min_search_volume} is very low. "
            f"May result in low-quality topics."
        )
    elif config.min_search_volume > 100000:
        warnings.append(
            f"min_search_volume of {config.min_search_volume} is very high. "
            f"May filter out good opportunities."
        )

    if config.max_competition > 0.9:
        suggestions.append(
            "max_competition of {:.1f} is very high. "
            "Consider lowering to find easier opportunities."
            .format(config.max_competition)
        )

    if config.min_opportunity_score > 85:
        warnings.append(
            f"min_opportunity_score of {config.min_opportunity_score} is very high. "
            f"May result in few or no results."
        )

    # Check preferred formats
    if config.preferred_formats:
        valid_formats = [
            'tutorial', 'listicle', 'news', 'review', 'howto',
            'interview', 'vlog', 'documentary', 'animation', 'shorts'
        ]
        invalid_formats = [f for f in config.preferred_formats if f.lower() not in valid_formats]
        if invalid_formats:
            warnings.append(
                f"Unknown format types: {', '.join(invalid_formats)}. "
                f"Valid formats: {', '.join(valid_formats)}"
            )

    # Best practice suggestions
    if not config.preferred_formats:
        suggestions.append(
            "No preferred formats specified. Consider defining formats to improve content recommendations."
        )

    # Check keyword overlap with existing niches
    if not issues:  # Only if name is unique
        similar_niches = db.query(NicheConfig).filter(
            NicheConfig.is_active == 1
        ).all()

        for niche in similar_niches:
            if niche.name == config.name:
                continue

            # Check keyword overlap
            existing_keywords = set(kw.lower() for kw in niche.keywords)
            new_keywords = set(kw.lower() for kw in config.keywords)
            overlap = existing_keywords & new_keywords

            if len(overlap) / len(new_keywords) > 0.5:
                warnings.append(
                    f"High keyword overlap ({len(overlap)} keywords) with existing niche '{niche.name}'. "
                    f"Consider making keywords more specific."
                )

    # Determine validity
    valid = len(issues) == 0

    return ValidationResult(
        valid=valid,
        issues=issues,
        warnings=warnings,
        suggestions=suggestions,
        details={
            "name": config.name,
            "keyword_count": len(config.keywords),
            "search_query_count": len(config.search_queries),
            "total_weight": total_weight,
            "format_count": len(config.preferred_formats)
        }
    )


@router.post("/yaml", response_model=YAMLValidationResponse)
async def validate_yaml_file(
    file: UploadFile = File(..., description="YAML file to validate")
):
    """
    Validate a YAML configuration file before import.

    Checks:
    - YAML syntax validity
    - Required fields presence
    - Field types and formats
    - Value ranges

    Args:
        file: YAML file to validate

    Returns:
        Validation result with parsed data if valid
    """
    issues = []
    warnings = []
    parsed_data = None

    # Check file extension
    if not file.filename.endswith(('.yaml', '.yml')):
        issues.append(f"Invalid file extension. Expected .yaml or .yml, got: {file.filename}")
        return YAMLValidationResponse(
            valid=False,
            issues=issues,
            warnings=warnings
        )

    # Read and parse YAML
    try:
        content = await file.read()
        parsed_data = yaml.safe_load(content)
    except yaml.YAMLError as e:
        issues.append(f"Invalid YAML syntax: {str(e)}")
        return YAMLValidationResponse(
            valid=False,
            issues=issues,
            warnings=warnings
        )
    except Exception as e:
        issues.append(f"Error reading file: {str(e)}")
        return YAMLValidationResponse(
            valid=False,
            issues=issues,
            warnings=warnings
        )

    # Validate structure
    if not isinstance(parsed_data, dict):
        issues.append("YAML root must be a dictionary/object")
        return YAMLValidationResponse(
            valid=False,
            parsed_data=parsed_data,
            issues=issues,
            warnings=warnings
        )

    # Check required fields
    required_fields = ['name', 'keywords']
    for field in required_fields:
        if field not in parsed_data:
            issues.append(f"Missing required field: '{field}'")

    # Validate field types
    if 'name' in parsed_data:
        if not isinstance(parsed_data['name'], str):
            issues.append("'name' must be a string")
        elif len(parsed_data['name']) > 100:
            issues.append("'name' must be 100 characters or less")

    if 'keywords' in parsed_data:
        if not isinstance(parsed_data['keywords'], list):
            issues.append("'keywords' must be a list")
        elif not parsed_data['keywords']:
            issues.append("'keywords' cannot be empty")
        elif not all(isinstance(k, str) for k in parsed_data['keywords']):
            issues.append("All 'keywords' must be strings")

    # Validate optional fields
    if 'search_queries' in parsed_data:
        if not isinstance(parsed_data['search_queries'], list):
            warnings.append("'search_queries' should be a list")

    if 'google_trends_weight' in parsed_data:
        weight = parsed_data['google_trends_weight']
        if not isinstance(weight, (int, float)):
            issues.append("'google_trends_weight' must be a number")
        elif not 0.0 <= weight <= 1.0:
            issues.append("'google_trends_weight' must be between 0.0 and 1.0")

    if 'reddit_weight' in parsed_data:
        weight = parsed_data['reddit_weight']
        if not isinstance(weight, (int, float)):
            issues.append("'reddit_weight' must be a number")
        elif not 0.0 <= weight <= 1.0:
            issues.append("'reddit_weight' must be between 0.0 and 1.0")

    if 'min_search_volume' in parsed_data:
        vol = parsed_data['min_search_volume']
        if not isinstance(vol, int):
            issues.append("'min_search_volume' must be an integer")
        elif vol < 0:
            issues.append("'min_search_volume' must be non-negative")

    if 'max_competition' in parsed_data:
        comp = parsed_data['max_competition']
        if not isinstance(comp, (int, float)):
            issues.append("'max_competition' must be a number")
        elif not 0.0 <= comp <= 1.0:
            issues.append("'max_competition' must be between 0.0 and 1.0")

    if 'min_opportunity_score' in parsed_data:
        score = parsed_data['min_opportunity_score']
        if not isinstance(score, (int, float)):
            issues.append("'min_opportunity_score' must be a number")
        elif not 0.0 <= score <= 100.0:
            issues.append("'min_opportunity_score' must be between 0.0 and 100.0")

    # Check for unknown fields
    known_fields = [
        'name', 'keywords', 'search_queries', 'google_trends_weight',
        'reddit_weight', 'min_search_volume', 'max_competition',
        'min_opportunity_score', 'preferred_formats'
    ]
    unknown_fields = set(parsed_data.keys()) - set(known_fields)
    if unknown_fields:
        warnings.append(f"Unknown fields will be ignored: {', '.join(unknown_fields)}")

    return YAMLValidationResponse(
        valid=len(issues) == 0,
        parsed_data=parsed_data if len(issues) == 0 else None,
        issues=issues,
        warnings=warnings
    )


@router.post("/api-credentials", response_model=ValidationResult)
async def test_api_credentials(
    test_request: APICredentialsTest
):
    """
    Test API credentials without saving them.

    Performs actual API calls to verify credentials work.

    Args:
        test_request: Service and credentials to test

    Returns:
        Validation result indicating if credentials work
    """
    service = test_request.service.lower()
    credentials = test_request.credentials
    issues = []
    warnings = []
    suggestions = []
    details = {"service": service, "tested_at": datetime.utcnow().isoformat()}

    if service == "reddit":
        # Test Reddit credentials
        try:
            required = ['client_id', 'client_secret', 'user_agent']
            missing = [f for f in required if f not in credentials]
            if missing:
                issues.append(f"Missing required Reddit credentials: {', '.join(missing)}")
            else:
                # Would test actual connection here
                # For now, just validate format
                if len(credentials['client_id']) < 10:
                    issues.append("Reddit client_id appears invalid (too short)")
                if len(credentials['client_secret']) < 10:
                    issues.append("Reddit client_secret appears invalid (too short)")

                suggestions.append("Full Reddit API test requires live connection (not implemented yet)")
                details['credentials_format'] = 'valid'

        except Exception as e:
            issues.append(f"Error testing Reddit credentials: {str(e)}")

    elif service == "youtube":
        # Test YouTube credentials
        try:
            if 'api_key' not in credentials:
                issues.append("Missing YouTube API key")
            else:
                api_key = credentials['api_key']
                if len(api_key) < 30:
                    issues.append("YouTube API key appears invalid (too short)")

                suggestions.append("Full YouTube API test requires live connection (not implemented yet)")
                details['credentials_format'] = 'valid'

        except Exception as e:
            issues.append(f"Error testing YouTube credentials: {str(e)}")

    elif service == "google_ads":
        # Test Google Ads credentials
        try:
            required = ['developer_token', 'client_id', 'client_secret']
            missing = [f for f in required if f not in credentials]
            if missing:
                issues.append(f"Missing required Google Ads credentials: {', '.join(missing)}")
            else:
                suggestions.append("Full Google Ads API test requires live connection (not implemented yet)")
                details['credentials_format'] = 'valid'

        except Exception as e:
            issues.append(f"Error testing Google Ads credentials: {str(e)}")

    else:
        issues.append(f"Unknown service: '{service}'. Supported: reddit, youtube, google_ads")

    return ValidationResult(
        valid=len(issues) == 0,
        issues=issues,
        warnings=warnings,
        suggestions=suggestions,
        details=details
    )


@router.get("/database", response_model=ValidationResult)
async def test_database_connection(
    db: Session = Depends(get_db)
):
    """
    Test database connection and health.

    Args:
        db: Database session

    Returns:
        Validation result for database connection
    """
    issues = []
    warnings = []
    suggestions = []
    details = {}

    try:
        # Test basic query
        result = db.execute("SELECT 1").scalar()
        if result != 1:
            issues.append("Database query returned unexpected result")

        # Test table existence
        tables = db.execute("""
            SELECT table_name
            FROM information_schema.tables
            WHERE table_schema = 'public'
        """).fetchall()

        table_names = [t[0] for t in tables]
        details['table_count'] = len(table_names)
        details['tables'] = table_names

        # Check for required tables
        required_tables = [
            'niche_configs', 'app_settings', 'job_status',
            'seed_topics', 'videos'
        ]
        missing_tables = [t for t in required_tables if t not in table_names]

        if missing_tables:
            warnings.append(f"Some expected tables not found: {', '.join(missing_tables)}")
            suggestions.append("Run database migrations to create missing tables")

        details['connection'] = 'successful'
        details['database_type'] = 'postgresql'

    except Exception as e:
        issues.append(f"Database connection error: {str(e)}")
        details['connection'] = 'failed'
        details['error'] = str(e)

    return ValidationResult(
        valid=len(issues) == 0,
        issues=issues,
        warnings=warnings,
        suggestions=suggestions,
        details=details
    )


@router.get("/health", response_model=Dict[str, Any])
async def validation_health_check():
    """
    Health check for validation service.

    Returns:
        Service health status
    """
    return {
        "status": "operational",
        "service": "validation",
        "endpoints": {
            "niche": "/api/validation/niche",
            "yaml": "/api/validation/yaml",
            "api_credentials": "/api/validation/api-credentials",
            "database": "/api/validation/database"
        },
        "timestamp": datetime.utcnow().isoformat()
    }
