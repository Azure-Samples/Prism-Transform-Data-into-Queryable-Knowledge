# Troubleshooting

Common issues and solutions when running Prism.

## Deployment Issues

### `azd up` fails with permission error

**Error**: `Authorization failed for user`

**Solution**: Ensure your Azure account has the required permissions:
- `Microsoft.Authorization/roleAssignments/write`
- `Microsoft.Resources/deployments/write`

You may need Owner or User Access Administrator role on the subscription.

### `azd up` fails with quota error

**Error**: `QuotaExceeded` or `InsufficientQuota`

**Solution**:
1. Check your Azure OpenAI quota in the Azure portal
2. Request a quota increase or use a different region
3. Use the `--location` flag to deploy to a region with available quota:
   ```shell
   azd up --location eastus2
   ```

### Container Apps not starting

**Error**: Container keeps restarting or shows "Unhealthy"

**Solution**:
1. Check container logs:
   ```shell
   az containerapp logs show --name prism-backend --resource-group <rg> --follow
   ```
2. Verify environment variables are set correctly
3. Check if Azure OpenAI endpoint is accessible

### Storage AuthorizationFailure error

**Error**: `AuthorizationFailure: This request is not authorized to perform this operation`

This can happen if:
- The storage account has public network access disabled (often by Azure Policy)
- The managed identity role assignment hasn't propagated yet

**Solution**:
1. Check storage account network access:
   ```shell
   az storage account show --name <storage-account> --resource-group <rg> --query publicNetworkAccess -o tsv
   ```
2. If it shows "Disabled", enable it:
   ```shell
   az storage account update --name <storage-account> --resource-group <rg> --public-network-access Enabled
   ```
3. Verify the role assignment exists:
   ```shell
   az role assignment list --scope "/subscriptions/<sub-id>/resourceGroups/<rg>/providers/Microsoft.Storage/storageAccounts/<storage-account>" --query "[].roleDefinitionName" -o tsv
   ```
   Should include `Storage Blob Data Contributor`.
4. Restart the container app:
   ```shell
   az containerapp revision restart --name prism-backend --resource-group <rg> --revision <revision-name>
   ```

## Local Development Issues

### Docker containers won't start

**Error**: Port already in use

**Solution**:
```bash
# Check what's using the ports
lsof -i :8000  # Backend
lsof -i :3000  # Frontend

# Kill the process or use different ports
docker-compose -f infra/docker/docker-compose.yml down
docker-compose -f infra/docker/docker-compose.yml up -d
```

### Backend returns 500 errors

**Solution**:
1. Check backend logs:
   ```bash
   docker-compose -f infra/docker/docker-compose.yml logs backend
   ```
2. Verify `.env` file has all required variables
3. Test Azure connectivity:
   ```bash
   curl -I $AZURE_OPENAI_ENDPOINT
   ```

### Frontend shows "Network Error"

**Solution**:
1. Verify backend is running: `curl http://localhost:8000/health`
2. Check CORS settings if running frontend separately
3. Ensure `VITE_API_URL` is set correctly in frontend

## Processing Issues

### Document extraction fails

**Error**: "Failed to process document" or timeout

**Solutions**:
1. **Large PDFs**: Split into smaller files (< 50 pages recommended)
2. **Scanned PDFs**: Ensure OCR layer exists; Prism uses text extraction
3. **Corrupted files**: Try opening the file locally first
4. **API limits**: Check Azure OpenAI rate limits

Check extraction logs:
```bash
# View container logs with debug logging
docker-compose -f infra/docker/docker-compose.yml logs backend
```

### Extraction status shows "failed"

**Solution**:
1. Check extraction status in the Pipeline view for error details
2. Use "Re-run" button to force re-extraction
3. Check Azure OpenAI service health

### Pipeline step stuck or slow

**Solutions**:
1. **Embedding step slow**: Large documents take time; check progress in logs
2. **Index upload failing**: Check Azure AI Search service tier limits
3. **Memory issues**: Increase Docker memory limit or process fewer documents

## Query Issues

### Poor or irrelevant answers

**Solutions**:
1. **Verify indexing completed**: Check all pipeline steps are green
2. **Check document content**: Ensure documents contain the information
3. **Rephrase question**: Try more specific queries
4. **Add instructions**: Use workflow questions with detailed instructions

### "No results found" error

**Solutions**:
1. Verify search index exists:
   ```bash
   az search index list --service-name <search-name> --resource-group <rg>
   ```
2. Re-run "Index Upload" step
3. Check if documents were properly chunked and embedded

### Citations not showing

**Solution**:
1. Ensure extraction produced proper source references
2. Check chunk metadata includes document names
3. Verify search results include source fields

## Authentication Issues

### Can't login to UI

**Solutions**:
1. Get the current password:
   ```bash
   az containerapp secret show --name prism-backend --resource-group <rg> --secret-name auth-password --query value -o tsv
   ```
2. For local development, check `AUTH_PASSWORD` in `.env`
3. Clear browser cache/cookies

### API returns 401 Unauthorized

**Solutions**:
1. Include auth token in requests
2. Check password hasn't changed
3. For development, verify auth is configured in backend

## Azure Service Issues

### Azure OpenAI errors

**Error**: `RateLimitExceeded`

**Solution**:
- Wait and retry (exponential backoff is built-in)
- Request higher quota
- Use a different deployment

**Error**: `InvalidRequest` or `ContentFilterError`

**Solution**:
- Document may contain content blocked by Azure content filters
- Review and clean document content

### Azure AI Search errors

**Error**: `IndexNotFound`

**Solution**: Run "Index Create" step before "Index Upload"

**Error**: `ServiceUnavailable`

**Solution**:
- Check Azure AI Search service health
- May need to upgrade service tier for higher availability

## Getting More Help

1. **Enable debug logging**:
   ```bash
   export PRISM_LOG_LEVEL=DEBUG
   ```

2. **Check all logs**:
   ```bash
   # Docker logs
   docker-compose -f infra/docker/docker-compose.yml logs

   # Azure logs
   az containerapp logs show --name prism-backend --resource-group <rg>
   ```

3. **API documentation**: Visit http://localhost:8000/docs for interactive API docs

4. **Open an issue**: [GitHub Issues](../../issues) with:
   - Error message
   - Steps to reproduce
   - Relevant logs (redact secrets)
