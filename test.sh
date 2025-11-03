#!/bin/bash

set -e

BASE_URL="http://localhost"
EMAIL="testuser@example.com"
USERNAME="testuser"
PASSWORD="testpass123"

echo "================================"
echo "Microservices Integration Test"
echo "================================"

# Colors for output
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Helper function to print colored output
print_status() {
  local status=$1
  local message=$2
  if [ $status -eq 0 ]; then
    echo -e "${GREEN}✓ $message${NC}"
  else
    echo -e "${RED}✗ $message${NC}"
    exit 1
  fi
}

# 1. Test Auth Service - Register
echo ""
echo "1. Testing Auth Service..."
echo "   - Registering user..."

REGISTER_RESPONSE=$(curl -s -X POST $BASE_URL/api/auth/register \
  -H "Content-Type: application/json" \
  -d "{
    \"email\": \"$EMAIL\",
    \"username\": \"$USERNAME\",
    \"password\": \"$PASSWORD\"
  }")

USER_ID=$(echo $REGISTER_RESPONSE | grep -o '"id":[0-9]*' | head -1 | grep -o '[0-9]*')

if [ -z "$USER_ID" ]; then
  print_status 1 "User registration failed"
else
  print_status 0 "User registered (ID: $USER_ID)"
fi

# 2. Test Auth Service - Login
echo "   - Logging in..."

LOGIN_RESPONSE=$(curl -s -X POST $BASE_URL/api/auth/login \
  -H "Content-Type: application/json" \
  -d "{
    \"email\": \"$EMAIL\",
    \"password\": \"$PASSWORD\"
  }")

TOKEN=$(echo $LOGIN_RESPONSE | grep -o '"access_token":"[^"]*' | cut -d'"' -f4)

if [ -z "$TOKEN" ]; then
  print_status 1 "Login failed"
else
  print_status 0 "Login successful (token: ${TOKEN:0:20}...)"
fi

# 3. Test User Profile Service - Create
echo ""
echo "2. Testing User Profile Service..."
echo "   - Creating profile..."

PROFILE_RESPONSE=$(curl -s -X POST $BASE_URL/api/profile \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "first_name": "Test",
    "last_name": "User",
    "dob": "1990-01-15",
    "city": "San Francisco",
    "state": "CA",
    "country": "USA"
  }')

PROFILE_ID=$(echo $PROFILE_RESPONSE | grep -o '"id":[0-9]*' | head -1 | grep -o '[0-9]*')

if [ -z "$PROFILE_ID" ]; then
  print_status 1 "Profile creation failed"
else
  print_status 0 "Profile created (ID: $PROFILE_ID)"
fi

# 4. Test User Profile Service - Get
echo "   - Fetching profile..."

FETCH_PROFILE=$(curl -s -X GET $BASE_URL/api/profile \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json")

if echo $FETCH_PROFILE | grep -q "Test"; then
  print_status 0 "Profile fetched successfully"
else
  print_status 1 "Profile fetch failed"
fi

# 5. Test Posts Service - Create
echo ""
echo "3. Testing Posts Service..."
echo "   - Creating posts..."

POST_IDS=()
for i in {1..3}; do
  POST_RESPONSE=$(curl -s -X POST $BASE_URL/api/posts \
    -H "Authorization: Bearer $TOKEN" \
    -H "Content-Type: application/json" \
    -d "{
      \"title\": \"Test Post $i\",
      \"content\": \"This is test post number $i\",
      \"tags\": [\"test\", \"post$i\"]
    }")

  POST_ID=$(echo $POST_RESPONSE | grep -o '"id":"[^"]*' | head -1 | cut -d'"' -f4)
  
  if [ -z "$POST_ID" ]; then
    print_status 1 "Post $i creation failed"
  else
    POST_IDS+=($POST_ID)
    print_status 0 "Post $i created (ID: ${POST_ID:0:8}...)"
  fi
  
  # Small delay between posts to ensure different timestamps
  sleep 0.5
done

# 6. Test Posts Service - Get
echo "   - Fetching posts..."

if [ ! -z "${POST_IDS[0]}" ]; then
  GET_POST=$(curl -s -X GET "$BASE_URL/api/posts/${POST_IDS[0]}")
  
  if echo $GET_POST | grep -q "Test Post 1"; then
    print_status 0 "Post fetched successfully"
  else
    print_status 1 "Post fetch failed"
  fi
fi

# 7. Test Posts Service - List
echo "   - Listing posts..."

LIST_POSTS=$(curl -s -X GET "$BASE_URL/api/posts")

if echo $LIST_POSTS | grep -q "Test Post"; then
  print_status 0 "Posts listed successfully"
else
  print_status 1 "Posts listing failed"
fi

# 8. Wait for Kafka events to propagate
echo ""
echo "4. Testing Feed Generator Service..."
echo "   - Waiting for Kafka events to propagate (3 seconds)..."
sleep 3

# 9. Test Feed Generator - Stats
echo "   - Checking feed statistics..."

STATS=$(curl -s -X GET "$BASE_URL/api/activity-stream/stats")

if echo $STATS | grep -q "global_activity_count"; then
  print_status 0 "Feed stats retrieved"
else
  print_status 1 "Feed stats retrieval failed"
fi

# 10. Test Feed Generator - Global Stream
echo "   - Fetching global activity stream..."

GLOBAL_FEED=$(curl -s -X GET "$BASE_URL/api/activity-stream?limit=10")

if echo $GLOBAL_FEED | grep -q "items"; then
  print_status 0 "Global activity stream retrieved"
else
  print_status 1 "Global activity stream retrieval failed"
fi

# 11. Test Feed Generator - User Stream
echo "   - Fetching user activity stream..."

USER_FEED=$(curl -s -X GET "$BASE_URL/api/activity-stream/user" \
  -H "Authorization: Bearer $TOKEN")

if echo $USER_FEED | grep -q "items"; then
  print_status 0 "User activity stream retrieved"
else
  print_status 1 "User activity stream retrieval failed"
fi

# 12. Test Posts Service - Update
echo ""
echo "5. Testing Posts Update..."
echo "   - Updating first post..."

if [ ! -z "${POST_IDS[0]}" ]; then
  UPDATE_POST=$(curl -s -X PUT "$BASE_URL/api/posts/${POST_IDS[0]}" \
    -H "Authorization: Bearer $TOKEN" \
    -H "Content-Type: application/json" \
    -d '{
      "title": "Updated Test Post 1",
      "content": "This post has been updated"
    }')
  
  if echo $UPDATE_POST | grep -q "Updated Test Post 1"; then
    print_status 0 "Post updated successfully"
  else
    print_status 1 "Post update failed"
  fi
fi

# 13. Test Posts Service - Delete
echo ""
echo "6. Testing Posts Delete..."
echo "   - Deleting first post..."

if [ ! -z "${POST_IDS[0]}" ]; then
  DELETE_POST=$(curl -s -X DELETE "$BASE_URL/api/posts/${POST_IDS[0]}" \
    -H "Authorization: Bearer $TOKEN")
  
  if echo $DELETE_POST | grep -q "deleted"; then
    print_status 0 "Post deleted successfully"
  else
    print_status 1 "Post deletion failed"
  fi
fi

# Final summary
echo ""
echo "================================"
echo -e "${GREEN}All tests completed!${NC}"
echo "================================"
