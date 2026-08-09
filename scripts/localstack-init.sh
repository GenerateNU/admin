#!/bin/sh
set -eu

awslocal s3api create-bucket --bucket "${BUCKET_NAME}" --region "${DEFAULT_REGION}"
awslocal s3api put-bucket-versioning \
  --bucket "${BUCKET_NAME}" \
  --versioning-configuration Status=Enabled

# Browsers preflight direct-to-S3 uploads; without this the presigned POST is
# rejected before any bytes are sent.
awslocal s3api put-bucket-cors --bucket "${BUCKET_NAME}" --cors-configuration '{
  "CORSRules": [
    {
      "AllowedHeaders": ["*"],
      "AllowedMethods": ["GET", "HEAD", "POST", "PUT"],
      "AllowedOrigins": [
        "http://localhost:3000",
        "http://localhost:5173",
        "https://generatenu.com",
        "https://www.generatenu.com"
      ],
      "ExposeHeaders": ["ETag", "Location"],
      "MaxAgeSeconds": 3000
    }
  ]
}'

# Public prefix is readable without signing so the website and admin can render
# images straight from the CDN origin.
awslocal s3api put-bucket-policy --bucket "${BUCKET_NAME}" --policy "{
  \"Version\": \"2012-10-17\",
  \"Statement\": [
    {
      \"Sid\": \"PublicReadForPublicPrefix\",
      \"Effect\": \"Allow\",
      \"Principal\": \"*\",
      \"Action\": \"s3:GetObject\",
      \"Resource\": \"arn:aws:s3:::${BUCKET_NAME}/public/*\"
    }
  ]
}"
