import json
import os
import uuid
import boto3

from collections import defaultdict

# Initialize the DynamoDB client
dynamodb = boto3.resource('dynamodb')
table_name = os.environ.get('TABLE_NAME')
table = dynamodb.Table(table_name)

# A dictionary to store the routes
routes = defaultdict(dict)


def route(path, http_method):
    """
    A decorator to register a function for a specific API path and method.
    """

    def decorator(func):
        routes[path][http_method] = func
        return func

    return decorator


def handle_errors(func):
    """
    A decorator to wrap a function with a consistent try/except block.
    """

    def wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except Exception as e:
            print(f"Error executing function: {str(e)}")
            return {
                'statusCode': 500,
                'body': json.dumps({'message': f'An internal error occurred: {str(e)}'})
            }

    return wrapper


@handle_errors
def lambda_handler(event, context):
    """
    Main handler for all API Gateway requests.
    Routes the request to the correct function using the registered decorators.
    """
    http_method = event.get('httpMethod')
    path = event.get('path')

    # Check for path parameters
    dynamic_path = None
    path_parameters = None
    if path.startswith('/projects/'):
        path_parts = path.split('/')
        if len(path_parts) == 3 and path_parts[1] == 'projects':
            dynamic_path = '/projects/{id}'
            path_parameters = {'id': path_parts[2]}

    # Find the correct handler based on the path and method
    handler_path = dynamic_path if dynamic_path else path
    handler = routes.get(handler_path, {}).get(http_method)

    if not handler:
        return {
            'statusCode': 404,
            'body': json.dumps({'message': 'Not Found'})
        }

    # Pass the event and extracted path parameters to the handler
    event['pathParameters'] = path_parameters
    return handler(event)


@route('/projects', 'POST')
def create_project(event):
    """Creates a new project item in DynamoDB."""
    body = json.loads(event.get('body'))
    item = {
        'id': str(uuid.uuid4()),
        'name': body.get('name'),
        'description': body.get('description'),
        'status': body.get('status'),
        'createdAt': body.get('createdAt')
    }
    table.put_item(Item=item)
    return {
        'statusCode': 201,
        'body': json.dumps(item)
    }


@route('/projects', 'GET')
def get_all_projects(event):
    """Retrieves all projects from DynamoDB."""
    response = table.scan()
    return {
        'statusCode': 200,
        'body': json.dumps(response['Items'])
    }


@route('/projects/{id}', 'GET')
def get_project_by_id(event):
    """Retrieves a single project by its ID."""
    project_id = event['pathParameters']['id']
    response = table.get_item(Key={'id': project_id})
    item = response.get('Item')
    if not item:
        return {
            'statusCode': 404,
            'body': json.dumps({'message': 'Project not found'})
        }
    return {
        'statusCode': 200,
        'body': json.dumps(item)
    }


@route('/projects/{id}', 'PUT')
def update_project(event):
    """Updates an existing project in DynamoDB."""
    project_id = event['pathParameters']['id']
    body = json.loads(event.get('body'))
    update_expression = "SET #n = :name, #d = :description, #s = :status"
    expression_attribute_names = {
        '#n': 'name',
        '#d': 'description',
        '#s': 'status'
    }
    expression_attribute_values = {
        ':name': body.get('name'),
        ':description': body.get('description'),
        ':status': body.get('status')
    }

    table.update_item(
        Key={'id': project_id},
        UpdateExpression=update_expression,
        ExpressionAttributeNames=expression_attribute_names,
        ExpressionAttributeValues=expression_attribute_values,
        ReturnValues="UPDATED_NEW"
    )
    return {
        'statusCode': 200,
        'body': json.dumps({'message': 'Project updated successfully'})
    }


@route('/projects/{id}', 'DELETE')
def delete_project(event):
    """Deletes a project from DynamoDB."""
    project_id = event['pathParameters']['id']
    table.delete_item(Key={'id': project_id})
    return {
        'statusCode': 200,
        'body': json.dumps({'message': 'Project deleted successfully'})
    }
