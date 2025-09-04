import boto3
import json
from botocore.exceptions import ClientError

class SecretsHelper:
    """
    A helper class to manage AWS Secrets Manager operations.
    """
    
    def __init__(self, region_name="us-east-1"):
        """
        Initialize the SecretsHelper with AWS region.
        
        Args:
            region_name (str, optional): AWS region name. Defaults to "us-east-1".
        """
        self.session = boto3.session.Session()
        self.client = self.session.client(
            service_name='secretsmanager',
            region_name=region_name
        )
        self.region_name = region_name
    
    def manage_secret(self, key, value, secret_name):
        """
        Manages an AWS secret by either retrieving, creating, or updating it.
        Always appends/updates the provided key-value pair.
        
        Args:
            key (str): The key to add to the secret
            value (str): The value to associate with the key
            secret_name (str): The name of the secret in AWS Secrets Manager
        
        Returns:
            bool: True if operation was successful, False otherwise
        """
        try:
            # Try to get the existing secret
            get_secret_response = self.client.get_secret_value(SecretId=secret_name)
            
            # Parse existing secret
            if 'SecretString' in get_secret_response:
                secret_data = json.loads(get_secret_response['SecretString'])
                print("Existing secret key/value pairs:")
                for k, v in secret_data.items():
                    print(f"  {k}: {v}")
            else:
                # Binary secrets are not supported in this function
                print("Binary secrets are not supported by this function")
                return False
            
            # Add or update the key-value pair
            if key in secret_data:
                print(f"Updating existing key '{key}' in the secret.")
            else:
                print(f"Adding new key '{key}' to the secret.")
                
            # Update the secret data with the new key-value pair
            secret_data[key] = value
            
            # Update the secret with the modified data
            self.client.update_secret(
                SecretId=secret_name,
                SecretString=json.dumps(secret_data)
            )
            print(f"Successfully added/updated key '{key}' in secret '{secret_name}'")
            
        except ClientError as e:
            error_code = e.response.get('Error', {}).get('Code', '')
            
            if error_code == 'ResourceNotFoundException':
                # Secret doesn't exist, create a new one
                print(f"Secret '{secret_name}' not found. Creating a new secret.")
                
                # Create a new secret with the provided key-value pair
                new_secret_data = {key: value}
                self.client.create_secret(
                    Name=secret_name,
                    SecretString=json.dumps(new_secret_data)
                )
                print(f"Successfully created secret '{secret_name}' with key '{key}'")
            else:
                # Handle other exceptions
                print(f"Error: {e}")
                return False
        
        return True
    
    def get_secret(self, secret_name):
        """
        Retrieves a secret from AWS Secrets Manager.
        
        Args:
            secret_name (str): The name of the secret to retrieve
            
        Returns:
            dict: The secret data as a dictionary, or None if not found
        """
        try:
            get_secret_response = self.client.get_secret_value(SecretId=secret_name)
            
            if 'SecretString' in get_secret_response:
                return json.loads(get_secret_response['SecretString'])
            else:
                print("Binary secrets are not supported by this function")
                return None
                
        except ClientError as e:
            print(f"Error retrieving secret: {e}")
            return None
    
    def delete_secret(self, secret_name, recovery_window_in_days=30):
        """
        Deletes a secret from AWS Secrets Manager.
        
        Args:
            secret_name (str): The name of the secret to delete
            recovery_window_in_days (int, optional): Number of days before permanent deletion.
                                                    Set to 0 for immediate deletion.
                                                    Defaults to 30.
                                                    
        Returns:
            bool: True if deletion was successful, False otherwise
        """
        try:
            self.client.delete_secret(
                SecretId=secret_name,
                RecoveryWindowInDays=recovery_window_in_days
            )
            print(f"Secret '{secret_name}' scheduled for deletion in {recovery_window_in_days} days")
            return True
        except ClientError as e:
            print(f"Error deleting secret: {e}")
            return False
