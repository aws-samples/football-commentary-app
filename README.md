## Football commentary stack

### Requirements
- AWS CDK
- jq
- make
- AWS CLI

### Usage

To work with the stack you *should* use the `make` commands. The reason is because we use it to deploy HTML to an S3 bucket. Also make sure that you have permissions locally to upload files to S3, and Invalidate CloudFront caches.

To deploy:
```
make deploy
```

To delete the stack:
```
make destroy
```


Deploy the code, this will also update the HTML with the API Gateway URL:
```
make upload-to-s3
```

## Security

See [CONTRIBUTING](CONTRIBUTING.md#security-issue-notifications) for more information.

## License

This library is licensed under the MIT-0 License. See the LICENSE file.

