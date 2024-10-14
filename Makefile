INPUT_FILE = ./dist/index.html.template
OUTPUT_FILE = ./dist/index.html
S3_FILE = index.html
JSON_FILE = outputs.json
EVENTS_FILE = football_events.json

# Check if JSON_FILE exists
ifneq ("$(wildcard $(JSON_FILE))","")
# Extract the stack name (first key) from the JSON file
STACK_NAME := $(shell jq -r 'keys[0]' $(JSON_FILE))
# Read values from JSON file
API_GATEWAY_URL := $(shell jq -r '.$(STACK_NAME).ApiGatewayUrl' $(JSON_FILE))
S3_BUCKET := $(shell jq -r '.$(STACK_NAME).S3BucketName' $(JSON_FILE))
CLOUDFRONT_DISTRIBUTION_ID := $(shell jq -r '.$(STACK_NAME).CloudFrontDistributionId' $(JSON_FILE))
KINESIS_STREAM_NAME := $(shell jq -r '.$(STACK_NAME).KinesisStreamName' $(JSON_FILE))
TABLE_NAME := $(shell jq -r '.$(STACK_NAME).TableName' $(JSON_FILE))

# Define targets that require JSON_FILE
.PHONY: update-html upload-to-s3 invalidate-cloudfront kinesis-event-loop

update-html: $(INPUT_FILE)
	@echo "updating html file..."
	@sed -e 's|{{api_url}}|$(API_GATEWAY_URL)|g' \
		$(INPUT_FILE) > $(OUTPUT_FILE)
	@echo "html file updated."

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

# Kinesis event loop
kinesis-event-loop:
		@if [ ! -f $(EVENTS_FILE) ]; then \
				echo "Error: $(EVENTS_FILE) not found."; \
				exit 1; \
		fi
		@echo "Starting Kinesis event loop. Press any key to send the next event, or 'q' to quit."
		@./send_kinesis_events.sh $(EVENTS_FILE) $(KINESIS_STREAM_NAME)

# Truncate DynamoDB
truncate-dynamodb:
		@echo "Deleting every record from DynamoDB"
		aws dynamodb delete-item --table-name $(TABLE_NAME) --key '{"id": {"S": "latest"}}'
		@echo "The memory of the LLM generating the commentary has been reset."

endif

# Always available targets
.PHONY: deploy destroy clean

# deploy stack
deploy:
	@echo Deploying CDK stack
	cdk deploy --outputs-file $(JSON_FILE)

# destroy stack
destroy:
	@echo Destroying CDK stack
	cdk destroy

# Clean up
clean:
	rm -f $(OUTPUT_FILE)

# Check if JSON_FILE exists before allowing certain commands
ifeq ("$(wildcard $(JSON_FILE))","")
update-html upload-to-s3 invalidate-cloudfront kinesis-event-loop:
	@echo "Error: $(JSON_FILE) not found. Please run 'make deploy' first."
	@exit 1
endif
