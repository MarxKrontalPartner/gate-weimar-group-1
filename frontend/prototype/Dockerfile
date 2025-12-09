# Use Node.js for dev
FROM node:22-bullseye

# Set working directory
WORKDIR /app

# Copy package files and install dependencies
COPY package*.json ./
RUN npm install

# Copy the rest of the source code
COPY . .

# Expose Vue dev server port
EXPOSE 5173

# Start dev server with host binding for container
CMD ["npm", "run", "dev", "--", "--host", "0.0.0.0"]
