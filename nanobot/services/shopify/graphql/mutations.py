"""
GraphQL mutations for Shopify app subscription operations.
"""

CREATE_APP_SUBSCRIPTION = """
mutation appSubscriptionCreate($name: String!, $lineItems: [AppSubscriptionLineItemInput!]!, $returnUrl: URL!, $trialDays: Int, $test: Boolean) {
  appSubscriptionCreate(
    name: $name
    lineItems: $lineItems
    returnUrl: $returnUrl
    trialDays: $trialDays
    test: $test
  ) {
    appSubscription {
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
      returnUrl
      test
    }
    confirmationUrl
    userErrors {
      field
      message
    }
  }
}
"""

CANCEL_APP_SUBSCRIPTION = """
mutation appSubscriptionCancel($id: ID!) {
  appSubscriptionCancel(id: $id) {
    appSubscription {
      id
      status
    }
    userErrors {
      field
      message
    }
  }
}
"""
