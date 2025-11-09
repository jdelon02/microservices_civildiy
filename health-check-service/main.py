"""
Health Check Service
Aggregates and proxies health check requests from all microservices
Provides a single endpoint for health status queries
"""

import os
import asyncio
import httpx
import json
from fastapi import FastAPI, HTTPException, Query
from fastapi.responses import JSONResponse
from typing import Dict, Any, Optional
import consul
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="Health Check Service", version="1.0.0")

# Configuration
CONSUL_HOST = os.getenv("CONSUL_HOST", "consul-server")
CONSUL_PORT = int(os.getenv("CONSUL_PORT", "8500"))
REQUEST_TIMEOUT = 5.0

# Initialize Consul client for querying services
consul_client = consul.Consul(host=CONSUL_HOST, port=CONSUL_PORT)


@app.on_event("startup")
async def startup_event():
    """Startup event - health-check-service will be registered via docker-compose/Traefik"""
    try:
        # Verify Consul connectivity on startup
        consul_client.agent.self()
        logger.info("Health Check Service started - connected to Consul")
    except Exception as e:
        logger.warning(f"Consul not immediately available: {e}")


@app.on_event("shutdown")
async def shutdown_event():
    """Shutdown event"""
    logger.info("Health Check Service shutting down")


async def fetch_service_health(
    service_name: str, 
    endpoint: str = "health",
    timeout: float = REQUEST_TIMEOUT
) -> Dict[str, Any]:
    """
    Fetch health status from a specific service
    
    Args:
        service_name: Name of the service (e.g., 'book-catalog-service')
        endpoint: Health endpoint ('health', 'ready', 'health/db', 'health/kafka', etc.)
        timeout: Request timeout in seconds
    
    Returns:
        Health status response or error information
    """
    try:
        # Get service instances from Consul
        _, services = consul_client.health.service(service_name, passing=False)
        
        if not services:
            return {
                "service": service_name,
                "endpoint": endpoint,
                "status": "unreachable",
                "error": "No instances found in Consul"
            }
        
        # Use the first passing instance, or the first instance if none are passing
        service_instance = next(
            (s for s in services if s["Checks"][0]["Status"] == "passing"),
            services[0] if services else None
        )
        
        if not service_instance:
            return {
                "service": service_name,
                "endpoint": endpoint,
                "status": "unreachable",
                "error": "No healthy instances available"
            }
        
        # Construct the URL
        service_info = service_instance["Service"]
        service_url = f"http://{service_info['Address']}:{service_info['Port']}/{endpoint}"
        
        logger.info(f"Fetching health from {service_url}")
        
        # Make the HTTP request
        async with httpx.AsyncClient(timeout=timeout) as client:
            response = await client.get(service_url)
            
            if response.status_code == 200:
                data = response.json()
                return {
                    "service": service_name,
                    "endpoint": endpoint,
                    "status": "reachable",
                    "code": response.status_code,
                    "data": data
                }
            else:
                return {
                    "service": service_name,
                    "endpoint": endpoint,
                    "status": "unhealthy",
                    "code": response.status_code,
                    "error": f"Service returned {response.status_code}"
                }
    
    except asyncio.TimeoutError:
        return {
            "service": service_name,
            "endpoint": endpoint,
            "status": "timeout",
            "error": "Request timeout"
        }
    except Exception as e:
        logger.error(f"Error fetching health for {service_name}/{endpoint}: {str(e)}")
        return {
            "service": service_name,
            "endpoint": endpoint,
            "status": "error",
            "error": str(e)
        }


@app.get("/health")
async def health():
    """Liveness probe for this service"""
    return {
        "service": "health-check-service",
        "status": "healthy",
        "timestamp": str(__import__('datetime').datetime.utcnow())
    }


@app.get("/ready")
async def readiness():
    """Readiness probe - check if we can connect to Consul"""
    try:
        consul_client.agent.self()
        return {
            "service": "health-check-service",
            "status": "ready",
            "dependencies": {
                "consul": "healthy"
            }
        }
    except Exception as e:
        return JSONResponse(
            status_code=503,
            content={
                "service": "health-check-service",
                "status": "not-ready",
                "error": str(e)
            }
        )


@app.get("/api/health/services")
async def get_all_services_health():
    """
    Get health status for all registered services
    
    Returns:
        Dictionary mapping service names to their health endpoints
    """
    try:
        # Get all services from Consul
        _, services = consul_client.catalog.services()
        
        # Exclude infrastructure services
        excluded = {"consul", "zookeeper", "kafka", "postgres-db", "mongodb", "read-db", "api-gateway"}
        service_list = [s for s in services if s not in excluded]
        
        # Fetch health for each service
        tasks = []
        for service_name in service_list:
            # Try primary health endpoint first
            tasks.append(fetch_service_health(service_name, "health"))
        
        results = await asyncio.gather(*tasks)
        
        # Aggregate results
        services_health = {
            result["service"]: result
            for result in results
        }
        
        return {
            "timestamp": str(__import__('datetime').datetime.utcnow()),
            "services": services_health,
            "total_services": len(services_health),
            "healthy_services": sum(1 for s in services_health.values() if s["status"] == "reachable")
        }
    
    except Exception as e:
        logger.error(f"Error getting all services health: {str(e)}")
        return JSONResponse(
            status_code=503,
            content={
                "error": str(e),
                "message": "Failed to retrieve services health"
            }
        )


@app.get("/api/health/service/{service_name}")
async def get_service_health(
    service_name: str,
    endpoint: str = Query("health", description="Health endpoint to check")
):
    """
    Get health status for a specific service
    
    Args:
        service_name: Service name (e.g., 'book-catalog-service')
        endpoint: Health endpoint ('health', 'ready', 'health/db', 'health/kafka', etc.)
    
    Returns:
        Health status for the service
    """
    result = await fetch_service_health(service_name, endpoint)
    
    if result["status"] in ["unreachable", "timeout", "error", "unhealthy"]:
        return JSONResponse(
            status_code=503,
            content=result
        )
    
    return result


@app.get("/api/health/service/{service_name}/{endpoint}")
async def get_service_endpoint_health(
    service_name: str,
    endpoint: str
):
    """
    Get health status for a specific service endpoint
    
    Args:
        service_name: Service name (e.g., 'book-catalog-service')
        endpoint: Health endpoint ('ready', 'health/db', 'health/kafka', etc.)
    
    Returns:
        Health status for the service endpoint
    """
    # Reconstruct full endpoint path
    full_endpoint = endpoint if endpoint.startswith("health") else f"health/{endpoint}"
    
    result = await fetch_service_health(service_name, full_endpoint)
    
    if result["status"] in ["unreachable", "timeout", "error", "unhealthy"]:
        return JSONResponse(
            status_code=503,
            content=result
        )
    
    return result


@app.get("/api/health/status")
async def get_system_health():
    """
    Get overall system health status
    
    Returns:
        Overall health with breakdown by service type
    """
    try:
        result = await get_all_services_health()
        services_health = result.get("services", {})
        
        # Categorize services
        categories = {
            "data-services": ["book-catalog-service", "book-review-service", "posts-service", "user-profile-service"],
            "event-services": ["feed-generator-service"],
            "auth-services": ["auth-service"]
        }
        
        category_health = {}
        for category, service_names in categories.items():
            category_services = {
                name: services_health.get(name, {"status": "unknown"})
                for name in service_names
                if name in services_health
            }
            category_health[category] = {
                "services": category_services,
                "healthy": sum(1 for s in category_services.values() if s.get("status") == "reachable"),
                "total": len(category_services)
            }
        
        # Overall status
        total_services = sum(c["total"] for c in category_health.values())
        healthy_services = sum(c["healthy"] for c in category_health.values())
        overall_status = "healthy" if healthy_services == total_services else "degraded" if healthy_services > 0 else "unhealthy"
        
        return {
            "timestamp": result["timestamp"],
            "status": overall_status,
            "overall": {
                "healthy": healthy_services,
                "total": total_services,
                "percentage": (healthy_services / total_services * 100) if total_services > 0 else 0
            },
            "by_category": category_health
        }
    
    except Exception as e:
        logger.error(f"Error getting system health: {str(e)}")
        return JSONResponse(
            status_code=503,
            content={
                "error": str(e),
                "message": "Failed to retrieve system health"
            }
        )


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=5000)
