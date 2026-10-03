from rest_framework.pagination import PageNumberPagination


class StandardPagination(PageNumberPagination):
    """Default 25 per page; clients may ask for up to 200 with ?page_size=N."""

    page_size = 25
    page_size_query_param = "page_size"
    max_page_size = 200
