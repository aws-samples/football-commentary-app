INPUT_FILE = ./dist/index.html.template
OUTPUT_FILE = ./dist/index.html
S3_FILE = index.html
JSON_FILE = outputs.json

# Extract the stack name (first key) from the JSON file
STACK_NAME := $(shell jq -r 'keys[0]' $(JSON_FILE))

# Read values from JSON file
API_GATEWAY_URL := $(shell jq -r '.$(STACK_NAME).ApiGatewayUrl' $(JSON_FILE))
S3_BUCKET := $(shell jq -r '.$(STACK_NAME).S3BucketName' $(JSON_FILE))
CLOUDFRONT_DISTRIBUTION_ID := $(shell jq -r '.$(STACK_NAME).CloudFrontDistributionId' $(JSON_FILE))

# deploy stack
deploy:
	@echo Deploying CDK stack
	cdk deploy --outputs-file $(JSON_FILE)

# destroy stack
destroy:
	@echo Destroying CDK stack
	cdk destroy

update-html: $(INPUT_FILE) $(JSON_FILE)
	@echo "Updating HTML file..."
	@sed -e 's|{{api_url}}|$(API_GATEWAY_URL)|g' \
				$(INPUT_FILE) > $(OUTPUT_FILE)
	@echo "HTML file updated."

# Upload to S3
upload-to-s3: update-html
	@echo "Uploading to S3..."
	aws s3 cp $(OUTPUT_FILE) s3://$(S3_BUCKET)/$(S3_FILE)
	@echo "Upload complete."

# Invalidate CloudFront distribution
invalidate-cloudfront: upload-to-s3
	@echo "Invalidating CloudFront distribution..."
	aws cloudfront create-invalidation --distribution-id $(CLOUDFRONT_DISTRIBUTION_ID) --paths "/$(S3_FILE)"
	@echo "Invalidation request sent."

# Clean up
clean:
	rm -f $(OUTPUT_FILE)

# Make targets .PHONY to ensure they always run
.PHONY: deploy destroy update-html upload-to-s3 invalidate-cloudfront clean
