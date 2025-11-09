import React, { useState, useEffect } from 'react';
import { getServices, buildAPIEndpoints, getFullServiceHealth } from '../services/consul';

const ServiceDiscoveryPage = () => {
  const [services, setServices] = useState({});
  const [endpoints, setEndpoints] = useState([]);
  const [healthStatuses, setHealthStatuses] = useState({});
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [lastUpdated, setLastUpdated] = useState(null);

  useEffect(() => {
    const loadServices = async () => {
      try {
        const servicesData = await getServices();
        setServices(servicesData);

        const endpointsData = await buildAPIEndpoints();
        setEndpoints(endpointsData);

        // Fetch health status for all services
        const healthData = {};
        const serviceNames = Object.keys(servicesData);
        for (const serviceName of serviceNames) {
          try {
            const health = await getFullServiceHealth(serviceName);
            healthData[serviceName] = health;
          } catch (healthErr) {
            console.warn(`Could not fetch health for ${serviceName}:`, healthErr);
            healthData[serviceName] = {
              service: serviceName,
              overallStatus: 'error',
              error: 'Could not fetch health status'
            };
          }
        }
        setHealthStatuses(healthData);
        setLastUpdated(new Date());
      } catch (err) {
        setError('Failed to load service discovery data');
        console.error(err);
      } finally {
        setLoading(false);
      }
    };

    loadServices();

    // Refresh every 10 seconds
    const interval = setInterval(loadServices, 10000);
    return () => clearInterval(interval);
  }, []);

  if (loading) {
    return <div className="discovery-container"><p>Loading service discovery...</p></div>;
  }

  // Helper function to get status badge color
  const getStatusColor = (status) => {
    switch (status) {
      case 'healthy':
        return '#4CAF50'; // Green
      case 'unhealthy':
        return '#F44336'; // Red
      case 'error':
        return '#FF9800'; // Orange
      case 'unreachable':
        return '#9E9E9E'; // Gray
      default:
        return '#9E9E9E';
    }
  };

  const getStatusLabel = (status) => {
    return status.charAt(0).toUpperCase() + status.slice(1);
  };

  return (
    <div className="discovery-container">
      <h2>Service Discovery</h2>
      <p>Services registered with Consul</p>

      {error && <div className="error-message">{error}</div>}

      {lastUpdated && (
        <div className="last-updated">
          Last updated: {lastUpdated.toLocaleTimeString()}
        </div>
      )}

      <section className="services-section">
        <h3>Available Services ({Object.keys(services).length})</h3>
        <div className="services-grid">
          {Object.entries(services).map(([serviceName, tags]) => {
            const health = healthStatuses[serviceName];
            const statusColor = health ? getStatusColor(health.overallStatus) : '#9E9E9E';

            return (
              <div key={serviceName} className="service-card">
                <div className="card-header">
                  <h4>{serviceName}</h4>
                  {health && (
                    <div
                      className="status-badge"
                      style={{
                        backgroundColor: statusColor,
                        color: 'white',
                        padding: '4px 8px',
                        borderRadius: '4px',
                        fontSize: '12px',
                        fontWeight: 'bold'
                      }}
                    >
                      {getStatusLabel(health.overallStatus)}
                    </div>
                  )}
                </div>
                <div className="tags">
                  {tags.map((tag, i) => (
                    <span key={i} className="tag">{tag}</span>
                  ))}
                </div>
                {health && (
                  <div className="health-details">
                    <div className="health-item">
                      <span className="label">Liveness:</span>
                      <span
                        className="value"
                        style={{ color: health.liveness.status === 'healthy' ? '#4CAF50' : '#F44336' }}
                      >
                        {health.liveness.status}
                      </span>
                    </div>
                    <div className="health-item">
                      <span className="label">Ready:</span>
                      <span
                        className="value"
                        style={{ color: health.readiness.ready ? '#4CAF50' : '#F44336' }}
                      >
                        {health.readiness.ready ? 'Yes' : 'No'}
                      </span>
                    </div>
                    <div className="health-item">
                      <span className="label">Database:</span>
                      <span
                        className="value"
                        style={{ color: health.database.status === 'healthy' ? '#4CAF50' : '#F44336' }}
                      >
                        {health.database.status}
                      </span>
                    </div>
                  </div>
                )}
              </div>
            );
          })}
        </div>
      </section>

      {Object.keys(endpoints).length > 0 && (
        <section className="endpoints-section">
          <h3>API Endpoints</h3>
          <div className="endpoints-grid">
            {Object.entries(endpoints).map(([serviceName, info]) => (
              <div key={serviceName} className="endpoint-card">
                <h4>{info.name}</h4>
                <p className="path"><strong>Path:</strong> {info.path}</p>
                <p className="instances"><strong>Instances:</strong> {info.instances.length}</p>
                <ul className="instance-list">
                  {info.instances.map((instance, i) => (
                    <li key={i}>
                      {instance.ServiceAddress}:{instance.ServicePort}
                    </li>
                  ))}
                </ul>
              </div>
            ))}
          </div>
        </section>
      )}
    </div>
  );
};

export default ServiceDiscoveryPage;
