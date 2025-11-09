# Build stage
FROM node:18-alpine as builder
WORKDIR /app
COPY package.json package-lock.json ./
RUN npm install
COPY . .
RUN npm run build

# Production stage
FROM node:18-alpine
WORKDIR /app
COPY package.json package-lock.json ./
RUN npm install --only=production
COPY --from=builder /app/build ./build
COPY server.js .
EXPOSE 3000
CMD ["node", "server.js"]
