import React, { useState, useEffect } from 'react';
import { getServices, buildAPIEndpoints } from '../services/consul';
import './ServiceDiscoveryPage.css';

const ServiceDiscoveryPage = () => {
  const [services, setServices] = useState({});
  const [endpoints, setEndpoints] = useState({});
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');

  useEffect(() => {
    const loadServices = async () => {
      try {
        const servicesData = await getServices();
        setServices(servicesData);

        const endpointsData = await buildAPIEndpoints();
        setEndpoints(endpointsData);
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

  return (
    <div className="discovery-container">
      <h2>Service Discovery</h2>
      <p>Services registered with Consul</p>

      {error && <div className="error-message">{error}</div>}

      <section className="services-section">
        <h3>Available Services ({Object.keys(services).length})</h3>
        <div className="services-grid">
          {Object.entries(services).map(([serviceName, tags]) => (
            <div key={serviceName} className="service-card">
              <h4>{serviceName}</h4>
              <div className="tags">
                {tags.map((tag, i) => (
                  <span key={i} className="tag">{tag}</span>
                ))}
              </div>
            </div>
          ))}
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
