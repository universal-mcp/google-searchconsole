import urllib.parse
from typing import Any, Optional, List, Dict # Changed from dict to Dict for older Pythons, but dict is fine for 3.9+

from universal_mcp.applications import APIApplication
from universal_mcp.integrations import Integration
import logging

logger = logging.getLogger(__name__)


class GoogleSearchconsoleApp(APIApplication):
    def __init__(self, integration: Integration = None, **kwargs) -> None:
        super().__init__(name='google-searchconsole', integration=integration, **kwargs)
        self.webmasters_base_url = "https://www.googleapis.com/webmasters/v3"
        self.searchconsole_base_url = "https://searchconsole.googleapis.com/v1"

    def delete_sitemap(self, siteUrl: str, feedpath: str) -> None:
        """
        Deletes a sitemap from this site. Typically returns HTTP 204 No Content on success.

        Args:
            siteUrl (str): The site's URL, including protocol (e.g. 'http://www.example.com/').
            feedpath (str): The URL of the sitemap to delete. Example: 'http://www.example.com/sitemap.xml'.

        Returns:
            None: If the request is successful.
        
        Tags:
            sitemap_management
        """
        # Encode URL parts used as path segments
        siteUrl_encoded = urllib.parse.quote(siteUrl, safe='')
        feedpath_encoded = urllib.parse.quote(feedpath, safe='')
        
        url = f"{self.webmasters_base_url}/sites/{siteUrl_encoded}/sitemaps/{feedpath_encoded}"
        response = self._delete(url)
        response.raise_for_status()
        return None

    def get_sitemap(self, siteUrl: str, feedpath: str) -> Dict[str, Any]:
        """
        Retrieves information about a specific sitemap.

        Args:
            siteUrl (str): The site's URL, including protocol (e.g. 'http://www.example.com/').
            feedpath (str): The URL of the sitemap to retrieve. Example: 'http://www.example.com/sitemap.xml'.

        Returns:
            Dict[str, Any]: Sitemap resource.
            
        Tags:
            sitemap_management
        """
        siteUrl_encoded = urllib.parse.quote(siteUrl, safe='')
        feedpath_encoded = urllib.parse.quote(feedpath, safe='')

        url = f"{self.webmasters_base_url}/sites/{siteUrl_encoded}/sitemaps/{feedpath_encoded}"
        response = self._get(url)
        response.raise_for_status()
        return response.json()

    def list_sitemaps(self, siteUrl: str, sitemapIndex: Optional[str] = None) -> Dict[str, Any]:
        """
        Lists the sitemaps-entries submitted for this site, or included in the sitemap index file 
        (if sitemapIndex is specified in the request).

        Args:
            siteUrl (str): The site's URL, including protocol (e.g. 'http://www.example.com/').
            sitemapIndex (Optional[str]): The URL of the sitemap index. 
                                          Example: 'http://www.example.com/sitemap_index.xml'.

        Returns:
            Dict[str, Any]: List of sitemap resources.
            
        Tags:
            sitemap_management, important
        """
        siteUrl_encoded = urllib.parse.quote(siteUrl, safe='')
        url = f"{self.webmasters_base_url}/sites/{siteUrl_encoded}/sitemaps"
        
        query_params = {}
        if sitemapIndex is not None:
            query_params['sitemapIndex'] = sitemapIndex
        
        response = self._get(url, params=query_params if query_params else None)
        response.raise_for_status()
        return response.json()

    def submit_sitemap(self, siteUrl: str, feedpath: str) -> None:
        """
        Submits a sitemap for a site. Typically returns HTTP 204 No Content on success.

        Args:
            siteUrl (str): The site's URL, including protocol (e.g. 'http://www.example.com/').
            feedpath (str): The URL of the sitemap to submit. Example: 'http://www.example.com/sitemap.xml'.

        Returns:
            None: If the request is successful.
            
        Tags:
            sitemap_management
        """
        siteUrl_encoded = urllib.parse.quote(siteUrl, safe='')
        feedpath_encoded = urllib.parse.quote(feedpath, safe='')

        url = f"{self.webmasters_base_url}/sites/{siteUrl_encoded}/sitemaps/{feedpath_encoded}"
        # PUT requests for submitting/notifying often don't have a body.
        response = self._put(url, data=None) 
        response.raise_for_status()
        return None

    # --- Sites ---

    def add_site(self, siteUrl: str) -> Dict[str, Any]:
        """
        Adds a site to the set of the user's sites in Search Console.
        This will require verification of the site ownership.
        If successful, this method returns a site resource in the response body.

        Args:
            siteUrl (str): The URL of the site to add. Example: 'http://www.example.com/'.

        Returns:
            Dict[str, Any]: Site resource upon successful addition.
            
        Tags:
            site_management, important
        """
        siteUrl_encoded = urllib.parse.quote(siteUrl, safe='')
        url = f"{self.webmasters_base_url}/sites/{siteUrl_encoded}"
        # This specific PUT for adding a site generally does not require a body;
        # the resource identifier is the siteUrl itself.
        # Google API docs state it returns a site resource.
        response = self._put(url, data=None)
        response.raise_for_status()
        return response.json()

    def delete_site(self, siteUrl: str) -> None:
        """
        Removes a site from the set of the user's Search Console sites.
        Typically returns HTTP 204 No Content on success.

        Args:
            siteUrl (str): The URL of the site to delete. Example: 'http://www.example.com/'.

        Returns:
            None: If the request is successful.
            
        Tags:
            site_management
        """
        siteUrl_encoded = urllib.parse.quote(siteUrl, safe='')
        url = f"{self.webmasters_base_url}/sites/{siteUrl_encoded}"
        response = self._delete(url)
        response.raise_for_status()
        return None

    def get_site(self, siteUrl: str) -> Dict[str, Any]:
        """
        Retrieves information about a specific site.

        Args:
            siteUrl (str): The site's URL, including protocol (e.g. 'http://www.example.com/').

        Returns:
            Dict[str, Any]: Site resource.
            
        Tags:
            site_management
        """
        siteUrl_encoded = urllib.parse.quote(siteUrl, safe='')
        url = f"{self.webmasters_base_url}/sites/{siteUrl_encoded}"
        response = self._get(url)
        response.raise_for_status()
        return response.json()

    def list_sites(self) -> Dict[str, Any]:
        """
        Lists the user's Search Console sites.

        Returns:
            Dict[str, Any]: List of site resources.
            
        Tags:
            site_management
        """
        url = f"{self.webmasters_base_url}/sites"
        response = self._get(url)
        response.raise_for_status()
        return response.json()

    # --- URL Inspection ---

    def index_inspect_url(self, inspectionUrl: str, siteUrl: str, languageCode: Optional[str] = None) -> Dict[str, Any]:
        """
        Inspects a URL in Google Index and provides information about its status.

        Args:
            inspectionUrl (str): The URL to inspect. Example: 'https://www.example.com/mypage'.
            siteUrl (str): The site URL (property) to inspect the URL under. 
                           Must be a property in Search Console. Example: 'sc-domain:example.com' or 'https://www.example.com/'.
            languageCode (Optional[str]): Optional. The BCP-47 language code for the inspection. Example: 'en-US'.

        Returns:
            Dict[str, Any]: Inspection result containing details about the URL's indexing status.
            
        Tags:
            url_inspection, indexing
        """
        url = f"{self.searchconsole_base_url}/urlInspection/index:inspect"
        request_body: Dict[str, Any] = {
            'inspectionUrl': inspectionUrl,
            'siteUrl': siteUrl,
        }
        if languageCode is not None:
            request_body['languageCode'] = languageCode
        
        # Assuming _post handles dict as JSON payload, similar to ExaApp
        response = self._post(url, data=request_body) 
        response.raise_for_status()
        return response.json()

    # --- Search Analytics ---
    
    def query_search_analytics(
        self,
        siteUrl: str,
        startDate: str,
        endDate: str,
        dimensions: Optional[List[str]] = None,
        dimensionFilterGroups: Optional[List[Dict[str, Any]]] = None,
        aggregationType: Optional[str] = None,
        rowLimit: Optional[int] = None,
        startRow: Optional[int] = None,
        dataState: Optional[str] = None,
        search_type: Optional[str] = None  # 'type' is a reserved keyword in Python
    ) -> Dict[str, Any]:
        """
        Queries your search traffic data with filters and parameters that you define.
        The method returns zero or more rows grouped by the row that you define.
        You must define a date range of one or more days.

        Args:
            siteUrl (str): The site's URL, including protocol (e.g. 'http://www.example.com/').
            startDate (str): Start date of the requested period in YYYY-MM-DD format.
            endDate (str): End date of the requested period in YYYY-MM-DD format.
            dimensions (Optional[List[str]]): List of dimensions to group the data by.
                Possible values: "date", "query", "page", "country", "device", "searchAppearance".
                Example: ["date", "query"].
            dimensionFilterGroups (Optional[List[Dict[str, Any]]]): Filter the results by dimensions.
                Example: [{
                    "groupType": "and",
                    "filters": [{
                        "dimension": "country",
                        "operator": "equals",
                        "expression": "USA"
                    }, {
                        "dimension": "device",
                        "operator": "equals",
                        "expression": "DESKTOP"
                    }]
                }]
            aggregationType (Optional[str]): How data is aggregated.
                Possible values: "auto", "byPage", "byProperty". Default is "auto".
            rowLimit (Optional[int]): The maximum number of rows to return. Default is 1000. Max 25000.
            startRow (Optional[int]): Zero-based index of the first row to return. Default is 0.
            dataState (Optional[str]): Whether to filter for fresh data or all data.
                Possible values: "all", "final". Default "all".
            search_type (Optional[str]): Filter by search type.
                Example: "web", "image", "video", "news", "discover", "googleNews".
                This corresponds to the 'type' parameter in the API.

        Returns:
            Dict[str, Any]: Search analytics data.
            
        Tags:
            search_analytics, reporting
        """
        siteUrl_encoded = urllib.parse.quote(siteUrl, safe='')
        url = f"{self.webmasters_base_url}/sites/{siteUrl_encoded}/searchAnalytics/query"

        request_body: Dict[str, Any] = {
            'startDate': startDate,
            'endDate': endDate,
        }
        if dimensions is not None:
            request_body['dimensions'] = dimensions
        if dimensionFilterGroups is not None:
            request_body['dimensionFilterGroups'] = dimensionFilterGroups
        if aggregationType is not None:
            request_body['aggregationType'] = aggregationType
        if rowLimit is not None:
            request_body['rowLimit'] = rowLimit
        if startRow is not None:
            request_body['startRow'] = startRow
        if dataState is not None:
            request_body['dataState'] = dataState
        if search_type is not None:
            request_body['type'] = search_type # API expects 'type'

        response = self._post(url, data=request_body)
        response.raise_for_status()
        return response.json()

    def list_tools(self):
        return [
            self.get_sitemap,
            self.list_sitemaps,
            self.submit_sitemap,
            self.delete_sitemap,
            self.get_site,
            self.list_sites,
            self.add_site,
            self.delete_site,
            self.index_inspect_url,
            self.query_search_analytics,
        ]