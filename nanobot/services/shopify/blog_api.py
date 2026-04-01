"""
API for managing Shopify blog articles.
"""

from typing import Any

from loguru import logger

from nanobot.services.shopify.graphql.blog_mutations import CREATE_ARTICLE, DELETE_ARTICLE
from nanobot.services.shopify.graphql.blog_queries import GET_CURRENT_STAFF_MEMBER, GET_SHOP_INFO
from nanobot.services.shopify.shopify_client import ShopifyClient


class BlogApi:
    """
    API for managing Shopify blog articles.
    Handles creation and deletion of blog articles.
    """

    def __init__(self, client: ShopifyClient):
        """
        Initialize with a Shopify client.

        Args:
            client: ShopifyClient instance.
        """
        self.client = client

    def _get_author_name(self) -> str:
        """
        Fetch the current user's full name from Shopify to use as the article author.

        Uses the staffMember query (current authenticated user). Falls back to shop name
        or domain if the request fails (e.g. missing read_users scope).

        Returns:
            The user's full name, or a fallback (shop name or domain).
        """
        try:
            result = self.client.execute_query(GET_CURRENT_STAFF_MEMBER)
            staff = result.get("staffMember")
            if staff:
                full_name = staff.get("name")
                if full_name:
                    logger.debug(f"Using current user as author: {full_name}")
                    return full_name
                first = staff.get("firstName") or ""
                last = staff.get("lastName") or ""
                if first or last:
                    name = f"{first} {last}".strip()
                    logger.debug(f"Using current user as author: {name}")
                    return name
        except Exception as e:
            logger.warning(f"Failed to fetch current staff member: {e}")

        # Fallback: shop name
        try:
            result = self.client.execute_query(GET_SHOP_INFO)
            shop_name = (result.get("shop") or {}).get("name")
            if shop_name:
                logger.debug(f"Using shop name as fallback author: {shop_name}")
                return shop_name
        except Exception as e:
            logger.warning(f"Failed to fetch shop info: {e}")

        # Last fallback: domain or "Admin"
        fallback = self.client.domain.split(".")[0] if self.client.domain else "Admin"
        logger.debug(f"Using fallback author name: {fallback}")
        return fallback

    def create_article_draft(
        self,
        blog_id: str,
        title: str,
        body_html: str,
        summary: str | None = None,
        tags: list[str] | None = None,
        author: str | None = None,
        draft: bool = True,
    ) -> dict[str, Any]:
        """
        Create a new Shopify blog article as a draft or published.

        Args:
            blog_id: The Shopify blog ID (GID format: gid://shopify/OnlineStoreBlog/{id}).
            title: The article title.
            body_html: The HTML content of the article body (Shopify API accepts HTML only).
            summary: Optional article summary/excerpt.
            tags: Optional list of tags.
            author: Optional author name. If not provided, uses the current user's full name.
            draft: If True, creates as draft (isPublished: False). If False, publishes immediately.

        Returns:
            Created article data including ID and admin URL.

        Raises:
            ValueError: If article creation fails.
        """
        logger.info(f"Creating Shopify blog article: {'draft' if draft else 'published'}: {title}")

        input_data: dict[str, Any] = {
            "blogId": blog_id,
            "title": title,
            "body": body_html,
            "isPublished": not draft,
        }

        if summary:
            input_data["summary"] = summary

        if tags:
            input_data["tags"] = tags

        author_name = author if author else self._get_author_name()
        input_data["author"] = {"name": author_name}
        logger.info(f"Setting article author to: {author_name}")

        variables = {"article": input_data}

        try:
            result = self.client.execute_query(CREATE_ARTICLE, variables)

            if result.get("articleCreate", {}).get("userErrors"):
                errors = result["articleCreate"]["userErrors"]
                error_message = "; ".join([f"{e.get('field')}: {e.get('message')}" for e in errors])
                raise ValueError(f"Failed to create article: {error_message}")

            article = result["articleCreate"]["article"]

            raw_id = article.get("id") or ""
            article_id = str(raw_id).replace("gid://shopify/Article/", "").strip()
            shop_domain = self.client.domain or ""
            store_handle = shop_domain.split(".")[0] if shop_domain else "admin"
            admin_url = f"https://admin.shopify.com/store/{store_handle}/content/articles/{article_id}" if article_id and store_handle else None
            if admin_url:
                logger.success(f"Created article draft: {admin_url}")

            return {
                "id": article.get("id"),
                "title": article.get("title"),
                "handle": article.get("handle"),
                "adminUrl": admin_url,
            }
        except Exception as e:
            logger.error(f"Article creation failed: {str(e)}")
            raise ValueError(f"Failed to create article: {str(e)}") from e

    def delete_article(self, article_id: str) -> bool:
        """
        Delete a Shopify blog article.

        Args:
            article_id: The Shopify article ID in GID format.

        Returns:
            Success status (True if successful).

        Raises:
            ValueError: If article deletion fails.
        """
        logger.info(f"Deleting Shopify blog article: {article_id}")

        variables = {"id": article_id}

        try:
            result = self.client.execute_query(DELETE_ARTICLE, variables)

            if result.get("articleDelete", {}).get("userErrors"):
                errors = result["articleDelete"]["userErrors"]
                error_message = "; ".join([f"{e.get('field')}: {e.get('message')}" for e in errors])
                raise ValueError(f"Failed to delete article: {error_message}")

            logger.success(f"Deleted article: {article_id}")
            return True
        except Exception as e:
            logger.error(f"Article deletion failed: {str(e)}")
            raise ValueError(f"Failed to delete article: {str(e)}") from e
