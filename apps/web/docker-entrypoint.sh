#!/bin/sh
set -e

# Replace placeholder with actual backend URL
if [ -n "$BACKEND_URL" ]; then
    # Remove trailing slash if present
    BACKEND_URL="${BACKEND_URL%/}"
    # Extract host from URL (remove https:// prefix)
    BACKEND_HOST=$(echo "$BACKEND_URL" | sed 's|https://||' | sed 's|http://||' | sed 's|/.*||')

    sed -i "s|__BACKEND_URL__|${BACKEND_URL}|g" /etc/nginx/conf.d/default.conf
    sed -i "s|__BACKEND_HOST__|${BACKEND_HOST}|g" /etc/nginx/conf.d/default.conf
    echo "BACKEND_URL set to: ${BACKEND_URL}"
    echo "BACKEND_HOST set to: ${BACKEND_HOST}"
else
    echo "WARNING: BACKEND_URL not set, API proxy will not work"
fi

# Start nginx
exec nginx -g 'daemon off;'
