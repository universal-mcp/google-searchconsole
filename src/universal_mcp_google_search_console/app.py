from typing import Any, List, Dict, Callable

from googleapiclient.discovery import build
from googleapiclient.errors import HttpError # For handling API errors
from google.oauth2.credentials import Credentials as UserCredentials # For type hinting and _get_client

from loguru import logger # Assuming loguru is used in your project

# Assuming these base classes are defined in your project structure
from universal_mcp.applications.application import APIApplication
from universal_mcp.integrations import Integration # Expected to be AgentRIntegration
from universal_mcp.exceptions import NotAuthorizedError # Your custom exception

class GoogleSearchConsoleApp(APIApplication):
    """
    Application for interacting with the Google Search Console API
    to query analytics, inspect URLs, manage sitemaps, etc.
    This application uses the google-api-python-client library, which dynamically
    builds the service object based on the Search Console API's discovery document.
    Requires Google API credentials (OAuth 2.0) managed by an Integration class
    (expected to be AgentRIntegration for OAuth flows).
    """

    def __init__(self, integration: Integration | None = None) -> None:
        super().__init__(name="google_search_console", integration=integration)
        # Scopes required by the Google Search Console API
        self.scopes = ['https://www.googleapis.com/auth/webmasters']
        logger.info(
            f"Initialized GoogleSearchConsoleApp with integration: {integration.name if integration else 'None'}"
        )

    def _get_client(self) -> Any: # Returns a googleapiclient.discovery.Resource object
        """
        Initializes and returns the Google Search Console API client (service object).
        This method uses the `googleapiclient.discovery.build` function, powered by
        the SDK files you provided. It relies on the Integration object (expected to
        be AgentRIntegration for OAuth) to provide Google API credentials obtained via AgentR.
        """
        if not self.integration:
            logger.error("Integration not provided. Cannot initialize Google Search Console client.")
            raise ValueError("Integration not provided. Cannot initialize Google Search Console client.")

        logger.debug(
            f"Attempting to get credentials via integration: {self.integration.name} of type {type(self.integration)}"
        )

        try:
            # self.integration.get_credentials() is expected to return a dictionary
            # from AgentRIntegration, containing OAuth 2.0 credential components.
            creds_dict = self.integration.get_credentials()
            logger.debug(f"Raw credentials dictionary received from integration '{self.integration.name}'.")
        except NotAuthorizedError as e:
            logger.error(f"Integration '{self.integration.name}' reported not authorized: {e}")
            raise
        except Exception as e:
            logger.error(
                f"Failed to get credentials from integration '{self.integration.name}': {type(e).__name__} - {e}"
            )
            raise RuntimeError(
                f"Failed to get credentials from integration '{self.integration.name}': {type(e).__name__} - {e}"
            )

        if not isinstance(creds_dict, dict):
            logger.error(
                f"Expected a dictionary from integration.get_credentials(), got {type(creds_dict)}"
            )
            raise ValueError(
                f"Expected a dictionary from integration.get_credentials(), got {type(creds_dict)}"
            )

        # Construct google.oauth2.credentials.Credentials object
        # Expected keys from AgentR: 'access_token', 'refresh_token', 'client_id', 'client_secret', 'token_uri'
        # The google-api-python-client library expects 'token' for access_token.
        credential_key_map = {
            "token": creds_dict.get("access_token") or creds_dict.get("token"),
            "refresh_token": creds_dict.get("refresh_token"),
            "token_uri": creds_dict.get("token_uri") or creds_dict.get("token_url", "https://oauth2.googleapis.com/token"),
            "client_id": creds_dict.get("client_id"),
            "client_secret": creds_dict.get("client_secret"),
            "scopes": self.scopes # Use scopes defined by this app
        }

        # Filter out None values to avoid passing them to UserCredentials constructor if not set
        google_creds_params = {k: v for k, v in credential_key_map.items() if v is not None}

        if "token" not in google_creds_params:
            msg = ("Missing 'access_token' (or 'token') in credentials from AgentR integration. "
                   "This is required to build Google API credentials.")
            logger.error(msg)
            raise ValueError(msg)
        
        if "client_id" not in google_creds_params or "client_secret" not in google_creds_params:
             logger.warning("Missing 'client_id' or 'client_secret' in credentials. Token refresh might fail.")


        try:
            credentials = UserCredentials(**google_creds_params)
            logger.info(f"Successfully created Google UserCredentials for integration '{self.integration.name}'.")
        except Exception as e:
            logger.error(
                f"Failed to create Google OAuth2 credentials from data provided by AgentR: {type(e).__name__} - {e}"
            )
            raise ValueError(
                f"Failed to create Google OAuth2 credentials from data provided by AgentR: {type(e).__name__} - {e}"
            )

        try:
            # The core of the SDK usage: discovery.build dynamically creates the service.
            # cache_discovery=False is often recommended for long-running server applications
            # to ensure the latest API definition is used, though True can improve performance.
            service = build('searchconsole', 'v1', credentials=credentials, cache_discovery=True)
            logger.info(f"Google Search Console service client (v1) built successfully for integration '{self.integration.name}'.")
            return service
        except HttpError as e: # Errors during discovery document fetch itself
            logger.error(f"Google API HTTP Error while building service client: {e.resp.status} - {e._get_reason()}")
            if e.resp.status in [401, 403]:
                 raise NotAuthorizedError(f"Google API authorization failed during service build: {e.resp.status} - {e._get_reason()}")
            raise RuntimeError(f"Google API HTTP Error while building service client: {e.resp.status} - {e._get_reason()}")
        except Exception as e: # Other errors like issues with google.auth or discovery URI
            logger.error(f"Failed to build Google Search Console service client: {type(e).__name__} - {e}")
            raise RuntimeError(f"Failed to build Google Search Console service client: {type(e).__name__} - {e}")

    def list_sites(self) -> Dict[str, Any] | str:
        """
        Lists all sites (properties) accessible to the authenticated user.
        This uses the `sites().list().execute()` pattern from the dynamically built service.

        Returns:
            A dictionary containing the list of sites ('siteEntry' key) on success,
            or a string containing an error message on failure.

        Tags:
            sites, list, important
        """
        logger.info("Attempting to list sites.")
        try:
            client = self._get_client()
            # The SDK's discovery.py dynamically creates .sites().list() which returns an HttpRequest
            request = client.sites().list()
            response = request.execute()
            logger.info(f"Successfully listed sites. Found {len(response.get('siteEntry', []))} sites.")
            return response
        except HttpError as e:
            error_msg = (f"Google API HTTP Error listing sites: {e.resp.status} - {e._get_reason()}. "
                         f"Details: {getattr(e, 'error_details', 'N/A')}")
            logger.error(error_msg)
            return error_msg
        except Exception as e:
            error_msg = f"Error listing sites: {type(e).__name__} - {e}"
            logger.error(error_msg)
            return error_msg

    def query_search_analytics(
        self, site_url: str, start_date: str, end_date: str, dimensions: List[str],
        search_type: str | None = None, row_limit: int = 1000, start_row: int = 0,
        dimension_filter_groups: List[Dict[str, Any]] | None = None,
        aggregation_type: str | None = None, data_state: str | None = None
    ) -> Dict[str, Any] | str:
        """
        Queries search analytics data for a given site.
        Uses `searchanalytics().query(siteUrl=..., body=...).execute()`.

        Args:
            site_url: The URL of the site (e.g., "sc-domain:example.com" or "https://www.example.com/").
            start_date: Start date of the period in YYYY-MM-DD format.
            end_date: End date of the period in YYYY-MM-DD format.
            dimensions: List of dimensions to group by (e.g., ['date', 'query', 'page']).
            search_type: Optional. The search type to filter by (e.g., 'web', 'image', 'video', 'news', 'discover', 'googleNews').
            row_limit: Optional. Number of rows to return. Default is 1000. Max 25000.
            start_row: Optional. Zero-based index of the first row to return. Default is 0.
            dimension_filter_groups: Optional. Filters to apply to dimensions.
            aggregation_type: Optional. How data is aggregated. (e.g., 'auto', 'byPage', 'byProperty').
            data_state: Optional. Filter by data state (e.g., 'all', 'final'). 'final' for fresh data.

        Returns:
            A dictionary containing the search analytics data on success,
            or a string containing an error message on failure.

        Tags:
            analytics, query, important
        """
        logger.info(f"Querying search analytics for site: {site_url}, from {start_date} to {end_date}.")
        try:
            client = self._get_client()
            request_body: Dict[str, Any] = {
                'startDate': start_date,
                'endDate': end_date,
                'dimensions': dimensions,
                'rowLimit': row_limit,
                'startRow': start_row,
            }
            if search_type:
                request_body['searchType'] = search_type
            if dimension_filter_groups:
                request_body['dimensionFilterGroups'] = dimension_filter_groups
            if aggregation_type:
                request_body['aggregationType'] = aggregation_type
            if data_state:
                request_body['dataState'] = data_state

            # siteUrl is a path parameter for the query method, body contains other params.
            request = client.searchanalytics().query(siteUrl=site_url, body=request_body)
            response = request.execute()
            logger.info(f"Successfully queried search analytics for '{site_url}'. Response rows: {len(response.get('rows', []))}")
            return response
        except HttpError as e:
            error_msg = (f"Google API HTTP Error querying search analytics for '{site_url}': "
                         f"{e.resp.status} - {e._get_reason()}. Details: {getattr(e, 'error_details', 'N/A')}")
            logger.error(error_msg)
            return error_msg
        except Exception as e:
            error_msg = f"Error querying search analytics for '{site_url}': {type(e).__name__} - {e}"
            logger.error(error_msg)
            return error_msg

    def inspect_url(
        self, site_url: str, inspection_url: str, language_code: str | None = None
    ) -> Dict[str, Any] | str:
        """
        Runs a URL inspection for the given URL using the Index Inspection API.
        Uses `urlInspection().index().inspect(body=...).execute()`.

        Args:
            site_url: The site URL as defined in Search Console (e.g., "sc-domain:example.com" or "https://www.example.com/").
            inspection_url: The specific URL to inspect (must be under site_url).
            language_code: Optional. The language code for the inspection (e.g., "en-US").

        Returns:
            A dictionary containing the URL inspection results on success,
            or a string containing an error message on failure.

        Tags:
            inspection, url, important
        """
        logger.info(f"Inspecting URL: {inspection_url} under site: {site_url}.")
        try:
            client = self._get_client()
            request_body: Dict[str, Any] = {
                'inspectionUrl': inspection_url,
                'siteUrl': site_url
            }
            if language_code:
                request_body['languageCode'] = language_code

            # The .index() here is part of the resource path for this specific API method.
            request = client.urlInspection().index().inspect(body=request_body)
            response = request.execute()
            logger.info(f"Successfully inspected URL '{inspection_url}'.")
            return response
        except HttpError as e:
            error_msg = (f"Google API HTTP Error inspecting URL '{inspection_url}': "
                         f"{e.resp.status} - {e._get_reason()}. Details: {getattr(e, 'error_details', 'N/A')}")
            logger.error(error_msg)
            return error_msg
        except Exception as e:
            error_msg = f"Error inspecting URL '{inspection_url}': {type(e).__name__} - {e}"
            logger.error(error_msg)
            return error_msg

    def list_sitemaps(self, site_url: str) -> Dict[str, Any] | str:
        """
        Lists the sitemaps submitted for a site.
        Uses `sitemaps().list(siteUrl=...).execute()`.

        Args:
            site_url: The URL of the site.

        Returns:
            A dictionary containing the list of sitemaps ('sitemap' key) on success,
            or a string containing an error message on failure.

        Tags:
            sitemaps, list
        """
        logger.info(f"Listing sitemaps for site: {site_url}.")
        try:
            client = self._get_client()
            request = client.sitemaps().list(siteUrl=site_url)
            response = request.execute()
            logger.info(f"Successfully listed sitemaps for '{site_url}'. Found {len(response.get('sitemap', []))} sitemaps.")
            return response
        except HttpError as e:
            error_msg = (f"Google API HTTP Error listing sitemaps for '{site_url}': "
                         f"{e.resp.status} - {e._get_reason()}. Details: {getattr(e, 'error_details', 'N/A')}")
            logger.error(error_msg)
            return error_msg
        except Exception as e:
            error_msg = f"Error listing sitemaps for '{site_url}': {type(e).__name__} - {e}"
            logger.error(error_msg)
            return error_msg

    def add_site(self, site_url: str) -> Dict[str, Any] | str:
        """
        Adds a site to the set of the user's sites in Search Console.
        This typically initiates the verification process for the site.
        Uses `sites().add(siteUrl=...).execute()`.
        Note: The API returns an empty response (204 No Content) on success.

        Args:
            site_url: The URL of the site to add (e.g., "https://www.example.com/").
                      For domain properties, use "sc-domain:example.com".

        Returns:
            A dictionary confirming success or a string containing an error message.

        Tags:
            sites, add, management, verification
        """
        logger.info(f"Attempting to add site: {site_url}.")
        try:
            client = self._get_client()
            # The siteUrl is a path parameter.
            # The 'add' method for sites doesn't typically take a request body
            # in the client library; it's a PUT to the resource URI.
            request = client.sites().add(siteUrl=site_url)
            request.execute()  # Returns None on 204 success
            success_msg = f"Site '{site_url}' added successfully. Please proceed with verification if needed."
            logger.info(success_msg)
            return {"status": "success", "message": success_msg}
        except HttpError as e:
            error_msg = (f"Google API HTTP Error adding site '{site_url}': "
                         f"{e.resp.status} - {e._get_reason()}. Details: {getattr(e, 'error_details', 'N/A')}")
            logger.error(error_msg)
            return error_msg
        except Exception as e:
            error_msg = f"Error adding site '{site_url}': {type(e).__name__} - {e}"
            logger.error(error_msg)
            return error_msg

    def delete_site(self, site_url: str) -> Dict[str, Any] | str:
        """
        Removes a site from the set of the user's Search Console sites.
        Uses `sites().delete(siteUrl=...).execute()`.
        Note: The API returns an empty response (204 No Content) on success.

        Args:
            site_url: The URL of the site to delete.

        Returns:
            A dictionary confirming success or a string containing an error message.

        Tags:
            sites, delete, management
        """
        logger.info(f"Attempting to delete site: {site_url}.")
        try:
            client = self._get_client()
            request = client.sites().delete(siteUrl=site_url)
            request.execute()  # Returns None on 204 success
            success_msg = f"Site '{site_url}' deleted successfully."
            logger.info(success_msg)
            return {"status": "success", "message": success_msg}
        except HttpError as e:
            error_msg = (f"Google API HTTP Error deleting site '{site_url}': "
                         f"{e.resp.status} - {e._get_reason()}. Details: {getattr(e, 'error_details', 'N/A')}")
            logger.error(error_msg)
            return error_msg
        except Exception as e:
            error_msg = f"Error deleting site '{site_url}': {type(e).__name__} - {e}"
            logger.error(error_msg)
            return error_msg

    def get_site(self, site_url: str) -> Dict[str, Any] | str:
        """
        Retrieves information about a specific site, including its verification status.
        Uses `sites().get(siteUrl=...).execute()`.

        Args:
            site_url: The URL of the site to retrieve information for.

        Returns:
            A dictionary containing the site information (Site resource) on success,
            or a string containing an error message on failure.

        Tags:
            sites, get, verification
        """
        logger.info(f"Attempting to get site information for: {site_url}.")
        try:
            client = self._get_client()
            request = client.sites().get(siteUrl=site_url)
            response = request.execute()
            logger.info(f"Successfully retrieved information for site '{site_url}'.")
            return response
        except HttpError as e:
            error_msg = (f"Google API HTTP Error getting site '{site_url}': "
                         f"{e.resp.status} - {e._get_reason()}. Details: {getattr(e, 'error_details', 'N/A')}")
            logger.error(error_msg)
            return error_msg
        except Exception as e:
            error_msg = f"Error getting site '{site_url}': {type(e).__name__} - {e}"
            logger.error(error_msg)
            return error_msg

    def submit_sitemap(self, site_url: str, feed_path: str) -> Dict[str, Any] | str:
        """
        Submits a sitemap for a site.
        Uses `sitemaps().submit(siteUrl=..., feedpath=...).execute()`.
        Note: The API returns an empty response (204 No Content) on success.

        Args:
            site_url: The URL of the site.
            feed_path: The full URL of the sitemap to submit (e.g., "https://www.example.com/sitemap.xml").

        Returns:
            A dictionary confirming success or a string containing an error message.

        Tags:
            sitemaps, submit, management
        """
        logger.info(f"Submitting sitemap: {feed_path} for site: {site_url}.")
        try:
            client = self._get_client()
            # siteUrl and feedpath are path parameters for this method.
            request = client.sitemaps().submit(siteUrl=site_url, feedpath=feed_path)
            request.execute() # Returns None on 204 success
            success_msg = f"Sitemap '{feed_path}' submitted successfully for site '{site_url}'."
            logger.info(success_msg)
            return {"status": "success", "message": success_msg}
        except HttpError as e:
            error_msg = (f"Google API HTTP Error submitting sitemap '{feed_path}' for '{site_url}': "
                         f"{e.resp.status} - {e._get_reason()}. Details: {getattr(e, 'error_details', 'N/A')}")
            logger.error(error_msg)
            return error_msg
        except Exception as e:
            error_msg = f"Error submitting sitemap '{feed_path}' for '{site_url}': {type(e).__name__} - {e}"
            logger.error(error_msg)
            return error_msg

    def delete_sitemap(self, site_url: str, feed_path: str) -> Dict[str, Any] | str:
        """
        Deletes a sitemap from a site. This does not remove it from the web.
        Uses `sitemaps().delete(siteUrl=..., feedpath=...).execute()`.
        Note: The API returns an empty response (204 No Content) on success.

        Args:
            site_url: The URL of the site.
            feed_path: The full URL of the sitemap to delete.

        Returns:
            A dictionary confirming success or a string containing an error message.

        Tags:
            sitemaps, delete, management
        """
        logger.info(f"Deleting sitemap: {feed_path} for site: {site_url}.")
        try:
            client = self._get_client()
            request = client.sitemaps().delete(siteUrl=site_url, feedpath=feed_path)
            request.execute() # Returns None on 204 success
            success_msg = f"Sitemap '{feed_path}' deleted successfully for site '{site_url}'."
            logger.info(success_msg)
            return {"status": "success", "message": success_msg}
        except HttpError as e:
            error_msg = (f"Google API HTTP Error deleting sitemap '{feed_path}' for '{site_url}': "
                         f"{e.resp.status} - {e._get_reason()}. Details: {getattr(e, 'error_details', 'N/A')}")
            logger.error(error_msg)
            return error_msg
        except Exception as e:
            error_msg = f"Error deleting sitemap '{feed_path}' for '{site_url}': {type(e).__name__} - {e}"
            logger.error(error_msg)
            return error_msg
            
    def get_sitemap(self, site_url: str, feed_path: str) -> Dict[str, Any] | str:
        """
        Retrieves information about a specific sitemap.
        Uses `sitemaps().get(siteUrl=..., feedpath=...).execute()`.

        Args:
            site_url: The site's URL, including protocol. For example: `http://www.example.com/`.
            feed_path: The URL of the sitemap to retrieve. For example: `http://www.example.com/sitemap.xml`.

        Returns:
            A dictionary containing the sitemap information on success,
            or a string containing an error message on failure.

        Tags:
            sitemaps, get
        """
        logger.info(f"Getting sitemap: {feed_path} for site: {site_url}.")
        try:
            client = self._get_client()
            request = client.sitemaps().get(siteUrl=site_url, feedpath=feed_path)
            response = request.execute()
            logger.info(f"Successfully retrieved sitemap '{feed_path}'.")
            return response
        except HttpError as e:
            error_msg = (f"Google API HTTP Error getting sitemap '{feed_path}' for '{site_url}': "
                         f"{e.resp.status} - {e._get_reason()}. Details: {getattr(e, 'error_details', 'N/A')}")
            logger.error(error_msg)
            return error_msg
        except Exception as e:
            error_msg = f"Error getting sitemap '{feed_path}' for '{site_url}': {type(e).__name__} - {e}"
            logger.error(error_msg)
            return error_msg


    def list_tools(self) -> List[Callable[..., Dict[str, Any] | str]]:
        """Returns a list of methods exposed as tools, callable by the agent."""
        return [
            self.list_sites,
            self.add_site,   
            self.delete_site,
            self.get_site,
            self.query_search_analytics,
            self.inspect_url,
            self.list_sitemaps,
            self.submit_sitemap,
            self.delete_sitemap,
            self.get_sitemap, 
        ]