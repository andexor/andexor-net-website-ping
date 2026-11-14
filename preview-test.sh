#!/bin/bash

# SPDX-License-Identifier: Apache-2.0
# Copyright 2026 Andexor Network, Inc.
# Author: Ed Jenkins <ed@andexor.net>

NAME=preview

# Deploy
echo "Deploying preview..."
uv run pywrangler preview --name ${NAME}
echo ""
echo ""

# Health check
echo "Health check..."
curl -si -X GET https://${NAME}-andexor-net-website-ping.andexor.workers.dev/api/v1/ping/health
echo ""
echo ""

# Test database connection
echo "Testing database connection..."
# The Worker sets received_at itself from the current UTC time. The service returns 204 with no body.
RND=$(printf '%05d' $((RANDOM * 3 % 100000)))
curl -si -X POST https://${NAME}-andexor-net-website-ping.andexor.workers.dev/api/v1/ping \
    -H "Referer: https://andexor.net/preview-test/${RND}" \
    -H "Ping-From: https://andexor.net/preview-test/${RND}" \
    -H "Ping-To: https://example.com/preview-test/${RND}"
echo ""
echo ""
