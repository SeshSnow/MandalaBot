"""
GraphQL mutations for Shopify blog article operations.
"""

CREATE_ARTICLE = """
mutation articleCreate($article: ArticleCreateInput!) {
  articleCreate(article: $article) {
    article {
      id
      title
      handle
    }
    userErrors {
      field
      message
    }
  }
}
"""

UPDATE_ARTICLE = """
mutation articleUpdate($id: ID!, $article: ArticleUpdateInput!) {
  articleUpdate(id: $id, article: $article) {
    article {
      id
      title
      handle
    }
    userErrors {
      field
      message
    }
  }
}
"""

DELETE_ARTICLE = """
mutation articleDelete($id: ID!) {
  articleDelete(id: $id) {
    deletedArticleId
    userErrors {
      field
      message
    }
  }
}
"""
