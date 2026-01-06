from typing import Any, Dict, List
from fastapi import HTTPException
import boto3
from botocore.exceptions import ClientError
from .base import DatabaseService


class DynamoDBService(DatabaseService):
    """DynamoDB implementation of the DatabaseService."""

    def __init__(self, region_name: str = None, endpoint_url: str = None, aws_access_key_id: str = None, aws_secret_access_key: str = None):
        """
        Initialize DynamoDB service.

        Args:
            region_name: AWS region name (e.g., 'us-east-1')
            endpoint_url: Optional endpoint URL for local DynamoDB
            aws_access_key_id: Optional AWS access key ID
            aws_secret_access_key: Optional AWS secret access key
        """
        try:
            # Create DynamoDB client
            client_kwargs = {}
            if region_name:
                client_kwargs['region_name'] = region_name
            if endpoint_url:
                client_kwargs['endpoint_url'] = endpoint_url
            if aws_access_key_id:
                client_kwargs['aws_access_key_id'] = aws_access_key_id
            if aws_secret_access_key:
                client_kwargs['aws_secret_access_key'] = aws_secret_access_key

            self.dynamodb = boto3.resource('dynamodb', **client_kwargs)
            self.client = boto3.client('dynamodb', **client_kwargs)
            print(f"Successfully connected to DynamoDB{' (local)' if endpoint_url else ''}.")
        except Exception as e:
            print(f"Failed to connect to DynamoDB: {e}")
            raise ConnectionError(f"Could not connect to DynamoDB: {e}") from e

    def _get_or_create_table(self, table_name: str):
        """Get existing table or create a new one with a simple schema."""
        try:
            table = self.dynamodb.Table(table_name)
            # Check if table exists by accessing its metadata
            table.load()
            return table
        except ClientError as e:
            if e.response['Error']['Code'] == 'ResourceNotFoundException':
                print(f"Table '{table_name}' not found. Creating it.")
                # Create table with simple schema: id as partition key
                table = self.dynamodb.create_table(
                    TableName=table_name,
                    KeySchema=[
                        {
                            'AttributeName': '_id',
                            'KeyType': 'HASH'  # Partition key
                        }
                    ],
                    AttributeDefinitions=[
                        {
                            'AttributeName': '_id',
                            'AttributeType': 'S'  # String
                        }
                    ],
                    BillingMode='PAY_PER_REQUEST'  # On-demand pricing
                )
                # Wait for table to be created
                table.meta.client.get_waiter('table_exists').wait(TableName=table_name)
                print(f"Table '{table_name}' created successfully.")
                return table
            else:
                raise

    def get(self, db_name: str, doc_id: str) -> Dict[str, Any]:
        table = self._get_or_create_table(db_name)
        try:
            response = table.get_item(Key={'_id': doc_id})
            if 'Item' not in response:
                raise HTTPException(status_code=404, detail=f"Document '{doc_id}' not found in '{db_name}'")
            return dict(response['Item'])
        except ClientError as e:
            if e.response['Error']['Code'] == 'ResourceNotFoundException':
                raise HTTPException(status_code=404, detail=f"Document '{doc_id}' not found in '{db_name}'")
            raise

    def save(self, db_name: str, doc_id: str, doc: Dict[str, Any]) -> Dict[str, Any]:
        table = self._get_or_create_table(db_name)
        try:
            # Ensure _id is set
            doc['_id'] = doc_id
            table.put_item(Item=doc)
            return {"id": doc_id, "rev": "dynamodb-rev"}
        except ClientError as e:
            raise HTTPException(status_code=500, detail=f"Failed to save document: {e}")

    def delete(self, db_name: str, doc_id: str):
        table = self._get_or_create_table(db_name)
        try:
            # First check if the item exists
            response = table.get_item(Key={'_id': doc_id})
            if 'Item' not in response:
                raise HTTPException(status_code=404, detail=f"Document '{doc_id}' not found for deletion.")

            # Delete the item
            table.delete_item(Key={'_id': doc_id})
        except ClientError as e:
            if e.response['Error']['Code'] == 'ResourceNotFoundException':
                raise HTTPException(status_code=404, detail=f"Document '{doc_id}' not found for deletion.")
            raise

    def list_all(self, db_name: str) -> List[Dict[str, Any]]:
        table = self._get_or_create_table(db_name)
        try:
            response = table.scan()
            items = response.get('Items', [])

            # Handle pagination if there are more items
            while 'LastEvaluatedKey' in response:
                response = table.scan(ExclusiveStartKey=response['LastEvaluatedKey'])
                items.extend(response.get('Items', []))

            return [dict(item) for item in items]
        except ClientError as e:
            raise HTTPException(status_code=500, detail=f"Failed to list documents: {e}")
