const CONSUL_URL = process.env.REACT_APP_CONSUL_URL || 'http://localhost:8500';

// Get all registered services from Consul
export const getServices = async () => {
  try {
    const response = await fetch(`${CONSUL_URL}/v1/catalog/services`);
    if (!response.ok) throw new Error('Failed to fetch services');
    return await response.json();
  } catch (error) {
    console.error('Error fetching services from Consul:', error);
    return {};
  }
};

// Get details of a specific service
export const getServiceInstances = async (serviceName) => {
  try {
    const response = await fetch(`${CONSUL_URL}/v1/catalog/service/${serviceName}`);
    if (!response.ok) throw new Error(`Failed to fetch ${serviceName} instances`);
    return await response.json();
  } catch (error) {
    console.error(`Error fetching ${serviceName} instances:`, error);
    return [];
  }
};

// Get all services with their details
export const getAllServiceDetails = async () => {
  try {
    const services = await getServices();
    const serviceDetails = {};

    for (const serviceName of Object.keys(services)) {
      serviceDetails[serviceName] = await getServiceInstances(serviceName);
    }

    return serviceDetails;
  } catch (error) {
    console.error('Error fetching service details:', error);
    return {};
  }
};

// Get Traefik routes from Consul KV
export const getTraefikRoutes = async () => {
  try {
    const response = await fetch(`${CONSUL_URL}/v1/kv/traefik/http/routers?recurse`);
    if (!response.ok) throw new Error('Failed to fetch Traefik routes');
    const kvPairs = await response.json();

    const routes = {};
    kvPairs.forEach(pair => {
      const decodedValue = atob(pair.Value);
      const keyParts = pair.Key.split('/');
      const routeName = keyParts[keyParts.length - 1];
      
      if (!routes[routeName]) {
        routes[routeName] = {};
      }
      
      routes[routeName][keyParts[keyParts.length - 2]] = decodedValue;
    });

    return routes;
  } catch (error) {
    console.error('Error fetching Traefik routes:', error);
    return {};
  }
};

// Get service health status
export const getServiceHealth = async (serviceName) => {
  try {
    const response = await fetch(`${CONSUL_URL}/v1/health/service/${serviceName}`);
    if (!response.ok) throw new Error(`Failed to fetch health for ${serviceName}`);
    return await response.json();
  } catch (error) {
    console.error(`Error fetching health for ${serviceName}:`, error);
    return [];
  }
};

// Build API endpoints from service discovery
export const buildAPIEndpoints = async () => {
  const services = await getServices();
  const endpoints = {};

  // Map known services to their API paths
  const serviceMapping = {
    'posts-service': '/api/posts',
    'feed-generator-service': '/api/activity-stream',
    'user-profile-service': '/api/profile',
    'auth-service': '/api/auth',
  };

  for (const [serviceName, apiPath] of Object.entries(serviceMapping)) {
    if (services[serviceName]) {
      endpoints[serviceName] = {
        name: serviceName,
        path: apiPath,
        instances: await getServiceInstances(serviceName),
      };
    }
  }

  return endpoints;
};

// Monitor service changes (useful for dynamic UI updates)
export const watchServices = async (callback, interval = 5000) => {
  const previousServices = {};

  const check = async () => {
    const currentServices = await getServices();

    // Compare with previous state
    if (JSON.stringify(previousServices) !== JSON.stringify(currentServices)) {
      Object.assign(previousServices, currentServices);
      callback(currentServices);
    }
  };

  // Initial check
  check();

  // Poll for changes
  return setInterval(check, interval);
};

// Get service with fallback to default API gateway
export const getServiceEndpoint = async (serviceName, fallbackGateway = 'http://api-gateway:80') => {
  try {
    const instances = await getServiceInstances(serviceName);

    if (instances.length > 0) {
      // Return first healthy instance
      const instance = instances[0];
      return `http://${instance.ServiceAddress}:${instance.ServicePort}`;
    }

    console.warn(`No instances found for ${serviceName}, using fallback: ${fallbackGateway}`);
    return fallbackGateway;
  } catch (error) {
    console.error(`Error getting endpoint for ${serviceName}:`, error);
    return fallbackGateway;
  }
};
