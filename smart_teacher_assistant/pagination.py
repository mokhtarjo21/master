"""
Custom Pagination Classes
"""
from rest_framework.pagination import PageNumberPagination


class StandardResultsSetPagination(PageNumberPagination):
    """
    Standard pagination with 50 items per page
    """
    page_size = 50
    page_size_query_param = 'page_size'
    max_page_size = 100


class LargeResultsSetPagination(PageNumberPagination):
    """
    Pagination for large datasets with 100 items per page
    """
    page_size = 100
    page_size_query_param = 'page_size'
    max_page_size = 200


class SmallResultsSetPagination(PageNumberPagination):
    """
    Pagination for small datasets with 20 items per page
    """
    page_size = 20
    page_size_query_param = 'page_size'
    max_page_size = 50
