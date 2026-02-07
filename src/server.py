"""
FastAPI server for CampusConnect AI Service.

Exposes:
  - GET /health - Health check
  - POST /run-graph - Execute any graph (matching, safety, onboarding, events_communities)
  - GET /docs - Interactive API documentation (Swagger UI)
  - GET /openapi.json - OpenAPI schema
"""

from dotenv import load_dotenv
load_dotenv()

from fastapi import FastAPI, HTTPException, Request, status, Header
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from typing import Dict, Any, Optional, Annotated
import logging
import time

# Import configuration (loads .env automatically)
from src.config import config, validate_config

# Import logging setup
from src.utils.logging_config import logger, setup_logging

# Import graphs
from src.graphs.matching import create_matching_graph
from src.graphs.safety import create_safety_graph
from src.graphs.onboarding import create_onboarding_graph
from src.graphs.events_communities import create_events_communities_graph
from src.graphs.chat_assistant import create_chat_assistant_graph

# Setup logging
setup_logging(debug=config.DEBUG)

# ============================================================
# VALIDATE CONFIGURATION AT STARTUP
# ============================================================
try:
    config_status = validate_config()
    logger.info("✅ Configuration validated successfully")
    for key, value in config_status.items():
        logger.info(f"  {key}: {value}")
except ValueError as e:
    logger.error(f"❌ Configuration error: {e}")
    exit(1)

# ============================================================
# FASTAPI APPLICATION
# ============================================================
app = FastAPI(
    title="CampusConnect AI Service",
    description="LangGraph-based AI agents for multi-university matching, safety, and onboarding",
    version="1.0.0",
)

# ============================================================
# CORS CONFIGURATION
# ============================================================
# Allow requests from JS frontend/backend during dev and production.
# In production, update origins list with real domain.
origins = [
    "http://localhost:5173",  # Vite dev
    "http://localhost:3000",  # React/Next dev
    "http://localhost:5001",  # Express+frontend dev origin
    "https://your-production-domain.com",  # TODO: Update with real frontend domain
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ============================================================
# REQUEST/RESPONSE MODELS
# ============================================================
class GraphRequest(BaseModel):
    """
    Request body for /run-graph endpoint.
    
    Attributes:
        graph (str): Name of graph to execute.
                    Options: 'matching', 'safety', 'onboarding', 'events_communities'
        input (dict): Input state for the graph.
                     Content depends on which graph is being run.
    """
    graph: str
    input: Dict[str, Any]


class GraphResponse(BaseModel):
    """
    Response body for /run-graph endpoint.
    
    Attributes:
        success (bool): Whether graph executed successfully
        graph (str): Name of the graph that was executed
        data (dict): Output from the graph
        error (Optional[str]): Error message if something went wrong
    """
    success: bool
    graph: str
    data: Dict[str, Any] = {}
    error: Optional[str] = None


# ============================================================
# MIDDLEWARE
# ============================================================
@app.middleware("http")
async def add_process_time_header(request: Request, call_next):
    """
    Middleware to track request processing time.
    
    Adds X-Process-Time header to all responses showing how long request took.
    Useful for performance debugging.
    """
    start_time = time.time()
    response = await call_next(request)
    process_time = time.time() - start_time
    response.headers["X-Process-Time"] = str(process_time)
    return response


# ============================================================
# ROUTES
# ============================================================

@app.get("/health", tags=["System"])
async def health_check() -> Dict[str, str]:
    """
    Health check endpoint.
    
    Returns:
        dict: {"status": "healthy"}
    
    Use this to verify the service is running.
    Called by load balancers and monitoring systems.
    """
    return {"status": "healthy"}


@app.post("/run-graph", response_model=GraphResponse, tags=["Graphs"])
async def run_graph(
    request: GraphRequest,
    authorization: Annotated[Optional[str], Header()] = None,
) -> GraphResponse:
    """
    Execute a LangGraph graph and return results.
    
    Supported graphs:
      - matching: Student compatibility matching with deterministic + LLM scoring
      - safety: Content moderation (pattern + LLM hybrid)
      - onboarding: Guided profile collection for new students
      - events_communities: Event and community recommendations
    
    Args:
        request (GraphRequest): Contains graph name and input state
        
    Returns:
        GraphResponse: Contains success flag, graph name, output data, and any errors
        
    Raises:
        HTTPException: If graph doesn't exist or fails to execute
    """
    try:
        # Validate API token if configured
        if config.AI_SERVICE_TOKEN:
            expected = f"Bearer {config.AI_SERVICE_TOKEN}"
            if authorization != expected:
                logger.warning("Unauthorized request: invalid or missing token")
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Unauthorized",
                )

        logger.info(f"Received request for graph: {request.graph}")
        logger.debug(f"Input keys: {list(request.input.keys())}")
        
        # ============================================================
        # ROUTE TO CORRECT GRAPH
        # ============================================================
        graph = None
        
        if request.graph == "matching":
            graph = create_matching_graph()
            logger.debug("Created matching graph")
            
        elif request.graph == "safety":
            graph = create_safety_graph()
            logger.debug("Created safety graph")
            
        elif request.graph == "onboarding":
            graph = create_onboarding_graph()
            logger.debug("Created onboarding graph")
            
        elif request.graph == "events_communities":
            graph = create_events_communities_graph()
            logger.debug("Created events_communities graph")

        elif request.graph == "chat_assistant":
            inp = request.input or {}
            auth_token = inp.get("auth_token") or ""
            user_id = inp.get("user_id") or ""
            if not auth_token or not user_id:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="chat_assistant graph requires auth_token and user_id in input",
                )
            graph = create_chat_assistant_graph()
            logger.debug("Created chat_assistant graph")
            
        else:
            logger.error(f"Unknown graph: {request.graph}")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Unknown graph: {request.graph}. "
                       f"Valid options: matching, safety, onboarding, events_communities, chat_assistant"
            )
        
        # ============================================================
        # EXECUTE GRAPH
        # ============================================================
        logger.info(f"Executing {request.graph} graph with timeout {config.GRAPH_TIMEOUT}s")
        start_time = time.time()
        
        try:
            # Invoke graph with input state, apply timeout
            result = graph.invoke(request.input)
            
            execution_time = time.time() - start_time
            logger.info(f"✅ {request.graph} graph completed in {execution_time:.2f}s")
            logger.debug(f"Graph output: {result}")
            logger.info(
                "run-graph summary: graph=%s input_keys=%s success=%s time=%.2fs",
                request.graph,
                list(request.input.keys()),
                True,
                execution_time,
            )
            
            return GraphResponse(
                success=True,
                graph=request.graph,
                data=result,
                error=None
            )
            
        except TimeoutError as e:
            """Graph took too long to execute"""
            execution_time = time.time() - start_time
            logger.error(f"⏱️ {request.graph} graph timed out after {execution_time:.2f}s")
            logger.info(
                "run-graph summary: graph=%s input_keys=%s success=%s time=%.2fs",
                request.graph,
                list(request.input.keys()),
                False,
                execution_time,
            )
            raise HTTPException(
                status_code=status.HTTP_504_GATEWAY_TIMEOUT,
                detail=f"Graph execution timed out after {config.GRAPH_TIMEOUT}s"
            )
        
        except Exception as e:
            """Graph execution failed with an error"""
            execution_time = time.time() - start_time
            logger.error(f"❌ {request.graph} graph failed after {execution_time:.2f}s: {str(e)}")
            logger.exception("Full traceback:")
            logger.info(
                "run-graph summary: graph=%s input_keys=%s success=%s time=%.2fs",
                request.graph,
                list(request.input.keys()),
                False,
                execution_time,
            )
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Graph execution failed: {str(e)}"
            )
    
    except HTTPException:
        """Re-raise HTTP exceptions"""
        raise
    
    except Exception as e:
        """Unexpected errors"""
        logger.error(f"❌ Unexpected error in /run-graph: {str(e)}")
        logger.exception("Full traceback:")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error"
        )


@app.get("/", tags=["System"])
async def root() -> Dict[str, str]:
    """
    Root endpoint.
    
    Returns information about the API and how to access documentation.
    """
    return {
        "service": "CampusConnect AI Service",
        "version": "1.0.0",
        "docs": "http://localhost:8000/docs",
        "health": "http://localhost:8000/health"
    }


# ============================================================
# ERROR HANDLERS
# ============================================================

@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    """
    Handle HTTP exceptions with consistent error response format.
    
    Catches all HTTPExceptions and returns them in a consistent format.
    """
    logger.error(f"HTTP Exception: {exc.status_code} - {exc.detail}")
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "success": False,
            "error": exc.detail,
            "status_code": exc.status_code
        }
    )


@app.exception_handler(Exception)
async def general_exception_handler(request: Request, exc: Exception):
    """
    Handle unexpected exceptions.
    
    Catches any exception not caught by other handlers and returns 500 error.
    Never returns a 500 error message to client; use logging instead.
    """
    logger.error(f"Unhandled exception: {str(exc)}")
    logger.exception("Full traceback:")
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "success": False,
            "error": "Internal server error",
            "status_code": 500
        }
    )


# ============================================================
# STARTUP EVENTS
# ============================================================

@app.on_event("startup")
async def startup_event():
    """
    Run when the application starts.
    
    Validates configuration, initializes Firebase, logs startup info.
    Configuration is already validated above (in module-level code),
    but we log it again here for visibility.
    """
    logger.info("=" * 60)
    logger.info("🚀 CampusConnect AI Service Starting Up")
    logger.info("=" * 60)
    
    # Configuration already validated above, but log again
    logger.info(f"Firebase Project: {config.FIREBASE_PROJECT_ID}")
    logger.info(f"LLM: {'Perplexity' if config.PERPLEXITY_API_KEY else 'OpenAI'}")
    logger.info(f"Debug Mode: {config.DEBUG}")
    logger.info(f"Graph Timeout: {config.GRAPH_TIMEOUT}s")
    logger.info(f"Max Candidates: {config.MAX_CANDIDATES}")
    
    logger.info("=" * 60)
    logger.info("✅ Service ready to handle requests")
    logger.info("=" * 60)


@app.on_event("shutdown")
async def shutdown_event():
    """
    Run when the application shuts down.
    
    Clean up resources, close connections, etc.
    """
    logger.info("🛑 CampusConnect AI Service Shutting Down")


# ============================================================
# ENTRY POINT
# ============================================================

if __name__ == "__main__":
    """
    Run with: python -m uvicorn src.server:app --reload
    
    This allows running the file directly for testing:
    $ python src/server.py
    
    But the standard way is via uvicorn CLI.
    """
    import uvicorn
    uvicorn.run(
        app,
        host=config.HOST,
        port=config.PORT,
        log_level="info" if not config.DEBUG else "debug"
    )
