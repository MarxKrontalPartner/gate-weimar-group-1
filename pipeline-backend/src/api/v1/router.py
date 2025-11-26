from fastapi import APIRouter
from src.api.v1.endpoints import health, test_errors, pipeline, input, output, transformation, flow, tag, validate

# Main router for API v1
api_router = APIRouter()

# Include all endpoint routers
api_router.include_router(
    health.router,
    tags=["Health"],
)

# Register the Pipeline Router
# This maps the logic to /api/v1/pipeline
api_router.include_router(
    pipeline.router,
    prefix="/pipeline", 
    tags=["Pipeline"],
)

api_router.include_router(
    input.router,
    prefix="/pipeline",
    tags=["Input"],
)

api_router.include_router(
    output.router,
    prefix="/pipeline",
    tags=["Output"],
)

api_router.include_router(
    transformation.router, 
    prefix="/pipeline", 
    tags=["Transformation"]
)

api_router.include_router(
    flow.router, 
    prefix="/pipeline", 
    tags=["Flow"]
)

api_router.include_router(
    tag.router, 
    prefix="/pipeline", 
    tags=["Tag"]
)

api_router.include_router(
    validate.router, 
    prefix="/pipeline", 
    tags=["Execution"]
)
api_router.include_router(
    test_errors.router,
    tags=["Testing"],
)