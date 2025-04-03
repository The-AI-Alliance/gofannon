Integration Tests are not currently functional

`test_boto3` - requires an AWS account and keys
`test_integrations` - Does work, but didn't fit into testing refactor as it 
tests interoperability between multiple frameworks
`test_mcp` fails on asyncio issues (it just hangs).
