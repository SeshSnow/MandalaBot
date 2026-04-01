"""
GraphQL queries for Shopify blog operations.
"""

GET_BLOGS = """
query {
  blogs(first: 10) {
    edges {
      node {
        id
        title
        handle
      }
    }
  }
}
"""

GET_BLOG = """
query getBlog($id: ID!) {
  blog(id: $id) {
    id
    title
    handle
  }
}
"""

GET_CURRENT_STAFF_MEMBER = """
query {
  staffMember {
    name
    firstName
    lastName
  }
}
"""

GET_SHOP_INFO = """
query {
  shop {
    id
    name
    myshopifyDomain
    primaryDomain {
      host
      url
    }
  }
}
"""
