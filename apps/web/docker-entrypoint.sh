#!/bin/sh
set -e

# Default API_URL if not set
export API_URL=${API_URL:-http://localhost:8080}

# Substitute environment variables in nginx config
envsubst '${API_URL}' < /etc/nginx/nginx.conf.template > /etc/nginx/nginx.conf

# Execute the main command
exec "$@"
