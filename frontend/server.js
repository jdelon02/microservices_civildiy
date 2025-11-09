const express = require('express');
const path = require('path');
const http = require('http');

const app = express();
const PORT = 3000;

// Serve static files from React build
app.use(express.static(path.join(__dirname, 'build')));

// API route to proxy health checks to internal services
app.get('/api/health/:serviceName/:endpoint?', async (req, res) => {
  const { serviceName, endpoint = 'health' } = req.params;
  
  try {
    // Map service name to internal address
    // Services are named like 'book-catalog-service' and run on port 5000
    const internalUrl = `http://${serviceName}:5000/${endpoint === 'health' ? 'health' : endpoint}`;
    
    console.log(`Proxying health check: ${internalUrl}`);
    
    // Fetch from the internal service
    const response = await new Promise((resolve, reject) => {
      http.get(internalUrl, { timeout: 5000 }, (response) => {
        let data = '';
        response.on('data', chunk => data += chunk);
        response.on('end', () => {
          resolve({
            status: response.statusCode,
            headers: response.headers,
            body: data
          });
        });
      }).on('error', reject)
        .on('timeout', () => {
          reject(new Error('Request timeout'));
        });
    });
    
    res.status(response.status)
       .set(response.headers)
       .send(response.body);
       
  } catch (error) {
    console.error(`Health check error for ${serviceName}/${endpoint}:`, error.message);
    res.status(503).json({
      status: 'unreachable',
      error: error.message,
      service: serviceName
    });
  }
});

// Catch-all for React Router
app.get('*', (req, res) => {
  res.sendFile(path.join(__dirname, 'build', 'index.html'));
});

app.listen(PORT, () => {
  console.log(`Frontend server running on port ${PORT}`);
});
