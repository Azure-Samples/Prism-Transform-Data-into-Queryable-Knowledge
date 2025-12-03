# Monitoring

This guide covers monitoring and observability for Prism using Azure Application Insights.

## Overview

Prism includes built-in integration with Azure Application Insights for:
- Request tracing
- Error logging
- Performance metrics
- Custom events

## Setup

### Automatic Setup (azd)

When deploying with `azd up`, Application Insights is automatically provisioned and configured. The connection string is injected into the Container Apps environment.

### Manual Setup

1. Create Application Insights resource in Azure Portal
2. Add the connection string to your environment:

```bash
APPLICATIONINSIGHTS_CONNECTION_STRING=InstrumentationKey=xxx;IngestionEndpoint=https://xxx.in.applicationinsights.azure.com/
```

3. The backend automatically detects and uses this connection string.

## Viewing Logs

### Azure Portal

1. Navigate to your Application Insights resource
2. Use these views:
   - **Live Metrics**: Real-time request flow
   - **Failures**: Error analysis
   - **Performance**: Request latency
   - **Logs**: Query with KQL

### Common Queries

**Recent errors:**
```kusto
exceptions
| where timestamp > ago(1h)
| order by timestamp desc
| project timestamp, type, message, outerMessage
```

**Slow requests:**
```kusto
requests
| where timestamp > ago(24h)
| where duration > 5000
| order by duration desc
| project timestamp, name, duration, resultCode
```

**Request volume by endpoint:**
```kusto
requests
| where timestamp > ago(24h)
| summarize count() by name
| order by count_ desc
```

**Azure OpenAI calls:**
```kusto
dependencies
| where timestamp > ago(1h)
| where type == "HTTP"
| where target contains "openai"
| project timestamp, name, duration, resultCode
```

## Key Metrics

### Application Metrics

| Metric | Description | Alert Threshold |
|--------|-------------|-----------------|
| Request rate | Requests per second | Varies by load |
| Response time | P95 latency | > 5 seconds |
| Failed requests | Error rate | > 5% |
| Exceptions | Unhandled errors | Any |

### Azure Service Metrics

| Service | Key Metrics |
|---------|-------------|
| Azure OpenAI | Token usage, latency, throttling |
| Azure AI Search | Query latency, index size, throttling |
| Container Apps | CPU, memory, replica count |

## Alerts

### Setting Up Alerts

1. In Application Insights, go to **Alerts**
2. Click **Create alert rule**
3. Configure conditions:

**High Error Rate:**
- Metric: Failed requests
- Threshold: > 10 in 5 minutes
- Severity: 2 (Warning)

**High Latency:**
- Metric: Server response time
- Threshold: P95 > 10 seconds
- Severity: 3 (Informational)

**Service Unavailable:**
- Metric: Availability
- Threshold: < 99%
- Severity: 1 (Error)

### Alert Actions

Configure action groups to:
- Send email notifications
- Trigger webhooks
- Create incidents in ITSM tools

## Dashboards

### Creating a Dashboard

1. In Azure Portal, create a new Dashboard
2. Add tiles for:
   - Request rate (line chart)
   - Error rate (line chart)
   - P95 latency (line chart)
   - Top errors (table)
   - Active users (metric)

### Sample Dashboard Layout

```
┌─────────────────────┬─────────────────────┐
│   Request Rate      │   Error Rate        │
│   (last 24h)        │   (last 24h)        │
├─────────────────────┼─────────────────────┤
│   P95 Latency       │   Azure OpenAI      │
│   (last 24h)        │   Token Usage       │
├─────────────────────┴─────────────────────┤
│            Top Errors (table)             │
└───────────────────────────────────────────┘
```

## Logging Best Practices

### Log Levels

| Level | Use Case |
|-------|----------|
| ERROR | Exceptions, failures requiring attention |
| WARNING | Degraded behavior, retries |
| INFO | Key operations (start, complete) |
| DEBUG | Detailed troubleshooting (not in prod) |

### What to Log

**Do log:**
- Request start/end with correlation ID
- External service calls (OpenAI, Search)
- Document processing progress
- Authentication events
- Configuration changes

**Don't log:**
- Sensitive data (API keys, passwords)
- PII (user emails, document content)
- High-frequency debug info in production

### Correlation IDs

All requests include a correlation ID for tracing:
- Passed in headers across services
- Included in all log entries
- Used to trace end-to-end requests

## Troubleshooting with Logs

### Tracing a Request

1. Find the request in Application Insights
2. Copy the operation ID
3. Query all related logs:

```kusto
union traces, exceptions, dependencies, requests
| where operation_Id == "your-operation-id"
| order by timestamp asc
```

### Investigating Errors

1. Go to **Failures** view
2. Select the exception type
3. View the full stack trace
4. Check related dependencies

### Performance Analysis

1. Go to **Performance** view
2. Select slow operation
3. View the dependency calls
4. Identify bottlenecks (usually Azure OpenAI)

## Cost Considerations

Application Insights charges based on data ingestion. To optimize:

1. **Sampling**: Enable sampling for high-traffic apps
2. **Log levels**: Use INFO in production, not DEBUG
3. **Retention**: Set appropriate retention period
4. **Daily cap**: Configure a daily ingestion cap

## Local Development

For local development, logs go to console. To send to Application Insights:

```bash
export APPLICATIONINSIGHTS_CONNECTION_STRING="your-connection-string"
```

Or use a separate dev Application Insights instance.
