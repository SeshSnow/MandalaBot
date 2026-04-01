"""
Tenant isolation package for multi-tenant Mandala deployments.

Each Shopify store (shop domain) is an isolated tenant. The tenant context
is extracted from the X-Shopify-Shop-Domain request header and stored in a
ContextVar for the duration of each request.
"""
