from rest_framework import pagination
from rest_framework.response import Response


class CustomPagination(pagination.PageNumberPagination):
    page_size = 10
    page_query_param = "page"
    page_size_query_param = "per_page"
    max_page_size = 100

    def get_paginated_response(self, data):
        return Response(
            {
                "success": True,
                "message": "OK",
                "results": data,
                "total_count": self.page.paginator.count,
                "page": self.page.number,
                "page_count": self.page.paginator.num_pages,
                "per_page": self.page.paginator.per_page,
            }
        )
