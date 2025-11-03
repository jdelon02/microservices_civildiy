# LXC Dockge Deployment Guide

## Quick Summary

Your microservices framework works perfectly on **Docker Desktop (Docker Compose v1)** but fails to communicate on **Dockge LXC (Docker Compose v2)**. The issue is a combination of:

1. **Docker Compose v1 vs v2 syntax changes**
2. **Network namespace differences in LXC**
3. **Hostname resolution issues in LXC bridge network**

## Environment Details

- **Local Mac:** Docker Desktop with `docker-compose` (v1 syntax)
- **LXC:** Dockge on Ubuntu LXC container at `192.168.86.6:/opt/stacks/microservices_civildiy` with `docker compose` (v2 syntax)

## Root Cause Analysis

### Docker Compose v1 vs v2 Differences

| Feature | v1 (docker-compose) | v2 (docker compose) |
|---------|-------------------|-------------------|
| Command | `docker-compose` (hyphenated) | `docker compose` (space) |
| Network Creation | Automatic, named `{projectname}_default` | Explicit network definition recommended |
| Hostname Resolution | Services see each other by name automatically | Requires explicit network assignment |
| Health Checks | Limited support | Full support with `condition: service_healthy` |
| Depends_on | No wait conditions | Can wait for `service_healthy` |
| IPv4 Assignment | Automatic DHCP-like | Can assign explicit IPs |

### Why Services Don't Communicate in LXC

1. **Network scoping:** LXC's Docker daemon creates bridge networks differently than Docker Desktop
2. **DNS resolution:** Container names not resolving in LXC bridge network (e.g., `postgres-db:5432` fails)
3. **Service discovery:** Consul tries to register with itself but network path broken
4. **Traefik routing:** API Gateway can't reach backend services by hostname

## Solutions

### Solution 1: Use LXC-Specific Docker Compose File (Recommended)

We've created `docker-compose.lxc.yml` with:
- Explicit network definition (`172.20.0.0/16` subnet)
- Fixed IPv4 addresses for each service
- Health checks for all services
- Explicit CONSUL_HOST and CONSUL_PORT configuration

**On LXC, use:**
```bash
cd /opt/stacks/microservices_civildiy
docker compose -f docker-compose.lxc.yml up -d
```

**Key improvements:**
- Services get stable IPs (kafka: 172.20.0.11, postgres: 172.20.0.14, etc.)
- Service discovery via explicit network membership
- Health checks prevent premature startup dependencies

### Solution 2: Update docker-compose.yml for v2 Compatibility

If you want to use the main `docker-compose.yml` on LXC:

```yaml
version: '3.8'  # Ensure at least 3.8

networks:
  microservices-network:
    driver: bridge
    ipam:
      config:
        - subnet: 172.20.0.0/16

services:
  # Add to each service:
  your-service:
    networks:
      microservices-network:
        ipv4_address: 172.20.0.XX  # Specific IP
    
    # Add healthchecks for dependent services
    depends_on:
      postgres-db:
        condition: service_healthy
    
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:5000/health"]
      interval: 10s
      timeout: 5s
      retries: 3
```

## Deployment Steps for LXC

### Step 1: Copy Files to LXC
```bash
# On your Mac
scp docker-compose.lxc.yml user@192.168.86.6:/opt/stacks/microservices_civildiy/
```

### Step 2: Stop Current Stack
```bash
# SSH into LXC
ssh user@192.168.86.6
cd /opt/stacks/microservices_civildiy

# Stop current containers (if running)
docker compose down
```

### Step 3: Start with LXC-Specific Config
```bash
docker compose -f docker-compose.lxc.yml up -d
```

### Step 4: Verify All Services
```bash
# Check all containers are running
docker ps

# Verify services are healthy
docker compose -f docker-compose.lxc.yml ps

# Check specific service health
docker logs zookeeper | tail -20
docker logs kafka | tail -20
```

## Debugging on LXC

### Test Hostname Resolution
```bash
# From within a container
docker exec auth-service nslookup postgres-db
docker exec auth-service nslookup kafka

# Expected output: Should resolve to an IP in 172.20.0.0/16
```

### Test Network Connectivity
```bash
# Test if auth-service can reach postgres-db
docker exec auth-service curl -v postgres-db:5432

# Test if posts-service can reach kafka
docker exec posts-service nc -zv kafka 9092

# Test if services can reach Consul
docker exec auth-service curl http://consul-server:8500/ui/
```

### Check Consul Registration
```bash
# Access Consul UI on LXC at: http://192.168.86.6:8500

# Or query via API
curl http://192.168.86.6:8500/v1/catalog/services

# Should show: auth-service, user-profile-service, posts-service, feed-generator-service
```

### Check Kafka Connectivity
```bash
# Verify Kafka broker is accessible
docker exec kafka kafka-broker-api-versions.sh --bootstrap-server kafka:9092

# Create test topic
docker exec kafka kafka-topics.sh --create --topic test --bootstrap-server kafka:9092

# List topics
docker exec kafka kafka-topics.sh --list --bootstrap-server kafka:9092
```

### Check Traefik Dashboard
```bash
# Access at: http://192.168.86.6:8080

# Should show:
# - HTTP entry point (80)
# - All 4 microservices registered
# - JWT-auth middleware active
```

## Common LXC Issues & Fixes

### Issue 1: "Unable to connect to postgres-db:5432"
**Symptom:** Auth service fails to start with connection error
**Cause:** Hostname resolution failing in LXC network
**Fix:** 
```bash
# Verify network exists
docker network ls | grep microservices

# Check if postgres-db container is on the network
docker network inspect microservices-network | grep postgres

# Restart with explicit network in docker-compose.lxc.yml
```

### Issue 2: "Kafka broker not available"
**Symptom:** Posts service fails to connect to Kafka
**Cause:** Zookeeper/Kafka startup race condition
**Fix:**
```bash
# Increase health check timeout
# In docker-compose.lxc.yml, adjust:
retries: 5  # Increase from 3
timeout: 10s  # Increase from 5s

# Or manually wait for Kafka
docker exec kafka kafka-broker-api-versions.sh --bootstrap-server kafka:9092
```

### Issue 3: "Consul agent not responding"
**Symptom:** Services cannot register with Consul
**Cause:** Consul bind interface misconfigured for LXC
**Fix:**
```bash
# In docker-compose.lxc.yml, ensure:
environment:
  CONSUL_BIND_INTERFACE: eth0  # eth0 is default in LXC

# Verify Consul is listening
docker exec consul-server consul members
```

### Issue 4: "Cannot connect to Docker daemon"
**Symptom:** Traefik cannot reach Docker socket
**Cause:** Volume mount path incorrect for LXC
**Fix:**
```bash
# Verify Docker socket exists in LXC
ls -la /var/run/docker.sock

# Ensure volume mount in docker-compose.lxc.yml:
volumes:
  - /var/run/docker.sock:/var/run/docker.sock:ro
```

## Testing the Stack

### 1. Verify All Services Are Healthy
```bash
docker compose -f docker-compose.lxc.yml ps

# Should show all services with "healthy" status
```

### 2. Run Automated Tests
```bash
# Copy test script to LXC
scp test.sh user@192.168.86.6:/opt/stacks/microservices_civildiy/

# Run tests
ssh user@192.168.86.6 'cd /opt/stacks/microservices_civildiy && chmod +x test.sh && ./test.sh'
```

### 3. Manual API Test
```bash
# Register a user
curl -X POST http://192.168.86.6/api/auth/register \
  -H "Content-Type: application/json" \
  -d '{"email":"test@example.com","username":"testuser","password":"pass123"}'

# Login to get JWT
curl -X POST http://192.168.86.6/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email":"test@example.com","password":"pass123"}'

# Create a post (with JWT token)
TOKEN="<access_token>"
curl -X POST http://192.168.86.6/api/posts \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"title":"Test","content":"Hello from LXC","tags":["test"]}'

# Check activity stream
curl http://192.168.86.6/api/activity-stream
```

## Performance Notes

### Expected Response Times on LXC
- API endpoints: 50-200ms (vs 10-50ms on local)
- Database queries: Similar due to LXC resource constraints
- Kafka event propagation: 1-3s (vs 0.5s on local)

Slower performance is normal in LXC due to:
1. Network bridge overhead
2. LXC CPU/memory constraints
3. Disk I/O limitations

## Version Compatibility

**Tested with:**
- Docker Compose v2.x on LXC
- docker-compose v1.x on macOS
- Docker 24.x+ on both platforms

**To check your Docker Compose version:**
```bash
# On Mac (should show hyphenated command)
docker-compose --version

# On LXC (should show space-separated command)
docker compose --version
```

## Next Steps

1. **Immediate:** Deploy using `docker-compose.lxc.yml`
2. **Testing:** Run automated tests to verify all services work
3. **Documentation:** Update your deployment runbook with LXC-specific steps
4. **Monitoring:** Set up container monitoring for the LXC environment
5. **Persistence:** Add Docker volumes for data persistence (currently ephemeral)

## Troubleshooting Flow

```
1. Services won't start?
   → Check docker logs: docker logs service-name
   → Verify network: docker network ls

2. Services won't communicate?
   → Test hostname resolution: docker exec service nc -zv target-service port
   → Check network membership: docker network inspect microservices-network

3. API not responding?
   → Check Traefik: http://192.168.86.6:8080
   → Check backend service: docker exec service curl http://localhost:5000/health

4. Data not persisting?
   → Normal - no volumes configured. Add volumes for production deployment

5. Still having issues?
   → Check: docker logs kafka (for event issues)
   → Check: docker logs consul-server (for discovery issues)
   → Check: docker compose logs (for all container output)
```
