# Endpoints

You can see the documentation for the actual API endpoints provided by Fates List via Swagger, Redoc or the raw OpenAPI schema (for those who just want the raw OpenAPI schema to plug into an API tester):

Redoc (recommended): [https://fateslist.xyz/api/docs/redoc](https://fateslist.xyz/api/docs/redoc)

Swagger: [https://fateslist.xyz/api/docs/swagger](https://fateslist.xyz/api/docs/swagger)

OpenAPI JSON: [https://fateslist.xyz/api/docs/openapi](https://fateslist.xyz/api/docs/openapi)

???+ warning
    **Do not use Swagger "Try It Out" to test the API as Swagger does not support Authorization headers unless it's a Bearer token or HTTP Basic Auth.**
    
    It is recommended to use (python) requests, (NodeJS) node-fetch or [reqbin](https://reqbin.com) though reqbin should be used as a **last resort** as it does not support DELETE requests with a request body.


These endpoints are subject to change over time. For information on the rest of the API and how to use the API, continue reading the API Documentation here. The above URLs cover all the endpoints while this documentation \(the main one\) just covers the additional things you need to know in order to read the above properly.
