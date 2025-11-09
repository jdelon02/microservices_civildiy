#!/bin/bash
# Initialize Kafka topics for microservices_civildiy

set -e

KAFKA_HOST=${KAFKA_HOST:-kafka:9092}
ZOOKEEPER_HOST=${ZOOKEEPER_HOST:-zookeeper:2181}

echo "Waiting for Kafka to be ready..."
sleep 10

# Function to create topic
create_topic() {
    local topic=$1
    local partitions=${2:-3}
    local replication_factor=${3:-1}
    
    echo "Creating topic: $topic (partitions: $partitions, replication-factor: $replication_factor)"
    
    docker exec kafka kafka-topics --create \
        --bootstrap-server $KAFKA_HOST \
        --topic $topic \
        --partitions $partitions \
        --replication-factor $replication_factor \
        --if-not-exists || true
}

# Create topics for existing services
echo "Creating topics for existing services..."
create_topic "posts-events" 3 1
create_topic "feed-events" 3 1

# Create topics for book review service
echo "Creating topics for book review service..."
create_topic "reviews-events" 3 1
create_topic "book-catalog-events" 3 1

# List all topics to verify
echo ""
echo "Verifying topics created:"
docker exec kafka kafka-topics --list \
    --bootstrap-server $KAFKA_HOST

echo ""
echo "✅ Kafka topics initialized successfully!"
