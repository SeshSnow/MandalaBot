"""
Centralized GraphQL queries for Shopify Admin API.
"""

GET_SHOP_DOMAIN = """
query {
  shop {
    id
    myshopifyDomain
    name
    primaryDomain {
      host
      url
    }
  }
}
"""

GET_PRODUCT_TAGS = """
query getProductTags($first: Int!, $after: String) {
  products(first: $first, after: $after) {
    pageInfo {
      hasNextPage
      endCursor
    }
    edges {
      node {
        id
        tags
      }
    }
  }
}
"""

GET_PRODUCT_TYPES = """
query getProductTypes($first: Int!, $after: String) {
  products(first: $first, after: $after) {
    pageInfo {
      hasNextPage
      endCursor
    }
    edges {
      node {
        id
        productType
      }
    }
  }
}
"""

GET_PRODUCT_TYPES_AND_TAGS = """
query getProductTypesAndTags($first: Int!, $after: String) {
  products(first: $first, after: $after) {
    pageInfo {
      hasNextPage
      endCursor
    }
    edges {
      node {
        productType
        tags
      }
    }
  }
}
"""

GET_TOP_SELLING_PRODUCTS = """
query getTopSellingProducts($first: Int!) {
  products(first: $first, sortKey: INVENTORY_TOTAL, reverse: false) {
    edges {
      node {
        title
        description
        priceRangeV2 {
          minVariantPrice {
            amount
            currencyCode
          }
          maxVariantPrice {
            amount
            currencyCode
          }
        }
      }
    }
  }
}
"""

GET_COLLECTIONS = """
query getCollections($first: Int!, $productsFirst: Int!) {
  collections(first: $first) {
    edges {
      node {
        id
        title
        handle
        description
        image {
          url
          altText
        }
        productsCount {
          count
        }
        products(first: $productsFirst) {
          edges {
            node {
              id
              title
              handle
              productType
              tags
            }
          }
        }
        updatedAt
      }
    }
  }
}
"""

GET_APP_SUBSCRIPTION = """
query appSubscription($id: ID!) {
  appSubscription(id: $id) {
    id
    name
    status
    currentPeriodEnd
    lineItems {
      id
      plan {
        pricingDetails {
          ... on AppRecurringPricing {
            price {
              amount
              currencyCode
            }
            interval
          }
        }
      }
    }
    test
  }
}
"""
